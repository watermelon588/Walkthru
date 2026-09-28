"""Walkthru MCP server (Plus): Claude Code, Cursor and other agents scan, read reports and fix prompts from the editor.

Streamable HTTP at /mcp, stateless, authenticated by a personal API key (`Authorization: Bearer wt_...`). Every tool
runs under the same plan check, limits and grounding as the web API. ARCHITECTURE.md `mcp`.
"""

from __future__ import annotations

import contextvars
import hashlib
import json
import logging
import secrets
import threading
import uuid
from datetime import UTC, datetime
from urllib.parse import urlsplit

from fastapi import HTTPException, Request
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError  # its message reaches the agent; other errors are hidden
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import ValidationError

from app import db, limits, plans

KEY_PREFIX = "wt_"
MAX_KEYS = 5
SCANS_PER_DAY = 50  # per Plus user, on top of the web's own limits; MCP scans never use the free capacity

_user: contextvars.ContextVar[str] = contextvars.ContextVar("mcp_user")
_request: contextvars.ContextVar[Request] = contextvars.ContextVar("mcp_request")  # for addresses the API serves (badges, hooks)
log = logging.getLogger("walkthru.mcp")


def new_key() -> tuple[str, str]:
    """(key shown once, hash stored)."""
    key = KEY_PREFIX + secrets.token_urlsafe(32)
    return key, key_hash(key)


def key_hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def require_plus(user_id: str) -> None:
    if plans.current(user_id)["plan"].name != "plus":
        raise HTTPException(402, "The Walkthru MCP server is part of the Plus plan.")


# ---------- tools ----------

server = MCPServer(
    "Walkthru",
    instructions=(
        "Walkthru is the launch check for apps built with AI. Reports: scan_site for SEO, AI search readiness and passive "
        "security on a public site, get_report to read any of the user's reports, get_fix_prompt for a ready list of "
        "fixes to apply in this codebase, get_finding for everything about one finding, verify_finding to re-check just "
        "that finding after a fix, rerun to repeat every check, compare_sites for competitors, accept_finding for a "
        "deliberate won't-fix. Ownership: get_site_verification gives the meta tag to put in this codebase's <head> and "
        "checks it once deployed; verified sites get the owner-only security checks. GitHub: list_github_repos and "
        "open_fix_pull_request (preview first, confirm to open). AI answers: track_ai_answers, get_ai_answers, "
        "set_ai_prompts, check_ai_answers_now. Weekly watch: list_watched_sites, watch_site, check_watched_site_now, "
        "create_deploy_hook for CI. share_report makes a report public and returns its Launch Ready badge. Findings are "
        "grounded in evidence; never invent findings the report does not contain. User journeys run only from the "
        "Walkthru Chrome extension."
    ),
)


def _row(run_id: str) -> dict:
    row = db.get_run(run_id) if run_id.isalnum() and len(run_id) == 32 else None
    if row is None or str(row.get("user_id")) != _user.get():
        raise ToolError("No run with that id in your account. Use list_runs to see your runs.")
    return row


def _summary(row: dict, full: bool = False) -> str:
    from app.main import WEB_URL  # the web address links point to

    rep = row.get("report")
    link = f"{WEB_URL}/app/runs/{row['id']}"
    if not rep:
        return f"Run {row['id']} for {row['site']} is {row['status']} and has no report yet. Open {link} or try again in a minute."
    if "compare" in rep:
        return _compare_summary(row, rep["compare"], link)
    score = (rep.get("launch_ready") or {}).get("score")
    lines = [
        f"# Walkthru report for {row['site']}",
        f"Run {row['id']} ({'Instant Scan' if row.get('kind') == 'scan' else row.get('goal')}), {row.get('status')}. {link}",
        f"Launch Ready score: {score if score is not None else 'not measured'} of 100.",
        "",
        rep.get("summary", ""),
    ]
    if rep.get("top_fixes"):
        lines += ["", "## Fix these first", *[f"{i + 1}. {fix}" for i, fix in enumerate(rep["top_fixes"])]]
    findings = rep.get("findings") or []
    lines += ["", f"## Findings ({len(findings)})"]
    for fid, f in _ids(findings):
        lines.append(f"- [{f['severity']}] {f['kind']}: {f['title']} (id: {fid})" + (f"\n  Evidence: {f['evidence']}\n  Fix: {f['fix']}" if full else ""))
    if not full and findings:
        lines += ["", "Call get_report for evidence and fixes, or get_fix_prompt for a prompt to apply them."]
    if findings:
        lines += ["", "Pass a finding's id to get_finding for its full recipe, or to verify_finding after fixing it."]
    return "\n".join(lines)


def _compare_summary(row: dict, sites: list[dict], link: str) -> str:
    lines = [f"# Walkthru comparison for {row['site']}", f"Run {row['id']}, {row.get('status')}. {link}", "",
             "Public checks only for every site. A missing score means that check did not run, not zero.", ""]
    for x in sites:
        name = x.get("site", "?") + (" (yours)" if x.get("yours") else "")
        if x.get("error"):
            lines.append(f"- {name}: not scanned: {x['error']}")
            continue
        found = x.get("findings") or {}
        lines.append(f"- {name}: Launch Ready {x.get('score', '-')}, AI search readiness {x.get('geo', '-')}, findings high "
                     f"{found.get('high', 0)} / medium {found.get('medium', 0)} / low {found.get('low', 0)}, report run {x.get('run_id', '-')}")
    return "\n".join(lines)


def finding_id(finding: dict) -> str:
    """The id an agent passes back: the finding's stable rule id when the report has one, else its fingerprint."""
    from app.agent.compare import fingerprint

    return finding.get("rule") or fingerprint(finding)


def _ids(findings: list[dict]) -> list[tuple[str, dict]]:
    """Each finding with an id unique in its report. Two cookies can break the same rule, so the second is rule#2."""
    seen: dict[str, int] = {}
    out = []
    for f in findings:
        base = finding_id(f)
        seen[base] = seen.get(base, 0) + 1
        out.append((base if seen[base] == 1 else f"{base}#{seen[base]}", f))
    return out


def _find(row: dict, rule: str) -> tuple[str, dict]:
    """The report finding (and its id) that an id, fingerprint or exact title names."""
    from app.agent.compare import fingerprint

    wanted = rule.strip().lower()
    for fid, f in _ids((row.get("report") or {}).get("findings", [])):
        if wanted in {fid.lower(), fingerprint(f), f["title"].lower()} - {""}:
            return fid, f
    raise ToolError(f"The report of run {row['id']} has no finding {rule!r}. Call get_report to see each finding's id.")


_verifies: dict[tuple[str, str], int] = {}  # (user, UTC day) -> verify_finding calls; ponytail: one API process, like the scan limit
_verifies_lock = threading.Lock()


def _within_daily_cap(user: str) -> None:
    """Scans, comparisons and finding checks share one daily cap per Plus user."""
    day = datetime.now(UTC).date().isoformat()
    if db.user_scans_today(user) + _verifies.get((user, day), 0) >= SCANS_PER_DAY:
        raise ToolError(f"You have run {SCANS_PER_DAY} MCP scans and checks today. The limit resets at midnight UTC.")


def _count_verify(user: str) -> None:
    day = datetime.now(UTC).date().isoformat()
    with _verifies_lock:
        for key in [k for k in _verifies if k[1] != day]:
            del _verifies[key]
        _verifies[(user, day)] = _verifies.get((user, day), 0) + 1


def _scan(site: str) -> dict:
    from app.main import run_scan

    user = _user.get()
    _within_daily_cap(user)
    try:
        run_id, _ = run_scan(site, user_id=user)
    except ValueError as e:  # not public, not responding: say so plainly
        raise ToolError(str(e)) from e
    except HTTPException as e:  # the site's hourly scan limit (SD-2.3)
        raise ToolError(str(e.detail)) from e
    return db.get_run(run_id)


@server.tool(structured_output=False)  # text only: a structured copy doubles what the agent reads
def scan_site(url: str) -> str:
    """Scan a public website: SEO across up to 10 pages, AI search readiness (GEO), passive security headers and a
    first impression. Takes about 20 seconds. Returns the report summary and findings."""
    return _summary(_scan(url))


@server.tool(structured_output=False)
def get_report(run_id: str) -> str:
    """Read one of your Walkthru reports in full: summary, Launch Ready score, every finding with its evidence and fix."""
    return _summary(_row(run_id), full=True)


@server.tool(structured_output=False)
def get_fix_prompt(run_id: str, style: str = "full") -> str:
    """A Markdown prompt listing every finding in the report with where it is, the required change and an acceptance
    check, ready for you to apply in this codebase. style: "full" or "chat" (shorter)."""
    from app.agent import compare, fix_prompt

    row = _row(run_id)
    if not row.get("report"):
        raise ToolError("The report is not ready yet. Try again in a minute.")
    ignored = db.ignored_fingerprints(_user.get(), compare.origin(row["site"]))
    return fix_prompt.build(row, row["report"], ignored, "chat" if style == "chat" else "full")


@server.tool(structured_output=False)
def rerun(run_id: str) -> str:
    """Run the server-side checks again on the site of an earlier run, after you applied fixes. User journeys rerun
    from the Walkthru Chrome extension."""
    row = _row(run_id)
    fresh = _scan(row["site"])
    before = {(f["kind"], f["title"]) for f in (row.get("report") or {}).get("findings", [])}
    after = {(f["kind"], f["title"]) for f in (fresh.get("report") or {}).get("findings", [])}
    gone, new = sorted(before - after), sorted(after - before)
    note = [
        "",
        "## Compared with the earlier run",
        f"No longer reported ({len(gone)}): " + ("; ".join(t for _, t in gone) or "none"),
        f"New ({len(new)}): " + ("; ".join(t for _, t in new) or "none"),
    ]
    if row.get("kind") == "test":
        note.append("The earlier run was a journey; this rerun covers the server-side checks only. Rerun the journey in the extension.")
    return _summary(fresh) + "\n".join(note)


@server.tool(structured_output=False)
def get_finding(run_id: str, rule: str) -> str:
    """Everything the report holds about one finding: why it matters, the evidence, every affected page, the change to
    make (with ready-made code when Walkthru has it) and how to confirm the fix. rule: the finding's id from get_report."""
    from app.agent import fix_prompt
    from app.scans import stack as stacks

    row = _row(run_id)
    fid, f = _find(row, rule)
    rep = row["report"]
    item = {"finding": f, "recipe": fix_prompt.recipe(f) or {}, "step": fix_prompt.step(f, rep.get("stack"))}
    fixes = {x["id"]: x for x in (rep.get("geo") or {}).get("fixes", [])}
    lines = [f"id: {fid}. Finding on {row['site']} (run {row['id']}). Stack: {stacks.label(rep.get('stack'))}.", "",
             *fix_prompt.finding_lines(item, rep, fix_prompt._places(row, rep), fixes, heading=f"# {f['title']}")]
    if item["recipe"].get("manual_text"):
        lines += [f"Outside the code ({fix_prompt.MANUAL.get(item['recipe']['manual'], 'hosting')}): {item['recipe']['manual_text']}"]
    lines += ["", "## Done when",
              ("Rerun the journey in the Walkthru Chrome extension: journey findings need a real browser."
               if f["kind"] == "ux" else f'verify_finding("{row["id"]}", "{fid}") answers fixed.')]
    return "\n".join(lines)


@server.tool(structured_output=False)
def verify_finding(run_id: str, rule: str) -> str:
    """After fixing one finding, re-run only the check behind it on the pages it affected and answer fixed or still
    broken. Faster than rerun. Counts toward the same daily limit as scans. rule: the finding's id from get_report."""
    from app.main import _verified

    row = _row(run_id)
    _, f = _find(row, rule)
    if f["kind"] == "ux":
        raise ToolError("This finding comes from a user journey. Rerun the journey from the Walkthru Chrome extension to check it.")
    user = _user.get()
    _within_daily_cap(user)
    _count_verify(user)
    pages = (row["report"].get("pages") or {}).get(_fingerprint(f)) or []
    from app.main import polite

    _as_owner(lambda u: polite(row["site"]))  # a re-check fetches the site too (SD-2.3)
    try:
        result = recheck(row["site"], f, pages, verified=_verified(row["site"], user))
    except ValueError as e:
        raise ToolError(str(e)) from e
    return result


def _fingerprint(finding: dict) -> str:
    from app.agent.compare import fingerprint

    return fingerprint(finding)


def recheck(site: str, finding: dict, pages: list[str], *, verified: bool) -> str:
    """Run the scanner family that produced `finding` again, on its pages, and say whether it is still there."""
    from app.agent.compare import _same
    from app.scans import accessibility, fetch, performance, security, takeover, tls
    from app.scans import site as site_audit

    fetch.assert_public(site)
    targets = pages[:10] or [site]
    found: list[dict] = []
    checked: list[str] = []
    with fetch.client() as c:
        kind = finding["kind"]
        if kind == "security":
            for url in targets:
                resp = fetch.get(c, url)
                if resp is None:
                    continue
                checked.append(url)
                found += [x.model_dump() | {"page": url} for x in security.check_headers(resp) + security.check_content(resp.text, str(resp.url))]
            root = fetch.get(c, site)
            if root is not None:
                root_url = str(root.url)
                verified = verified and fetch.same_site(site, root_url)  # the owner verified this host, not a redirect target
                site_wide = security.check_transport(site, root, c) + security.check_cors(root_url, c) + tls.check(root_url) + tls.check_caa(root_url, c)
                if verified:
                    site_wide += security.check_exposed(fetch.origin(root_url), c) + security.check_bundles(root.text, root_url, c)
                    site_wide += takeover.check([(root_url, root.text)], root_url, c)
                found += [x.model_dump() | {"page": root_url} for x in site_wide]
                checked.append(root_url)
        elif kind in ("seo", "geo"):
            audit = site_audit.audit(site, c, verified=verified, visited=targets, max_pages=site_audit.DEFAULT_MAX_PAGES, time_limit=site_audit.DEFAULT_TIME_LIMIT)
            checked = audit.coverage.urls
            by_title = {(k, t): urls for k, t, urls in audit.pages}
            for x in audit.seo + (audit.geo.findings if audit.geo else []):
                found += [x.model_dump() | {"page": u} for u in by_title.get((x.kind, x.title), [None])]
        elif kind == "accessibility":
            for url in targets:
                resp = fetch.get(c, url)
                if resp is not None:
                    checked.append(url)
                    found += [x.model_dump() | {"page": url} for x in accessibility.scan(resp.text, str(resp.url))]
        elif kind == "performance":
            measured, ok, _ = performance.scan_pages(targets, c, limit=len(targets))
            if not ok:
                return f"Could not measure speed right now (PageSpeed unavailable), so {finding['title']!r} was not re-checked. Try again later."
            checked = targets
            found = [x.model_dump() | {"page": None} for x in measured]
        else:
            raise ValueError(f"Walkthru cannot re-check {kind} findings on their own. Use rerun.")
    if not checked:
        return f"{site} did not respond, so {finding['title']!r} was not re-checked. Try again when the site is up."
    still = [x for x in found if _same(finding, x)]
    if still:
        where = sorted({x["page"] for x in still if x.get("page")})
        return "\n".join([f"Still broken: {finding['title']}", *(f"- {u}" for u in where), "", f"Evidence now: {still[0].get('evidence') or '-'}",
                          f"Change: {still[0]['fix']}"])
    if pages and not set(pages) & set(checked):
        return f"Not re-checked: none of the pages that had {finding['title']!r} were reached this time ({', '.join(pages[:3])}). Use rerun for a full check."
    new = [x for x in found if x["kind"] == finding["kind"] and x["severity"] == "high"][:3]
    lines = [f"Fixed: {finding['title']} is no longer reported on {len(checked)} checked page{'s' if len(checked) != 1 else ''}."]
    if new:
        lines += ["", "High-severity issues this check reports now (they may be new or already known):", *(f"- {x['title']}" for x in new)]
    return "\n".join(lines)


@server.tool(structured_output=False)
def list_runs(site: str = "", limit: int = 10) -> str:
    """Your most recent Walkthru runs and scans, newest first, optionally only for one site (any part of the address)."""
    # ponytail: reads every run of the user (the export query); add a limited query if accounts grow past a few hundred runs
    rows = [r for r in reversed(db.runs_for_user(_user.get())) if site.lower() in r["site"].lower()][: max(1, min(limit, 50))]
    if not rows:
        return "No runs yet" + (f" for {site}." if site else ".") + " Use scan_site to start."
    out = []
    for r in rows:
        score = ((r.get("report") or {}).get("launch_ready") or {}).get("score")
        out.append(f"- {r['id']} {r['created_at'][:16]} {r['site']} {'scan' if r.get('kind') == 'scan' else repr(r.get('goal'))} "
                   f"{r.get('status')}, score {score if score is not None else '-'}")
    return "\n".join(out)


# ---------- the rest of the web app, as the key's owner ----------
# Each tool below calls the web API's own route function, so it has exactly the website's plan checks, limits and
# ownership rules. Deleting things (sites, prompts, GitHub connections, keys) stays in the web app on purpose.


def _as_owner(call):
    """Run `call(user)` for the key's owner. Route errors and invalid arguments become messages the agent reads."""
    try:
        return call({"id": _user.get()})
    except HTTPException as e:
        raise ToolError(str(e.detail)) from e
    except ValidationError as e:  # a request body built from the agent's arguments
        raise ToolError("; ".join(f"{'.'.join(map(str, err['loc'])) or 'input'}: {err['msg']}" for err in e.errors())) from e


def _url(site: str) -> str:
    site = site.strip()
    return site if "://" in site else "https://" + site


def _host(site: str) -> str:
    return (urlsplit(_url(site)).hostname or "").lower().removeprefix("www.")


def _pick(rows: list[dict], site: str, missing: str) -> dict:
    """The row for a site given as any address on its host."""
    row = next((r for r in rows if _host(r["site"]) == _host(site)), None)
    if row is None:
        raise ToolError(missing)
    return row


def _api_base() -> str:
    """The address this request reached the API on: badges and deploy hooks are served from it."""
    return str(_request.get().base_url).rstrip("/")


@server.tool(structured_output=False)
def get_plan() -> str:
    """Your Walkthru plan: runs left this period, when it ends, and what it includes."""
    s = plans.summary(plans.current(_user.get()))
    until = f", until {s['expires_at'][:10]}." if s.get("expires_at") else "."
    used = f" ({', '.join(s['sites_used'])})." if s["sites_used"] else "."
    return "\n".join([f"Plan: {s['plan']}. Runs left: {s['runs_left']} of {s['runs_allowed']}{until}",
                      f"Steps per journey: {s['max_steps']}. Signed-in journeys: {'yes' if s['logged_in'] else 'no'}. Test users: {', '.join(s['personas'])}.",
                      f"Sites: {len(s['sites_used'])} of {s['sites']} used{used}",
                      f"MCP scans and finding checks: {SCANS_PER_DAY} a day."])


# Where the <head> lives in common stacks, for the verification meta tag.
HEAD_PLACES = [
    'Next.js App Router: app/layout.tsx, `export const metadata = { other: { "walkthru-verification": "TOKEN" } }`',
    "Next.js Pages Router: pages/_document.tsx, inside <Head>",
    "Vite, Create React App or plain HTML: index.html, inside <head>",
    "Astro: the base layout's <head>; SvelteKit: src/app.html; Nuxt: nuxt.config, app.head.meta; Remix: the meta export in app/root.tsx",
    "Rails, Django, Laravel, WordPress: the base layout template's <head>",
]


@server.tool(structured_output=False)
def get_site_verification(site: str) -> str:
    """Prove that a site is yours. Says whether it is verified for your Walkthru account and, if not, gives the exact
    meta tag to add to the <head> of this codebase (with where the head lives in common frameworks), plus the file and
    DNS alternatives. Verification unlocks the owner-only security checks and signed-in journeys. After adding the tag,
    deploy, then call this again: Walkthru checks the live site, never the code."""
    from app import main

    v = _as_owner(lambda u: main.verification(site=site, user=u))
    if v["verified"]:
        return (f"Verified: {v['site']} is proven yours for this Walkthru account. Scans and verify_finding now include the "
                "owner-only checks (exposed files, secrets in bundles, source maps, subdomain takeover, backend exposure). "
                "Keep the tag or file in place: it is checked again at every run.")
    token = v["token"]
    return "\n".join([
        f"Not verified yet: {v['site']} does not show this account's token. Add one of these, deploy, then call get_site_verification again.",
        "",
        "1. Meta tag on the homepage (best done in the codebase):",
        f"   {v['meta']}",
        "   Where the <head> lives:",
        *(f"   - {place.replace('TOKEN', token)}" for place in HEAD_PLACES),
        f"2. A file served at {v['file']} whose whole content is: {token}",
        "   (public/.well-known/walkthru.txt in Next.js, Vite and Astro; static/.well-known/walkthru.txt in SvelteKit)",
        f"3. A DNS TXT record (at the DNS host, outside the code): name {v['txt_name']}, value {v['txt_value']}",
        "",
        "The token belongs to this Walkthru account. It is not a secret, so it is safe to commit.",
    ])


@server.tool(structured_output=False)
def list_github_repos() -> str:
    """The GitHub repositories you gave the Walkthru GitHub App, for open_fix_pull_request. If GitHub is not connected
    yet, returns the link the owner opens once in a browser to connect it."""
    from app import main

    status = _as_owner(lambda u: main.github_status(user=u))
    if not status["configured"]:
        return "The Walkthru GitHub App is not set up on this server yet, so fix pull requests are unavailable. Use get_fix_prompt and apply the fixes here instead."
    if not status["installations"]:
        where = status.get("install_url") or f"{main.WEB_URL}/app/settings"
        return f"GitHub is not connected. The owner connects it once in a browser (GitHub asks them to approve): {where}\nThen call list_github_repos again."
    got = _as_owner(lambda u: main.github_repos(user=u))
    lines = [f"- {r['full_name']} (default branch {r['default_branch']}{', private' if r['private'] else ''})" for r in got["repos"]]
    lines += [f"Could not list {e}" for e in got["errors"]]
    return "\n".join(lines) or "The GitHub App is connected but sees no repositories. Give it access to the repository on GitHub."


@server.tool(structured_output=False)
def open_fix_pull_request(run_id: str, repo: str, confirm: bool = False) -> str:
    """Open a pull request with a report's config-only fixes (security headers in vercel.json, netlify.toml or _headers,
    robots.txt, llms.txt and similar) on the repository's default branch; the owner reviews and merges it. With confirm
    false (the default) it only previews the files it would change; call again with confirm true to open it. repo:
    "owner/name" from list_github_repos. Code changes are listed as left for you: apply them with get_fix_prompt."""
    from app import main

    _row(run_id)
    repos = _as_owner(lambda u: main.github_repos(user=u))["repos"]
    match = next((r for r in repos if r["full_name"].lower() == repo.strip().lower()), None)
    if match is None:
        raise ToolError(f"{repo!r} is not among the repositories the Walkthru GitHub App can see. Call list_github_repos.")
    body = {"installation_id": match["installation_id"], "repo": match["full_name"], "confirm": confirm}
    got = _as_owner(lambda u: main.fix_pull_request(run_id, main.FixPullRequest(**body), user=u))
    if got.get("url"):
        lines = [f"Opened pull request #{got.get('number')}: {got['url']} (branch {got.get('branch')} into {got['base']})."]
    else:
        lines = [f"Preview for {got['repo']} (into {got['base']}). Nothing was written. Call again with confirm true to open the pull request."]
    lines += ["", f"Files changed ({len(got['changes'])}):", *(f"- {x.get('path')}: {x.get('summary', '')}" for x in got["changes"])]
    if got.get("left"):
        lines += ["", "Left for you (changes the pull request does not make):", *(f"- {x}" for x in got["left"])]
    return "\n".join(lines)


@server.tool(structured_output=False)
def accept_finding(run_id: str, rule: str, reason: str) -> str:
    """Mark a finding as a deliberate won't-fix for this site, with the reason (paid plans). It stays in the score but
    leaves fix prompts and rerun comparisons. Use only when the owner decided so. rule: the finding's id from get_report."""
    from app import main

    row = _row(run_id)
    fid, f = _find(row, rule)
    _as_owner(lambda u: main.ignore_finding(run_id, main.IgnoreFinding(fingerprint=_fingerprint(f), reason=reason), user=u))
    return f"Accepted as won't fix on {row['site']}: {f['title']} (id {fid}). Reason: {reason.strip()}. reopen_finding undoes it."


@server.tool(structured_output=False)
def reopen_finding(run_id: str, rule: str) -> str:
    """Undo accept_finding: the finding counts as open again in fix prompts and comparisons."""
    from app import main

    row = _row(run_id)
    fid, f = _find(row, rule)
    _as_owner(lambda u: main.unignore_finding(run_id, _fingerprint(f), user=u))
    return f"Reopened: {f['title']} (id {fid}) on {row['site']}."


@server.tool(structured_output=False)
def compare_sites(site: str, competitors: list[str]) -> str:
    """Run your site and up to three competitors through the same public checks, side by side (paid plans). Takes a
    minute or two; returns a run id to read with get_report. Each site counts toward the daily scan limit."""
    from app import main

    body = {"site": _url(site), "competitors": [_url(c) for c in competitors]}
    got = _as_owner(lambda u: main.start_compare(main.CompareRequest(**body), user=u))
    return f'Comparison queued as run {got["run_id"]}. Call get_report("{got["run_id"]}") in a minute or two.'


@server.tool(structured_output=False)
def share_report(run_id: str) -> str:
    """Make one report public (anyone with the link can read it) and return its link plus the Launch Ready badge to add
    to a README or site footer. The badge always shows the latest shared score for that site."""
    from app import main

    row = _row(run_id)
    got = _as_owner(lambda u: main.share_run(run_id, user=u))
    score = ((row.get("report") or {}).get("launch_ready") or {}).get("score")
    img, link = f"{_api_base()}/badge/{run_id}.svg", f"{_api_base()}/badge/{run_id}"
    alt = f"Walkthru Launch Ready score: {score if score is not None else '-'} of 100"
    return "\n".join([f"Public report: {got['url']}", "", "Badge (Markdown):", f"[![{alt}]({img})]({link})", "", "Badge (HTML):",
                      f'<a href="{link}"><img src="{img}" alt="{alt}" height="20"></a>'])


# ---------- AI answers (citation tracking, app/citations.py) ----------


def _answers(view: dict) -> str:
    site, status = view["site"], view["status"]
    lines = [f"# AI answers for {site['site']} (brand {site['brand']!r})",
             "Configured API engines: " + ", ".join(e["label"] for e in view["engines"]) + ". Not measured: " + ", ".join(view["not_measured"]) + ".",
             f"Latest batch: {status['done']} answered, {status['queued']} waiting for provider capacity, {status['failed']} failed.",
             "Next weekly check: " + (site["next_check_at"][:16] if site.get("next_check_at") else "none scheduled") + "."]
    if view.get("share_of_voice"):
        lines += ["", "## Share of voice (latest batch)"]
        for b in view["share_of_voice"]:
            count = b.get("citation_answers", 0)
            citations = f"cited in {b['citations']} of {count} measurable answers" if count else "citations not measured"
            lines.append(f"- {b['name']}{' (you)' if b['you'] else ''}: {b['share']}% of mentions, named in {b['mentions']} of {b['answers']} answers; {citations}")
    lines += ["", "## Prompts", *(f"{i + 1}. {p['prompt']}" for i, p in enumerate(view.get("prompts") or []))]
    done = [a for a in view.get("answers") or [] if a.get("status") == "done"]
    if done:
        lines += ["", "## Answers"]
        for a in done[:30]:
            result = a.get("result") or {}
            you = next((b for b in result.get("brands", []) if b.get("you")), {})
            cited = ("yes" if you.get("cited") else "no") if result.get("citation_eligible") is True else "not measurable"
            label = (result.get("provenance") or {}).get("label") or a["engine"]
            lines.append(f"- [{label}] {a['prompt']}: you named {'yes' if you.get('mentioned') else 'no'}, cited {cited}")
    if view.get("limit"):
        lim = view["limit"]
        lines += ["", f"Your plan: {lim['prompts']} prompts per site, engines {', '.join(lim['engines'])}, {'weekly checks' if lim['weekly'] else 'one batch'}."]
    return "\n".join(lines)


def _citation_row(site: str) -> dict:
    return _pick(db.citation_sites(_user.get()), site, f"You do not track AI answers for {site}. Call track_ai_answers first.")


@server.tool(structured_output=False)
def list_ai_answer_sites() -> str:
    """Sites whose AI answers you track: how AI assistants answer your prompts and whether they name or cite you."""
    from app import main

    got = _as_owner(lambda u: main.list_citation_sites(user=u))
    if not got["limit"]:
        return f"AI answer tracking is not in your {got['plan']} plan."
    rows = [f"- {s['site']} (brand {s['brand']!r})" for s in got["sites"]] or ["No sites tracked yet. Use track_ai_answers."]
    return "\n".join([*rows, f"Your plan tracks {got['limit']['sites']} site(s)."])


@server.tool(structured_output=False)
def track_ai_answers(site: str, competitors: list[str] | None = None, brand: str = "") -> str:
    """Start tracking how AI assistants answer questions in your market and whether they name or cite your site.
    Suggested prompts come from your homepage; change them with set_ai_prompts. competitors: domains or "Name
    domain.com", up to the plan's limit. brand defaults to the name on your homepage."""
    from app import main

    body = {"site": _url(site), "brand": brand, "competitors": competitors or []}
    view = _as_owner(lambda u: main.add_citation_site(main.CitationSite(**body), user=u))
    return _answers(view) + "\n\nCall check_ai_answers_now to ask the assistants, or wait for the weekly check."


@server.tool(structured_output=False)
def get_ai_answers(site: str) -> str:
    """The latest AI answers for a tracked site: share of voice against competitors, and per prompt whether each
    assistant named or cited you."""
    from app import main

    row = _citation_row(site)
    return _answers(_as_owner(lambda u: main.get_citation_site(uuid.UUID(row["id"]), user=u)))


@server.tool(structured_output=False)
def set_ai_prompts(site: str, prompts: list[str] | None = None, competitors: list[str] | None = None, brand: str | None = None) -> str:
    """Replace the prompts (questions people ask AI assistants), the competitors or the brand name of a tracked site.
    Anything left out stays as it is. New prompts are asked from the next check."""
    from app import main

    if prompts is None and competitors is None and brand is None:
        raise ToolError("Pass prompts, competitors or brand to change.")
    row = _citation_row(site)
    body = {k: v for k, v in {"prompts": prompts, "competitors": competitors, "brand": brand}.items() if v is not None}
    return _answers(_as_owner(lambda u: main.edit_citation_site(uuid.UUID(row["id"]), main.CitationEdit(**body), user=u)))


@server.tool(structured_output=False)
def check_ai_answers_now(site: str) -> str:
    """Queue a check of every prompt of a tracked site now. Answers arrive as the shared free provider capacity allows,
    which can take hours; read them with get_ai_answers."""
    from app import main

    row = _citation_row(site)
    got = _as_owner(lambda u: main.check_citations_now(uuid.UUID(row["id"]), user=u))
    return f"Queued {got['queued']} answers for {row['site']}. Read them later with get_ai_answers."


# ---------- weekly watch and deploy hooks (Plus, app/watch.py) ----------


def _watched(site: str) -> dict:
    return _pick(db.sites_for_user(_user.get()), site, f"You do not watch {site}. Call watch_site first.")


@server.tool(structured_output=False)
def list_watched_sites() -> str:
    """Sites Walkthru re-checks every week and after each deploy, with what changed in the last check."""
    from app import main

    got = _as_owner(lambda u: main.list_watched(user=u))
    if got["plan"] != "plus":
        return "Weekly watch is part of the Plus plan."
    out = []
    for s in got["sites"]:
        last = s.get("last_changes") or {}
        change = f"last check {len(last.get('new', []))} new, {len(last.get('fixed', []))} fixed (run {last.get('run_id')})" if last else "first check pending"
        out.append(f"- {s['site']}: {change}; next check {(s.get('next_check_at') or '-')[:16]}")
    return "\n".join([*(out or ["No watched sites. Use watch_site."]), f"{len(got['sites'])} of {got['limit']} sites."])


@server.tool(structured_output=False)
def watch_site(site: str) -> str:
    """Re-check a site every week (SEO, AI search readiness, passive security) and email the owner when findings
    change (Plus). The first check, the baseline, starts now."""
    from app import main

    row = _as_owner(lambda u: main.add_watched(main.WatchSite(site=_url(site)), user=u))
    return f"Watching {row['site']}. The baseline check is running; later checks run weekly. create_deploy_hook adds a check after each deploy."


@server.tool(structured_output=False)
def check_watched_site_now(site: str) -> str:
    """Check a watched site now, for example right after a deploy. At most once every 10 minutes per site."""
    from app import main

    row = _watched(site)
    _as_owner(lambda u: main.check_watched_now(row["id"], user=u))
    return f"Checking {row['site']} now. list_watched_sites shows what changed in a minute or two."


@server.tool(structured_output=False)
def create_deploy_hook(site: str) -> str:
    """A URL for CI or the hosting provider to POST after each deploy, so Walkthru re-checks the watched site. Shown
    once; creating a new one replaces the old. Keep it out of the repository: store it as a CI secret."""
    from app import main

    row = _watched(site)
    got = _as_owner(lambda u: main.create_deploy_hook(row["id"], _request.get(), user=u))
    return "\n".join([f"Deploy hook for {row['site']} (store it as a secret, for example WALKTHRU_DEPLOY_HOOK):", got["url"], "",
                      "GitHub Actions step after the deploy:", '  - run: curl -fsS -X POST "$WALKTHRU_DEPLOY_HOOK"',
                      "    env:", "      WALKTHRU_DEPLOY_HOOK: ${{ secrets.WALKTHRU_DEPLOY_HOOK }}",
                      "Vercel or Netlify: add it as a deploy notification webhook."])


def build_transport() -> None:
    """Create the session manager (it exists only once the HTTP app is built). A manager runs once per process, so
    tests that start the app again call this for a fresh one. Stateless JSON suits one request per tool call."""
    server.streamable_http_app(
        stateless_http=True,
        json_response=True,
        # Rebinding protection guards unauthenticated local servers; here every request must carry a valid key.
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )


build_transport()


async def _reply(send, status: int, message: str, headers: dict | None = None) -> None:
    body = json.dumps({"detail": message}).encode()
    extra = [(k.lower().encode(), str(v).encode()) for k, v in (headers or {}).items()]
    await send({"type": "http.response.start", "status": status, "headers": [(b"content-type", b"application/json"), *extra]})
    await send({"type": "http.response.body", "body": body})


class Endpoint:
    """ASGI endpoint for /mcp: checks the API key and the Plus plan, then hands the request to the MCP session manager."""

    async def __call__(self, scope, receive, send) -> None:
        import anyio

        header = dict(scope.get("headers") or []).get(b"authorization", b"").decode()
        key = header.removeprefix("Bearer ").strip()
        if not key.startswith(KEY_PREFIX):
            return await _reply(send, 401, "Send your Walkthru API key as 'Authorization: Bearer wt_...'. Create one in Settings.")
        owner = await anyio.to_thread.run_sync(db.api_key_owner, key_hash(key))
        if owner is None:
            return await _reply(send, 401, "That API key is not valid or was revoked. Create a new one in Settings.")
        user = str(owner["user_id"])
        from app.observability import bind_user

        bind_user(scope, user)
        try:
            await anyio.to_thread.run_sync(require_plus, user)
            await anyio.to_thread.run_sync(limits.apply, "mcp", str(owner["id"]))  # per API key (SD-2.1)
        except HTTPException as e:
            return await _reply(send, e.status_code, e.detail, e.headers)
        try:
            await anyio.to_thread.run_sync(db.touch_api_key, owner["id"])
        except Exception:
            log.warning("could not record API key use", exc_info=True)
        token, request = _user.set(user), _request.set(Request(scope))
        try:
            await server.session_manager.handle_request(scope, receive, send)
        finally:
            _user.reset(token)
            _request.reset(request)
