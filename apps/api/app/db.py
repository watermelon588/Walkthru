"""Runs table access. Plain SQL through a psycopg pool; no ORM."""

import atexit
import json
import os
from functools import lru_cache

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

SCHEMA = os.path.join(os.path.dirname(__file__), "..", "schema.sql")


@lru_cache(maxsize=1)
def pool() -> ConnectionPool:
    p = ConnectionPool(os.environ["DATABASE_URL"], min_size=1, max_size=4, kwargs={"row_factory": dict_row}, open=True)
    atexit.register(p.close)
    return p


def insert_run(run_id: str, user_id: str | None, site: str, goal: str, persona: str, tier: str, logged_in: bool, *, kind: str = "test", email: str | None = None, public: bool = False) -> None:
    with pool().connection() as conn:
        conn.execute(
            "insert into runs (id, user_id, site, goal, persona, tier, logged_in, kind, email, public) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (run_id, user_id, site, goal, persona, tier, logged_in, kind, email, public),
        )


def get_run(run_id: str) -> dict | None:
    with pool().connection() as conn:
        return conn.execute("select * from runs where id = %s", (run_id,)).fetchone()


def update_run(run_id: str, status: str, steps: list[dict], tokens: int = 0) -> None:
    with pool().connection() as conn:
        conn.execute("update runs set status = %s, steps = %s, tokens = %s, updated_at = now() where id = %s", (status, Jsonb(steps), tokens, run_id))


def set_report(run_id: str, report: dict, status: str | None = None) -> None:
    with pool().connection() as conn:
        conn.execute(
            "update runs set report = %s, tokens = %s, status = coalesce(%s, status), updated_at = now() where id = %s",
            (Jsonb(report), report.get("tokens", 0), status, run_id),
        )


def set_public(run_id: str, public: bool = True) -> None:
    with pool().connection() as conn:
        conn.execute("update runs set public = %s, updated_at = now() where id = %s", (public, run_id))


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
