"""Abuse controls for journeys (docs/agent-safety-plan.md sections 5 and 6): kill switches, per-target rate limits,
the per-run audit log and automatic suspension.

Everything is counted in Postgres (run_audit, run_blocks), so the limits hold across API processes and restarts.
Recording never breaks a run: a failed audit write is logged and the journey goes on.
"""

import logging
import os
import threading
import time
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit

from app import db
from app.agent import policy

log = logging.getLogger("walkthru.abuse")

HOST_PER_HOUR = int(os.environ.get("AGENT_HOST_PER_HOUR", "20"))  # journeys against one unverified host, all users
# The same, for one user. The plan started at 5, but one Plus test set is up to plus.MAX_GROUP (6) journeys on the
# same page, so the floor is two full sets an hour.
USER_HOST_PER_HOUR = int(os.environ.get("AGENT_USER_HOST_PER_HOUR", "12"))
SUSPEND_AFTER = int(os.environ.get("AGENT_SUSPEND_AFTER", "5"))  # refused goals or sites in a day before a pause
REFUSALS = ("goal_refused", "blocked_site")  # a user aiming the agent where it may not go, not an honest limit
BLOCK_CACHE_S = 10

_blocks: tuple[float, list[dict]] = (0.0, [])
_lock = threading.Lock()


def _ago(**delta) -> str:
    return (datetime.now(UTC) - timedelta(**delta)).isoformat()


def active_blocks() -> list[dict]:
    """Kill switches in force, cached for a few seconds so a step does not wait on the database each time."""
    global _blocks
    with _lock:
        if time.monotonic() - _blocks[0] < BLOCK_CACHE_S:
            return _blocks[1]
    rows = db.active_run_blocks(datetime.now(UTC).isoformat())
    with _lock:
        _blocks = (time.monotonic(), rows)
    return rows


def forget_blocks() -> None:
    global _blocks
    with _lock:
        _blocks = (0.0, [])


def paused(user_id: str, host: str) -> str | None:
    """Why journeys are off for this user and target host, or None."""
    for b in active_blocks():
        v = (b.get("value") or "").lower()
        if b["scope"] == "global" or (b["scope"] == "user" and v == user_id.lower()) or (b["scope"] == "host" and v and (host == v or host.endswith("." + v))):
            return b.get("reason") or b["scope"]
    return None


def check_start(user_id: str, host: str, verified) -> None:
    """Raise policy.Refused when this journey may not start: a kill switch, or too many journeys against a host the
    user has not verified. `verified` is called only when a limit is reached."""
    if paused(user_id, host):
        raise policy.Refused("journeys_paused", 403, policy.STOP_REASONS["journeys_paused"][0])
    since = _ago(hours=1)
    recent = db.run_audit_since(since, host=host)
    busy = len(recent) >= HOST_PER_HOUR or sum(1 for r in recent if str(r.get("user_id")) == user_id) >= USER_HOST_PER_HOUR
    if busy and not verified():  # the owner's own site is limited by their plan, not by this
        raise policy.Refused("rate_limited", 429, policy.STOP_REASONS["rate_limited"][0])


def record_start(run_id: str, user_id: str, host: str, mode: str, goal: str) -> None:
    _safe(db.audit_run, {"run_id": run_id, "user_id": user_id, "host": host, "mode": mode, "goal": goal[:500]})


def record_refusal(user_id: str, host: str, mode: str, goal: str, code: str) -> None:
    """Audit a refused journey; a user who keeps aiming the agent at refused goals or sites is paused for review."""
    _safe(db.audit_run, {"user_id": user_id, "host": host or "?", "mode": mode, "goal": goal[:500], "code": code})
    if code not in REFUSALS:
        return
    try:
        refused = [r for r in db.run_audit_since(_ago(days=1), user_id=user_id, refused=True) if r.get("code") in REFUSALS]
        if len(refused) >= SUSPEND_AFTER and not paused(user_id, host):
            reason = f"{len(refused)} refused goals or sites in a day; journeys paused pending review"
            db.add_run_block("user", user_id, reason, "auto-suspension")
            forget_blocks()
            db.app_event("abuse", user_id, {"reason": reason, "last_host": host, "last_goal": goal[:200]})
            log.warning("journeys paused for user %s: %s", user_id, reason)
    except Exception:  # a failed check must never turn a refusal into a crash
        log.warning("auto-suspension check failed", exc_info=True)


def record_end(run_id: str, steps: list[dict], status: str, code: str | None) -> None:
    """The actions of a finished run: type and target label, never typed values or page text."""
    actions = [{"action": s.get("action"), "target": (s.get("target_label") or "")[:80], "path": urlsplit(s.get("url") or "").path[:200]}
               for s in steps]
    _safe(db.end_run_audit, run_id, status, code, actions)


def journeys_for(user_id: str) -> dict:
    """What the extension asks before a test (GET /runs/policy): may this account start journeys right now?"""
    reason = next((b.get("reason") for b in active_blocks() if b["scope"] == "global" or (b["scope"] == "user" and b.get("value") == user_id)), None)
    return {"journeys": reason is None, "message": policy.STOP_REASONS["journeys_paused"][0] if reason else ""}


def purge_old(days: int = 90) -> None:
    db.purge_run_audit(_ago(days=days))


def _safe(fn, *args) -> None:
    try:
        fn(*args)
    except Exception:
        log.warning("run audit write failed", exc_info=True)
