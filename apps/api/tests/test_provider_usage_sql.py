"""R-S7 proposed migration on disposable PostgreSQL, never the configured database."""

import copy
import json
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor

import psycopg
import pytest
from psycopg.types.json import Jsonb

from app import db, migrate
from app import provider_usage as usage
from tests import test_migrate

cluster = test_migrate.cluster
conn = test_migrate.conn


def identity():
    return {"operation_id": str(uuid.uuid4()), "stage_id": str(uuid.uuid4()), "stage": "synthesis", "attempt_number": 1,
            "provider": "groq", "model": "openai/gpt-oss-120b", "run_id": str(uuid.uuid4()), "user_id": None,
            "job_id": None, "job_attempt": None, "request_id": None}


def result():
    packet = usage.normalize({"input_tokens": 10, "output_tokens": 10})
    return {"state": "succeeded", "error_kind": None, "duration_ms": 3, "usage": packet,
            "estimate": usage.estimate("groq", "openai/gpt-oss-120b", packet), "provider_request_id_hash": None}


def begin(c, identifier, meta):
    return c.execute("select public.begin_provider_attempt(%s,%s)", (identifier, Jsonb(meta))).fetchone()[0]


def finish(c, identifier, value):
    return c.execute("select public.finish_provider_attempt(%s,%s)", (identifier, Jsonb(value))).fetchone()[0]


def test_concurrent_duplicate_acknowledgements_and_conflicting_terminal_writes(conn):
    migrate.up(conn)
    identifier, meta, value = str(uuid.uuid4()), identity(), result()
    def duplicate(_):
        with psycopg.connect(conn.info.dsn, autocommit=True) as c:
            return begin(c, identifier, meta), finish(c, identifier, value)
    with ThreadPoolExecutor(max_workers=6) as executor:
        assert list(executor.map(duplicate, range(6))) == [(True, True)] * 6
    assert conn.execute("select count(*) from provider_attempts").fetchone()[0] == 1
    assert begin(conn, identifier, meta | {"model": "other"}) is False
    assert finish(conn, identifier, value | {"duration_ms": 4}) is False
    assert finish(conn, uuid.uuid4(), value) is False


def test_pending_crash_record_survives_process_exit_and_new_stage_retry(conn):
    migrate.up(conn)
    identifier, meta = str(uuid.uuid4()), identity()
    script = """
import json,sys,psycopg
from psycopg.types.json import Jsonb
with psycopg.connect(sys.argv[1],autocommit=True) as c:
    assert c.execute('select begin_provider_attempt(%s,%s)',(sys.argv[2],Jsonb(json.loads(sys.argv[3])))).fetchone()[0]
"""
    subprocess.run([sys.executable, "-c", script, conn.info.dsn, identifier, json.dumps(meta)], check=True, capture_output=True)
    # A second process/connection sees the uncertain receipt. No lease expiry erases it.
    with psycopg.connect(conn.info.dsn, autocommit=True) as restarted:
        assert restarted.execute("select state,result from provider_attempts where id=%s", (identifier,)).fetchone() == ("pending", None)
        retry = meta | {"stage_id": str(uuid.uuid4()), "job_attempt": 2}
        assert begin(restarted, uuid.uuid4(), retry)
        assert finish(restarted, identifier, result())
    assert conn.execute("select count(*) from provider_attempts where identity->>'operation_id'=%s", (meta["operation_id"],)).fetchone()[0] == 2


@pytest.mark.parametrize("role", ["anon", "authenticated"])
def test_rls_and_rpc_permissions_deny_public_and_customer_roles(conn, role):
    migrate.up(conn)
    identifier, meta = str(uuid.uuid4()), identity()
    assert begin(conn, identifier, meta)
    conn.execute(f"set role {role}")
    try:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("select * from public.provider_attempts")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            begin(conn, str(uuid.uuid4()), identity())
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            finish(conn, identifier, result())
    finally:
        conn.execute("reset role")
    conn.execute("set role service_role")
    try:
        assert finish(conn, identifier, result())
        assert conn.execute("select count(*) from provider_attempts").fetchone()[0] == 1
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("delete from provider_attempts")
    finally:
        conn.execute("reset role")


def test_unexpected_private_fields_and_non_numeric_usage_rejected(conn):
    migrate.up(conn)
    identifier, meta = str(uuid.uuid4()), identity()
    with pytest.raises(psycopg.Error):
        begin(conn, identifier, meta | {"prompt": "secret"})
    assert begin(conn, identifier, meta)
    for field, invalid in (("prompt", "private"), ("input_tokens", "password"), ("input_tokens", True), ("input_tokens", -1)):
        value = result()
        value["usage"][field] = invalid
        with pytest.raises(psycopg.Error):
            finish(conn, identifier, value)
    bad = result() | {"response": "private"}
    with pytest.raises(psycopg.Error):
        finish(conn, identifier, bad)
    bad = copy.deepcopy(result())
    bad["estimate"]["total_cost_microusd"] = 0
    with pytest.raises(psycopg.Error):
        finish(conn, identifier, bad)
    assert conn.execute("select state from provider_attempts").fetchone()[0] == "pending"


def test_http_acknowledgement_retry_is_same_receipt_and_terminal_data(conn, monkeypatch):
    migrate.up(conn)
    paths, counts = [], {}
    import httpx
    def request(method, path, *, params, json, headers):
        paths.append((path, copy.deepcopy(json)))
        identifier = json["p_id"]
        out = begin(conn, identifier, json["p_identity"]) if "p_identity" in json else finish(conn, identifier, json["p_result"])
        counts[path] = counts.get(path, 0) + 1
        if counts[path] == 1:
            raise httpx.ReadTimeout("lost acknowledgement")
        return httpx.Response(200, json=out, request=httpx.Request(method, "https://offline.test" + path))
    monkeypatch.setattr(db, "client", lambda: type("Client", (), {"request": staticmethod(request)})())
    monkeypatch.setenv("PROVIDER_USAGE", "postgres")
    dispatched = []
    with usage.stage("synthesis"), usage.attempt("groq", "openai/gpt-oss-120b"):
        dispatched.append("once")
        usage.capture({"input_tokens": 10, "output_tokens": 10})
    assert dispatched == ["once"] and len(paths) == 4
    assert paths[0] == paths[1] and paths[2] == paths[3]
    assert conn.execute("select count(*) from provider_attempts where state='succeeded'").fetchone()[0] == 1


def test_migration_can_be_rolled_back_and_reapplied_locally(conn):
    applied = migrate.up(conn)
    assert "0004" in applied
    later = [v for v in applied if v > "0004"]  # newer migrations (0005 run reservations) roll back first
    assert [migrate.down(conn) for _ in range(len(later) + 1)] == [*reversed(later), "0004"]
    assert conn.execute("select to_regclass('public.provider_attempts')").fetchone()[0] is None
    assert migrate.up(conn) == ["0004", *later]
