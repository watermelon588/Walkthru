"""Runs table access over Supabase's HTTPS Data API (PostgREST) with the server secret key.

Why HTTPS and not a Postgres socket: the direct database host is IPv6-only and raw Postgres to the
project region drops connections on some networks, while the HTTPS API sits behind Cloudflare and
reuses one keep-alive connection. Every call fails fast (4 s connect) and retries once.
`setup()` alone still speaks SQL, because schema changes need it; run it with `python -m app.db`.
"""

import json
import os
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any

import httpx

SCHEMA = os.path.join(os.path.dirname(__file__), "..", "schema.sql")
BUCKET = "run-evidence"


class DatabaseUnavailable(Exception):
    """Supabase could not be reached or answered with a server error. Mapped to a fast 503."""


@lru_cache(maxsize=1)
def client() -> httpx.Client:
    key = os.environ["SUPABASE_SECRET_KEY"]
    return httpx.Client(
        base_url=os.environ["SUPABASE_URL"],
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
        timeout=httpx.Timeout(10.0, connect=4.0),
        limits=httpx.Limits(max_keepalive_connections=8, keepalive_expiry=60),
    )


def _request(method: str, path: str, *, params: dict | None = None, json_body: Any = None, prefer: str | None = None) -> Any:
    headers = {"Prefer": prefer} if prefer else {}
    for attempt in range(2):  # every call here is idempotent, so one retry is safe
        try:
            r = client().request(method, path, params=params, json=json_body, headers=headers)
        except httpx.TransportError as e:
            if attempt:
                raise DatabaseUnavailable(str(e) or type(e).__name__) from e
            continue
        if r.status_code >= 500:
            if attempt:
                raise DatabaseUnavailable(f"{r.status_code} {r.text[:200]}")
            continue
        r.raise_for_status()
        return r.json() if r.content else None
    return None


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _rows(params: dict) -> list[dict]:
    return _request("GET", "/rest/v1/runs", params=params) or []


def _patch(filters: dict, values: dict, *, returning: bool = False) -> list[dict]:
    prefer = "return=representation" if returning else "return=minimal"
    return _request("PATCH", "/rest/v1/runs", params=filters | ({"select": "id"} if returning else {}), json_body=values, prefer=prefer) or []


def insert_run(run_id: str, user_id: str | None, site: str, goal: str, persona: str, tier: str, logged_in: bool, *, kind: str = "test", email: str | None = None, public: bool = False) -> None:
    row = {"id": run_id, "user_id": user_id, "site": site, "goal": goal, "persona": persona, "tier": tier, "logged_in": logged_in, "kind": kind, "email": email, "public": public}
    _request("POST", "/rest/v1/runs", json_body=row, prefer="resolution=ignore-duplicates,return=minimal")


def get_run(run_id: str) -> dict | None:
    rows = _rows({"id": f"eq.{run_id}", "select": "*", "limit": "1"})
    return rows[0] if rows else None


def update_run(run_id: str, status: str, steps: list[dict], tokens: int = 0) -> None:
    _patch({"id": f"eq.{run_id}"}, {"status": status, "steps": steps, "tokens": tokens, "updated_at": _now()})


def mark_run_stopped(run_id: str, steps: list[dict], tokens: int = 0) -> bool:
    """Atomically close a running row. False means another request already closed it."""
    changed = _patch({"id": f"eq.{run_id}", "status": "eq.running"}, {"status": "stopped", "steps": steps, "tokens": tokens, "updated_at": _now()}, returning=True)
    return bool(changed)


def set_report(run_id: str, report: dict, status: str | None = None) -> None:
    values = {"report": report, "tokens": report.get("tokens", 0), "updated_at": _now()}
    if status:
        values["status"] = status
    _patch({"id": f"eq.{run_id}"}, values)


def set_public(run_id: str, public: bool = True) -> None:
    _patch({"id": f"eq.{run_id}"}, {"public": public, "updated_at": _now()})


def runs_for_user(user_id: str) -> list[dict]:
    return _rows({"user_id": f"eq.{user_id}", "select": "*", "order": "created_at.asc"})


def run_ids_for_user(user_id: str) -> list[str]:
    return [r["id"] for r in _rows({"user_id": f"eq.{user_id}", "select": "id"})]


def evidence_objects(run_ids: list[str]) -> list[str]:
    """Storage paths under each run's folder, through the Storage API."""
    names: list[str] = []
    for run_id in run_ids:
        listed = _request("POST", f"/storage/v1/object/list/{BUCKET}", json_body={"prefix": run_id, "limit": 1000}) or []
        names += [f"{run_id}/{o['name']}" for o in listed if o.get("name") and not o["name"].startswith(".")]
    return names


def _cutoff(days: int) -> str:
    return (datetime.now(UTC) - timedelta(days=days)).isoformat()


def expired_evidence_runs(days: int, limit: int = 100) -> list[dict]:
    return _rows({"kind": "eq.test", "evidence_purged_at": "is.null", "created_at": f"lt.{_cutoff(days)}", "select": "id,steps", "order": "created_at.asc", "limit": str(limit)})


def mark_evidence_purged(run_id: str, steps: list[dict]) -> None:
    _patch({"id": f"eq.{run_id}"}, {"steps": steps, "evidence_purged_at": _now()})


def forget_scan_emails(days: int) -> None:
    """Instant Scan emails are only needed to deliver the report."""
    _patch({"kind": "eq.scan", "email": "not.is.null", "created_at": f"lt.{_cutoff(days)}"}, {"email": None})


def delete_runs(run_ids: list[str]) -> None:
    if run_ids:
        _request("DELETE", "/rest/v1/runs", params={"id": f"in.({','.join(run_ids)})"}, prefer="return=minimal")


def setup() -> None:
    """Apply schema.sql over a direct SQL connection (admin task, retried by hand if the network drops)."""
    import psycopg

    with open(SCHEMA, encoding="utf-8") as f, psycopg.connect(os.environ["DATABASE_URL"], autocommit=True, connect_timeout=15) as conn:
        sql = "\n".join(line for line in f if not line.lstrip().startswith("--"))
        for stmt in sql.split(";"):
            if stmt.strip():
                conn.execute(stmt)


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    setup()
    print(json.dumps({"ok": True, "runs": get_run("__none__") is None}))
