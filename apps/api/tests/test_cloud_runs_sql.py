"""The live-run queue's claim function (migrations/0007_cloud_runs.sql) in a throwaway local Postgres: one browser
at a time, whoever asks, and an interrupted run is closed instead of replayed.

Skips when the Postgres server binaries (initdb, pg_ctl) are not on PATH or in PG_BIN.
"""

import os
import socket
import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

from app import db
from tests.test_jobs_sql import _bin

MIGRATION = os.path.join(os.path.dirname(db.SCHEMA), "0007_cloud_runs.sql")
USER = str(uuid.uuid4())


@pytest.fixture(scope="module")
def sql(tmp_path_factory):
    psycopg = pytest.importorskip("psycopg")
    initdb, pg_ctl = _bin("initdb"), _bin("pg_ctl")
    if not initdb or not pg_ctl:
        pytest.skip("Postgres server binaries required")
    data = tmp_path_factory.mktemp("cloud-runs-postgres") / "data"
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    quiet = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    subprocess.run([initdb, "-D", str(data), "-A", "trust", "-U", "postgres", "-E", "UTF8"], check=True, **quiet)
    subprocess.run([pg_ctl, "-D", str(data), "-l", str(data.parent / "log"), "-o", f"-h 127.0.0.1 -p {port}", "-w", "start"], check=True, **quiet)
    dsn = f"host=127.0.0.1 port={port} dbname=postgres user=postgres"

    def query(statement: str, params: tuple | None = None) -> list[tuple]:
        with psycopg.connect(dsn, autocommit=True) as conn:
            cur = conn.execute(statement, params)
            return cur.fetchall() if cur.description else []

    try:
        query("create role anon; create role authenticated; create role service_role bypassrls")
        query("create schema auth; create table auth.users (id uuid primary key)")
        query("insert into auth.users values (%s)", (USER,))
        with open(MIGRATION, encoding="utf-8") as f:
            for statement in db.statements(f.read()):
                query(statement)
        yield query
    finally:
        subprocess.run([pg_ctl, "-D", str(data), "-m", "immediate", "stop"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


@pytest.fixture
def q(sql):
    sql("truncate public.cloud_runs")
    return sql


def queue(q, n: int) -> list[str]:
    ids = []
    for i in range(n):
        ids.append(str(q("insert into cloud_runs (user_id, group_id, site, goal, persona, max_steps, created_at) "
                         "values (%s, gen_random_uuid(), 'https://example.com', 'find pricing', 'first_timer', 10, now() + make_interval(secs => %s)) returning id",
                         (USER, i))[0][0]))
    return ids


def claim(q, limit: int = 1, lease: int = 120) -> list[tuple]:
    return q("select id, status, lease from claim_cloud_run(%s, %s)", (lease, limit))


def test_the_oldest_queued_test_user_is_claimed_and_the_next_waits(q):
    first, second = queue(q, 2)
    got = claim(q)
    assert [str(r[0]) for r in got] == [first] and got[0][1] == "running" and got[0][2]
    assert claim(q) == []  # one browser at a time
    q("update cloud_runs set status = 'finished' where id = %s", (first,))
    assert [str(r[0]) for r in claim(q)] == [second]


def test_many_runners_asking_at_once_start_one_browser(q):
    queue(q, 6)
    with ThreadPoolExecutor(8) as pool:
        got = [r for rows in pool.map(lambda _: claim(q), range(8)) for r in rows]
    assert len(got) == 1
    assert q("select count(*) from cloud_runs where status = 'running'")[0][0] == 1


def test_a_higher_limit_allows_that_many(q):
    queue(q, 3)
    assert len(claim(q, 2)) == 1 and len(claim(q, 2)) == 1 and claim(q, 2) == []


def test_a_run_whose_runner_died_is_closed_not_replayed(q):
    first, second = queue(q, 2)
    claim(q)
    q("update cloud_runs set locked_until = now() - interval '1 second' where id = %s", (first,))
    assert [str(r[0]) for r in claim(q)] == [second]
    status, error, lease = q("select status, error, lease from cloud_runs where id = %s", (first,))[0]
    assert status == "failed" and error.startswith("interrupted") and lease is None


def test_browsers_cannot_read_or_claim(q):
    assert q("select has_table_privilege('authenticated', 'public.cloud_runs', 'select')")[0][0] is False
    assert q("select has_function_privilege('anon', 'public.claim_cloud_run(integer, integer)', 'execute')")[0][0] is False
    assert q("select has_function_privilege('service_role', 'public.claim_cloud_run(integer, integer)', 'execute')")[0][0] is True
