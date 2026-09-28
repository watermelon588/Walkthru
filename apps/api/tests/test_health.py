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
