"""Evidence retention and owner-initiated deletion.

Screenshots expire after EVIDENCE_RETENTION_DAYS; runs and reports stay until the owner deletes them.
Storage objects are removed through the Storage API (Supabase blocks direct deletes from storage.objects).
Order matters: objects go first, rows last, so a failed storage call never leaves unreachable files.

    .venv/Scripts/python -m app.retention      # one purge pass, for cron or manual use
"""

import logging
import os

import httpx

from app import db

log = logging.getLogger("walkthru.retention")
BUCKET = "run-evidence"
RETENTION_DAYS = int(os.environ.get("EVIDENCE_RETENTION_DAYS", "30"))


def _admin_headers() -> dict[str, str]:
    key = os.environ["SUPABASE_SECRET_KEY"]
    return {"apikey": key, "Authorization": f"Bearer {key}"}


def delete_objects(names: list[str]) -> int:
    for i in range(0, len(names), 1000):  # Storage API accepts up to 1000 prefixes per call
        r = httpx.request("DELETE", f"{os.environ['SUPABASE_URL']}/storage/v1/object/{BUCKET}", headers=_admin_headers(), json={"prefixes": names[i : i + 1000]}, timeout=30)
        r.raise_for_status()
    return len(names)


def strip_evidence(steps: list[dict]) -> list[dict]:
    return [{k: v for k, v in s.items() if k != "evidence"} for s in steps]


def purge_expired(days: int = RETENTION_DAYS) -> dict:
    """Delete screenshots of runs older than `days`; keep the run, its steps and its report."""
    runs = db.expired_evidence_runs(days)
    removed = 0
    for run in runs:
        removed += delete_objects(db.evidence_objects([run["id"]]))
        db.mark_evidence_purged(run["id"], strip_evidence(run["steps"] or []))
    return {"runs": len(runs), "objects": removed}


def delete_runs(run_ids: list[str]) -> None:
    from app.agent import runtime

    if not run_ids:
        return
    delete_objects(db.evidence_objects(run_ids))
    for run_id in run_ids:
        runtime.checkpointer().delete_thread(run_id)
    db.delete_runs(run_ids)


def delete_account(user_id: str) -> None:
    delete_runs(db.run_ids_for_user(user_id))
    r = httpx.delete(f"{os.environ['SUPABASE_URL']}/auth/v1/admin/users/{user_id}", headers=_admin_headers(), timeout=30)
    if r.status_code not in (200, 204, 404):
        r.raise_for_status()


def run_pass() -> None:
    """The six-hourly `retention` job (app/jobs.py): expired screenshots, run audit rows past 90 days
    (docs/agent-safety-plan.md section 6), finished jobs and expired request responses.
    Each part runs even when another fails; the next window retries."""
    from app import abuse, jobs

    def old_limits() -> None:  # rate limit windows that ended a day ago (app/limits.py)
        db.purge_rate_limits(abuse._ago(days=1))

    for name, part in (("evidence purge", purge_expired), ("run audit purge", abuse.purge_old), ("job purge", jobs.purge_finished),
                       ("rate limit purge", old_limits), ("request response purge", db.expire_run_requests)):
        try:
            result = part()
            if name == "evidence purge" and result["runs"]:
                log.info("evidence purge: %s", result)
        except Exception:
            log.exception("%s failed", name)


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    print(purge_expired())
