"""Vulnerable JavaScript libraries, matched against retire.js data (Apache-2.0; notice in apps/api/THIRD_PARTY.md).

Script URLs and file names are matched on every plan (no extra request). File contents are matched only for bundles
the verified-domain scan already fetched. The data lives in app/scans/data/retire.json; refresh it weekly with
scripts/refresh_security_data.py.
"""

import json
import os
import re
from functools import lru_cache
from urllib.parse import urlsplit

from app.agent.schema import Finding

DATA = os.path.join(os.path.dirname(__file__), "data", "retire.json")
VERSION = r"[0-9][0-9.a-z_\-]+"  # retire.js's own placeholder expansion
SEVERITY = {"critical": "high", "high": "high", "medium": "medium", "low": "low"}
RANK = {"low": 0, "medium": 1, "high": 2}
MAX_CONTENT = 2_000_000


# npm CDNs name the package and version in the path: cdn.jsdelivr.net/npm/bootstrap@3.3.7/..., unpkg.com/lodash@4.17.4/...
NPM_CDN = re.compile(r"^https?://(?:cdn\.jsdelivr\.net/npm|unpkg\.com|esm\.sh|ga\.jspm\.io/npm:)/?((?:@[\w.-]+/)?[\w.-]+)@(\d[\w.-]*)/", re.IGNORECASE)
BUILD_SUFFIX = re.compile(r"[.-](min|slim|js|umd|esm|prod|production)$", re.IGNORECASE)


@lru_cache(maxsize=1)
def _repo() -> list[tuple[str, dict[str, list[re.Pattern]], list[dict]]]:
    with open(DATA, encoding="utf-8") as f:
        raw = json.load(f)
    compiled = []
    for name, lib in raw.items():
        patterns = {kind: [re.compile(p.replace("§§version§§", VERSION)) for p in lib["extractors"].get(kind, [])] for kind in ("uri", "filename", "filecontent")}
        compiled.append((name, patterns, lib["vulnerabilities"]))
    return compiled


@lru_cache(maxsize=1)
def _npm_names() -> dict[str, str]:
    with open(DATA, encoding="utf-8") as f:
        raw = json.load(f)
    # retire.js names most libraries after their npm package (bootstrap, lodash); npmname covers the rest
    return {name.lower(): name for name in raw} | {lib["npm"].lower(): name for name, lib in raw.items() if lib.get("npm")}


def _clean(version: str) -> str:
    """Drop build words the greedy version pattern swallows: 3.7.1.min -> 3.7.1."""
    while (stripped := BUILD_SUFFIX.sub("", version)) != version:
        version = stripped
    return version


def _comparable(part: str | None) -> int | str:
    if not part:
        return 0
    return int(part) if part.isdigit() else part


def at_or_above(version: str, other: str) -> bool:
    """retire.js isAtOrAbove: dotted and dashed parts compared in order; a number beats a word (1.0 > 1.0-beta)."""
    a, b = re.split(r"[.\-]", version), re.split(r"[.\-]", other)
    for i in range(max(len(a), len(b))):
        x, y = _comparable(a[i] if i < len(a) else None), _comparable(b[i] if i < len(b) else None)
        if type(x) is not type(y):
            return isinstance(x, int)
        if x > y:
            return True
        if x < y:
            return False
    return True


def vulnerabilities(name: str, version: str) -> list[dict]:
    for lib, _, vulns in _repo():
        if lib == name:
            return [v for v in vulns if not at_or_above(version, v["below"]) and ("atOrAbove" not in v or at_or_above(version, v["atOrAbove"]))]
    return []


def detect_url(url: str) -> list[tuple[str, str]]:
    """(library, version) named by a script URL or its file name."""
    path = urlsplit(url).path
    filename = path.rsplit("/", 1)[-1]
    npm = NPM_CDN.match(url)
    if npm and (name := _npm_names().get(npm.group(1).lower())):
        return [(name, _clean(npm.group(2)))]
    found = []
    for name, patterns, _ in _repo():
        for kind, target in (("uri", url), ("filename", filename)):
            match = next((m for p in patterns[kind] if (m := p.search(target))), None)
            if match and match.groups() and match.group(1):
                found.append((name, _clean(match.group(1))))
                break
    return found


def detect_content(text: str) -> list[tuple[str, str]]:
    """(library, version) from banners and markers inside a script file."""
    text = text[:MAX_CONTENT]
    found = []
    for name, patterns, _ in _repo():
        match = next((m for p in patterns["filecontent"] if (m := p.search(text))), None)
        if match and match.groups() and match.group(1):
            found.append((name, _clean(match.group(1))))
    return found


def finding(name: str, version: str, where: str) -> Finding | None:
    vulns = vulnerabilities(name, version)
    if not vulns:
        return None
    severity = max((SEVERITY.get(v.get("severity", "medium"), "medium") for v in vulns), key=RANK.__getitem__)
    ids = list(dict.fromkeys(i for v in vulns for i in (v.get("cve") or [v.get("ghsa")]) if i))
    summaries = list(dict.fromkeys(v["summary"] for v in vulns if v.get("summary")))
    fixed = max((v["below"] for v in vulns), key=_sort_key)
    detail = f"{name} {version} has {len(vulns)} published vulnerabilit{'y' if len(vulns) == 1 else 'ies'}"
    detail += f" ({', '.join(ids[:5])}{' and more' if len(ids) > 5 else ''})" if ids else ""
    detail += f": {'; '.join(summaries[:3])}." if summaries else "."
    return Finding(kind="security", severity=severity, title=f"{name} {version} has known vulnerabilities", detail=detail[:600],
                   fix=f"Upgrade {name} to {fixed} or later, then test the pages that use it.", evidence=where[:300])


def _sort_key(version: str) -> tuple:
    """Order versions the retire.js way, for picking the highest fixed version."""
    return tuple((0, p, "") if isinstance(p, int) else (-1, 0, p) for p in map(_comparable, re.split(r"[.\-]", version)))


def check_scripts(script_urls: list[str]) -> list[Finding]:
    out, seen = [], set()
    for url in script_urls:
        for name, version in detect_url(url):
            if (name, version) not in seen and (f := finding(name, version, url)):
                seen.add((name, version))
                out.append(f)
    return out


def check_content(text: str, url: str) -> list[Finding]:
    return [f for name, version in detect_content(text) if (f := finding(name, version, url))]
