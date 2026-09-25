"""Refresh the vendored security data in app/scans/data/ (P1.2). Run weekly, review the diff, commit.

    .venv/Scripts/python scripts/refresh_security_data.py

Sources (licences and notices in apps/api/THIRD_PARTY.md):
- retire.js jsrepository-v4.json (Apache-2.0): vulnerable JavaScript library versions.
- gitleaks config/gitleaks.toml (MIT): secret patterns, converted from Go RE2 to Python `re`.
- can-i-take-over-xyz fingerprints.json (CC-BY-4.0): subdomain takeover fingerprints, vulnerable services only.

Only the fields Walkthru uses are kept, so the files stay small and the diff stays readable.
"""

import hashlib
import json
import os
import re
import sys
import tomllib

import httpx

DATA = os.path.join(os.path.dirname(__file__), "..", "app", "scans", "data")
RETIRE = "https://raw.githubusercontent.com/RetireJS/retire.js/master/repository/jsrepository-v4.json"
GITLEAKS = "https://raw.githubusercontent.com/gitleaks/gitleaks/master/config/gitleaks.toml"
TAKEOVER = "https://raw.githubusercontent.com/EdOverflow/can-i-take-over-xyz/master/fingerprints.json"

# Secret rules Walkthru does not run on public JavaScript. Public-by-design values would be false alarms on almost
# every site: JWTs (the Supabase anon key is one; app/scans/backend.py judges Supabase keys properly) and the generic
# rule, which matches ordinary minified code.
SKIP_RULES = {"generic-api-key", "jwt", "jwt-base64"}
POSIX = {"[:alnum:]": "a-zA-Z0-9", "[:alpha:]": "a-zA-Z", "[:digit:]": "0-9", "[:xdigit:]": "0-9a-fA-F", "[:upper:]": "A-Z",
         "[:lower:]": "a-z", "[:space:]": r"\s", "[:word:]": r"\w", "[:punct:]": r"!-/:-@\[-`{-~"}


def go_to_python(pattern: str) -> str:
    """RE2 syntax that Python's `re` spells differently."""
    for posix, plain in POSIX.items():
        pattern = pattern.replace(posix, plain)
    pattern = pattern.replace(r"\z", r"\Z")
    return _scope_flags(pattern)


def _scope_flags(pattern: str) -> str:
    """RE2 applies a bare flag group such as (?i) from that point to the end of the enclosing group, across any
    later `|`. Python only allows bare flags at the very start, so each later one becomes a scoped group that is
    closed at `|` and `)` and reopened after `|`: a(?i)b|c) -> a(?i:b)|(?i:c))."""
    out: list[str] = []
    active: list[list[str]] = [[]]  # per open group: flags opened as scoped groups since the group began
    i, in_class = 0, False
    while i < len(pattern):
        ch = pattern[i]
        if ch == "\\":
            out.append(pattern[i:i + 2])
            i += 2
            continue
        if in_class:
            in_class = ch != "]"
        elif ch == "[":
            in_class = True
            if pattern[i + 1:i + 2] == "]":  # a leading ] is literal inside a class
                out.append("[]")
                i += 2
                continue
        elif ch == "(":
            flag = re.match(r"\(\?([a-zA-Z]+)\)", pattern[i:])
            if flag and i > 0:
                out.append(f"(?{flag.group(1)}:")
                active[-1].append(flag.group(1))
                i += len(flag.group(0))
                continue
            active.append([])
        elif ch == ")":
            out.append(")" * len(active.pop()))
        elif ch == "|" and active[-1]:
            out.append(")" * len(active[-1]) + "|" + "".join(f"(?{f}:" for f in active[-1]))
            i += 1
            continue
        out.append(ch)
        i += 1
    out.append(")" * len(active[0]))
    return "".join(out)


def secrets(raw: bytes) -> list[dict]:
    config = tomllib.loads(raw.decode())
    global_allow = config.get("allowlist", {})
    rules, skipped = [], []
    for rule in config["rules"]:
        if rule["id"] in SKIP_RULES or "regex" not in rule:
            skipped.append(rule["id"])
            continue
        pattern = go_to_python(rule["regex"])
        try:
            re.compile(pattern)
        except re.error as e:
            skipped.append(f"{rule['id']} ({e})")
            continue
        allow = {"regexes": [], "stopwords": []}
        for entry in rule.get("allowlists", []) + ([rule["allowlist"]] if "allowlist" in rule else []):
            if entry.get("regexTarget", "secret") == "secret":
                allow["regexes"] += [go_to_python(r) for r in entry.get("regexes", [])]
            allow["stopwords"] += entry.get("stopwords", [])
        allow["regexes"] = [r for r in allow["regexes"] if _compiles(r)]
        # Literal allowlist entries are known public keys (Google's own browser keys, for example). Store their SHA-256
        # instead, so no key-shaped string is committed; matching stays exact.
        literal = [r for r in allow["regexes"] if re.fullmatch(r"[A-Za-z0-9_\-]+", r)]
        allow["regexes"] = [r for r in allow["regexes"] if r not in literal]
        allow["sha256"] = sorted(hashlib.sha256(v.encode()).hexdigest() for v in literal)
        rules.append({"id": rule["id"], "description": rule.get("description", ""), "regex": pattern,
                      "keywords": [k.lower() for k in rule.get("keywords", [])], "entropy": rule.get("entropy"),
                      "group": rule.get("secretGroup"), **{k: v for k, v in allow.items() if v}})
    stop = [s.lower() for s in global_allow.get("stopwords", [])]
    print(f"gitleaks: {len(rules)} rules kept, skipped: {', '.join(skipped)}")
    return {"rules": rules, "stopwords": stop, "regexes": [r for r in map(go_to_python, global_allow.get("regexes", [])) if _compiles(r)]}


def _compiles(pattern: str) -> bool:
    try:
        re.compile(pattern)
        return True
    except re.error:
        return False


def libraries(raw: bytes) -> dict:
    repo = json.loads(raw)
    out = {}
    for name, lib in repo.items():
        if name == "retire-example":
            continue
        ext = lib.get("extractors", {})
        vulns = [{k: v for k, v in {
            "below": vuln.get("below"), "atOrAbove": vuln.get("atOrAbove"), "severity": vuln.get("severity", "medium"),
            "cve": vuln.get("identifiers", {}).get("CVE", []), "ghsa": vuln.get("identifiers", {}).get("githubID"),
            "summary": vuln.get("identifiers", {}).get("summary", ""),
        }.items() if v} for vuln in lib.get("vulnerabilities", []) if vuln.get("below")]
        keep = {k: [p for p in ext.get(k, []) if _compiles(p.replace("§§version§§", "[0-9][0-9.a-z_\\-]+"))] for k in ("uri", "filename", "filecontent")}
        if vulns and any(keep.values()):
            out[name] = {"extractors": {k: v for k, v in keep.items() if v}, "vulnerabilities": vulns, **({"npm": lib["npmname"]} if lib.get("npmname") else {})}
    print(f"retire.js: {len(out)} libraries")
    return out


def takeovers(raw: bytes) -> list[dict]:
    """Vulnerable services only. Fingerprints are regular expressions (the upstream table escapes | as &#124;); a
    status-code-only fingerprint (HTTP_STATUS=...) proves nothing on its own and is dropped."""
    kept = []
    for f in json.loads(raw):
        fingerprint = (f.get("fingerprint") or "").replace("&#124;", "|")
        if not (f.get("vulnerable") and f.get("cname") and fingerprint) or fingerprint.startswith("HTTP_STATUS"):
            continue
        if fingerprint != "NXDOMAIN" and not _compiles(fingerprint):
            fingerprint = re.escape(fingerprint)
        kept.append({"service": f["service"], "cname": f["cname"], "fingerprint": fingerprint, "nxdomain": bool(f.get("nxdomain"))})
    print(f"takeover: {len(kept)} vulnerable services")
    return kept


def main() -> None:
    os.makedirs(DATA, exist_ok=True)
    with httpx.Client(timeout=30, follow_redirects=True) as c:
        files = {
            "retire.json": libraries(c.get(RETIRE).raise_for_status().content),
            "gitleaks.json": secrets(c.get(GITLEAKS).raise_for_status().content),
            "takeover.json": takeovers(c.get(TAKEOVER).raise_for_status().content),
        }
    for name, data in files.items():
        with open(os.path.join(DATA, name), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=0, ensure_ascii=False, sort_keys=True)
            f.write("\n")
    print("written to", os.path.normpath(DATA))


if __name__ == "__main__":
    sys.exit(main())
