"""Weekly watch (Plus): re-scan watched sites weekly and on a deploy hook, email the owner only when findings change.

Server-side checks only (SEO, AI search readiness, passive security): journeys need a browser. ARCHITECTURE.md `watch`.
"""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from app import db, deliver, plans, reservations
from app.agent import compare

log = logging.getLogger("walkthru.watch")
EVERY = timedelta(days=7)
HOOK_COOLDOWN = timedelta(minutes=10)
# R-S9 accepted cap on scheduled and triggered checks per owner per UTC day (weekly, manual and deploy hooks together).
# Plus watches up to 5 sites; each site's manual/hook checks are also spaced by HOOK_COOLDOWN. Pending founder approval.
CHECKS_PER_DAY = int(os.environ.get("WATCH_CHECKS_PER_DAY", "20"))


def hook_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_hook() -> tuple[str, str]:
    token = "wh_" + secrets.token_urlsafe(24)
    return token, hook_hash(token)


def changes(before: dict | None, after: dict) -> dict:
    """What a new report fixed and introduced compared with the previous one, by finding fingerprint (compare.py)."""
    diff = compare.compare((before or {}).get("findings", []), after.get("findings", []))
    return {"new": [f["title"] for f in diff["new"]], "fixed": [f["title"] for f in diff["fixed"]],
            "score": (after.get("launch_ready") or {}).get("score"), "at": datetime.now(UTC).isoformat()}


def check(site: dict, reason: str = "weekly") -> dict:
    """Scan one watched site, store what changed, and email the owner when something did. Returns the changes."""
    from app.main import WEB_URL, run_scan

    previous = db.get_run(site["last_run_id"]) if site.get("last_run_id") else None
    with reservations.work("watch", str(site["user_id"]), f"watch-{uuid.uuid4().hex}", CHECKS_PER_DAY) as dispatch:
        run_id, fresh = run_scan(site["site"], user_id=str(site["user_id"]), kind="watch", dispatch=dispatch)
    diff = changes(previous.get("report") if previous else None, fresh["report"]) | {"reason": reason, "run_id": run_id, "baseline": previous is None}
    db.update_site(site["id"], {"last_run_id": run_id, "last_changes": diff, "next_check_at": (datetime.now(UTC) + EVERY).isoformat()})
    if previous and (diff["new"] or diff["fixed"]):
        from app import notify

        notify.watch_changed(str(site["user_id"]), run_id, site["site"], len(diff["new"]), len(diff["fixed"]))
        to = db.user_email(str(site["user_id"]))
        if to:
            deliver.send_watch(to, site["site"], f"{WEB_URL}/app/runs/{run_id}", diff)
    return diff


def run_due() -> int:
    """Queue a check for every watched site whose week is up. The key holds one job per site and due time, so a
    pass that runs again before the check does never doubles it. Returns how many sites were queued."""
    from app import jobs

    queued = 0
    for site in db.due_sites(datetime.now(UTC).isoformat()):
        if plans.current(str(site["user_id"]))["plan"].name != "plus":  # lapsed pass: keep the site, stop checking
            db.update_site(site["id"], {"next_check_at": (datetime.now(UTC) + EVERY).isoformat()})
            continue
        jobs.enqueue("watch_site", {"site": site}, key=f"watch:{site['id']}:{site['next_check_at']}")
        queued += 1
    return queued


def check_due(site: dict) -> None:
    """The weekly check of one site (a `watch_site` job). A failure is retried in 6 hours with a new job."""
    try:
        check(site)
    except Exception:  # logged, and the new due time queues the retry
        log.warning("watch check failed for %s", site.get("site"), exc_info=True)
        db.update_site(site["id"], {"next_check_at": (datetime.now(UTC) + timedelta(hours=6)).isoformat()})
