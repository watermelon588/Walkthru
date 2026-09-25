"""Walkthru MCP server (Plus): personal API keys and the /mcp endpoint. ARCHITECTURE.md `mcp`."""

import json
import threading
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
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
        assert tools == {"scan_site", "get_report", "get_fix_prompt", "rerun", "list_runs", "get_finding", "verify_finding"}

        got = _rpc(c, key, "tools/call", {"name": "get_report", "arguments": {"run_id": mine}}, id_=3).json()["result"]
        text = got["content"][0]["text"]
        assert not got.get("isError") and "Launch Ready score: 81" in text and "Fix: Add one." in text

        other = _rpc(c, key, "tools/call", {"name": "get_report", "arguments": {"run_id": theirs}}, id_=4).json()["result"]
        assert other.get("isError") and "No run with that id" in other["content"][0]["text"]  # never another user's run

        passes.clear()  # the Plus pass lapsed: the key alone is not enough
        assert _rpc(c, key, "tools/list", id_=5).status_code == 402


# ---------- P1.4: one finding at a time ----------




class Site:
    """A local site whose headers and HTML the test changes between checks, like a developer applying a fix."""

    def __init__(self):
        self.headers = {"Content-Security-Policy": "default-src 'self'", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer"}
        self.html = "<html lang='en'><head><title>Acme</title></head><body><h1>Acme</h1><p>Plenty of words here.</p></body></html>"
        site = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                body = site.html.encode() if self.path == "/" else b"not found"
                self.send_response(200 if self.path == "/" else 404)
                self.send_header("Content-Type", "text/html")
                for k, v in site.headers.items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()


@pytest.fixture(autouse=True)
def fresh_transport(monkeypatch):
    """Each test starts the app's lifespan again, and an MCP session manager can run only once. No scans today."""
    mcp_server.build_transport()
    monkeypatch.setattr(db, "user_scans_today", lambda user: 0)
    monkeypatch.setattr(mcp_server, "_verifies", {})


@pytest.fixture
def site(monkeypatch):
    monkeypatch.setenv("ALLOW_LOCAL_SCANS", "1")
    s = Site()
    yield s
    s.server.shutdown()


def _call(c, key, tool, args, id_=10):
    got = _rpc(c, key, "tools/call", {"name": tool, "arguments": args}, id_=id_).json()["result"]
    return got.get("isError", False), got["content"][0]["text"]


def _stored(fake_db, site_url, findings, run_id="c" * 32):
    fake_db[run_id] = {"id": run_id, "user_id": USER, "site": site_url, "kind": "scan", "status": "done", "goal": "Instant Scan",
                       "report": {"summary": "", "top_fixes": [], "findings": findings, "pages": {}}}
    return run_id


NOSNIFF = {"kind": "security", "severity": "low", "title": "No X-Content-Type-Options", "detail": "Browsers may sniff file types.",
           "fix": "Send X-Content-Type-Options: nosniff.", "evidence": "http://site/"}


def test_verify_finding_flips_to_fixed_after_the_fix(monkeypatch, passes, fake_db, site):
    fake_keys(monkeypatch)
    plus(passes)
    run_id = _stored(fake_db, site.url, [NOSNIFF, {"kind": "seo", "severity": "medium", "title": "Missing meta description",
                                                  "detail": "d", "fix": "Add one.", "evidence": site.url}])
    with TestClient(app) as c:
        key = c.post("/me/api-keys", json={"name": "claude"}).json()["key"]
        _rpc(c, key, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}})

        error, report = _call(c, key, "get_report", {"run_id": run_id})
        assert not error and "(id: security:no x-content-type-options)" in report

        error, recipe = _call(c, key, "get_finding", {"run_id": run_id, "rule": "security:no x-content-type-options"})
        assert not error and "## Change\nSend X-Content-Type-Options: nosniff." in recipe and 'verify_finding("' in recipe

        error, before = _call(c, key, "verify_finding", {"run_id": run_id, "rule": "security:no x-content-type-options"})
        assert not error and before.startswith("Still broken: No X-Content-Type-Options"), before

        site.headers["X-Content-Type-Options"] = "nosniff"  # the fix
        error, after = _call(c, key, "verify_finding", {"run_id": run_id, "rule": "No X-Content-Type-Options"})  # the title works too
        assert not error and after.startswith("Fixed: No X-Content-Type-Options"), after

        # An SEO finding goes through the site audit, the same check that reported it.
        error, seo = _call(c, key, "verify_finding", {"run_id": run_id, "rule": "seo:missing meta description"})
        assert not error and seo.startswith("Still broken: Missing meta description"), seo
        site.html = site.html.replace("<title>", "<meta name='description' content='Acme makes notes you can find.'><title>")
        error, seo = _call(c, key, "verify_finding", {"run_id": run_id, "rule": "seo:missing meta description"})
        assert not error and seo.startswith("Fixed: Missing meta description"), seo


def test_verify_finding_refuses_journeys_unknown_ids_and_other_users(monkeypatch, passes, fake_db, site):
    fake_keys(monkeypatch)
    plus(passes)
    run_id = _stored(fake_db, site.url, [{"kind": "ux", "severity": "high", "title": "Signup button does nothing", "detail": "d", "fix": "f", "evidence": "step 3"}])
    theirs = _stored(fake_db, site.url, [NOSNIFF], run_id="d" * 32)
    fake_db[theirs]["user_id"] = OTHER
    with TestClient(app) as c:
        key = c.post("/me/api-keys", json={"name": "claude"}).json()["key"]
        error, text = _call(c, key, "verify_finding", {"run_id": run_id, "rule": "Signup button does nothing"})
        assert error and "Chrome extension" in text
        error, text = _call(c, key, "get_finding", {"run_id": run_id, "rule": "security:made-up"})
        assert error and "has no finding" in text
        error, text = _call(c, key, "verify_finding", {"run_id": theirs, "rule": "No X-Content-Type-Options"})
        assert error and "No run with that id" in text


def test_verify_finding_shares_the_daily_scan_cap(monkeypatch, passes, fake_db, site):
    fake_keys(monkeypatch)
    plus(passes)
    run_id = _stored(fake_db, site.url, [NOSNIFF])
    monkeypatch.setattr(db, "user_scans_today", lambda user: mcp_server.SCANS_PER_DAY - 1)
    with TestClient(app) as c:
        key = c.post("/me/api-keys", json={"name": "claude"}).json()["key"]
        assert not _call(c, key, "verify_finding", {"run_id": run_id, "rule": "No X-Content-Type-Options"})[0]
        error, text = _call(c, key, "verify_finding", {"run_id": run_id, "rule": "No X-Content-Type-Options"}, id_=11)
        assert error and "limit resets at midnight UTC" in text
