"""Rerun and compare (paid plans): each finding marked fixed, still broken or new against the previous run of the
same goal on the same site. Plain code, never the model. Ignored findings leave every list (SPEC.md)."""

import re
from urllib.parse import urlsplit

import httpx

from app import db
from app.agent.schema import finding_rule


def legacy_fingerprint(finding: dict) -> str:
    """Title key used by reports and ignored findings written before rule ids."""
    title = re.sub(r"\d+", "#", finding["title"].lower())
    return f"{finding['kind']}:{' '.join(title.split())}"


def fingerprint(finding: dict) -> str:
    """Prefer the stable rule id; old report rows still use the title key."""
    rule = finding.get("rule")
    return f"{finding['kind']}:{rule}" if isinstance(rule, str) and rule.strip() else legacy_fingerprint(finding)


def is_ignored(finding: dict, ignored: set[str] | dict) -> bool:
    generated = f"{finding['kind']}:{finding_rule(finding['kind'], finding['title'])}"
    return fingerprint(finding) in ignored or legacy_fingerprint(finding) in ignored or generated in ignored


def _pages(pages: dict, finding: dict) -> list[str]:
    return pages.get(fingerprint(finding), pages.get(legacy_fingerprint(finding), []))


def _words(text: str) -> set[str]:
    return {w[:5] for w in re.findall(r"[a-z]+", text.lower()) if len(w) > 3}


def _same(a: dict, b: dict) -> bool:
    if fingerprint(a) == fingerprint(b):
        return True
    if a.get("rule") and b.get("rule") and a["kind"] != "ux":
        return False
    if legacy_fingerprint(a) == legacy_fingerprint(b):
        return True
    if a["kind"] != "ux" or b["kind"] != "ux":
        return False
    # UX titles are written by the model and vary between runs; close wording is the same problem.
    wa, wb = _words(a["title"]), _words(b["title"])
    return bool(wa and wb) and len(wa & wb) / len(wa | wb) >= 0.5


def _brief(finding: dict) -> dict:
    return {"kind": finding["kind"], "severity": finding["severity"], "title": finding["title"], "fingerprint": fingerprint(finding)}


def compare(previous: list[dict], current: list[dict], ignored: set[str] | dict = frozenset(), *,
            prev_pages: dict | None = None, cur_pages: dict | None = None, audited: list[str] | None = None) -> dict:
    """Finding by finding, and page by page where the reports know the pages. A finding that vanished only because
    none of its pages were audited this time is "not re-checked", never "fixed"."""
    before = [p for p in previous if not is_ignored(p, ignored)]
    after = [c for c in current if not is_ignored(c, ignored)]
    prev_pages, cur_pages, seen = prev_pages or {}, cur_pages or {}, set(audited or [])
    fixed, not_rechecked, still = [], [], []
    for p in before:
        if any(_same(p, c) for c in after):
            continue
        was = _pages(prev_pages, p)
        if was and audited is not None and not seen & set(was):
            not_rechecked.append(_brief(p) | {"pages_unchecked": was})
        else:
            fixed.append(_brief(p))
    for c in after:
        match = next((p for p in before if _same(c, p)), None)
        if match is None:
            continue
        was, now = _pages(prev_pages, match), _pages(cur_pages, c)
        item = _brief(c)
        if was or now:
            item |= {"pages_fixed": [u for u in was if u not in now and u in seen], "pages_new": [u for u in now if u not in was],
                     "pages_unchecked": [u for u in was if u not in seen]}
        still.append(item)
    new = [_brief(c) for c in after if not any(_same(c, p) for p in before)]
    return {"fixed": fixed, "still_broken": still, "new": new, "not_rechecked": not_rechecked}


def origin(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}".lower()


def _goal(text: str) -> str:
    return " ".join(text.lower().split())


def attach(row: dict, report: dict) -> dict | None:
    """The comparison for a finished paid run, or None (free plan, first run of this goal, or no user)."""
    if row.get("tier") != "paid" or not row.get("user_id"):
        return None
    user_id, site = str(row["user_id"]), origin(row["site"])
    previous = next((r for r in db.recent_reports(user_id, row["id"])
                     if origin(r["site"]) == site and _goal(r["goal"]) == _goal(row["goal"])), None)
    if previous is None:
        return None
    try:
        ignored = db.ignored_fingerprints(user_id, site)
    except (httpx.HTTPError, db.DatabaseUnavailable):  # still useful without them (e.g. before the table is applied)
        ignored = {}
    result = compare(previous["report"].get("findings", []), report.get("findings", []), ignored,
                     prev_pages=previous["report"].get("pages"), cur_pages=report.get("pages"),
                     audited=(report.get("site_audit") or {}).get("urls"))
    return result | {"previous_run_id": previous["id"], "previous_at": previous["created_at"]}
