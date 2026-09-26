"""SD-3.1: every route, called as user B on user A's run, key, site, test user, offer, installation, workspace or
invitation, answers 404 or 403. Routes are read from the app itself: a new route fails this test until it is added
to ROUTES with the way it is protected.

Workspace (team) routes are also tested for real against Postgres and PostgREST in tests/test_teams_live.py.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app
from tests.conftest import USER

OWNER = "00000000-0000-0000-0000-00000000000a"  # user A; the signed-in caller is USER (user B)
RUN = "a" * 32
ID = str(uuid.UUID(int=7))
OBS = {"observation": {"url": "https://a.example/", "elements": []}}
MSG = {"body": "hi"}

# "public": no sign-in, protected by a secret or a signature. "self": acts only on the caller's own data, with no
# foreign id in the request. Otherwise: (path with user A's ids, JSON body) and the answer must be 403 or 404.
ROUTES: dict[str, str | tuple[str, dict | None]] = {
    "GET /health": "public",
    "POST /scans": "public",
    "GET /badge/{run_id}.svg": "public",
    "GET /badge/{run_id}": "public",
    "POST /hooks/deploy/{token}": "public",
    "POST /webhooks/dodo": "public",
    "GET /me/plan": "self",
    "POST /runs": "self",
    "GET /me/test-users": "self",
    "POST /me/test-users": "self",
    "GET /me/branding": "self",
    "POST /me/branding": "self",
    "DELETE /me/branding": "self",
    "GET /me/api-keys": "self",
    "POST /me/api-keys": "self",
    "GET /watch": "self",
    "POST /watch": "self",
    "POST /compare": "self",
    "GET /github": "self",
    "POST /github/connect": "self",
    "GET /github/repos": "self",
    "GET /account/export": "self",
    "POST /account/delete": "self",
    "GET /billing": "self",
    "POST /billing/access-requests": "self",
    "POST /feedback": "self",
    "GET /verification": "self",
    "GET /teams": "self",
    "POST /teams": "self",
    "POST /invites/preview": "self",
    "POST /invites/accept": "self",
    "POST /runs/{run_id}/observe": (f"/runs/{RUN}/observe", OBS),
    "GET /runs/{run_id}": (f"/runs/{RUN}", None),
    "POST /runs/{run_id}/findings/ignore": (f"/runs/{RUN}/findings/ignore", {"fingerprint": "seo:x", "reason": "r"}),
    "DELETE /runs/{run_id}/findings/ignore": (f"/runs/{RUN}/findings/ignore?fingerprint=seo:x", None),
    "GET /runs/{run_id}/fix-prompt": (f"/runs/{RUN}/fix-prompt", None),
    "POST /runs/{run_id}/stop": (f"/runs/{RUN}/stop", {}),
    "POST /runs/{run_id}/fix-pr": (f"/runs/{RUN}/fix-pr", {"installation_id": 7, "repo": "acme/site"}),
    "POST /runs/{run_id}/share": (f"/runs/{RUN}/share", {}),
    "POST /runs/{run_id}/email": (f"/runs/{RUN}/email", {}),
    "DELETE /runs/{run_id}": (f"/runs/{RUN}", None),
    "GET /runs/{run_id}/teams": (f"/runs/{RUN}/teams", None),
    "DELETE /me/test-users/{test_user_id}": (f"/me/test-users/{ID}", None),
    "DELETE /me/api-keys/{key_id}": (f"/me/api-keys/{ID}", None),
    "DELETE /watch/{site_id}": (f"/watch/{ID}", None),
    "POST /watch/{site_id}/check": (f"/watch/{ID}/check", {}),
    "POST /watch/{site_id}/hook": (f"/watch/{ID}/hook", {}),
    "DELETE /github/installations/{installation_id}": ("/github/installations/7", None),
    "POST /billing/offers/{offer_id}/checkout": (f"/billing/offers/{ID}/checkout", {}),
    "POST /invites/{invite_id}/accept": (f"/invites/{ID}/accept", {}),
    "POST /invites/{invite_id}/decline": (f"/invites/{ID}/decline", {}),
    "GET /teams/{team_id}": (f"/teams/{ID}", None),
    "POST /teams/{team_id}": (f"/teams/{ID}", {"name": "Taken over"}),
    "POST /teams/{team_id}/delete": (f"/teams/{ID}/delete", {"confirm": "x"}),
    "POST /teams/{team_id}/transfer": (f"/teams/{ID}/transfer", {"user_id": USER}),
    "POST /teams/{team_id}/me": (f"/teams/{ID}/me", {"auto_share": True}),
    "GET /teams/{team_id}/members": (f"/teams/{ID}/members", None),
    "POST /teams/{team_id}/members/{member_id}/role": (f"/teams/{ID}/members/{OWNER}/role", {"role": "viewer"}),
    "DELETE /teams/{team_id}/members/{member_id}": (f"/teams/{ID}/members/{OWNER}", None),
    "POST /teams/{team_id}/invites": (f"/teams/{ID}/invites", {"email": "x@example.com"}),
    "POST /teams/{team_id}/links": (f"/teams/{ID}/links", {}),
    "DELETE /teams/{team_id}/invites/{invite_id}": (f"/teams/{ID}/invites/{ID}", None),
    "GET /teams/{team_id}/runs": (f"/teams/{ID}/runs", None),
    "POST /teams/{team_id}/runs": (f"/teams/{ID}/runs", {"run_id": RUN}),
    "DELETE /teams/{team_id}/runs/{run_id}": (f"/teams/{ID}/runs/{RUN}", None),
    "GET /teams/{team_id}/findings": (f"/teams/{ID}/findings", None),
    "POST /teams/{team_id}/findings": (f"/teams/{ID}/findings", {"origin": "https://a.example", "fingerprint": "seo:x", "status": "fixed"}),
    "GET /teams/{team_id}/messages": (f"/teams/{ID}/messages", None),
    "POST /teams/{team_id}/messages": (f"/teams/{ID}/messages", MSG),
    "POST /teams/{team_id}/messages/{message_id}": (f"/teams/{ID}/messages/1", MSG),
    "DELETE /teams/{team_id}/messages/{message_id}": (f"/teams/{ID}/messages/1", None),
    "POST /teams/{team_id}/read": (f"/teams/{ID}/read", {"message_id": 1}),
    "GET /teams/{team_id}/activity": (f"/teams/{ID}/activity", None),
}


def _routes() -> set[str]:
    return {f"{method.upper()} {path}" for path, ops in app.openapi()["paths"].items() for method in ops}


def test_every_route_is_classified():
    assert _routes() == set(ROUTES), "classify new routes in ROUTES (public, self, or a foreign-id call)"


@pytest.fixture
def user_a_owns_everything(monkeypatch, fake_db, passes):
    """User A's run, test user, key, watched site, offer, GitHub installation, workspace and invitation. User B (the
    caller) is on Plus, and the in-memory rate limits start empty, so neither hides a missing ownership check."""
    from app import main, teams

    for hits in (main._billing_hits, main._github_hits, main._scan_hits, teams._hits):
        hits.clear()
    fake_db[RUN] = {"id": RUN, "user_id": OWNER, "site": "https://a.example/", "status": "running", "steps": [], "tier": "paid", "kind": "test",
                    "report": {"summary": "s", "findings": [], "top_fixes": []}, "public": False}
    passes.append({"user_id": USER, "plan": "plus", "starts_at": "2000-01-01T00:00:00+00:00", "expires_at": "2999-01-01T00:00:00+00:00", "runs_granted": 150})
    monkeypatch.setattr(db, "delete_test_user", lambda user_id, tid: user_id == OWNER)
    monkeypatch.setattr(db, "revoke_api_key", lambda user_id, kid: user_id == OWNER)
    monkeypatch.setattr(db, "remove_site", lambda user_id, sid: user_id == OWNER)
    monkeypatch.setattr(db, "sites_for_user", lambda user_id: [{"id": ID, "site": "https://a.example/"}] if user_id == OWNER else [])
    monkeypatch.setattr(db, "get_offer", lambda oid: {"id": oid, "user_id": OWNER, "status": "approved"})
    monkeypatch.setattr(db, "remove_github_installation", lambda user_id, iid: user_id == OWNER)
    monkeypatch.setattr(db, "github_installations", lambda user_id: [{"installation_id": 7, "account_login": "a"}] if user_id == OWNER else [])
    monkeypatch.setattr(db, "membership", lambda team_id, user_id: {"team_id": team_id, "user_id": OWNER, "role": "owner", "name": "A", "email": "a@x.io",
                                                                    "auto_share": False, "last_read_message_id": 0, "last_seen_at": None,
                                                                    "team": {"id": team_id, "owner_id": OWNER, "name": "A"}} if user_id == OWNER else None)
    monkeypatch.setattr(db, "get_invite", lambda iid: {"id": iid, "team_id": ID, "kind": "email", "email": "a@x.io", "role": "member", "uses": 0,
                                                        "max_uses": 1, "revoked_at": None, "expires_at": "2999-01-01T00:00:00+00:00", "team": {"id": ID, "owner_id": OWNER}})


FOREIGN = sorted(k for k, v in ROUTES.items() if isinstance(v, tuple))


@pytest.mark.parametrize("route", FOREIGN)
def test_user_b_cannot_reach_user_a_resources(route, signed_in, user_a_owns_everything):
    method = route.split(" ", 1)[0]
    path, body = ROUTES[route]
    r = TestClient(app).request(method, path, json=body) if body is not None else TestClient(app).request(method, path)
    assert r.status_code in (403, 404), f"{route} answered {r.status_code}: {r.text[:200]}"
