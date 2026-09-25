"""Walkthru MCP server (Plus): personal API keys and the /mcp endpoint. ARCHITECTURE.md `mcp`."""

import json
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app import db, mcp_server
from app.main import app
from tests.conftest import USER

OTHER = "00000000-0000-0000-0000-000000000002"
MCP_HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


def plus(passes, user=USER):
    now = datetime.now(UTC)
    passes.append({"user_id": user, "plan": "plus", "starts_at": (now - timedelta(days=1)).isoformat(),
                   "expires_at": (now + timedelta(days=29)).isoformat(), "runs_granted": 150})


def fake_keys(monkeypatch):
    keys: dict[str, dict] = {}

    def insert(user_id, name, key_hash):
        key_id = f"00000000-0000-0000-0000-{len(keys):012d}"
        keys[key_id] = {"id": key_id, "user_id": user_id, "name": name, "key_hash": key_hash, "revoked": False}
        return {"id": key_id, "name": name, "created_at": "now"}

    monkeypatch.setattr(db, "insert_api_key", insert)
    monkeypatch.setattr(db, "api_keys_for_user", lambda user_id: [{"id": k["id"], "name": k["name"]} for k in keys.values() if k["user_id"] == user_id and not k["revoked"]])
    monkeypatch.setattr(db, "api_key_owner", lambda h: next(({"id": k["id"], "user_id": k["user_id"]} for k in keys.values() if k["key_hash"] == h and not k["revoked"]), None))
    monkeypatch.setattr(db, "touch_api_key", lambda key_id: None)

    def revoke(user_id, key_id):
        k = keys.get(key_id)
        if not k or k["user_id"] != user_id or k["revoked"]:
            return False
        k["revoked"] = True
        return True

    monkeypatch.setattr(db, "revoke_api_key", revoke)
    return keys


def test_keys_are_plus_only_shown_once_capped_and_revocable(monkeypatch, passes):
    keys = fake_keys(monkeypatch)
    c = TestClient(app)
    assert c.post("/me/api-keys", json={"name": "laptop"}).status_code == 402  # free plan
    plus(passes)
    made = c.post("/me/api-keys", json={"name": "laptop"}).json()
    assert made["key"].startswith("wt_") and len(made["key"]) > 40
    stored = next(iter(keys.values()))
    assert stored["key_hash"] == mcp_server.key_hash(made["key"]) and made["key"] not in json.dumps(keys)  # only the hash is kept
    assert "key" not in c.get("/me/api-keys").json()[0]  # never shown again
    for i in range(4):
        c.post("/me/api-keys", json={"name": f"k{i}"})
    assert c.post("/me/api-keys", json={"name": "sixth"}).status_code == 409
    assert c.delete(f"/me/api-keys/{made['id']}").status_code == 200
    assert c.delete(f"/me/api-keys/{made['id']}").status_code == 404  # already revoked
    assert c.delete("/me/api-keys/not-a-key").status_code == 404


def _rpc(c, key, method, params=None, id_=1):
    body = {"jsonrpc": "2.0", "id": id_, "method": method, "params": params or {}}
    return c.post("/mcp", headers=MCP_HEADERS | {"Authorization": f"Bearer {key}"}, json=body)


def test_mcp_endpoint_checks_the_key_and_plan_then_serves_tools(monkeypatch, passes, fake_db):
    fake_keys(monkeypatch)
    plus(passes)
    mine, theirs = "a" * 32, "b" * 32
    report = {"summary": "Mostly ready.", "top_fixes": ["Add a meta description."], "launch_ready": {"score": 81},
              "findings": [{"kind": "seo", "severity": "high", "title": "Missing meta description", "detail": "d", "fix": "Add one.", "evidence": "https://site.test/"}]}
    fake_db[mine] = {"id": mine, "user_id": USER, "site": "https://site.test/", "kind": "scan", "status": "done", "goal": "Instant Scan", "report": report}
    fake_db[theirs] = {"id": theirs, "user_id": OTHER, "site": "https://other.test/", "kind": "scan", "status": "done", "goal": "Instant Scan", "report": report}

    with TestClient(app) as c:  # the lifespan starts the MCP session manager
        key = c.post("/me/api-keys", json={"name": "cursor"}).json()["key"]

        assert c.post("/mcp", headers=MCP_HEADERS, json={}).status_code == 401  # no key
        assert _rpc(c, "wt_not-a-real-key", "tools/list").status_code == 401

        init = _rpc(c, key, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}})
        assert init.status_code == 200, init.text
        tools = {t["name"] for t in _rpc(c, key, "tools/list", id_=2).json()["result"]["tools"]}
        assert tools == {"scan_site", "get_report", "get_fix_prompt", "rerun", "list_runs"}

        got = _rpc(c, key, "tools/call", {"name": "get_report", "arguments": {"run_id": mine}}, id_=3).json()["result"]
        text = got["content"][0]["text"]
        assert not got.get("isError") and "Launch Ready score: 81" in text and "Fix: Add one." in text

        other = _rpc(c, key, "tools/call", {"name": "get_report", "arguments": {"run_id": theirs}}, id_=4).json()["result"]
        assert other.get("isError") and "No run with that id" in other["content"][0]["text"]  # never another user's run

        passes.clear()  # the Plus pass lapsed: the key alone is not enough
        assert _rpc(c, key, "tools/list", id_=5).status_code == 402
