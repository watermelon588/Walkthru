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


def _unique(findings: list[dict]) -> list[dict]:
    """A finding reported twice is one problem: keep the first of each fingerprint."""
    seen: set[str] = set()
    return [f for f in findings if not (fingerprint(f) in seen or seen.add(fingerprint(f)))]


def compare(previous: list[dict], current: list[dict], ignored: set[str] | dict = frozenset(), *,
            prev_pages: dict | None = None, cur_pages: dict | None = None, audited: list[str] | None = None,
            journey_finished: bool | None = None) -> dict:
    """Finding by finding, and page by page where the reports know the pages. A finding that vanished only because
    none of its pages were audited this time is "not re-checked", never "fixed". So is a UX finding that vanished
    from a journey that did not finish (R-S13): the test user may simply not have reached that point."""
    before = _unique([p for p in previous if not is_ignored(p, ignored)])
    after = _unique([c for c in current if not is_ignored(c, ignored)])
    prev_pages, cur_pages, seen = prev_pages or {}, cur_pages or {}, set(audited or [])
    fixed, not_rechecked, still = [], [], []
    for p in before:
        if any(_same(p, c) for c in after):
            continue
        was = _pages(prev_pages, p)
        if p["kind"] == "ux" and journey_finished is False:
            not_rechecked.append(_brief(p))
        elif was and audited is not None and not seen & set(was):
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


def assertion_of(report: dict) -> dict | None:
    return next(iter((report.get("assessment") or {}).get("assertions") or []), None)


TERMS = {"expected_count": "expected count", "tolerance": "tolerance", "dataset_id": "dataset", "max_age_seconds": "maximum age"}
VERDICTS = {("failed", "passed"): ("fixed", "It failed before and passes now under the same declared conditions."),
            ("failed", "failed"): ("still_failing", "It still fails under the same declared conditions."),
            ("passed", "failed"): ("regressed", "It passed before and fails now under the same declared conditions."),
            ("passed", "passed"): ("still_passing", "It passes again under the same declared conditions.")}


def recheck_assertion(previous: dict, current: dict) -> dict | None:
    """R-S13: the declared count check against its previous result, like for like. Rows carry report, persona and
    logged_in. Missing coverage is "not_rechecked" and changed conditions are "not_comparable"; neither is ever fixed.
    The dataset timestamp is fresh on every run by design, so it is not a changed condition."""
    before, after = assertion_of(previous["report"]), assertion_of(current["report"])
    if before is None:
        return None  # nothing was declared earlier, so there is nothing to recheck
    e = before["expected"]
    out = {"fingerprint": f"assertion:{e['path']}|{e['filter_value']}|{e['count_label']}",
           "identity": f"{e['path']}, Filter: {e['filter_value']}, {e['count_label']}", "before": before["status"],
           "after": after["status"] if after else None, "before_count": before.get("observed_count"),
           "after_count": after.get("observed_count") if after else None, "expected_count": e.get("expected_count")}
    if after is None:
        return out | {"verdict": "not_rechecked", "reason": "This run did not declare the count check, so it was not re-checked."}
    a = after["expected"]
    if (a["path"], a["filter_value"], a["count_label"]) != (e["path"], e["filter_value"], e["count_label"]):
        return out | {"verdict": "not_comparable", "reason": "This run checked a different path, filter or count label."}
    changed = [label for key, label in TERMS.items() if e.get(key) != a.get(key)]
    changed += [key.replace("_", " ") for key in ("persona", "logged_in") if previous.get(key) != current.get(key)]
    if changed:
        return out | {"verdict": "not_comparable", "reason": f"Declared conditions changed ({', '.join(changed)}), so the results are not directly comparable."}
    if after["status"] not in ("passed", "failed"):
        return out | {"verdict": "not_rechecked", "reason": f"This run's check was {after['status']}: {after['reason']}"}
    if before["status"] not in ("passed", "failed"):
        return out | {"verdict": "first_result", "reason": f"The earlier check was {before['status']}, so this {after['status']} result is a first result, not a fix."}
    verdict, reason = VERDICTS[(before["status"], after["status"])]
    return out | {"verdict": verdict, "reason": reason}


def attach(row: dict, report: dict, status: str | None = None) -> dict | None:
    """The comparison for a finished paid run, or None (free plan, first run of this goal, or no user)."""
    if row.get("tier") != "paid" or not row.get("user_id"):
        return None
    from app.agent.report_contract import ensure_supported

    ensure_supported(report)
    user_id, site = str(row["user_id"]), origin(row["site"])
    previous = next((r for r in db.recent_reports(user_id, row["id"])
                     if origin(r["site"]) == site and _goal(r["goal"]) == _goal(row["goal"])), None)
    if previous is None:
        return None
    ensure_supported(previous["report"])
    try:
        ignored = db.ignored_fingerprints(user_id, site)
    except (httpx.HTTPError, db.DatabaseUnavailable):  # still useful without them (e.g. before the table is applied)
        ignored = {}
    result = compare(previous["report"].get("findings", []), report.get("findings", []), ignored,
                     prev_pages=previous["report"].get("pages"), cur_pages=report.get("pages"),
                     audited=(report.get("site_audit") or {}).get("urls"), journey_finished=None if status is None else status == "done")
    return result | {"previous_run_id": previous["id"], "previous_at": previous["created_at"],
                     "assertion": recheck_assertion(previous, row | {"report": report})}
