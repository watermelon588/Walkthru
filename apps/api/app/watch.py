"""Weekly watch (Plus): re-scan watched sites weekly and on a deploy hook, email the owner only when findings change.

Server-side checks only (SEO, AI search readiness, passive security): journeys need a browser. ARCHITECTURE.md `watch`.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import threading
from datetime import UTC, datetime, timedelta

from app import db, deliver, plans
from app.agent import compare

log = logging.getLogger("walkthru.watch")
EVERY = timedelta(days=7)
HOOK_COOLDOWN = timedelta(minutes=10)


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
    run_id, fresh = run_scan(site["site"], user_id=str(site["user_id"]), kind="watch")
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
    """Check every watched site whose week is up. Failures are logged and retried on the next pass."""
    done = 0
    for site in db.due_sites(datetime.now(UTC).isoformat()):
        try:
            if plans.current(str(site["user_id"]))["plan"].name != "plus":  # lapsed pass: keep the site, stop checking
                db.update_site(site["id"], {"next_check_at": (datetime.now(UTC) + EVERY).isoformat()})
                continue
            check(site)
            done += 1
        except Exception:  # one broken site must not stop the others
            log.warning("watch check failed for %s", site.get("site"), exc_info=True)
            db.update_site(site["id"], {"next_check_at": (datetime.now(UTC) + timedelta(hours=6)).isoformat()})
    return done


def start_background() -> None:
    """Look for due sites every 30 minutes. ponytail: one thread per API process, like retention; a cron job with more instances."""
    def loop() -> None:
        stop = threading.Event()
        while not stop.wait(1800):
            try:
                if done := run_due():
                    log.info("watch: checked %s sites", done)
            except Exception:  # the loop must survive a database outage
                log.warning("watch pass failed", exc_info=True)

    threading.Thread(target=loop, name="weekly-watch", daemon=True).start()
