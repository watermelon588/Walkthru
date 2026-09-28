"""Real persistence, abrupt process exit, schema migration and privilege checks; never uses the live database."""

import json
import os
import subprocess
import sys
import uuid
from contextlib import asynccontextmanager

import psycopg
import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.postgres import PostgresSaver

from app import main, migrate
from app.agent import runtime
from scripts.checkpoint_smoke import ScriptedModel
from tests import test_migrate

MIGRATION = migrate.DIRECTORY / "0002_agent_checkpoints.sql"
cluster = test_migrate.cluster
conn = test_migrate.conn


def install(conn):
    with conn.transaction():
        conn.execute(MIGRATION.read_text(encoding="utf-8"))


def test_persona_survives_abrupt_process_exit_and_cleans_all_checkpoint_tables(conn):
    install(conn)
    thread = "smoke-" + uuid.uuid4().hex
    env = dict(os.environ, CHECKPOINT_DATABASE_URL=conn.info.dsn, CHECKPOINTER="postgres", APP_ENV="production",
               LANGCHAIN_TRACING_V2="false", LANGSMITH_TRACING="false")
    # os._exit deliberately skips all atexit/finally hooks, like a terminated worker.
    start = subprocess.run([sys.executable, "-c", "import os,sys; from scripts.checkpoint_smoke import run; run('start',sys.argv[1]); os._exit(0)", thread],
                           env=env, capture_output=True, text=True, timeout=45, check=True)
    assert json.loads(start.stdout)["steps"] == 1
    resume = subprocess.run([sys.executable, "-m", "scripts.checkpoint_smoke", "resume", thread],
                            env=env, capture_output=True, text=True, timeout=45, check=True)
    assert json.loads(resume.stdout) == {"thread": thread, "phase": "resume", "steps": 2, "status": "done"}
    for table in ("checkpoints", "checkpoint_blobs", "checkpoint_writes"):
        assert conn.execute(f"select count(*) from walkthru_checkpoints.{table}").fetchone()[0] == 0


def test_legacy_state_moves_atomically_and_browser_roles_cannot_read_it(conn):
    # Reproduce the old runtime's public-schema setup and existing stored customer state.
    PostgresSaver(conn).setup()
    conn.execute("insert into public.checkpoints(thread_id,checkpoint_id,checkpoint) values ('old-run','old-checkpoint','{}')")
    install(conn)
    assert conn.execute("select thread_id from walkthru_checkpoints.checkpoints").fetchone()[0] == "old-run"
    assert conn.execute("select to_regclass('public.checkpoints')").fetchone()[0] is None
    assert conn.execute("select max(v) from walkthru_checkpoints.checkpoint_migrations").fetchone()[0] == len(PostgresSaver.MIGRATIONS) - 1
    for role in ("anon", "authenticated", "service_role"):
        conn.execute(f"set role {role}")
        try:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute("select * from walkthru_checkpoints.checkpoints")
        finally:
            conn.execute("reset role")


def test_conflicting_schemas_roll_back_instead_of_discarding_state(conn):
    install(conn)
    conn.execute("create table public.checkpoints (id int)")
    with pytest.raises(psycopg.errors.RaiseException, match="both schemas"):
        install(conn)
    assert conn.execute("select to_regclass('public.checkpoints')").fetchone()[0]
    assert conn.execute("select to_regclass('walkthru_checkpoints.checkpoints')").fetchone()[0]


def test_startup_requires_migration_and_matching_version_and_pool_closes(conn, monkeypatch):
    runtime.close_checkpointer()
    monkeypatch.setenv("CHECKPOINT_DATABASE_URL", conn.info.dsn)
    monkeypatch.setenv("CHECKPOINTER", "postgres")
    with pytest.raises(RuntimeError, match="numbered agent checkpoint migration"):
        runtime.make_checkpointer()
    install(conn)
    runtime.initialize_checkpointer()
    saver = runtime.checkpointer()
    assert not saver.conn.closed
    runtime.close_checkpointer()
    assert saver.conn.closed
    conn.execute("insert into walkthru_checkpoints.checkpoint_migrations values (999)")
    with pytest.raises(RuntimeError, match="versions differ"):
        runtime.make_checkpointer()


def test_http_observation_resumes_after_api_lifespan_restart(conn, monkeypatch):
    install(conn)
    runtime.close_checkpointer()
    monkeypatch.setenv("CHECKPOINT_DATABASE_URL", conn.info.dsn)
    monkeypatch.setenv("CHECKPOINTER", "postgres")
    # A real restart creates a fresh MCP manager. Its single-use transport is outside this HTTP journey test.
    @asynccontextmanager
    async def transport_lifespan():
        yield
    monkeypatch.setattr(main.mcp_server.server.session_manager, "run", transport_lifespan)
    model = ScriptedModel("start")
    monkeypatch.setattr(runtime, "make_model", lambda tier: model)
    page = {"url": "https://fixture.test/", "title": "Guide", "text": "Guide page", "elements": [{"id": 1, "tag": "a", "text": "Guide"}]}
    with TestClient(main.app) as client:
        response = client.post("/runs", json={"site": page["url"], "goal": "read the guide", "observation": page})
        assert response.status_code == 200
        run_id = response.json()["run_id"]
        assert response.json()["action"]["action"] == "click" and model.calls == 1
        first_pool = runtime.checkpointer().conn
    assert first_pool.closed
    model = ScriptedModel("resume")
    with TestClient(main.app) as client:
        response = client.post(f"/runs/{run_id}/observe", json={"observation": page | {"url": "https://fixture.test/guide", "elements": []}})
        assert response.status_code == 200
        assert response.json()["status"] == "done" and len(response.json()["steps"]) == 2 and model.calls == 1
        assert runtime.checkpointer().conn is not first_pool
        assert client.get(f"/runs/{run_id}").json()["status"] == "done"
