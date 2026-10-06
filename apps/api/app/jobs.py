"""Durable background jobs in Postgres (SD-6.1, docs/system-design.md): reports, comparisons, watch checks, emails,
Scout answers and the periodic passes (evidence retention, weekly watch).

A job is a row in `jobs` (migrations/0001_initial.sql). Workers claim one at a time through `claim_job` (FOR UPDATE SKIP LOCKED), so
any number of threads and processes share the queue and a restart loses nothing. A claimed job holds a lease; if its
worker dies, the job is claimed again when the lease runs out, so every handler must be safe to run twice. A failed
job is retried with exponential backoff and jitter until it has used its attempts, then kept as `failed` for 14 days.

    .venv/Scripts/python -m app.jobs     # a worker process on its own; set JOB_WORKERS=0 on the API processes then
"""

import logging
import os
import random
import threading
import time
import uuid
from datetime import UTC, datetime, timedelta

from app import db, provider_usage

log = logging.getLogger("walkthru.jobs")
LEASE_S = 15 * 60  # longer than the slowest job, a comparison of four sites
POLL_S = 5  # idle wait; a job queued by this process wakes its workers at once
WORKERS = int(os.environ.get("JOB_WORKERS", "4"))
KEEP = timedelta(days=14)  # finished jobs, then deleted by the retention pass

# Every kind and its attempts. Most handlers catch their own errors, so attempts mostly cover a worker that died.
ATTEMPTS = {"finish_run": 3, "compare": 2, "watch_check": 2, "watch_site": 1, "notify_founder": 5, "scout_reply": 2,
            "retention": 1, "watch_due": 1}
PERIODIC = {"retention": 6 * 3600, "watch_due": 1800}  # kind -> seconds; queued once per window across all processes

_wake = threading.Event()


def enqueue(kind: str, payload: dict | None = None, *, key: str | None = None) -> None:
    """Queue a job. Payloads are plain JSON and hold ids, never emails or tokens. `key` makes the job unique."""
    if kind not in ATTEMPTS:
        raise ValueError(f"unknown job kind {kind}")
    db.enqueue_job(kind, payload or {}, max_attempts=ATTEMPTS[kind], dedupe_key=key or uuid.uuid4().hex)
    _wake.set()


def _reported(run_id: str) -> bool:
    return bool((db.get_run(run_id) or {}).get("report"))


def handle(kind: str, p: dict) -> None:
    from app import main, retention, scout, watch

    if kind == "finish_run":
        if not _reported(p["run_id"]):  # an earlier attempt already wrote it
            main.finish_run(p["run_id"], p["values"])
        if _reported(p["run_id"]):  # R-S8: settle on every attempt; identical outcomes are idempotent
            from app import reservations

            reservations.settle((db.get_run(p["run_id"]) or {}).get("user_id"), p["run_id"], "completed")  # credit used
    elif kind == "compare":
        if not _reported(p["run_id"]):
            main._compare(p["run_id"], p["user_id"], p["urls"], p.get("reservation"))
    elif kind == "watch_check":
        watch.check(p["site"], p["reason"])
    elif kind == "watch_site":
        watch.check_due(p["site"])
    elif kind == "notify_founder":
        main._notify_founder(p["user_id"], p["plan"], p["note"], p["request_id"])
    elif kind == "scout_reply":
        scout.reply(p["team_id"], p["thread"], p["question"], {"id": p["asker_id"]})
    elif kind == "retention":
        retention.run_pass()
    elif kind == "watch_due":
        watch.run_due()
    else:
        raise ValueError(f"unknown job kind {kind}")


def backoff(attempts: int) -> float:
    """Seconds before the next try: 30 s doubling per attempt, at most an hour, with jitter so retries spread out."""
    return min(3600, 30 * 2 ** (attempts - 1)) * random.uniform(0.5, 1.0)


def run_one() -> bool:
    """Claim and run one due job. False when nothing was due."""
    job = db.claim_job(LEASE_S)
    if not job:
        return False
    values: dict = {"status": "done", "locked_until": None, "last_error": None}
    try:
        payload = job["payload"]
        operation_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"walkthru:job:{job['id']}"))
        with provider_usage.scope(operation_id=operation_id, job_id=job["id"], job_attempt=job["attempts"], job_lease_id=job["lease"],
                                  run_id=payload.get("run_id"), user_id=payload.get("user_id") or payload.get("asker_id")):
            handle(job["kind"], payload)
    except Exception as e:  # any failure is retried or recorded, never lost
        last = job["attempts"] >= job["max_attempts"]
        log.warning("job %s (%s) failed on attempt %s%s", job["id"], job["kind"], job["attempts"], "" if last else ", will retry", exc_info=True)
        values = {"status": "failed" if last else "queued", "locked_until": None, "last_error": f"{type(e).__name__}: {e}"[:500]}
        if not last:
            values["run_after"] = (datetime.now(UTC) + timedelta(seconds=backoff(job["attempts"]))).isoformat()
    db.finish_job(job["id"], job["lease"], values)
    return True


def schedule(now: float | None = None) -> None:
    """Queue each periodic pass once per window. Every process calls this; the dedupe key keeps one job per window."""
    now = time.time() if now is None else now
    for kind, every in PERIODIC.items():
        enqueue(kind, key=f"{kind}:{int(now // every)}")


def purge_finished() -> None:
    db.purge_jobs((datetime.now(UTC) - KEEP).isoformat())


def _work() -> None:
    while True:
        _wake.clear()  # before the claim, so a job queued after it wakes this worker at once
        try:
            if run_one():
                continue
        except Exception:  # the database is down: wait and try again
            log.warning("job queue unreachable", exc_info=True)
        _wake.wait(POLL_S)


def _schedule_loop() -> None:
    stop = threading.Event()
    while True:
        try:
            schedule()
        except Exception:
            log.warning("scheduling periodic jobs failed", exc_info=True)
        stop.wait(60)


def start_background(workers: int = WORKERS) -> None:
    """Worker threads plus the periodic scheduler. ponytail: daemon threads, so a stop mid-job waits out the lease (SD-6.4)."""
    if workers <= 0:
        return
    for i in range(workers):
        threading.Thread(target=_work, name=f"job-{i}", daemon=True).start()
    threading.Thread(target=_schedule_loop, name="job-schedule", daemon=True).start()


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    os.environ["RETENTION_JOB"] = "0"  # the handlers import app.main; this process runs the workers itself
    from app.observability import configure_logging

    configure_logging()
    start_background(max(1, WORKERS))
    threading.Event().wait()
