"""Runs table access. Plain SQL through a psycopg pool; no ORM."""

import atexit
import json
import os
from functools import lru_cache
from typing import Any

from psycopg import OperationalError
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

SCHEMA = os.path.join(os.path.dirname(__file__), "..", "schema.sql")


@lru_cache(maxsize=1)
def pool() -> ConnectionPool:
    p = ConnectionPool(
        os.environ["DATABASE_URL"],
        min_size=0,
        max_size=4,
        kwargs={"row_factory": dict_row},
        check=ConnectionPool.check_connection,
        max_lifetime=300,
        max_idle=60,
        reconnect_timeout=10,
        open=True,
    )
    atexit.register(p.close)
    return p


def _execute(query: str, params: tuple[Any, ...] = (), *, fetchone: bool = False) -> dict | None:
    """Execute once more when Supabase closes an otherwise healthy pooled connection."""
    for attempt in range(2):
        try:
            with pool().connection() as conn:
                cursor = conn.execute(query, params)
                return cursor.fetchone() if fetchone else None
        except OperationalError:
            if attempt:
                raise
    return None


def _fetchall(query: str, params: tuple[Any, ...] = ()) -> list[dict]:
    for attempt in range(2):
        try:
            with pool().connection() as conn:
                return conn.execute(query, params).fetchall()
        except OperationalError:
            if attempt:
                raise
    return []


def insert_run(run_id: str, user_id: str | None, site: str, goal: str, persona: str, tier: str, logged_in: bool, *, kind: str = "test", email: str | None = None, public: bool = False) -> None:
    _execute(
        "insert into runs (id, user_id, site, goal, persona, tier, logged_in, kind, email, public) "
        "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) on conflict (id) do nothing",
        (run_id, user_id, site, goal, persona, tier, logged_in, kind, email, public),
    )


def get_run(run_id: str) -> dict | None:
    return _execute("select * from runs where id = %s", (run_id,), fetchone=True)


def update_run(run_id: str, status: str, steps: list[dict], tokens: int = 0) -> None:
    _execute("update runs set status = %s, steps = %s, tokens = %s, updated_at = now() where id = %s", (status, Jsonb(steps), tokens, run_id))


def mark_run_stopped(run_id: str, steps: list[dict], tokens: int = 0) -> bool:
    """Atomically close a running row. False means another request already closed it."""
    row = _execute(
        "update runs set status = 'stopped', steps = %s, tokens = %s, updated_at = now() "
        "where id = %s and status = 'running' returning id",
        (Jsonb(steps), tokens, run_id),
        fetchone=True,
    )
    return row is not None


def set_report(run_id: str, report: dict, status: str | None = None) -> None:
    _execute(
        "update runs set report = %s, tokens = %s, status = coalesce(%s, status), updated_at = now() where id = %s",
        (Jsonb(report), report.get("tokens", 0), status, run_id),
    )


def set_public(run_id: str, public: bool = True) -> None:
    _execute("update runs set public = %s, updated_at = now() where id = %s", (public, run_id))


def runs_for_user(user_id: str) -> list[dict]:
    return _fetchall("select * from runs where user_id = %s order by created_at", (user_id,))


def run_ids_for_user(user_id: str) -> list[str]:
    return [r["id"] for r in _fetchall("select id from runs where user_id = %s", (user_id,))]


def evidence_objects(run_ids: list[str]) -> list[str]:
    if not run_ids:
        return []
    rows = _fetchall("select name from storage.objects where bucket_id = 'run-evidence' and split_part(name, '/', 1) = any(%s)", (run_ids,))
    return [r["name"] for r in rows]


def expired_evidence_runs(days: int, limit: int = 100) -> list[dict]:
    return _fetchall(
        "select id, steps from runs where kind = 'test' and evidence_purged_at is null "
        "and created_at < now() - make_interval(days => %s) order by created_at limit %s",
        (days, limit),
    )


def mark_evidence_purged(run_id: str, steps: list[dict]) -> None:
    _execute("update runs set steps = %s, evidence_purged_at = now() where id = %s", (Jsonb(steps), run_id))


def forget_scan_emails(days: int) -> None:
    """Instant Scan emails are only needed to deliver the report."""
    _execute("update runs set email = null where kind = 'scan' and email is not null and created_at < now() - make_interval(days => %s)", (days,))


def delete_runs(run_ids: list[str]) -> None:
    _execute("delete from runs where id = any(%s)", (run_ids,))


def setup() -> None:
    with open(SCHEMA, encoding="utf-8") as f, pool().connection() as conn:
        sql = "\n".join(line for line in f if not line.lstrip().startswith("--"))
        for stmt in sql.split(";"):
            if stmt.strip():
                conn.execute(stmt)


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    setup()
    print(json.dumps({"ok": True, "runs": get_run("__none__") is None}))
