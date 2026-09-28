"""The job queue's claim function (migrations/0001_initial.sql, SD-6.1) in a throwaway local Postgres: concurrent workers, leases, retries.

Skips when the Postgres server binaries (initdb, pg_ctl) are not on PATH or in PG_BIN.
"""

import os
import shutil
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor

import pytest

from app import db

MARK = "-- Durable job queue (SD-6.1"


def _bin(name: str) -> str | None:
    found = os.path.join(os.environ["PG_BIN"], name) if os.environ.get("PG_BIN") else shutil.which(name)
    return found if found and (os.path.exists(found) or os.path.exists(found + ".exe")) else None


@pytest.fixture(scope="module")
def sql(tmp_path_factory):
    psycopg = pytest.importorskip("psycopg")
    initdb, pg_ctl = _bin("initdb"), _bin("pg_ctl")
    if not initdb or not pg_ctl:
        pytest.skip("Postgres server binaries required")
    data = tmp_path_factory.mktemp("jobs-postgres") / "data"
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    quiet = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}  # pg_ctl's server keeps pipes open on Windows
    subprocess.run([initdb, "-D", str(data), "-A", "trust", "-U", "postgres", "-E", "UTF8"], check=True, **quiet)
    subprocess.run([pg_ctl, "-D", str(data), "-l", str(data.parent / "log"), "-o", f"-h 127.0.0.1 -p {port}", "-w", "start"], check=True, **quiet)
    dsn = f"host=127.0.0.1 port={port} dbname=postgres user=postgres"

    def query(statement: str, params: tuple | None = None) -> list[tuple]:
        with psycopg.connect(dsn, autocommit=True) as conn:
            cur = conn.execute(statement, params)
            return cur.fetchall() if cur.description else []

    try:
        query("create role anon; create role authenticated; create role service_role bypassrls")
        with open(db.SCHEMA, encoding="utf-8") as f:
            block = MARK + f.read().split(MARK, 1)[1]
        for statement in db.statements(block):
            query(statement)
        yield query
    finally:
        subprocess.run([pg_ctl, "-D", str(data), "-m", "immediate", "stop"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


@pytest.fixture
def q(sql):
    sql("truncate public.jobs")
    return sql


def add(q, key: str, **cols) -> None:
    names = ["kind", "dedupe_key", *cols]
    q(f"insert into public.jobs ({', '.join(names)}) values ({', '.join(['%s'] * len(names))})", ("t", key, *cols.values()))


def claim(q, lease_s: int = 60) -> tuple | None:
    rows = q("select id, attempts, lease, status from public.claim_job(%s)", (lease_s,))
    return rows[0] if rows else None


def test_concurrent_workers_never_share_a_job(q):
    for i in range(40):
        add(q, f"k{i}")

    def drain() -> list[int]:
        got = []
        while (job := claim(q)) is not None:
            got.append(job[0])
        return got

    with ThreadPoolExecutor(8) as pool:
        claimed = [i for part in pool.map(lambda _: drain(), range(8)) for i in part]
    assert len(claimed) == 40 and len(set(claimed)) == 40
    assert q("select count(*) from public.jobs where status = 'running' and attempts = 1 and lease is not null") == [(40,)]


def test_future_jobs_wait_and_dedupe_keys_are_unique(q):
    add(q, "later", run_after="2999-01-01T00:00:00Z")
    assert claim(q) is None
    q("insert into public.jobs (kind, dedupe_key) values ('t', 'later') on conflict (dedupe_key) do nothing")
    assert q("select count(*) from public.jobs") == [(1,)]


def test_a_dead_workers_job_is_claimed_again_then_failed_after_its_attempts(q):
    add(q, "crash", max_attempts=2)
    first = claim(q)
    assert claim(q) is None  # leased to the first worker
    q("update public.jobs set locked_until = now() - interval '1 second'")  # that worker died
    second = claim(q)
    assert second[0] == first[0] and second[1] == 2 and second[2] != first[2]  # new lease: the old holder cannot finish it
    q("update public.jobs set locked_until = now() - interval '1 second'")
    assert claim(q) is None
    assert q("select status, last_error from public.jobs") == [("failed", "worker stopped before finishing")]


def test_browsers_cannot_touch_the_queue(q):
    assert q("select has_table_privilege('anon', 'public.jobs', 'select'), has_table_privilege('authenticated', 'public.jobs', 'insert')") == [(False, False)]
    assert q("select has_function_privilege('authenticated', 'public.claim_job(integer)', 'execute')") == [(False,)]
