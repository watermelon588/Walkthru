"""SD-2.1: every route has a rate limit. Signed-in routes count per user (in auth.require_user), the rest per client
address (limits.by_address), MCP per key. The counter itself is tested in test_rate_limits_sql.py."""

import httpx
import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app import auth, db, limits
from app.auth import require_user
from app.main import app
from tests.conftest import USER

TOKEN = "header.eyJleHAiOjk5OTk5OTk5OTl9.sig"


@pytest.fixture
def real_auth(monkeypatch):
    """The real require_user (conftest overrides it), with one cached session for USER."""
    app.dependency_overrides.pop(require_user, None)
    monkeypatch.setitem(auth._cache, auth.hashlib.sha256(TOKEN.encode()).hexdigest(), ({"id": USER, "email": "t@example.com"}, 9e9))
    return {"Authorization": f"Bearer {TOKEN}"}


def test_every_route_has_a_limit_and_every_named_route_exists():
    routes = [r for r in app.routes if isinstance(r, APIRoute)]
    real = {(m, r.path) for r in routes for m in r.methods}
    assert set(limits.ROUTES) <= real, set(limits.ROUTES) - real  # a typo here would leave a route on the default
    for key in limits.ROUTES:
        route = next(r for r in routes if r.path == key[1] and key[0] in r.methods)
        assert limits._signed_in(route), f"{key} is named for a per-user rule but has no sign-in"
    by_address = [r for r in routes if not limits._signed_in(r)]
    assert {r.path for r in by_address} >= {"/badge/{run_id}.svg", "/scans", "/hooks/deploy/{token}", "/webhooks/dodo"}
    assert all(any(d.call is limits.by_address for d in r.dependant.dependencies) for r in routes)  # the app-wide dependency


def test_public_routes_count_per_address_and_a_made_up_token_does_not_skip_it(monkeypatch, rate_limits):
    monkeypatch.setitem(limits.RULES, "public", (2, 60, "Too many requests from this address."))
    c = TestClient(app)
    assert c.get("/badge/" + "0" * 32 + ".svg").status_code == 404
    assert c.get("/badge/" + "0" * 32 + ".svg", headers={"Authorization": "Bearer made-up"}).status_code == 404
    third = c.get("/badge/" + "0" * 32 + ".svg")
    assert third.status_code == 429 and third.headers["Retry-After"] == "60" and rate_limits == {"public:testclient": 3}
    assert c.get("/health").status_code == 200 and rate_limits == {"public:testclient": 3}  # health never counts


def test_signed_in_routes_count_per_user_by_their_rule(monkeypatch, rate_limits, real_auth):
    monkeypatch.setitem(limits.RULES, "account", (3, 60, "Too many requests."))
    c = TestClient(app)
    assert [c.get("/me/plan", headers=real_auth).status_code for _ in range(4)] == [200, 200, 200, 429]
    assert rate_limits == {f"account:{USER}": 4}  # per user, never per address
    c.post("/runs/" + "a" * 32 + "/observe", headers=real_auth, json={})
    c.post("/compare", headers=real_auth, json={})
    assert rate_limits[f"observe:{'a' * 32}"] == 1 and rate_limits[f"costly:{USER}"] == 1  # observe counts per run


def test_a_spray_of_made_up_tokens_is_stopped_per_address(monkeypatch, rate_limits):
    app.dependency_overrides.pop(require_user, None)
    monkeypatch.setitem(limits.RULES, "auth", (2, 60, "Too many sign-in checks from this address."))
    checks = []
    monkeypatch.setattr(auth.httpx, "get", lambda *a, **k: checks.append(1) or httpx.Response(401))
    c = TestClient(app)
    codes = [c.get("/me/plan", headers={"Authorization": f"Bearer fake-{i}"}).status_code for i in range(4)]
    assert codes == [401, 401, 429, 429] and len(checks) == 2  # Supabase Auth was not asked again


def test_the_limits_fail_open_when_the_database_is_down(monkeypatch, real_auth):
    def down(*a):
        raise db.DatabaseUnavailable("timeout")

    monkeypatch.setattr(db, "hit_rate_limit", down)
    assert TestClient(app).get("/me/plan", headers=real_auth).status_code == 200


def test_mcp_counts_per_key(monkeypatch, passes, rate_limits):
    from app import mcp_server
    from tests.test_mcp import _rpc, fake_keys, plus

    mcp_server.build_transport()  # an MCP session manager runs once per app start
    fake_keys(monkeypatch)
    plus(passes)
    monkeypatch.setitem(limits.RULES, "mcp", (1, 60, "Too many MCP calls with this key."))
    try:
        with TestClient(app) as c:
            key = c.post("/me/api-keys", json={"name": "agent"}).json()["key"]
            assert _rpc(c, key, "tools/list").status_code == 200
            second = _rpc(c, key, "tools/list", id_=2)
    finally:
        mcp_server.build_transport()  # a fresh one for whichever test starts the app next
    assert second.status_code == 429 and second.headers["retry-after"] == "60" and "MCP calls" in second.json()["detail"]
