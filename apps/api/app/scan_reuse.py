"""Instant Scan reuse (R-S7a): reuse a saved anonymous public scan only when it is eligible, current and labelled.

Eligibility is the database lookup in db.recent_public_scan (anonymous, public, free, complete, exact URL, ten minutes
from creation, never owner/MCP/watch/comparison/journey work) plus one more rule here: the saved report must carry the
current `scan_version`. That version hashes the scanner, report and scoring code with the configured model chain, so a
deploy that changes any of them stops reuse of older results instead of showing them as current. Reports saved before
this field existed are never reused.

Simultaneous misses for the same page start one scan: a striped lock inside each API process, and an atomic shared
claim (the Postgres rate-limit counter) across processes. The claim key includes the newest scan row of the page, so a
finished scan frees the next claim at once; only a scan that failed before saving a row holds it for FLIGHT_SECONDS. Requests that lose the claim wait for that scan's report
and get it labelled `coalesced`; if it does not appear they get a retry message rather than a second scan. When the
shared counter is unreachable it fails open (limits.hit), so cross-process coalescing is best effort in that case only.

`fresh=True` skips reuse for re-checking a fix. It still pays the address limit, the daily free capacity and the
per-host politeness limit, and a waiting fresh request accepts only a report that started after it asked.

Keys hold a hash of the URL, never the URL itself (queries can carry tokens), and no credentials or typed values.
"""

import hashlib
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException

from app import db, limits
from app.agent import runtime

REUSE_SECONDS = 600  # must match db.recent_public_scan
FLIGHT_SECONDS = 60  # the shared claim window; an Instant Scan normally takes about 20 seconds
WAIT_SECONDS = 30.0  # how long a request that lost the claim waits for the winner's report
POLL_SECONDS = 0.5
_SOURCES = ("scans/*.py", "agent/report.py", "agent/report_contract.py", "agent/score.py", "agent/schema.py", "agent/compare.py")
_LOCKS = [threading.Lock() for _ in range(64)]  # ponytail: striped by key, bounded memory; rare unrelated pages share a stripe


@lru_cache(maxsize=1)
def version() -> str:
    """The code and model configuration that writes Instant Scan reports. Any change invalidates reuse."""
    root = Path(__file__).parent
    digest = hashlib.sha256()
    for path in sorted({p for pattern in _SOURCES for p in root.glob(pattern)}):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    for models in (runtime.GROQ_MODELS, runtime.GEMINI_MODELS, runtime.OPENROUTER_MODELS, [runtime.CLAUDE_MODEL]):
        digest.update(",".join(models).encode() + b"|")
    return digest.hexdigest()[:16]


def flight_key(site: str, generation: str | None = None) -> str:
    return hashlib.sha256(f"{version()}|{site}|{generation or ''}".encode()).hexdigest()[:32]


def _created(row: dict) -> datetime:
    value = row.get("created_at")
    return datetime.fromisoformat(value) if value else datetime.now(UTC)


def label(status: str, row: dict, now: datetime | None = None) -> dict:
    """What the caller shows: fresh, reused or coalesced, with when the evidence was observed and until when it is reused."""
    observed = _created(row)
    now = now or datetime.now(UTC)
    return {"status": status, "source_run_id": row["id"], "observed_at": observed.isoformat(),
            "age_seconds": max(0, int((now - observed).total_seconds())),
            "reused_until": (observed + timedelta(seconds=REUSE_SECONDS)).isoformat(), "scan_version": version()}


def lookup(site: str, since: datetime | None = None) -> dict | None:
    """The newest eligible saved scan of this exact page written by the current code, or None."""
    row = db.recent_public_scan(site)
    if not row or (row.get("report") or {}).get("scan_version") != version():
        return None
    if since and _created(row) < since:
        return None
    return row


def _wait(site: str, since: datetime | None) -> dict | None:
    deadline = time.monotonic() + WAIT_SECONDS
    while time.monotonic() < deadline:
        time.sleep(POLL_SECONDS)
        row = lookup(site, since)
        if row:
            return row
    return None


def get_or_scan(site: str, scan: Callable[[], tuple[str, dict]], *, fresh: bool = False) -> tuple[str, dict, dict]:
    """(run_id, {"site", "report"}, label). `scan` runs only when nothing current can be reused or awaited."""
    asked = datetime.now(UTC)
    since = asked if fresh else None
    if not fresh and (row := lookup(site)):
        return row["id"], row, label("reused", row)
    stripe = _LOCKS[int(flight_key(site), 16) % len(_LOCKS)]
    waited = not stripe.acquire(blocking=False)
    if waited:
        stripe.acquire()
    try:
        if (row := lookup(site, since)) and (waited or not fresh):
            return row["id"], row, label("coalesced" if waited else "reused", row)
        try:
            claim = flight_key(site, db.latest_public_scan_id(site))
            limits.hit(f"scanflight:{claim}", 1, FLIGHT_SECONDS, "A scan of this page is already running.")
        except HTTPException:
            row = _wait(site, since)
            if row:
                return row["id"], row, label("coalesced", row)
            raise HTTPException(503, "A scan of this page is already running. Open it again in a minute.", headers={"Retry-After": "30"}) from None
        run_id, result = scan()
        return run_id, result, label("fresh", {"id": run_id, "created_at": asked.isoformat()})
    finally:
        stripe.release()
