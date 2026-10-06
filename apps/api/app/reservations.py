"""Run reservations (R-S8): admit a test run only after one database transaction reserves its run credit and its
maximum provider cost (migrations/0005_run_reservations.sql). Contract: docs/run-reservations.md.

`RESERVATIONS=off` (default) makes no reservation requests and leaves today's count-based admission unchanged.
`RESERVATIONS=postgres` needs the applied migration and funded `spend_budgets` rows; then admission fails closed:
if the reservation cannot be confirmed, the run does not start and no model is called.

State machine: reserved -> (dispatched) -> settled | released (only if never dispatched) ; settled -> refunded (founder).
Settlements say separately whether the run credit was used (`credit`): a refused goal or a start that failed after
the planner call gives the credit back but keeps its provider cost counted.
Provider work is marked dispatched before the first model call, so a crash after that keeps the run credit and the
reserved maximum counted until a terminal settlement records the outcome. Nothing releases on a lease or a timer.
"""

import logging
import os
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import HTTPException

from app import db

log = logging.getLogger("walkthru.reservations")

# Versioned per-run provider caps in integer micro-USD. Free plans run on free models (0). Paid caps await the
# founder's approved funded balance and caps (payment.md, "Decisions still requiring explicit founder approval").
PRICE_VERSION = "run-caps-2026-10-06"
CAP_ENV = {"free": None, "launch": "RUN_MAX_COST_MICROUSD_LAUNCH", "pro": "RUN_MAX_COST_MICROUSD_PRO", "plus": "RUN_MAX_COST_MICROUSD_PLUS"}
UNAVAILABLE = "Walkthru could not confirm your run credits just now, so nothing was started. Try again in a minute."


def enabled() -> bool:
    value = os.environ.get("RESERVATIONS", "off").lower()
    if value not in ("off", "postgres"):
        raise RuntimeError("RESERVATIONS must be off or postgres")
    return value == "postgres"


def max_cost(plan: str) -> int:
    name = CAP_ENV[plan]
    raw = os.environ.get(name, "0") if name else "0"
    if not raw.isdigit() or int(raw) > 1_000_000_000_000:
        raise RuntimeError(f"{name} must be a whole number of micro-USD")
    return int(raw)


def reserve(user_id: str, run_id: str, usage: dict) -> str | None:
    """Reserve one run credit and the plan's maximum provider cost. Returns the reservation id (None when off)."""
    if not enabled():
        return None
    plan = usage["plan"].name
    try:
        result = db.reserve_run(user_id, run_id, usage["since"], usage["until"], usage["allowed"], max_cost(plan), PRICE_VERSION)
    except (db.DatabaseUnavailable, httpx.HTTPError) as error:
        raise HTTPException(503, UNAVAILABLE) from error
    status = result.get("status")
    if status in ("reserved", "replayed") and result.get("id"):
        return result["id"]
    if status == "no_credits":
        window = "this month" if plan == "free" else "this pass"
        raise HTTPException(402, f"You have used all {usage['allowed']} test runs {window}. Instant Scans stay free.")
    if status == "budget":
        raise HTTPException(503, "Walkthru has reached today's paid testing capacity. Try again tomorrow; Instant Scans still work.")
    if status == "conflict":
        raise HTTPException(409, "This run request was already admitted with different terms. Start a new run.")
    log.error("run reservation refused: %s", status)  # unfunded or unexpected: fail closed
    raise HTTPException(503, UNAVAILABLE)


def dispatched(reservation_id: str | None) -> None:
    """Record that provider work may start. Without this record, no model call is made."""
    if not reservation_id:
        return
    try:
        ok = db.mark_reservation_dispatched(reservation_id)
    except (db.DatabaseUnavailable, httpx.HTTPError) as error:
        release(reservation_id)  # nothing was dispatched; best effort, and the credit stays counted if it fails
        raise HTTPException(503, UNAVAILABLE) from error
    if not ok:
        raise HTTPException(503, UNAVAILABLE)


def release(reservation_id: str | None) -> None:
    """Return the credit and budget of a run that never dispatched provider work. Failures leave it counted (safe)."""
    if not reservation_id:
        return
    try:
        if not db.finish_reservation(reservation_id, {"state": "released", "actual_cost_microusd": 0, "reason": "not_dispatched", "credit": 0}):
            log.warning("reservation %s could not be released; it stays counted", reservation_id)
    except (db.DatabaseUnavailable, httpx.HTTPError):
        log.warning("reservation %s release unconfirmed; it stays counted", reservation_id, exc_info=True)


def settle(user_id: str | None, run_id: str, reason: str, *, credit: bool = True, actual_cost_microusd: int | None = None,
           reservation_id: str | None = None) -> None:
    """Record the run's terminal outcome. An unknown actual cost (None) keeps the reserved maximum counted.
    Idempotent: job retries and replays send the identical outcome."""
    if not enabled() or not user_id:
        return
    outcome = {"state": "settled", "actual_cost_microusd": actual_cost_microusd, "reason": reason, "credit": int(credit)}
    try:
        found = {"id": reservation_id} if reservation_id else db.reservation_for(str(user_id), run_id)
        if found and not db.finish_reservation(found["id"], outcome):
            log.warning("reservation %s already has a different outcome", found["id"])
    except (db.DatabaseUnavailable, httpx.HTTPError):
        # The reservation stays open and counted at its maximum; the next job attempt or reconciliation settles it.
        log.warning("reservation for run %s not settled yet", run_id, exc_info=True)


# ---------- R-S9: the same admission for every other model/data entry point (migrations/0006) ----------
# Inventory and per-operation contract: docs/work-admission.md. Allowances count per owner and UTC day; every operation
# also adds its maximum cost to the one funded platform budget, so no entry point has a separate free pool.
PUBLIC = "00000000-0000-0000-0000-000000000000"  # owner of anonymous Instant Scans: one platform-wide daily pool
WORK_CAP_ENV = {op: f"WORK_MAX_COST_MICROUSD_{op.upper()}" for op in ("public_scan", "scan", "watch", "citations", "scout")}
REFUSED = {  # no_credits: (status, message) for each operation
    "public_scan": (429, "Free scan capacity is used up for today. Try again tomorrow."),
    "scan": (429, "You have used today's scans and finding checks. The limit resets at midnight UTC."),
    "watch": (429, "Today's watch checks for your account are used up. The next check runs tomorrow."),
    "citations": (429, "Today's AI answer checks for your account are used up. Try again tomorrow."),
    "scout": (429, "Scout has answered its daily limit of questions in this workspace. Ask again tomorrow."),
}


def work_cost(operation: str) -> int:
    """Maximum provider cost of one unit, integer micro-USD. Every route uses free models today, so 0 until approved."""
    raw = os.environ.get(WORK_CAP_ENV[operation], "0")
    if not raw.isdigit() or int(raw) > 1_000_000_000:
        raise RuntimeError(f"{WORK_CAP_ENV[operation]} must be a whole number of micro-USD")
    return int(raw)


def _day() -> tuple[str, str]:
    start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    return start.isoformat(), (start + timedelta(days=1)).isoformat()


def reserve_work(operation: str, owner: str, key: str, allowed: int, *, units: int = 1) -> str | None:
    """Reserve `units` of today's allowance and their maximum cost. Returns the reservation id (None when off).
    Raises HTTPException when refused or unconfirmed, so nothing is dispatched."""
    if not enabled():
        return None
    since, until = _day()
    try:
        result = db.reserve_work(str(owner), operation, key, since, until, allowed, units, work_cost(operation) * units, PRICE_VERSION)
    except (db.DatabaseUnavailable, httpx.HTTPError) as error:
        raise HTTPException(503, UNAVAILABLE) from error
    status = result.get("status")
    if status == "reserved" and result.get("id"):
        return result["id"]
    if status == "replayed" and result.get("state") == "reserved" and result.get("id"):
        return result["id"]  # the same admitted work, retried
    if status == "replayed":
        raise HTTPException(409, "This work was already done under the same request. Start a new one.")
    if status == "no_credits":
        code, message = REFUSED[operation]
        raise HTTPException(code, message)
    if status == "budget":
        raise HTTPException(503, "Walkthru has reached today's testing capacity. Try again tomorrow.")
    if status == "conflict":
        raise HTTPException(409, "This request was already admitted with different terms. Start a new one.")
    log.error("%s reservation refused: %s", operation, status)  # unfunded or unexpected: fail closed
    raise HTTPException(503, UNAVAILABLE)


def _finish(reservation_id: str, reason: str, credit: bool) -> None:
    outcome = {"state": "settled", "actual_cost_microusd": None, "reason": reason, "credit": int(credit)}
    try:
        if not db.finish_reservation(reservation_id, outcome):
            log.warning("reservation %s already has a different outcome", reservation_id)
    except (db.DatabaseUnavailable, httpx.HTTPError):
        log.warning("reservation %s not settled yet; it stays counted", reservation_id, exc_info=True)


@contextmanager
def work(operation: str, owner: str, key: str, allowed: int, *, units: int = 1):
    """Admit one synchronous piece of work. Yields `dispatch`, to call immediately before the first provider call.
    Exits: never dispatched -> released (credit and budget return); dispatched and done -> settled with the credit used;
    dispatched and failed -> settled without the credit, its cost still counted. Off: no requests, no-op dispatch."""
    reservation = reserve_work(operation, owner, key, allowed, units=units)
    sent = []

    def dispatch() -> None:
        if reservation and not sent:
            dispatched(reservation)
            sent.append(True)

    try:
        yield dispatch
    except BaseException:
        if reservation:
            _finish(reservation, "failed", False) if sent else release(reservation)
        raise
    if reservation:
        _finish(reservation, "completed", True) if sent else release(reservation)


def settle_work(reservation_id: str | None, *, failed: bool = False) -> None:
    """Settle asynchronous work admitted with reserve_work + dispatched (comparison jobs, AI answer batches)."""
    if reservation_id and enabled():
        _finish(reservation_id, "failed" if failed else "completed", not failed)
