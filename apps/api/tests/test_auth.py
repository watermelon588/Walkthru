"""Auth boundary: no token -> 401; another user's run -> 404; Supabase check is cached."""

import httpx
from fastapi.testclient import TestClient

from app import auth
from app.main import app
from tests.conftest import USER


def test_missing_token_is_401(signed_in):
    app.dependency_overrides.clear()  # use the real dependency
    assert TestClient(app).get("/runs/abc").status_code == 401
    assert TestClient(app).get("/runs/abc", headers={"Authorization": "Basic x"}).status_code == 401


def test_supabase_check_and_cache(signed_in, monkeypatch):
    app.dependency_overrides.clear()
    calls = []

    def fake_get(url, headers, timeout):
        calls.append(headers["Authorization"])
        ok = headers["Authorization"] == "Bearer good"
        return httpx.Response(200 if ok else 401, json={"id": USER} if ok else {})

    monkeypatch.setattr(auth.httpx, "get", fake_get)
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "pk")
    auth._cache.clear()
    c = TestClient(app)
    assert c.get("/runs/nope", headers={"Authorization": "Bearer bad"}).status_code == 401
    assert c.get("/runs/nope", headers={"Authorization": "Bearer good"}).status_code == 404  # authed, run unknown
    assert c.get("/runs/nope", headers={"Authorization": "Bearer good"}).status_code == 404
    assert calls.count("Bearer good") == 1  # second call served from cache


def test_other_users_run_is_404(fake_db):
    fake_db["r1"] = {"id": "r1", "user_id": "someone-else", "tier": "free", "status": "running", "steps": []}
    fake_db["r2"] = {"id": "r2", "user_id": USER, "tier": "free", "status": "done", "steps": [{"action": "done"}]}
    c = TestClient(app)
    assert c.get("/runs/r1").status_code == 404
    assert c.get("/runs/r2").json()["status"] == "done"
