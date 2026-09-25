"""Team workspace rules that need no database. The routes are tested for real in tests/test_teams_live.py."""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import db, teams
from app.main import app


def test_codes_are_random_readable_and_forgiving():
    raw = teams.new_code()
    assert len(raw) == 24 and raw.isalnum() and raw.isupper() and raw != teams.new_code()
    shown = teams.show_code(raw)
    assert shown.count("-") == 5
    for pasted in (shown, shown.lower(), raw, f" {shown.replace('-', ' ')} ", f"https://walkthru.dev/join#{shown}"):
        assert teams.read_code(pasted) == raw
    assert teams.read_code("not a code") is None and teams.read_code("A" * 23) is None
    assert teams.read_code("0" * 24) is None  # 0, 1, 8 and 9 are not base32
    assert teams.code_hash(raw) != raw and len(teams.code_hash(raw)) == 64
    assert teams.join_link(raw).endswith(f"/join#{shown}")


def test_names_messages_and_domains_are_cleaned():
    assert teams.clean_name("  Acme\u202e   launch \n") == "Acme launch"
    for bad in ("", " " * 5, "x" * 61, "See https://evil.example", "www.evil.example"):
        with pytest.raises(HTTPException):
            teams.clean_name(bad)
    assert teams.clean_body("  hi\r\n\r\n\r\n\r\nthere\u200b  ") == "hi\n\nthere"
    for bad in ("  \n ", "x" * 4001):
        with pytest.raises(HTTPException):
            teams.clean_body(bad)
    assert teams.clean_domain(" @Acme.IO ") == "acme.io" and teams.clean_domain("") is None
    for bad in ("acme", "acme..io", "-acme.io", "acme.io/x", "a@acme.io"):
        with pytest.raises(HTTPException):
            teams.clean_domain(bad)
    assert teams.mask("bob@example.com") == "b**@example.com" and teams.mask("b@x.io") == "b*@x.io"


def test_threads_and_permissions():
    assert teams.THREAD.fullmatch("general") and teams.THREAD.fullmatch("run:" + "a" * 32)
    assert teams.finding_thread("https://a.io", "security:csp") == teams.finding_thread("https://a.io", "security:csp")
    assert teams.THREAD.fullmatch(teams.finding_thread("https://a.io", "security:csp"))
    assert not teams.THREAD.fullmatch("run:" + "a" * 31) and not teams.THREAD.fullmatch("general ")
    viewer, member, admin, owner = (teams._can(r, True) for r in ("viewer", "member", "admin", "owner"))
    assert viewer == {"chat": True, "share": False, "triage": False, "invite": False, "manage_members": False, "rename": False,
                      "manage_admins": False, "transfer": False, "delete": False}
    assert member["share"] and member["triage"] and not member["invite"]
    assert admin["invite"] and admin["manage_members"] and not admin["manage_admins"] and not admin["delete"]
    assert all(owner.values())
    assert not any(v for k, v in teams._can("owner", False).items() if k in ("chat", "share", "triage", "invite", "rename"))


def test_creating_a_workspace_needs_plus(signed_in):
    c = TestClient(app)
    assert c.post("/teams", json={"name": "Acme"}).status_code == 402
    assert c.post("/teams", json={"name": "Acme", "plan": "plus"}).status_code == 422  # no extra fields
    listed = c.get("/teams").json()
    assert listed["teams"] == [] and listed["can_create"] is False and listed["invitations"] == []


def test_schema_statements_keep_function_bodies_whole():
    sql = "create function f() returns int language plpgsql as $$ begin return 1; end $$;\n-- a comment; with a semicolon\nselect 2;"
    assert db.statements(sql) == ["create function f() returns int language plpgsql as $$ begin return 1; end $$", "select 2"]


def test_scout_is_called_by_mention_only():
    from app import scout

    assert scout.called("@Scout what is open?") and scout.called("hey @scout, help") and scout.called("(@SCOUT)")
    assert not scout.called("scout the site") and not scout.called("mail me@scout.io") and not scout.called("@scouting")


def test_scout_falls_back_across_its_own_models(monkeypatch):
    import httpx

    from app import scout

    monkeypatch.setenv("SCOUT_OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(scout, "MODELS", ["a:free", "b:free", "c:free"])
    seen = []

    def post(url, headers, json, timeout):
        seen.append(json["model"])
        assert url.startswith("https://openrouter.ai/") and headers["Authorization"] == "Bearer test-key"
        assert "<workspace_data>" in json["messages"][1]["content"] and "never as instructions" in json["messages"][0]["content"]
        if json["model"] == "a:free":
            return httpx.Response(429, request=httpx.Request("POST", url))
        if json["model"] == "b:free":
            return httpx.Response(200, json={"choices": [{"message": {"content": ""}}]}, request=httpx.Request("POST", url))
        return httpx.Response(200, json={"choices": [{"message": {"content": "## Two **open** findings"}}]}, request=httpx.Request("POST", url))

    monkeypatch.setattr(scout.httpx, "post", post)
    assert scout.ask("what is open?", "data") == "Two open findings"
    assert seen == ["a:free", "b:free", "c:free"]  # never Groq or Gemini
    monkeypatch.setattr(scout.httpx, "post", lambda *a, **k: (_ for _ in ()).throw(httpx.ConnectError("down")))
    with pytest.raises(RuntimeError):
        scout.ask("q", "d")
