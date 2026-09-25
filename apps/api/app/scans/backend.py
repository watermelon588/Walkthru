"""Backend exposure check (todo P1.1): apps built with AI often talk to Supabase or Firebase straight from the browser,
so their data is only as safe as their row-level security or security rules.

Every plan: find the public config in the page and its bundles, and explain what it means.
Verified domains only: a read-only probe with the public key, as any visitor could run it. Row counts come from a HEAD
request (no row is ever fetched or shown), functions are listed but never called, nothing is written, and the probe stops
at 50 tables or 10 seconds. It only ever talks to the project's own *.supabase.co or Firebase host, never an address
taken from the page otherwise. Ideas from supabase-security-skill, vibeproof and rlsgate (MIT); no code copied.
"""

from __future__ import annotations

import base64
import json
import re
import time
from urllib.parse import urljoin

import httpx
from selectolax.parser import HTMLParser

from app.agent.schema import Finding
from app.scans import fetch

SUPABASE_URL = re.compile(r"https://([a-z0-9]{20})\.supabase\.co")
JWT = re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")
NEW_KEY = re.compile(r"\bsb_(publishable|secret)_[A-Za-z0-9_-]{20,}")
FIREBASE_DB = re.compile(r"https://([a-z0-9-]+)(?:-default-rtdb)?\.(firebaseio\.com|[a-z0-9-]+\.firebasedatabase\.app)")
FIREBASE_KEY = re.compile(r"AIza[0-9A-Za-z_-]{35}")
# Newer Supabase projects refuse to list tables to the public key, so also read the names the code itself uses.
FROM_CALL = re.compile(r"\.from\(\s*['\"`]([A-Za-z_][A-Za-z0-9_]{0,62})['\"`]")
RPC_CALL = re.compile(r"\.rpc\(\s*['\"`]([A-Za-z_][A-Za-z0-9_]{0,62})['\"`]")
MAX_TABLES, BUDGET_S, MAX_BUNDLES = 50, 10.0, 5


def _f(severity: str, title: str, detail: str, fix: str, evidence: str | None = None) -> Finding:
    return Finding(kind="security", severity=severity, title=title, detail=detail[:600], fix=fix[:400], evidence=(evidence or None) and evidence[:300])


def _role(jwt: str) -> str | None:
    try:
        payload = jwt.split(".")[1]
        return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))).get("role")
    except (ValueError, IndexError):
        return None


def sources(html: str, page_url: str, c: httpx.Client) -> str:
    """The homepage HTML plus up to five of its own script files: what any visitor's browser downloads anyway."""
    base = fetch.origin(page_url)
    texts = [html]
    for s in HTMLParser(html).css("script[src]")[:20]:
        src = urljoin(page_url, s.attributes.get("src") or "")
        if src.startswith(base) and len(texts) <= MAX_BUNDLES:
            r = fetch.get(c, src, same_origin=base)
            if r is not None and r.status_code == 200:
                texts.append(r.text[:3_000_000])
    return "\n".join(texts)


def find_config(text: str) -> dict:
    """Supabase project and keys, Firebase database and key, as they appear in the page's own code."""
    project = SUPABASE_URL.search(text)
    jwts = {m.group(0): _role(m.group(0)) for m in JWT.finditer(text)}
    new_keys = {m.group(0): m.group(1) for m in NEW_KEY.finditer(text)}
    anon = next((k for k, r in jwts.items() if r == "anon"), None) or next((k for k, r in new_keys.items() if r == "publishable"), None)
    secret = next((k for k, r in jwts.items() if r == "service_role"), None) or next((k for k, r in new_keys.items() if r == "secret"), None)
    firebase = FIREBASE_DB.search(text)
    return {"supabase": project.group(0) if project else None, "anon_key": anon, "secret_key": secret,
            "firebase_db": firebase.group(0) if firebase else None, "firebase_key": bool(FIREBASE_KEY.search(text)),
            "tables": list(dict.fromkeys(FROM_CALL.findall(text))), "rpcs": list(dict.fromkeys(RPC_CALL.findall(text)))}


def rls_sql(tables: list[str]) -> str:
    lines = []
    for t in tables:
        lines += [f"alter table public.{t} enable row level security;",
                  f'create policy "owners read {t}" on public.{t} for select to authenticated using (user_id = (select auth.uid()));  -- use your owner column']
    return "\n".join(lines)


def probe_supabase(project: str, key: str, c: httpx.Client, deadline: float, named_tables: list[str] = (), named_rpcs: list[str] = ()) -> list[Finding]:
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    out: list[Finding] = []
    spec = c.get(f"{project}/rest/v1/", headers=headers, timeout=5)
    paths = list((spec.json().get("paths") or {}) if spec.status_code == 200 else {})
    listed = [p.strip("/") for p in paths if p.count("/") == 1 and p != "/" and not p.startswith("/rpc/")]
    tables = list(dict.fromkeys([*listed, *named_tables]))[:MAX_TABLES]  # storage buckets named by .from() just answer 404
    rpcs = list(dict.fromkeys([*(p.removeprefix("/rpc/") for p in paths if p.startswith("/rpc/")), *named_rpcs]))
    readable: list[tuple[str, int]] = []
    for table in tables:
        if time.monotonic() > deadline:
            break
        r = c.head(f"{project}/rest/v1/{table}", params={"select": "*"}, headers=headers | {"Prefer": "count=exact", "Range": "0-0"}, timeout=5)
        total = (r.headers.get("content-range") or "").rpartition("/")[2]
        if r.status_code in (200, 206) and total.isdigit() and int(total) > 0:
            readable.append((table, int(total)))
    if readable:
        shown = ", ".join(f"{t} ({n:,} rows)" for t, n in readable[:8]) + (f" and {len(readable) - 8} more" if len(readable) > 8 else "")
        out.append(_f("high", f"Anyone can read {len(readable)} of your database table{'s' if len(readable) > 1 else ''}",
                      "With only the public key from your page, these tables return rows to anyone. Walkthru counted them without reading any row. "
                      "Row-level security is off or has a policy that lets everyone read. If a table is meant to be public, such as published posts or shared reports, ignore this finding with that reason.",
                      "Turn on row-level security and allow reads only to the row's owner. SQL to start from:\n" + rls_sql([t for t, _ in readable[:5]]), shown))
    if rpcs:
        out.append(_f("low", f"{len(rpcs)} database function{'s are' if len(rpcs) > 1 else ' is'} callable with the public key",
                      "These functions are exposed to anyone with the public key. Walkthru listed them and did not call them. Each must check who is calling.",
                      "Inside each function, check auth.uid() or revoke execute from anon; move admin functions to a private schema.", ", ".join(rpcs[:10])))
    if time.monotonic() < deadline:
        buckets = c.get(f"{project}/storage/v1/bucket", headers=headers, timeout=5)
        names = [b.get("name") for b in buckets.json()] if buckets.status_code == 200 and isinstance(buckets.json(), list) else []
        listable = []
        for name in names[:10]:
            if time.monotonic() > deadline:
                break
            r = c.post(f"{project}/storage/v1/object/list/{name}", headers=headers, json={"prefix": "", "limit": 1}, timeout=5)
            if r.status_code == 200 and isinstance(r.json(), list) and r.json():
                listable.append(name)
        if listable:
            out.append(_f("medium", f"Anyone can list the files in {len(listable)} storage bucket{'s' if len(listable) > 1 else ''}",
                          "The public key can list what is stored in these buckets, so file names and paths are visible to anyone.",
                          "Add a storage policy that allows list and read only to the file's owner, or make the bucket private.", ", ".join(listable)))
    return out


def check(html: str, page_url: str, c: httpx.Client, *, verified: bool) -> list[Finding]:
    """Findings for the site's Supabase or Firebase backend. Probes run only on verified domains."""
    cfg = find_config(sources(html, page_url, c))
    out: list[Finding] = []
    if cfg["secret_key"]:
        out.append(_f("high", "Supabase secret key in the browser",
                      "A service-role or secret key is in the page's code. It skips every security rule, so anyone can read, change or delete all of your data.",
                      "Rotate the secret key in Supabase now, then use only the publishable (anon) key in the browser and keep the secret key server-side.",
                      f"{cfg['secret_key'][:12]}..."))
    if cfg["supabase"] and cfg["anon_key"]:
        out.append(_f("low", "Your site reads Supabase straight from the browser",
                      "The Supabase URL and public key are in the page, which is normal. It means every table's safety depends on row-level security: anyone can use the same key.",
                      "Keep row-level security on for every table and storage bucket, and verify your domain so Walkthru can check what the public key can read.",
                      cfg["supabase"]))
    if cfg["firebase_db"] or cfg["firebase_key"]:
        out.append(_f("low", "Your site talks to Firebase from the browser",
                      "The Firebase config is in the page, which is normal. Your data is protected only by Firebase security rules.",
                      "Keep security rules that require sign-in for every read and write; never ship test-mode rules.", cfg["firebase_db"]))
    if not verified:
        return out

    deadline = time.monotonic() + BUDGET_S
    try:
        if cfg["supabase"] and cfg["anon_key"] and SUPABASE_URL.fullmatch(cfg["supabase"]):
            out += probe_supabase(cfg["supabase"], cfg["anon_key"], c, deadline, cfg["tables"], cfg["rpcs"])
        if cfg["firebase_db"] and FIREBASE_DB.fullmatch(cfg["firebase_db"]):
            r = c.get(f"{cfg['firebase_db']}/.json", params={"shallow": "true"}, timeout=5)
            if r.status_code == 200 and r.text.strip() not in ("null", ""):
                out.append(_f("high", "Anyone can read your Firebase database",
                              "The Realtime Database answered an unauthenticated read. Walkthru asked for top-level keys only and stored nothing.",
                              'Set database rules so reads need sign-in, for example ".read": "auth != null", then narrow them to each user\'s own data.',
                              cfg["firebase_db"]))
    except (httpx.HTTPError, ValueError):
        pass  # an unreachable backend is not a finding; the probe never blocks the report
    return out
