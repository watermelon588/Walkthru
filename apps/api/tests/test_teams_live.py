"""Team workspaces against a real Postgres + PostgREST with Supabase's roles (tests/live_stack.py).

These prove what fakes cannot: row-level security, the locked seat count, grants, and the PostgREST queries the API
sends. They skip when the binaries are missing (set PG_BIN and POSTGREST_BIN to run them anywhere).
"""

import json
import threading
import uuid
from datetime import UTC, datetime

import httpx
import pytest
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient

from app import auth, db, teams
from app.auth import require_user
from app.main import app
from tests import live_stack

# The real data functions, captured before conftest's autouse fakes replace some of them for each test.
REAL = {name: getattr(db, name) for name in dir(db) if callable(getattr(db, name)) and not name.startswith("__")}

pytestmark = pytest.mark.skipif(live_stack.binaries() is None, reason="needs Postgres server binaries and PostgREST (PG_BIN, POSTGREST_BIN)")

TOKENS: dict[str, dict] = {}
FINDINGS = [
    {"kind": "security", "severity": "high", "title": "Missing Content-Security-Policy", "detail": "d", "fix": "Add a CSP header", "evidence": "headers", "rule": "csp-missing"},
    {"kind": "ux", "severity": "medium", "title": "Signup button hidden on phones", "detail": "d", "fix": "Show it", "evidence": None},
]


@pytest.fixture(scope="session")
def stack():
    with open(db.SCHEMA, encoding="utf-8") as f, live_stack.stack(db.statements(f.read())) as s:
        s["psql"]("select 1")
        yield s


@pytest.fixture
def live(stack, monkeypatch):
    for name, fn in REAL.items():
        monkeypatch.setattr(db, name, fn)
    client = httpx.Client(base_url=stack["rest"], transport=live_stack.RestTransport(),
                          headers={"apikey": stack["service_key"], "Authorization": f"Bearer {stack['service_key']}"})
    monkeypatch.setattr(db, "client", lambda: client)
    monkeypatch.setattr(teams, "SEATS", 3)
    teams._hits.clear()

    def user_from(request: Request) -> dict:
        token = request.headers.get("authorization", "")[7:]
        if token not in TOKENS:
            raise HTTPException(401, "invalid or expired session")
        return TOKENS[token]

    app.dependency_overrides[require_user] = user_from
    yield stack
    app.dependency_overrides.clear()
    client.close()


api = TestClient(app)


def person(stack, *, plus=False, verified=True, email=None, name="") -> dict:
    uid = str(uuid.uuid4())
    email = email or f"{uid[:8]}@example.com"
    stack["psql"]("insert into auth.users (id, email, email_confirmed_at, raw_user_meta_data) values (%s, %s, %s, %s)",
                  (uid, email, datetime.now(UTC) if verified else None, json.dumps({"full_name": name})))
    if plus:
        grant_plus(stack, uid)
    profile = auth.profile({"id": uid, "email": email, "email_confirmed_at": "2026-09-25T00:00:00Z" if verified else None, "user_metadata": {"full_name": name}})
    token = live_stack.jwt({"role": "authenticated", "sub": uid})
    TOKENS[token] = profile
    return profile | {"h": {"Authorization": f"Bearer {token}"}, "jwt": token}


def grant_plus(stack, uid: str) -> None:
    stack["psql"]("insert into public.entitlements (user_id, plan, expires_at, runs_granted, source) values (%s, 'plus', now() + interval '30 days', 150, 'dev')", (uid,))


def workspace(owner: dict, name: str = "Acme launch") -> str:
    r = api.post("/teams", json={"name": name}, headers=owner["h"])
    assert r.status_code == 200, r.text
    return r.json()["id"]


def invite(team: str, by: dict, who: dict, role: str = "member") -> dict:
    r = api.post(f"/teams/{team}/invites", json={"email": who["email"], "role": role}, headers=by["h"])
    assert r.status_code == 200, r.text
    return r.json()


def join(team: str, owner: dict, who: dict, role: str = "member") -> None:
    code = invite(team, owner, who, role)["code"]
    r = api.post("/invites/accept", json={"code": code}, headers=who["h"])
    assert r.status_code == 200 and r.json() == {"team_id": team, "joined": True}, r.text


def a_run(owner: dict, site: str = "https://acme.example", findings: list[dict] | None = None) -> str:
    run_id = uuid.uuid4().hex
    db.insert_run(run_id, owner["id"], site, "Sign up", "first_timer", "paid", False)
    db.set_report(run_id, {"summary": "s", "findings": FINDINGS if findings is None else findings, "launch_ready": {"score": 71}, "tokens": 0}, status="done")
    return run_id


def rest(stack, path: str, who: dict | None = None, method: str = "GET", **kw) -> httpx.Response:
    headers = {"Authorization": f"Bearer {who['jwt']}"} if who else {}
    return httpx.request(method, stack["rest"] + path, headers=headers, timeout=10, **kw)


# ---------- schema ----------


def test_schema_is_idempotent_and_publishes_team_tables(live):
    with open(db.SCHEMA, encoding="utf-8") as f:
        for stmt in db.statements(f.read()):  # re-applying must not fail
            live["psql"](stmt)
    published = {r[0] for r in live["psql"]("select tablename from pg_publication_tables where pubname = 'supabase_realtime'")}
    assert {"teams", "team_members", "team_runs", "team_findings", "team_messages", "team_events"} <= published
    assert "team_invites" not in published


# ---------- creating workspaces ----------


def test_only_plus_creates_and_owns_at_most_three(live):
    free, plus = person(live), person(live, plus=True)
    assert api.post("/teams", json={"name": "Nope"}, headers=free["h"]).status_code == 402
    assert api.post("/teams", json={"name": "Visit https://evil.example"}, headers=plus["h"]).status_code == 422
    for i in range(3):
        workspace(plus, f"Team {i}")
    assert api.post("/teams", json={"name": "Fourth"}, headers=plus["h"]).status_code == 409
    listed = api.get("/teams", headers=plus["h"]).json()
    assert [t["role"] for t in listed["teams"]] == ["owner"] * 3 and listed["can_create"] is False


def test_strangers_get_404_everywhere(live):
    owner, stranger = person(live, plus=True), person(live, plus=True)
    team = workspace(owner)
    for path in ("", "/members", "/runs", "/findings", "/messages", "/activity"):
        assert api.get(f"/teams/{team}{path}", headers=stranger["h"]).status_code == 404, path
    assert api.post(f"/teams/{team}/messages", json={"body": "hi"}, headers=stranger["h"]).status_code == 404
    assert api.post(f"/teams/{team}/invites", json={"email": "x@example.com"}, headers=stranger["h"]).status_code == 404
    assert api.get(f"/teams/{uuid.uuid4()}", headers=owner["h"]).status_code == 404
    assert api.get("/teams/not-a-uuid", headers=owner["h"]).status_code == 422


# ---------- invitations ----------


def test_email_invitation_works_once_for_its_verified_address(live):
    owner = person(live, plus=True, name="Ana Owner")
    bob, eve, bob_unverified = person(live), person(live), person(live, verified=False)
    team = workspace(owner)
    sent = invite(team, owner, bob)
    assert sent["link"].endswith("#" + sent["code"]) and "/join#" in sent["link"] and sent["emailed"] is False
    code = sent["code"].replace("-", "").lower()  # typed without dashes, any case

    peek = api.post("/invites/preview", json={"code": code}, headers=eve["h"]).json()
    assert peek["team"]["name"] == "Acme launch" and peek["invited_by_name"] == "Ana Owner"
    assert peek["problem"].startswith("This invitation was sent to ") and bob["email"] not in peek["problem"]
    assert api.post("/invites/accept", json={"code": code}, headers=eve["h"]).status_code == 403
    assert api.post("/invites/accept", json={"code": code}, headers=bob_unverified["h"]).status_code == 403

    assert api.post("/invites/preview", json={"code": code}, headers=bob["h"]).json()["problem"] is None
    assert api.post("/invites/accept", json={"code": code}, headers=bob["h"]).json() == {"team_id": team, "joined": True}
    assert api.post("/invites/accept", json={"code": code}, headers=bob["h"]).json() == {"team_id": team, "joined": False}
    assert api.post("/invites/accept", json={"code": code}, headers=eve["h"]).status_code == 410  # used up
    assert api.post("/invites/accept", json={"code": "AAAA-AAAA-AAAA-AAAA-AAAA-AAAA"}, headers=eve["h"]).status_code == 404

    mine = api.get("/teams", headers=bob["h"]).json()["teams"]
    assert [(t["id"], t["role"], t["active"]) for t in mine] == [(team, "member", True)]
    events = [e["type"] for e in api.get(f"/teams/{team}/activity", headers=bob["h"]).json()["events"]]
    assert events[:3] == ["member.joined", "invite.sent", "team.created"]
    sent_event = api.get(f"/teams/{team}/activity", headers=bob["h"]).json()["events"][1]
    assert sent_event["detail"]["email"] != bob["email"] and sent_event["detail"]["email"].endswith("@example.com")
    stored = live["psql"]("select token_hash from public.team_invites where team_id = %s", (team,))
    assert stored and all(sent["code"] not in row[0] for row in stored)  # only the hash is kept


def test_invitations_listed_in_app_and_declined(live):
    owner, bob = person(live, plus=True), person(live)
    team = workspace(owner)
    invite(team, owner, bob, "viewer")
    listed = api.get("/teams", headers=bob["h"]).json()["invitations"]
    assert [(i["team"]["id"], i["role"]) for i in listed] == [(team, "viewer")]
    other = person(live)
    assert api.post(f"/invites/{listed[0]['id']}/accept", headers=other["h"]).status_code == 404
    assert api.post(f"/invites/{listed[0]['id']}/decline", headers=bob["h"]).status_code == 200
    assert api.get("/teams", headers=bob["h"]).json()["invitations"] == []


def test_seats_count_open_invitations_and_links_respect_them(live):
    owner, bob, carol, dan = person(live, plus=True), person(live), person(live), person(live)
    team = workspace(owner)
    invite(team, owner, bob)
    invite(team, owner, carol)
    r = api.post(f"/teams/{team}/invites", json={"email": dan["email"]}, headers=owner["h"])
    assert r.status_code == 409 and "3 seats" in r.json()["detail"]
    invite(team, owner, bob)  # inviting the same address again replaces the old invitation, no extra seat
    link = api.post(f"/teams/{team}/links", json={"role": "member"}, headers=owner["h"]).json()
    assert api.post("/invites/accept", json={"code": link["code"]}, headers=dan["h"]).status_code == 409  # both open seats are held
    members = api.get(f"/teams/{team}/members", headers=owner["h"]).json()
    assert members["seats"] == 3 and members["seats_used"] == 3 and len(members["invites"]) == 3


def test_two_people_racing_for_the_last_seat_get_one_seat(live):
    owner = person(live, plus=True)
    racers = [person(live) for _ in range(6)]
    team = workspace(owner)
    join(team, owner, person(live))  # 2 of 3 seats used
    code = api.post(f"/teams/{team}/links", json={"max_uses": 50}, headers=owner["h"]).json()["code"]
    results: list[int] = []

    def go(who):
        results.append(api.post("/invites/accept", json={"code": code}, headers=who["h"]).status_code)

    threads = [threading.Thread(target=go, args=(r,)) for r in racers]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(results) == [200] + [409] * 5
    assert live["psql"]("select count(*) from public.team_members where team_id = %s", (team,))[0][0] == 3


def test_invite_links_domain_role_and_revocation(live):
    owner = person(live, plus=True)
    team = workspace(owner)
    assert api.post(f"/teams/{team}/links", json={"role": "admin"}, headers=owner["h"]).status_code == 422  # links never grant admin
    assert api.post(f"/teams/{team}/links", json={"email_domain": "not a domain"}, headers=owner["h"]).status_code == 422
    link = api.post(f"/teams/{team}/links", json={"role": "viewer", "email_domain": "@Acme.io", "days": 3}, headers=owner["h"]).json()
    assert link["invite"]["email_domain"] == "acme.io"
    outsider, insider = person(live, email=f"{uuid.uuid4().hex[:6]}@other.io"), person(live, email=f"{uuid.uuid4().hex[:6]}@acme.io")
    assert api.post("/invites/accept", json={"code": link["link"]}, headers=outsider["h"]).status_code == 403  # a pasted full link works too
    assert api.post("/invites/accept", json={"code": link["link"]}, headers=insider["h"]).json()["joined"] is True
    assert api.get(f"/teams/{team}", headers=insider["h"]).json()["me"]["role"] == "viewer"
    assert api.delete(f"/teams/{team}/invites/{link['invite']['id']}", headers=owner["h"]).status_code == 200
    late = person(live, email=f"{uuid.uuid4().hex[:6]}@acme.io")
    assert api.post("/invites/accept", json={"code": link["code"]}, headers=late["h"]).status_code == 410


# ---------- roles ----------


def test_role_rules(live):
    owner, admin, member, viewer = person(live, plus=True), person(live), person(live), person(live)
    team = workspace(owner)
    join(team, owner, admin, "admin")
    join(team, owner, member)
    live["psql"]("delete from public.team_invites where team_id = %s", (team,))
    teams.SEATS = 4
    join(team, owner, viewer, "viewer")

    assert api.post(f"/teams/{team}/invites", json={"email": "z@example.com"}, headers=member["h"]).status_code == 403
    assert api.post(f"/teams/{team}/invites", json={"email": "z@example.com", "role": "admin"}, headers=admin["h"]).status_code == 403
    assert api.post(f"/teams/{team}/members/{member['id']}/role", json={"role": "admin"}, headers=admin["h"]).status_code == 403
    assert api.post(f"/teams/{team}/members/{member['id']}/role", json={"role": "viewer"}, headers=admin["h"]).status_code == 200
    assert api.post(f"/teams/{team}/members/{member['id']}/role", json={"role": "member"}, headers=admin["h"]).status_code == 200
    assert api.post(f"/teams/{team}/members/{owner['id']}/role", json={"role": "member"}, headers=admin["h"]).status_code == 403
    assert api.post(f"/teams/{team}/members/{admin['id']}/role", json={"role": "viewer"}, headers=admin["h"]).status_code == 409  # not yourself
    assert api.delete(f"/teams/{team}/members/{admin['id']}", headers=member["h"]).status_code == 403
    assert api.delete(f"/teams/{team}/members/{owner['id']}", headers=admin["h"]).status_code == 403
    assert api.delete(f"/teams/{team}/members/{owner['id']}", headers=owner["h"]).status_code == 409  # the owner cannot just leave
    assert api.post(f"/teams/{team}/me", json={"auto_share": True}, headers=viewer["h"]).status_code == 403
    assert api.post(f"/teams/{team}/runs", json={"run_id": a_run(viewer)}, headers=viewer["h"]).status_code == 403
    assert api.post(f"/teams/{team}/messages", json={"body": "viewers can chat"}, headers=viewer["h"]).status_code == 200

    can = api.get(f"/teams/{team}", headers=viewer["h"]).json()["me"]["can"]
    assert can["chat"] and not can["share"] and not can["invite"]
    assert api.delete(f"/teams/{team}/members/{viewer['id']}", headers=admin["h"]).status_code == 200
    assert api.delete(f"/teams/{team}/members/{member['id']}", headers=member["h"]).json() == {"left": team}
    assert api.get(f"/teams/{team}", headers=member["h"]).status_code == 404
    types = [e["type"] for e in api.get(f"/teams/{team}/activity", headers=owner["h"]).json()["events"]]
    assert types[:2] == ["member.left", "member.removed"] and "member.role" in types


def test_transfer_and_delete(live):
    owner, admin = person(live, plus=True), person(live, plus=True)
    team = workspace(owner)
    join(team, owner, admin, "admin")
    assert api.post(f"/teams/{team}/transfer", json={"user_id": admin["id"]}, headers=admin["h"]).status_code == 403
    assert api.post(f"/teams/{team}/transfer", json={"user_id": admin["id"]}, headers=owner["h"]).json() == {"owner_id": admin["id"], "active": True}
    roles = dict(live["psql"]("select user_id::text, role from public.team_members where team_id = %s", (team,)))
    assert roles == {owner["id"]: "admin", admin["id"]: "owner"}
    run = a_run(admin)
    api.post(f"/teams/{team}/runs", json={"run_id": run}, headers=admin["h"])
    api.post(f"/teams/{team}/messages", json={"body": "bye"}, headers=admin["h"])
    assert api.post(f"/teams/{team}/delete", json={"confirm": "wrong"}, headers=admin["h"]).status_code == 422
    assert api.post(f"/teams/{team}/delete", json={"confirm": "Acme launch"}, headers=owner["h"]).status_code == 403
    assert api.post(f"/teams/{team}/delete", json={"confirm": "Acme launch"}, headers=admin["h"]).status_code == 200
    assert live["psql"]("select count(*) from public.team_messages where team_id = %s", (team,))[0][0] == 0
    assert db.get_run(run) is not None  # the report stays in its owner's account


# ---------- shared reports and row-level security ----------


def test_shared_reports_are_readable_by_members_only(live):
    owner, member, stranger = person(live, plus=True), person(live), person(live)
    team = workspace(owner)
    join(team, owner, member)
    run = a_run(owner)
    live["psql"]("insert into storage.objects (bucket_id, name) values ('run-evidence', %s)", (f"{run}/step-01.jpg",))

    def sees(who) -> tuple[int, int]:
        rows = rest(live, f"/runs?id=eq.{run}&select=id", who).json()
        objects = live["psql"]("select count(*) from storage.objects where name like %s", (f"{run}/%",), user=who["id"])[0][0]
        return len(rows), objects

    assert sees(member) == (0, 0)
    assert api.post(f"/teams/{team}/runs", json={"run_id": a_run(member)}, headers=owner["h"]).status_code == 404  # only your own runs
    assert api.post(f"/teams/{team}/runs", json={"run_id": run}, headers=owner["h"]).status_code == 200
    assert sees(member) == (1, 1) and sees(stranger) == (0, 0)
    listed = api.get(f"/teams/{team}/runs", headers=member["h"]).json()["runs"]
    assert [(r["run_id"], r["score"], r["findings"]["high"]) for r in listed] == [(run, 71, 1)]
    assert api.get(f"/runs/{run}/teams", headers=owner["h"]).json()["teams"] == [{"id": team, "name": "Acme launch", "shared": True}]
    assert api.get(f"/runs/{run}/teams", headers=member["h"]).status_code == 404

    assert api.delete(f"/teams/{team}/runs/{run}", headers=member["h"]).status_code == 403
    assert api.delete(f"/teams/{team}/runs/{run}", headers=owner["h"]).status_code == 200
    assert sees(member) == (0, 0)

    api.post(f"/teams/{team}/runs", json={"run_id": run}, headers=owner["h"])
    api.delete(f"/teams/{team}/members/{member['id']}", headers=owner["h"])
    assert sees(member) == (0, 0)  # leaving the workspace ends access at once


def test_browsers_cannot_write_or_read_invites(live):
    owner, member = person(live, plus=True), person(live)
    team = workspace(owner)
    join(team, owner, member)
    assert len(rest(live, f"/team_members?team_id=eq.{team}", member).json()) == 2
    assert rest(live, "/team_members", person(live)).json() == []
    assert rest(live, "/teams").status_code in (401, 403)  # anonymous
    assert rest(live, "/team_invites", member).status_code in (401, 403)
    denied = [
        rest(live, "/team_messages", member, "POST", json={"team_id": team, "body": "direct"}),
        rest(live, f"/team_members?team_id=eq.{team}&user_id=eq.{member['id']}", member, "PATCH", json={"role": "owner"}),
        rest(live, f"/teams?id=eq.{team}", member, "DELETE"),
        rest(live, "/rpc/team_join", member, "POST", json={"p_invite": str(uuid.uuid4()), "p_user": member["id"], "p_name": "x", "p_email": "x", "p_seats": 99, "p_max_teams": 99}),
    ]
    assert all(r.status_code in (401, 403) for r in denied), [r.status_code for r in denied]
    assert live["psql"]("select role from public.team_members where team_id = %s and user_id = %s", (team, member["id"]))[0][0] == "member"


# ---------- findings board ----------


def test_findings_board_triage_and_seen_again(live):
    owner, member, viewer = person(live, plus=True), person(live), person(live)
    team = workspace(owner)
    join(team, owner, member)
    join(team, owner, viewer, "viewer")
    first = a_run(owner)
    api.post(f"/teams/{team}/runs", json={"run_id": first}, headers=owner["h"])
    board = api.get(f"/teams/{team}/findings", headers=viewer["h"]).json()
    assert [(f["title"], f["status"], f["reports"]) for f in board["findings"]] == [
        ("Missing Content-Security-Policy", "open", 1), ("Signup button hidden on phones", "open", 1)]
    assert board["can_triage"] is False and {a["user_id"] for a in board["assignees"]} == {owner["id"], member["id"]}
    csp = board["findings"][0]
    key = {"origin": csp["origin"], "fingerprint": csp["fingerprint"]}
    assert csp["fingerprint"] == "security:csp-missing" and csp["thread"].startswith("finding:")

    assert api.post(f"/teams/{team}/findings", json=key | {"status": "fixed"}, headers=viewer["h"]).status_code == 403
    assert api.post(f"/teams/{team}/findings", json=key | {"assignee_id": viewer["id"]}, headers=member["h"]).status_code == 422
    assert api.post(f"/teams/{team}/findings", json={"origin": "https://x.example", "fingerprint": "ux:nope", "status": "fixed"}, headers=member["h"]).status_code == 404
    done = api.post(f"/teams/{team}/findings", json=key | {"status": "in_progress", "assignee_id": member["id"]}, headers=member["h"]).json()
    assert (done["status"], done["assignee_id"], done["assignee_name"]) == ("in_progress", member["id"], member["email"].split("@")[0])
    assert api.get(f"/teams/{team}", headers=member["h"]).json()["findings"]["mine"] == 1
    api.post(f"/teams/{team}/findings", json=key | {"status": "fixed"}, headers=member["h"])
    assert api.get(f"/teams/{team}/findings", headers=owner["h"]).json()["findings"][-1]["status"] == "fixed"

    api.post(f"/teams/{team}/runs", json={"run_id": a_run(owner)}, headers=owner["h"])  # a later report finds it again
    again = next(f for f in api.get(f"/teams/{team}/findings", headers=owner["h"]).json()["findings"] if f["fingerprint"] == key["fingerprint"])
    assert again["seen_again"] is True and again["reports"] == 2
    overview = api.get(f"/teams/{team}", headers=owner["h"]).json()
    assert overview["findings"]["seen_again"] == 1 and overview["sites"][0]["reports"] == 2 and overview["sites"][0]["score"] == 71
    types = [e["type"] for e in overview["activity"]]
    assert "finding.status" in types and "finding.assigned" in types


# ---------- chat ----------


def test_chat_mentions_unread_edit_delete_and_threads(live):
    owner, member, admin = person(live, plus=True, name="Ana"), person(live, name="Bo"), person(live, name="Cy")
    team = workspace(owner)
    join(team, owner, member)
    join(team, owner, admin, "admin")
    client_id = str(uuid.uuid4())
    sent = api.post(f"/teams/{team}/messages", json={"body": "  Hello @Bo \u202e\n\n\n\nsee the CSP  ", "mentions": [member["id"], str(uuid.uuid4())],
                                                      "client_id": client_id}, headers=owner["h"]).json()
    assert sent["body"] == "Hello @Bo \n\nsee the CSP" and sent["mentions"] == [member["id"]] and sent["author_name"] == "Ana"
    again = api.post(f"/teams/{team}/messages", json={"body": "Hello again", "client_id": client_id}, headers=owner["h"]).json()
    assert again["id"] == sent["id"]  # a retried send lands once

    mine = next(t for t in api.get("/teams", headers=member["h"]).json()["teams"] if t["id"] == team)
    assert (mine["unread"], mine["mentions"]) == (1, 1)
    assert next(t for t in api.get("/teams", headers=owner["h"]).json()["teams"] if t["id"] == team)["unread"] == 0
    reply = api.post(f"/teams/{team}/messages", json={"body": "On it"}, headers=member["h"]).json()
    page = api.get(f"/teams/{team}/messages", params={"after": sent["id"]}, headers=owner["h"]).json()
    assert [m["id"] for m in page["messages"]] == [reply["id"]]
    assert [m["body"] for m in api.get(f"/teams/{team}/messages", headers=member["h"]).json()["messages"]] == [sent["body"], "On it"]

    assert api.post(f"/teams/{team}/messages/{sent['id']}", json={"body": "hijack"}, headers=member["h"]).status_code == 403
    edited = api.post(f"/teams/{team}/messages/{reply['id']}", json={"body": "On it now"}, headers=member["h"]).json()
    assert edited["body"] == "On it now" and edited["edited_at"]
    assert api.delete(f"/teams/{team}/messages/{sent['id']}", headers=member["h"]).status_code == 403
    assert api.delete(f"/teams/{team}/messages/{reply['id']}", headers=admin["h"]).status_code == 200
    gone = api.get(f"/teams/{team}/messages", headers=owner["h"]).json()["messages"][-1]
    assert gone["deleted"] is True and gone["body"] == ""
    assert "message.removed" in [e["type"] for e in api.get(f"/teams/{team}/activity", headers=owner["h"]).json()["events"]]

    later = api.post(f"/teams/{team}/messages", json={"body": "Thanks"}, headers=owner["h"]).json()
    assert next(t for t in api.get("/teams", headers=member["h"]).json()["teams"] if t["id"] == team)["unread"] == 1
    assert api.post(f"/teams/{team}/read", json={"message_id": later["id"]}, headers=member["h"]).json() == {"last_read_message_id": later["id"]}
    assert next(t for t in api.get("/teams", headers=member["h"]).json()["teams"] if t["id"] == team)["unread"] == 0

    assert api.post(f"/teams/{team}/messages", json={"body": "x", "thread": "run:" + "a" * 32}, headers=owner["h"]).status_code == 404
    assert api.post(f"/teams/{team}/messages", json={"body": "x", "thread": "random"}, headers=owner["h"]).status_code == 422
    assert api.post(f"/teams/{team}/messages", json={"body": "   "}, headers=owner["h"]).status_code == 422
    run = a_run(owner)
    api.post(f"/teams/{team}/runs", json={"run_id": run}, headers=owner["h"])
    assert api.post(f"/teams/{team}/messages", json={"body": "Look at step 3", "thread": f"run:{run}"}, headers=member["h"]).status_code == 200
    assert api.get(f"/teams/{team}/runs", headers=owner["h"]).json()["runs"][0]["comments"] == 1
    assert len(rest(live, f"/team_messages?team_id=eq.{team}", member).json()) == 4  # what Realtime can push to members
    assert rest(live, f"/team_messages?team_id=eq.{team}", person(live)).json() == []

    exported = teams.export(member["id"])
    assert exported["memberships"][0]["team"] == "Acme launch" and len(exported["messages"]) == 2


def test_message_rate_limit(live):
    owner = person(live, plus=True)
    team = workspace(owner)
    codes = [api.post(f"/teams/{team}/messages", json={"body": f"m{i}"}, headers=owner["h"]).status_code for i in range(31)]
    assert codes[:30] == [200] * 30 and codes[30] == 429


# ---------- plan changes, auto-share, account deletion ----------


def test_workspace_goes_read_only_when_the_owner_leaves_plus(live):
    owner, member = person(live, plus=True), person(live, plus=False)
    team = workspace(owner)
    join(team, owner, member, "admin")
    live["psql"]("update public.entitlements set expires_at = now() - interval '1 minute' where user_id = %s", (owner["id"],))
    overview = api.get(f"/teams/{team}", headers=member["h"]).json()
    assert overview["team"]["active"] is False and overview["me"]["can"]["chat"] is False
    assert api.post(f"/teams/{team}/messages", json={"body": "hello?"}, headers=member["h"]).status_code == 402
    assert api.post(f"/teams/{team}/links", json={}, headers=owner["h"]).status_code == 402
    grant_plus(live, member["id"])
    assert api.post(f"/teams/{team}/transfer", json={"user_id": member["id"]}, headers=owner["h"]).json()["active"] is True
    assert api.post(f"/teams/{team}/messages", json={"body": "back"}, headers=member["h"]).status_code == 200


def test_auto_share_puts_new_runs_in_the_workspace(live):
    owner, member = person(live, plus=True), person(live)
    team = workspace(owner)
    join(team, owner, member)
    assert api.post(f"/teams/{team}/me", json={"auto_share": True}, headers=member["h"]).json() == {"auto_share": True}
    run = a_run(member)
    teams.auto_share(member["id"], run, "https://acme.example", "test")
    teams.auto_share(member["id"], run, "https://acme.example", "test")  # twice is harmless
    assert [r["run_id"] for r in api.get(f"/teams/{team}/runs", headers=owner["h"]).json()["runs"]] == [run]
    assert [e["detail"].get("auto") for e in api.get(f"/teams/{team}/activity", headers=owner["h"]).json()["events"] if e["type"] == "run.shared"] == [True]


def test_account_deletion_waits_for_workspaces_with_members(live):
    owner, member = person(live, plus=True), person(live)
    solo, team = workspace(owner, "Solo"), workspace(owner, "Shared")
    join(team, owner, member)
    with pytest.raises(HTTPException) as refused:
        teams.before_account_delete(owner["id"])
    assert refused.value.status_code == 409 and "Shared" in refused.value.detail and "Solo" not in refused.value.detail
    teams.before_account_delete(member["id"])  # members may always delete their account
    api.post(f"/teams/{team}/messages", json={"body": "Last words"}, headers=member["h"])
    teams.forget_user(member["id"])
    live["psql"]("delete from auth.users where id = %s", (member["id"],))
    left = api.get(f"/teams/{team}/messages", headers=owner["h"]).json()["messages"]
    assert [(m["author_name"], m["author_id"], m["body"]) for m in left] == [("Former member", None, "Last words")]
    joined = next(e for e in api.get(f"/teams/{team}/activity", headers=owner["h"]).json()["events"] if e["type"] == "member.joined")
    assert joined["actor_name"] == "Former member"
    teams.before_account_delete(owner["id"])
    live["psql"]("delete from auth.users where id = %s", (owner["id"],))
    assert live["psql"]("select count(*) from public.teams where id in (%s, %s)", (solo, team))[0][0] == 0
