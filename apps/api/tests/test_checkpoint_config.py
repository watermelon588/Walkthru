import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import MemorySaver

from app import main
from app.agent import runtime


def test_memory_is_development_only_and_invalid_config_never_falls_back(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("CHECKPOINTER", "memory")
    assert isinstance(runtime.make_checkpointer(), MemorySaver)
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError, match="Production requires"):
        runtime.make_checkpointer()
    monkeypatch.setenv("CHECKPOINTER", "postgress")
    with pytest.raises(RuntimeError, match="must be memory or postgres"):
        runtime.make_checkpointer()


def test_postgres_needs_a_url_and_rejects_transaction_pooler(monkeypatch):
    monkeypatch.setenv("CHECKPOINTER", "postgres")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("CHECKPOINT_DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="requires CHECKPOINT_DATABASE_URL"):
        runtime.make_checkpointer()
    monkeypatch.setenv("CHECKPOINT_DATABASE_URL", "postgresql://postgres:private-password@aws-0.pooler.supabase.com:6543/postgres")
    with pytest.raises(RuntimeError, match="not the Supabase transaction pooler") as error:
        runtime.make_checkpointer()
    assert "private-password" not in str(error.value)


def test_production_startup_refuses_missing_persistence(monkeypatch):
    runtime.close_checkpointer()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CHECKPOINTER", "postgres")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("CHECKPOINT_DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="requires CHECKPOINT_DATABASE_URL"), TestClient(main.app):
        pytest.fail("The API must not finish startup")


def test_concurrent_initialization_creates_only_one_checkpointer(monkeypatch):
    runtime.close_checkpointer()
    created = []
    def make():
        time.sleep(0.01)
        created.append(MemorySaver())
        return created[-1]
    monkeypatch.setattr(runtime, "make_checkpointer", make)
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: runtime.checkpointer(), range(8)))
        assert len(created) == 1 and all(saver is created[0] for saver in results)
    finally:
        runtime.close_checkpointer()
