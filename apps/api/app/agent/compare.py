"""Rerun and compare (paid plans): each finding marked fixed, still broken or new against the previous run of the
same goal on the same site. Plain code, never the model. Ignored findings leave every list (SPEC.md)."""

import re
from urllib.parse import urlsplit

import httpx

from app import db


def fingerprint(finding: dict) -> str:
    """Stable id for a finding across runs: kind plus title, ignoring case, spacing and counts ("3 more pages")."""
    title = re.sub(r"\d+", "#", finding["title"].lower())
    return f"{finding['kind']}:{' '.join(title.split())}"


def _words(text: str) -> set[str]:
    return {w[:5] for w in re.findall(r"[a-z]+", text.lower()) if len(w) > 3}


def _same(a: dict, b: dict) -> bool:
    if fingerprint(a) == fingerprint(b):
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
    before = [p for p in previous if fingerprint(p) not in ignored]
    after = [c for c in current if fingerprint(c) not in ignored]
    prev_pages, cur_pages, seen = prev_pages or {}, cur_pages or {}, set(audited or [])
    fixed, not_rechecked, still = [], [], []
    for p in before:
        if any(_same(p, c) for c in after):
            continue
        was = prev_pages.get(fingerprint(p), [])
        if was and audited is not None and not seen & set(was):
            not_rechecked.append(_brief(p) | {"pages_unchecked": was})
        else:
            fixed.append(_brief(p))
    for c in after:
        match = next((p for p in before if _same(c, p)), None)
        if match is None:
            continue
        was, now = prev_pages.get(fingerprint(match), []), cur_pages.get(fingerprint(c), [])
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
