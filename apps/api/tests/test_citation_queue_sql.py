"""Real SQL concurrency checks in a disposable loopback-only Postgres cluster."""
import json
import shutil
import socket
import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psycopg
import pytest

from app import db


@pytest.fixture(scope="module")
def sql(tmp_path_factory):
    initdb = shutil.which("initdb")
    pg_ctl = shutil.which("pg_ctl")
    if not initdb or not pg_ctl:
        pytest.skip("Postgres server binaries required")
    root = tmp_path_factory.mktemp("citation-postgres")
    data = root / "data"
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    subprocess.run([initdb, "-D", str(data), "-A", "trust", "-U", "postgres", "--no-locale", "-E", "UTF8"], check=True, capture_output=True)
    # No captured pipes: the server pg_ctl starts inherits them on Windows, and run() would wait for it forever.
    subprocess.run([pg_ctl, "-D", str(data), "-l", str(root / "server.log"), "-o", f"-h 127.0.0.1 -p {port}", "-w", "start"], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"host=127.0.0.1 port={port} dbname=postgres user=postgres"
    def query(statement, params=None):
        with psycopg.connect(url) as conn:
            cur = conn.execute(statement, params)
            return cur.fetchall() if cur.description else []
    try:
        query("create role anon; create role authenticated; create role service_role bypassrls; create schema auth; create table auth.users(id uuid primary key)")
        schema = Path(db.SCHEMA).read_text(encoding="utf-8")
        block = schema.split("-- AI citation tracking (P3.2, 2026-09-26)", 1)[1].split("alter table public.notifications", 1)[0]
        # Restore the comment prefix before the first create table.
        block = block[block.index("create table"):]
        for _ in range(2):
            for statement in db.statements(block):
                query(statement)
        yield query
    finally:
        subprocess.run([pg_ctl, "-D", str(data), "-m", "fast", "-w", "stop"], check=True, capture_output=True)


@pytest.fixture
def site(sql):
    sql("truncate citation_checks, citation_prompts, citation_sites, citation_quota, auth.users cascade")
    user, site = uuid.uuid4(), uuid.uuid4()
    sql("insert into auth.users values (%s)", (user,))
    sql("insert into citation_sites(id,user_id,site,brand) values (%s,%s,'https://acme.example','Acme')", (site, user))
    return site


def enqueue(sql, site, batch=None, count=1, cap=20):
    rows = [{"prompt": f"Best app {i}?", "engine": "web", "result": {}} for i in range(count)]
    return sql("select queue_citation_batch(%s,%s,%s::jsonb,%s::jsonb,false)",
               (site, batch or uuid.uuid4(), json.dumps(rows), json.dumps({"web": cap})))[0][0]


def claim(sql, id, token=None, attempts=0, cap=1, gap=0):
    return sql("select claim_citation_job(%s,%s,'web',%s,%s,%s)", (id, attempts, cap, gap, token or uuid.uuid4()))[0][0]


def test_admission_is_idempotent_and_rejects_pending_and_excess_backlog(sql, site):
    batch = uuid.uuid4()
    assert enqueue(sql, site, batch, count=8, cap=1) == "capacity"
    assert enqueue(sql, site, batch) == "ok"
    assert enqueue(sql, site, batch) == "ok"
    assert enqueue(sql, site) == "pending"
    assert sql("select count(*) from citation_checks")[0][0] == 1


def test_parallel_claims_cannot_double_spend_last_quota_slot(sql, site):
    assert enqueue(sql, site, count=2) == "ok"
    ids = [r[0] for r in sql("select id from citation_checks")]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda id: claim(sql, id), ids))
    assert sum(results) == 1
    assert sql("select used from citation_quota")[0][0] == 1


def test_lease_is_exclusive_replay_safe_and_recovers_after_expiry(sql, site):
    enqueue(sql, site)
    id = sql("select id from citation_checks")[0][0]
    token = uuid.uuid4()
    assert claim(sql, id, token, cap=10)
    assert claim(sql, id, token, cap=10)  # transport retry
    assert not claim(sql, id, attempts=1, cap=10)
    assert sql("select used from citation_quota")[0][0] == 1
    sql("update citation_checks set lease_until = now() - interval '1 second'")
    assert claim(sql, id, attempts=1, cap=10)
    assert sql("select used from citation_quota")[0][0] == 2
    # Old worker cannot overwrite its replacement's answer.
    assert sql("update citation_checks set answer='stale' where id=%s and lease_token=%s returning id", (id, token)) == []


def test_daily_rollover_preserves_cooldown_and_anonymous_cannot_call_rpc(sql, site):
    enqueue(sql, site, count=2)
    ids = [r[0] for r in sql("select id from citation_checks")]
    assert claim(sql, ids[0], gap=60)
    sql("update citation_quota set day = current_date - 1")
    assert not claim(sql, ids[1])  # reset is not a bypass for provider spacing
    sql("update citation_quota set next_at = now() - interval '1 second'")
    assert claim(sql, ids[1])
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        sql("set role anon; select claim_citation_job(1,0,'web',20,0,gen_random_uuid())")
