"""The live-run service: `python -m app.runner`. Claims one queued test user at a time and walks the site.

One browser at a time is enforced in the database (claim_cloud_run), so a second copy of this service by mistake
waits its turn instead of doubling memory use. Reports are written by the ordinary job worker, as for every run.
"""

import logging
import os
import time

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
os.environ["RETENTION_JOB"] = "0"  # this process imports app.main for the run logic; it runs no schedulers
os.environ["JOB_WORKERS"] = "0"

from app import db
from app.agent import runtime
from app.observability import configure_logging
from app.runner import journey

log = logging.getLogger("walkthru.runner")
LEASE_S = 120  # renewed every step; one step (model call plus page settle) stays well under this
POLL_S = 3
LIMIT = max(1, int(os.environ.get("RUNNER_CONCURRENCY", "1")))  # ponytail: this loop is serial, so more needs more processes


def work_one() -> bool:
    row = db.claim_cloud_run(LEASE_S, LIMIT)
    if not row:
        return False
    log.info("live run %s started for %s", row["id"], row["site"][:80])
    status, error = journey.run(row, lambda values: db.hold_cloud_run(row["id"], row["lease"], LEASE_S, values))
    db.end_cloud_run(row["id"], row["lease"], status, error)
    log.info("live run %s ended: %s%s", row["id"], status, f" ({error})" if error else "")
    return True


def main() -> None:
    configure_logging()
    logging.getLogger("walkthru").setLevel(logging.INFO)
    runtime.initialize_checkpointer()
    log.info("live-run service ready, %s browser at a time", LIMIT)
    try:
        while True:
            try:
                if not work_one():
                    time.sleep(POLL_S)
            except Exception:
                log.exception("live-run loop error")
                time.sleep(POLL_S)
    finally:
        runtime.close_checkpointer()


if __name__ == "__main__":
    main()
