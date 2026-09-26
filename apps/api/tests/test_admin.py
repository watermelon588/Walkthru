"""The founder admin panel (apps/api/admin) and the two API pieces that feed it: feedback and server errors."""

import re
import time

import pytest
from fastapi.testclient import TestClient

from admin import app as admin_app
from admin.auth import Guard, hash_password, totp, totp_counter, verify_password
from app import db

SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"  # RFC 6238's test key, "12345678901234567890"
PASSWORD = "correct horse battery staple"
BASE = "http://127.0.0.1:8020"
ORIGIN = {"origin": BASE}
ME = "founder@example.com"
BUYER = {"id": "00000000-0000-0000-0000-0000000000b1", "email": "buyer@example.com", "created_at": "2026-09-20T10:00:00", "last_sign_in_at": "", "provider": "google"}


def code(offset: int = 0) -> str:
    return totp(SECRET, int(time.time() // 30) + offset)


@pytest.fixture
def panel(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", hash_password(PASSWORD))
    monkeypatch.setenv("ADMIN_TOTP_SECRET", SECRET)
    monkeypatch.setenv("ADMIN_EMAIL", ME)
    monkeypatch.setattr(admin_app, "guard", Guard())
    calls = {"grants": [], "audit": [], "ended": []}
    me = {**BUYER, "id": "00000000-0000-0000-0000-0000000000a1", "email": ME}
    monkeypatch.setattr(admin_app, "_users", lambda: [BUYER, me])
    monkeypatch.setattr(admin_app, "_passes", dict)
    monkeypatch.setattr(db, "pending_access_requests", list)
    monkeypatch.setattr(db, "_select", lambda table, params: [{"kind": "feedback", "user_id": BUYER["id"], "created_at": "2026-09-26T10:00:00",
                                                                "detail": {"message": "<script>alert(1)</script> love it", "page": "/app"}}] if table == "app_events" else [])
    monkeypatch.setattr(db, "grant_entitlement", lambda *a: calls["grants"].append(a))
    monkeypatch.setattr(db, "expire_entitlements", lambda uid: calls["ended"].append(uid))
    monkeypatch.setattr(db, "audit", lambda *a: calls["audit"].append(a))
    client = TestClient(admin_app.app, base_url=BASE, follow_redirects=False)
    return client, calls


def sign_in(client, password=PASSWORD, otp=None):
    return client.post("/login", data={"password": password, "code": otp or code()}, headers=ORIGIN)


def csrf_of(client) -> str:
    return re.search(r'name="csrf" value="([^"]+)"', client.get("/").text).group(1)


def test_password_hash_and_rfc6238_totp():
    stored = hash_password(PASSWORD)
    assert PASSWORD not in stored and stored.startswith("scrypt:")
    assert verify_password(PASSWORD, stored) and not verify_password("wrong", stored) and not verify_password(PASSWORD, "garbage")
    assert totp(SECRET, 1) == "287082"  # RFC 6238 appendix B, T = 59 s, last 6 digits of 94287082
    assert totp_counter(SECRET, "287 082", now=59) == 1 and totp_counter(SECRET, "000000", now=59) is None


def test_only_this_computer_and_same_origin_posts(panel):
    client, _ = panel
    assert TestClient(admin_app.app, base_url="http://evil.example").get("/login").status_code == 404  # DNS rebinding
    assert client.post("/login", data={"password": PASSWORD, "code": code()}).status_code == 403  # no Origin
    assert client.post("/login", data={"password": PASSWORD, "code": code()}, headers={"origin": "https://evil.example"}).status_code == 403
    page = client.get("/login")
    assert "script-src" not in page.headers["content-security-policy"] and "default-src 'none'" in page.headers["content-security-policy"]
    assert page.headers["x-frame-options"] == "DENY" and page.headers["cache-control"] == "no-store"


def test_sign_in_needs_password_and_a_fresh_code_and_locks_after_five_misses(panel):
    client, calls = panel
    assert client.get("/").headers["location"] == "/login"
    assert sign_in(client, otp="000000").headers["location"] == "/login?m=wrong"
    ok = sign_in(client)
    assert ok.headers["location"] == "/"
    cookie = ok.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie
    assert client.get("/").status_code == 200
    assert TestClient(admin_app.app, base_url=BASE, follow_redirects=False).post(
        "/login", data={"password": PASSWORD, "code": code()}, headers=ORIGIN).headers["location"] == "/login?m=wrong"  # a code works once

    admin_app.guard = Guard()
    for _ in range(5):
        sign_in(client, password="nope")
    assert sign_in(client).headers["location"] == "/login?m=locked"  # even the right password while locked
    assert any(a[1] == "admin.login_failed" for a in calls["audit"])


def test_every_change_needs_csrf_and_a_current_code(panel):
    client, calls = panel
    sign_in(client)
    token = csrf_of(client)
    form = {"email": BUYER["email"], "plan": "pro", "days": "30"}
    assert client.post("/grant", data=form | {"code": code()}, headers=ORIGIN).status_code == 403  # no CSRF token
    assert client.post("/grant", data=form | {"csrf": token, "code": "123456"}, headers=ORIGIN).headers["location"] == "/?m=bad-code"
    assert calls["grants"] == []
    assert client.post("/grant", data=form | {"csrf": token, "code": code()}, headers=ORIGIN).headers["location"] == "/?m=granted"
    assert calls["grants"] == [(BUYER["id"], "pro", 30, 40, "founder")]
    assert client.post("/grant", data=form | {"csrf": token, "code": code(), "email": "nobody@example.com"}, headers=ORIGIN).headers["location"] == "/?m=no-user"

    # "Give me this plan" always uses the admin's own email, whatever the form says.
    client.post("/grant-self", data={"csrf": token, "code": code(), "plan": "plus", "days": "7", "email": BUYER["email"]}, headers=ORIGIN)
    assert calls["grants"][-1][:2] == ("00000000-0000-0000-0000-0000000000a1", "plus")
    assert client.post("/end", data={"csrf": token, "code": code(), "email": BUYER["email"]}, headers=ORIGIN).headers["location"] == "/?m=ended"
    assert calls["ended"] == [BUYER["id"]] and {a[1] for a in calls["audit"]} >= {"pass.grant", "pass.end"}
    assert client.post("/reject", data={"csrf": token, "code": code(), "request_id": "not-a-uuid"}, headers=ORIGIN).headers["location"] == "/?m=no-request"


def test_dashboard_escapes_what_users_wrote(panel):
    client, _ = panel
    sign_in(client)
    page = client.get("/").text
    assert "<script>alert(1)</script>" not in page and "&lt;script&gt;alert(1)&lt;/script&gt; love it" in page
    assert "buyer@example.com" in page and "Users" in page


def test_feedback_is_stored_for_the_founder_and_rate_limited(monkeypatch):
    from app import main

    stored = []
    monkeypatch.setattr(db, "app_event", lambda kind, user_id, detail: stored.append((kind, user_id, detail)))
    monkeypatch.setattr(main, "_feedback_hits", {})
    c = TestClient(main.app)
    assert c.post("/feedback", json={"message": "hi"}).status_code == 422  # too short
    assert c.post("/feedback", json={"message": "Love the report", "page": "/app", "user_id": "x"}).status_code == 422  # no extra fields
    for _ in range(main.FEEDBACK_LIMIT):
        assert c.post("/feedback", json={"message": "Love the report", "page": "/app"}).status_code == 200
    assert c.post("/feedback", json={"message": "one more"}).status_code == 429
    assert stored[0][0] == "feedback" and stored[0][2] == {"message": "Love the report", "page": "/app"}


def test_unhandled_errors_answer_generically_and_reach_the_panel(monkeypatch):
    from app import main, plans

    stored = []
    monkeypatch.setattr(db, "app_event", lambda kind, user_id, detail: stored.append((kind, detail)))
    monkeypatch.setattr(plans, "current", lambda user_id: (_ for _ in ()).throw(RuntimeError("secret internals")))
    r = TestClient(main.app, raise_server_exceptions=False).get("/me/plan")
    assert r.status_code == 500 and "secret internals" not in r.text
    assert stored == [("server_error", {"method": "GET", "route": "/me/plan", "error": "RuntimeError", "message": "secret internals"})]
