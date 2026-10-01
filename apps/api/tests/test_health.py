from fastapi.testclient import TestClient

from app.main import app


def test_health():
    assert TestClient(app).get("/health").json() == {"status": "ok"}


def test_an_unexpected_error_still_reaches_the_web_app(monkeypatch):
    """A 500 must carry CORS headers, or the browser hides it and the page only says "Failed to fetch"."""
    from app import main

    def broken(user_id):
        raise RuntimeError("a column is missing")

    monkeypatch.setattr(main.citations, "limit_for", broken)
    c = TestClient(app, raise_server_exceptions=False)
    mine = c.get("/citations", headers={"Origin": main.WEB_URL})
    assert mine.status_code == 500 and mine.headers["access-control-allow-origin"] == main.WEB_URL
    assert mine.json()["detail"].startswith("Something went wrong") and "column" not in mine.text  # no internals
    assert "access-control-allow-origin" not in c.get("/citations", headers={"Origin": "https://evil.test"}).headers


def test_health_flags_a_job_queue_nobody_drains(monkeypatch):
    """2026-10-01: an API started with background jobs off took runs but never wrote their reports, and /health said ok."""
    from app import db

    monkeypatch.setattr(db, "oldest_waiting_job", lambda seconds: None)
    assert TestClient(app).get("/health").json() == {"status": "ok"}
    monkeypatch.setattr(db, "oldest_waiting_job", lambda seconds: {"id": 715, "kind": "finish_run", "run_after": "2026-10-01T10:39:16+00:00"})
    stalled = TestClient(app).get("/health")
    assert stalled.status_code == 503 and stalled.json()["status"] == "degraded" and "finish_run" in stalled.json()["detail"]
