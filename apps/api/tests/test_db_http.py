"""The HTTPS database layer: request shapes, one retry, fast failure. No network."""

import time

import httpx
import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import MemorySaver

from app import db
from app.agent import runtime
from app.main import app
from tests.conftest import USER


@pytest.fixture
def rest(monkeypatch):
    """Route db.client() to a MockTransport; tests set `handler`."""
    seen: list[httpx.Request] = []
    box = {"handler": lambda req: httpx.Response(200, json=[])}

    def transport(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return box["handler"](req)

    fake = httpx.Client(base_url="https://sb.test", transport=httpx.MockTransport(transport))
    monkeypatch.setattr(db, "client", lambda: fake)
    return box, seen


# conftest swaps these for in-memory fakes per test; keep the real ones captured at import time.
REAL = {name: getattr(db, name) for name in ("get_run", "mark_run_stopped")}


def real(name):
    return db.DatabaseUnavailable if name == "DatabaseUnavailable" else REAL[name]


def test_get_and_atomic_stop_request_shapes(rest):
    box, seen = rest
    box["handler"] = lambda req: httpx.Response(200, json=[{"id": "r1", "status": "running"}])
    assert real("get_run")("r1") == {"id": "r1", "status": "running"}
    assert seen[-1].url.params["id"] == "eq.r1"

    box["handler"] = lambda req: httpx.Response(200, json=[])  # nothing matched status=running
    assert real("mark_run_stopped")("r1", [], 0) is False
    assert seen[-1].method == "PATCH" and seen[-1].url.params["status"] == "eq.running"


def test_one_retry_then_fast_database_unavailable(rest):
    box, seen = rest

    def boom(req):
        raise httpx.ConnectTimeout("no route")

    box["handler"] = boom
    start = time.time()
    with pytest.raises(real("DatabaseUnavailable")):
        real("get_run")("r1")
    assert len(seen) == 2 and time.time() - start < 1  # tried twice, no sleeping


def test_retry_recovers_from_one_blip(rest):
    box, _ = rest
    calls = iter([httpx.Response(503, text="busy"), httpx.Response(200, json=[{"id": "r1"}])])
    box["handler"] = lambda req: next(calls)
    assert real("get_run")("r1") == {"id": "r1"}


def test_unreachable_database_is_a_503_not_a_hang(monkeypatch):
    def down(*_a, **_k):
        raise db.DatabaseUnavailable("down")

    monkeypatch.setattr(db, "get_run", down)
    r = TestClient(app, raise_server_exceptions=False).get("/runs/x")
    assert r.status_code == 503 and r.json()["detail"].startswith("Walkthru could not reach its database")


def test_lost_live_state_closes_run_instead_of_erroring(monkeypatch, fake_db):
    """After an API restart the in-memory agent state is gone; the next observation ends the run truthfully."""
    monkeypatch.setattr(runtime, "checkpointer", lambda: MemorySaver())
    runtime.graph.cache_clear()
    monkeypatch.setattr(db, "mark_run_stopped", lambda run_id, steps, tokens=0: fake_db[run_id].update(status="stopped", steps=steps) or True)
    fake_db["r1"] = {"id": "r1", "user_id": USER, "status": "running", "tier": "free", "steps": [{"thought": "t", "action": "click", "target_id": 1, "text": None, "confusion": 0, "url": "https://x.io/"}], "tokens": 0}
    obs = {"url": "https://x.io/next", "title": "t", "elements": [], "text": "", "errors": []}
    r = TestClient(app).post("/runs/r1/observe", json={"observation": obs})
    runtime.graph.cache_clear()
    assert r.status_code == 200 and r.json()["status"] == "stopped"
    assert fake_db["r1"]["steps"][-1]["interrupted"] is True
