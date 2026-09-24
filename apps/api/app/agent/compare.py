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


def compare(previous: list[dict], current: list[dict], ignored: set[str] | dict = frozenset()) -> dict:
    before = [p for p in previous if fingerprint(p) not in ignored]
    after = [c for c in current if fingerprint(c) not in ignored]
    return {
        "fixed": [_brief(p) for p in before if not any(_same(p, c) for c in after)],
        "still_broken": [_brief(c) for c in after if any(_same(c, p) for p in before)],
        "new": [_brief(c) for c in after if not any(_same(c, p) for p in before)],
    }


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
    result = compare(previous["report"].get("findings", []), report.get("findings", []), ignored)
    return result | {"previous_run_id": previous["id"], "previous_at": previous["created_at"]}
