import asyncio
import io
import json
import logging
import re

import httpx
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app import auth, main
from app.observability import JsonFormatter, RequestLog, SafeStreamHandler, bind_user
from tests.conftest import USER


def events(caplog):
    return [json.loads(JsonFormatter().format(r)) for r in caplog.records if getattr(r, "event", "") in {"request_finished", "request_failed", "server_error"}]


def test_correlation_header_cors_and_no_query_or_inbound_id_leak(caplog):
    c = TestClient(main.app)
    response = c.get("/health?token=private-query", headers={"X-Request-Id": "private-token", "Origin": main.WEB_URL})
    rid = response.headers["x-request-id"]
    assert re.fullmatch(r"[a-f0-9]{32}", rid)
    assert "X-Request-Id" in response.headers["access-control-expose-headers"]
    row = events(caplog)[-1]
    assert row["request_id"] == rid and row["route"] == "/health" and row["status"] == 200 and row["duration_ms"] >= 0
    assert "private-" not in json.dumps(row)
    assert c.get("/not-a-route/private-path?email=private-email").status_code == 404
    assert events(caplog)[-1]["route"] == "[unmatched]"


def test_early_body_limit_and_validation_errors_have_support_ids():
    c = TestClient(main.app)
    for response in (c.post("/scans", content=b"x", headers={"Content-Length": "1000001"}), c.post("/scans", json={})):
        assert response.status_code in (413, 422)
        assert re.fullmatch(r"[a-f0-9]{32}", response.headers["x-request-id"])


def test_unhandled_error_has_same_id_in_response_log_and_admin_event(monkeypatch, caplog):
    recorded = []
    def fail(user):
        raise RuntimeError("secret-token email@example.com typed-password snapshot-text")
    monkeypatch.setattr(main.citations, "limit_for", fail)
    monkeypatch.setattr(main.db, "app_event", lambda *args: recorded.append(args))
    response = TestClient(main.app, raise_server_exceptions=False).get("/citations", headers={"Origin": main.WEB_URL})
    rid = response.headers["x-request-id"]
    assert response.status_code == 500 and response.json()["request_id"] == rid
    assert "X-Request-Id" in response.headers["access-control-expose-headers"]
    rows = events(caplog)
    assert all(r["request_id"] == rid for r in rows)
    assert recorded[0][2]["request_id"] == rid
    text = json.dumps(rows) + response.text + json.dumps(recorded)
    for secret in ("secret-token", "email@example.com", "typed-password", "snapshot-text"):
        assert secret not in text
    assert next(r for r in rows if r["event"] == "server_error")["error_type"] == "RuntimeError"


def test_authenticated_user_is_bound_from_verified_auth_including_cache(monkeypatch, caplog):
    main.app.dependency_overrides.pop(auth.require_user)
    monkeypatch.setattr(auth, "_cache", auth.OrderedDict())
    monkeypatch.setattr(main.db, "citation_sites", lambda user_id: [])
    monkeypatch.setenv("SUPABASE_URL", "https://auth.example")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "test")
    monkeypatch.setattr(auth.httpx, "get", lambda *a, **kw: httpx.Response(200, json={"id": USER, "email": "private@example.com"}))
    c = TestClient(main.app)
    for _ in range(2):
        assert c.get("/citations", headers={"Authorization": "Bearer secret-test-session"}).status_code == 200
        assert events(caplog)[-1]["user_id"] == USER
    assert "secret-test-session" not in json.dumps(events(caplog))


def test_formatter_drops_untrusted_arguments_exceptions_and_extras():
    record = logging.LogRecord("httpx", logging.ERROR, __file__, 1, "secret %s", ("Bearer key",), None)
    record.email = "private@example.com"
    record.snapshot = "customer page"
    record.event = "secret-event"
    row = json.loads(JsonFormatter().format(record))
    assert row["event"] == "log"
    assert all(secret not in json.dumps(row) for secret in ("Bearer", "private@", "customer", "secret"))


def test_closed_log_sink_never_prints_unsanitized_logging_diagnostics(capsys):
    stream = io.StringIO()
    stream.close()
    handler = SafeStreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    handler.emit(logging.LogRecord("httpx", logging.ERROR, __file__, 1, "secret %s", ("Bearer key",), None))
    assert capsys.readouterr().err == ""


def test_parallel_requests_keep_ids_and_users_isolated(caplog):
    app = FastAPI()
    app.add_middleware(RequestLog)
    @app.get("/test/{user_id}")
    async def sample(user_id: str, request: Request):
        bind_user(request.scope, user_id)
        await asyncio.sleep(0.01)
        return {"ok": True}
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
            return await asyncio.gather(client.get(f"/test/{USER}"), client.get("/test/00000000-0000-0000-0000-000000000002"))
    responses = asyncio.run(run())
    rows = events(caplog)
    assert len({r["request_id"] for r in rows}) == 2
    assert rows[0]["request_id"] in {r.headers["x-request-id"] for r in responses}
    assert {r["user_id"] for r in rows} == {USER, "00000000-0000-0000-0000-000000000002"}
