"""Readiness fails closed on unavailable dependencies while health retains its liveness contract."""

import time

import httpx
import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app

PRIVATE = "synthetic-private-database-detail"
STALE = {"id": 987654, "kind": "finish_run", "run_after": "2001-01-01T00:00:00+00:00"}


def readiness_response():
    return TestClient(app, raise_server_exceptions=False).get("/ready")


def assert_unavailable(response):
    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.headers.get("cache-control") == "no-store"
    assert all(value not in response.text for value in (PRIVATE, str(STALE["id"]), STALE["kind"], STALE["run_after"]))


def test_ready_requires_a_successful_database_check_and_no_stalled_job(monkeypatch):
    monkeypatch.setattr(db, "readiness", lambda seconds: None, raising=False)
    response = readiness_response()
    assert response.status_code == 200 and response.json() == {"status": "ready"}
    assert response.headers.get("cache-control") == "no-store"


def test_stalled_job_makes_readiness_unavailable_without_exposing_job_details(monkeypatch):
    monkeypatch.setattr(db, "readiness", lambda seconds: STALE, raising=False)
    assert_unavailable(readiness_response())


def test_readiness_never_writes_a_rate_limit_counter(monkeypatch):
    calls = []
    monkeypatch.delenv("ALLOW_LOCAL_SCANS", raising=False)
    monkeypatch.setattr(db, "readiness", lambda seconds: None, raising=False)
    monkeypatch.setattr(db, "hit_rate_limit", lambda *args: calls.append(args) or 3600)
    response = readiness_response()
    assert response.status_code == 200
    assert calls == []


@pytest.mark.parametrize("failure", ["database", "http", "query", "delayed_timeout"])
def test_database_failures_fail_readiness_closed_without_exposing_details(monkeypatch, failure):
    def unavailable(seconds):
        if failure == "database":
            raise db.DatabaseUnavailable(PRIVATE)
        if failure == "http":
            response = httpx.Response(503, text=PRIVATE, request=httpx.Request("HEAD", "https://database.test/rest/v1/runs"))
            response.raise_for_status()
        if failure == "query":
            raise ValueError(PRIVATE)
        time.sleep(0.01)
        raise httpx.ReadTimeout(PRIVATE)

    monkeypatch.setattr(db, "readiness", unavailable, raising=False)
    assert_unavailable(readiness_response())


def test_database_readiness_failure_does_not_change_health_liveness(monkeypatch):
    def unavailable(seconds):
        raise db.DatabaseUnavailable(PRIVATE)

    monkeypatch.setattr(db, "readiness", unavailable, raising=False)
    monkeypatch.setattr(db, "oldest_waiting_job", unavailable)
    response = TestClient(app).get("/health")
    assert response.status_code == 200 and response.json() == {"status": "ok"}


def test_health_retains_existing_stalled_queue_compatibility(monkeypatch):
    monkeypatch.setattr(db, "oldest_waiting_job", lambda seconds: STALE)
    response = TestClient(app).get("/health")
    assert response.status_code == 503 and response.json()["status"] == "degraded"


def database_readiness():
    implementation = getattr(db, "readiness", None)
    assert callable(implementation), "Database readiness must check the database independently of the liveness endpoint"
    return implementation


def test_database_readiness_uses_only_bounded_reads_with_short_timeouts(monkeypatch):
    seen = []

    def handle(request):
        seen.append(request)
        return httpx.Response(200) if request.method == "HEAD" else httpx.Response(200, json=[])

    with httpx.Client(base_url="https://database.test", transport=httpx.MockTransport(handle)) as client:
        monkeypatch.setattr(db, "client", lambda: client)
        assert database_readiness()(120) is None

    assert [(request.method, request.url.path) for request in seen] == [("HEAD", "/rest/v1/runs"), ("GET", "/rest/v1/jobs")]
    for request in seen:
        assert request.content == b""
        assert request.url.params.get("limit") in {"0", "1"}
        assert request.url.params.get("select") and "*" not in request.url.params["select"]
        timeout = request.extensions["timeout"]
        assert timeout["connect"] == 1 and timeout["read"] == 2


def test_database_readiness_reports_the_oldest_stalled_job(monkeypatch):
    def handle(request):
        if request.method == "HEAD":
            return httpx.Response(200)
        return httpx.Response(200, json=[STALE])

    with httpx.Client(base_url="https://database.test", transport=httpx.MockTransport(handle)) as client:
        monkeypatch.setattr(db, "client", lambda: client)
        assert database_readiness()(120) == STALE


@pytest.mark.parametrize("failure", ["head_http", "head_timeout", "jobs_http", "jobs_timeout", "jobs_invalid_json"])
def test_database_readiness_surfaces_errors_without_retries(monkeypatch, failure):
    seen = []

    def handle(request):
        seen.append(request)
        if failure == "head_timeout" or (failure == "jobs_timeout" and request.method == "GET"):
            raise httpx.ReadTimeout(PRIVATE, request=request)
        if (failure == "head_http" and request.method == "HEAD") or (failure == "jobs_http" and request.method == "GET"):
            return httpx.Response(503, text=PRIVATE)
        if failure == "jobs_invalid_json" and request.method == "GET":
            return httpx.Response(200, text="not-json")
        return httpx.Response(200) if request.method == "HEAD" else httpx.Response(200, json=[])

    with httpx.Client(base_url="https://database.test", transport=httpx.MockTransport(handle)) as client:
        monkeypatch.setattr(db, "client", lambda: client)
        implementation = database_readiness()
        with pytest.raises((db.DatabaseUnavailable, httpx.HTTPError, ValueError)):
            implementation(120)
    assert len(seen) == (1 if failure.startswith("head_") else 2)
