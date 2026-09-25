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
        return httpx.Response(200 if ok else 401, json={"id": USER, "email": "t@x.io"} if ok else {})

    monkeypatch.setattr(auth.httpx, "get", fake_get)
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "pk")
    auth._cache.clear()
    c = TestClient(app)
    assert c.get("/runs/nope", headers={"Authorization": "Bearer bad"}).status_code == 401
    assert c.get("/runs/nope", headers={"Authorization": "Bearer good"}).status_code == 404  # authed, run unknown
    assert c.get("/runs/nope", headers={"Authorization": "Bearer good"}).status_code == 404
    assert calls.count("Bearer good") == 1  # second call served from cache


def test_supabase_outage_is_503(signed_in, monkeypatch):
    app.dependency_overrides.clear()
    monkeypatch.setattr(auth.httpx, "get", lambda *args, **kwargs: (_ for _ in ()).throw(httpx.ConnectError("offline")))
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "pk")
    auth._cache.clear()

    response = TestClient(app).get("/runs/nope", headers={"Authorization": "Bearer valid-looking"})

    assert response.status_code == 503
    assert response.json() == {"detail": "authentication service temporarily unavailable"}


def test_other_users_run_is_404(fake_db):
    fake_db["r1"] = {"id": "r1", "user_id": "someone-else", "tier": "free", "status": "running", "steps": []}
    fake_db["r2"] = {"id": "r2", "user_id": USER, "tier": "free", "status": "done", "steps": [{"action": "done"}]}
    c = TestClient(app)
    assert c.get("/runs/r1").status_code == 404
    assert c.get("/runs/r2").json()["status"] == "done"


def _token(exp: float) -> str:
    import base64
    import json

    body = base64.urlsafe_b64encode(json.dumps({"exp": exp, "sub": USER}).encode()).rstrip(b"=").decode()
    return f"eyJhbGciOiJIUzI1NiJ9.{body}.sig"


def test_profile_reads_verified_email_and_name():
    p = auth.profile({"id": USER, "email": "a@b.io", "email_confirmed_at": "2026-09-25T00:00:00Z", "user_metadata": {"full_name": " Ana \u202e Owner\n"}})
    assert p == {"id": USER, "email": "a@b.io", "email_verified": True, "name": "Ana Owner", "avatar": ""}
    assert auth.profile({"id": USER, "email": "a@b.io"})["email_verified"] is False
    assert auth.profile({"id": USER, "phone": "+1"})["email"] is None


def test_cache_is_hashed_bounded_and_never_outlives_the_token(signed_in, monkeypatch):
    app.dependency_overrides.clear()
    monkeypatch.setattr(auth.httpx, "get", lambda url, headers, timeout: httpx.Response(200, json={"id": USER, "email": "t@x.io"}))
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "pk")
    auth._cache.clear()
    now = [1_000_000.0]
    monkeypatch.setattr(auth.time, "time", lambda: now[0])
    token = _token(now[0] + 30)  # expires in 30 s, well inside the 5-minute cache window
    c = TestClient(app)
    assert c.get("/runs/nope", headers={"Authorization": f"Bearer {token}"}).status_code == 404
    assert token not in auth._cache and all(len(k) == 64 for k in auth._cache)  # SHA-256 keys, no raw tokens
    assert next(iter(auth._cache.values()))[1] == now[0] + 30

    monkeypatch.setattr(auth, "MAX_CACHED", 3)
    for i in range(5):
        c.get("/runs/nope", headers={"Authorization": f"Bearer other-{i}"})
    assert len(auth._cache) <= 3
    auth.forget(USER)
    assert auth._cache == {}
