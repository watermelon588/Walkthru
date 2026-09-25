"""GitHub App connect and fix pull requests (P4.4) against a fake GitHub: OAuth ownership check, App JWT, one-repo
tokens, and a pull request that only makes config changes and never merges."""

import base64
import json

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app import db, github
from app.main import app
from tests.conftest import USER

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PEM = KEY.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
REPORT = {
    "summary": "s", "top_fixes": [],
    "stack": {"hosting": "vercel", "framework": "nextjs", "backend": None, "evidence": {}},
    "findings": [
        {"kind": "security", "severity": "medium", "title": "No HSTS header", "detail": "d", "fix": "f", "evidence": None, "rule": "sec.hsts.missing"},
        {"kind": "security", "severity": "low", "title": "No X-Content-Type-Options", "detail": "d", "fix": "f", "evidence": None, "rule": "sec.no_x_content_type_options"},
        {"kind": "security", "severity": "medium", "title": "No Content-Security-Policy", "detail": "d", "fix": "f", "evidence": None, "rule": "sec.no_content_security_policy"},
        {"kind": "security", "severity": "high", "title": "Stripe live key in a JavaScript bundle", "detail": "d", "fix": "Rotate it.", "evidence": None,
         "rule": "sec.stripe_live_key_in_a_javascript_bundle"},
        {"kind": "geo", "severity": "low", "title": "No llms.txt", "detail": "d", "fix": "f", "evidence": None, "rule": "geo.no_llms_txt"},
    ],
    "geo": {"fixes": [{"id": "llms", "title": "llms", "file": "llms.txt", "code": "# Site\n\n> What it does.", "note": ""}]},
}


class FakeGitHub:
    def __init__(self):
        self.files = {"vercel.json": json.dumps({"headers": [{"source": "/(.*)", "headers": [{"key": "X-Content-Type-Options", "value": "nosniff"}]}]}),
                      "src/app.js": "console.log(1)"}
        self.writes: list[tuple[str, dict]] = []
        self.token_requests: list[dict] = []
        self.revoked = False
        self.pulls: list[dict] = []
        self.branches: list[str] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        path, method = request.url.path, request.method
        body = json.loads(request.content) if request.content and request.headers.get("content-type", "").startswith("application/json") else {}
        if path == "/login/oauth/access_token":
            return httpx.Response(200, json={"access_token": "user-token"} if b"code=good" in request.content else {"error": "bad_verification_code"})
        if path == "/user/installations":
            return httpx.Response(200, json={"installations": [{"id": 77, "account": {"login": "acme"}}]})
        if path.startswith("/applications/") and method == "DELETE":
            self.revoked = True
            return httpx.Response(204)
        if path == "/app/installations/77/access_tokens":
            claims = jwt.decode(request.headers["authorization"][7:], KEY.public_key(), algorithms=["RS256"])
            assert claims["iss"] == "123"
            self.token_requests.append(body)
            return httpx.Response(201, json={"token": "inst-token"})
        assert request.headers.get("authorization") == "Bearer inst-token", path
        if path == "/installation/repositories":
            return httpx.Response(200, json={"repositories": [{"full_name": "acme/site", "private": True, "default_branch": "main"}]})
        if path == "/repos/acme/site":
            return httpx.Response(200, json={"default_branch": "main"})
        if path.startswith("/repos/acme/site/contents/"):
            name = path.removeprefix("/repos/acme/site/contents/")
            if method == "PUT":
                self.writes.append((name, body))
                return httpx.Response(201, json={})
            if name == "public":
                return httpx.Response(200, json=[{"name": "favicon.ico"}])
            if name in self.files:
                text = self.files[name]
                return httpx.Response(200, json={"type": "file", "size": len(text), "sha": f"sha-{name}", "content": base64.b64encode(text.encode()).decode()})
            return httpx.Response(404, json={"message": "Not Found"})
        if path == "/repos/acme/site/git/ref/heads/main":
            return httpx.Response(200, json={"object": {"sha": "abc123"}})
        if path == "/repos/acme/site/git/refs" and method == "POST":
            self.branches.append(body["ref"])
            return httpx.Response(201, json={})
        if path == "/repos/acme/site/pulls" and method == "POST":
            self.pulls.append(body)
            return httpx.Response(201, json={"html_url": "https://github.com/acme/site/pull/9", "number": 9})
        return httpx.Response(404, json={"message": f"unexpected {method} {path}"})


@pytest.fixture
def gh(monkeypatch, signed_in, passes):
    fake = FakeGitHub()
    from app import main

    main._github_hits.clear()
    for k, v in {"GITHUB_APP_ID": "123", "GITHUB_APP_SLUG": "walkthru-test", "GITHUB_APP_PRIVATE_KEY": PEM.replace("\n", "\\n"),
                 "GITHUB_APP_CLIENT_ID": "Iv1.client", "GITHUB_APP_CLIENT_SECRET": "client-secret"}.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setattr(github, "_http", lambda: httpx.Client(transport=httpx.MockTransport(fake.handle), base_url="https://api.github.com"))
    monkeypatch.setattr(github, "API", "https://api.github.com")
    rows: dict[int, dict] = {}
    monkeypatch.setattr(db, "github_installations", lambda user_id: list(rows.values()) if user_id == USER else [])
    monkeypatch.setattr(db, "add_github_installation", lambda user_id, iid, account: rows.__setitem__(iid, {"installation_id": iid, "account_login": account}))
    monkeypatch.setattr(db, "remove_github_installation", lambda user_id, iid: rows.pop(iid, None) is not None)
    passes.append({"user_id": USER, "plan": "plus", "starts_at": "2000-01-01T00:00:00+00:00", "expires_at": "2999-01-01T00:00:00+00:00", "runs_granted": 150})
    return fake, rows


def test_connect_needs_a_fresh_state_and_the_github_user_owning_the_installation(gh):
    fake, rows = gh
    c = TestClient(app)
    status = c.get("/github").json()
    assert status["configured"] and status["install_url"].startswith("https://github.com/apps/walkthru-test/installations/new?state=")
    state = status["install_url"].split("state=")[1]
    assert c.post("/github/connect", json={"installation_id": 77, "code": "good", "state": "1.forged"}).status_code == 403
    assert c.post("/github/connect", json={"installation_id": 99, "code": "good", "state": state}).status_code == 403  # not theirs
    assert c.post("/github/connect", json={"installation_id": 77, "code": "bad", "state": state}).status_code == 403
    r = c.post("/github/connect", json={"installation_id": 77, "code": "good", "state": state})
    assert r.json() == {"id": 77, "account": "acme"} and fake.revoked and 77 in rows
    assert c.get("/github").json()["installations"] == [{"id": 77, "account": "acme"}]
    assert c.get("/github/repos").json()["repos"] == [{"full_name": "acme/site", "private": True, "default_branch": "main", "installation_id": 77}]
    assert c.delete("/github/installations/77").status_code == 200 and not rows


def test_state_is_bound_to_the_user():
    import os

    os.environ.setdefault("GITHUB_APP_CLIENT_SECRET", "x")
    state = github.state_for("user-a")
    assert github.state_ok("user-a", state) and not github.state_ok("user-b", state) and not github.state_ok("user-a", "1.00")


def test_fix_pr_previews_then_opens_a_config_only_pull_request(gh, fake_db):
    fake, rows = gh
    rows[77] = {"installation_id": 77, "account_login": "acme"}
    fake_db["r" * 32] = {"id": "r" * 32, "user_id": USER, "site": "https://acme.example/", "status": "done", "steps": [], "tier": "paid", "kind": "scan", "report": REPORT}
    c = TestClient(app)
    preview = c.post(f"/runs/{'r' * 32}/fix-pr", json={"installation_id": 77, "repo": "acme/site"}).json()
    assert [x["path"] for x in preview["changes"]] == ["vercel.json", "public/llms.txt"] and not fake.writes and not fake.pulls
    assert "Stripe live key in a JavaScript bundle" in preview["left"]  # secrets are never edited, only explained
    assert fake.token_requests[0]["repositories"] == ["site"] and fake.token_requests[0]["permissions"]["contents"] == "write"

    opened = c.post(f"/runs/{'r' * 32}/fix-pr", json={"installation_id": 77, "repo": "acme/site", "confirm": True}).json()
    assert opened["url"] == "https://github.com/acme/site/pull/9" and fake.branches[0].startswith("refs/heads/walkthru/fixes-rrrrrrrr-")
    written = {name: body for name, body in fake.writes}
    assert set(written) == {"vercel.json", "public/llms.txt"} and written["vercel.json"]["sha"] == "sha-vercel.json" and "sha" not in written["public/llms.txt"]
    config = json.loads(base64.b64decode(written["vercel.json"]["content"]))
    keys = [h["key"] for rule in config["headers"] for h in rule["headers"]]
    assert keys == ["X-Content-Type-Options", "Strict-Transport-Security", "Content-Security-Policy-Report-Only"]  # appended, existing kept, no duplicate
    pr = fake.pulls[0]
    assert pr["base"] == "main" and "never merges" in pr["body"] and "report-only mode" in pr["body"] and "curl -sI https://acme.example/" in pr["body"]
    assert "src/app.js" not in written


def test_fix_pr_rules(gh, fake_db):
    _, rows = gh
    fake_db["s" * 32] = {"id": "s" * 32, "user_id": USER, "site": "https://acme.example/", "status": "done", "steps": [], "tier": "paid", "kind": "scan", "report": REPORT}
    fake_db["t" * 32] = {"id": "t" * 32, "user_id": "someone-else", "site": "https://x.example/", "status": "done", "steps": [], "tier": "paid", "kind": "scan", "report": REPORT}
    c = TestClient(app)
    assert c.post(f"/runs/{'s' * 32}/fix-pr", json={"installation_id": 77, "repo": "acme/site"}).status_code == 404  # installation not connected
    rows[77] = {"installation_id": 77, "account_login": "acme"}
    assert c.post(f"/runs/{'t' * 32}/fix-pr", json={"installation_id": 77, "repo": "acme/site"}).status_code == 404  # another user's run
    for bad in ("../etc", "acme/..", "acme/.", ".acme/site", "acme/site/pulls", "acme"):
        assert c.post(f"/runs/{'s' * 32}/fix-pr", json={"installation_id": 77, "repo": bad}).status_code == 422, bad
    for _ in range(5):
        assert c.post(f"/runs/{'s' * 32}/fix-pr", json={"installation_id": 77, "repo": "acme/site", "confirm": True}).status_code == 200
    assert c.post(f"/runs/{'s' * 32}/fix-pr", json={"installation_id": 77, "repo": "acme/site", "confirm": True}).status_code == 429


def test_changes_per_host_append_and_never_rewrite():
    netlify = {**REPORT, "stack": {"hosting": "netlify", "framework": "vite"}}
    done, _ = github.changes(netlify, lambda p: '[build]\n  publish = "dist"\n' if p == "netlify.toml" else None)
    toml = next(x for x in done if x["path"] == "netlify.toml")["content"]
    assert toml.startswith('[build]\n  publish = "dist"\n') and 'Strict-Transport-Security = "max-age=63072000' in toml
    cloudflare = {**REPORT, "stack": {"hosting": "cloudflare", "framework": "astro"}}
    done, _ = github.changes(cloudflare, lambda p: None)
    assert next(x for x in done if x["path"] == "public/_headers")["content"].startswith("/*\n  Strict-Transport-Security:")
    unknown = {**REPORT, "stack": {"hosting": None, "framework": "nextjs"}}
    done, left = github.changes(unknown, lambda p: None)
    assert [x["path"] for x in done] == ["public/llms.txt"] and any("next.config.js" in x for x in left)
    done, left = github.changes({**REPORT, "stack": {"hosting": "vercel"}}, lambda p: "{not json" if p == "vercel.json" else None)
    assert all(x["path"] != "vercel.json" for x in done) and any("not plain JSON" in x for x in left)
