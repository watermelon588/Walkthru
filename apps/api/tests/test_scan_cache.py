"""Public Instant Scan reuse must never include owner or incomplete reports."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app import db, main

lookup = db.recent_public_scan


def test_database_lookup_is_public_anonymous_complete_and_recent(monkeypatch):
    seen = []
    monkeypatch.setattr(db, "_rows", lambda params: seen.append(params) or [{"id": "cached"}])
    before = datetime.now(UTC) - timedelta(minutes=10)
    assert lookup("https://example.test/a?x=1")["id"] == "cached"
    query = seen[0]
    assert query == {
        "site": "eq.https://example.test/a?x=1", "kind": "eq.scan", "tier": "eq.free",
        "user_id": "is.null", "public": "eq.true", "status": "eq.done",
        "report": "not.is.null", "created_at": query["created_at"],
        "order": "created_at.desc", "limit": "1", "select": "id,site,report",
    }
    assert before <= datetime.fromisoformat(query["created_at"][3:]) <= datetime.now(UTC) - timedelta(minutes=10)
    monkeypatch.setattr(db, "_rows", lambda params: [])
    assert lookup("https://example.test/") is None


@pytest.fixture
def cached(monkeypatch):
    row = {"id": "cached", "site": "https://example.test/", "report": {"summary": "Saved report"}}
    monkeypatch.setattr(db, "recent_public_scan", lambda site: row)
    monkeypatch.setattr(main.fetch, "assert_public", lambda site: None)
    monkeypatch.setattr(main, "run_scan", lambda *a, **k: pytest.fail("cache hit started a new scan"))
    return row


def test_hit_works_at_daily_capacity_and_can_email_saved_report(monkeypatch, cached):
    monkeypatch.setattr(db, "free_runs_today", lambda kind: main.plans.FREE_SCANS_PER_DAY)
    sent = []
    monkeypatch.setattr(main.deliver, "send_report", lambda *args: sent.append(args))
    response = TestClient(main.app).post("/scans", json={"site": cached["site"], "email": "reader@example.com"})
    assert response.status_code == 200
    assert response.json()["run_id"] == "cached"
    assert response.json()["report"] == cached["report"]
    assert sent == [("reader@example.com", f"{main.WEB_URL}/r/cached", cached["site"], cached["report"])]


@pytest.mark.parametrize("blocked", ["opt_out", "paused", "private"])
def test_cache_does_not_bypass_current_safety_rules(monkeypatch, cached, blocked):
    if blocked == "opt_out":
        monkeypatch.setattr(main.policy, "category", lambda site: "site owner opt-out")
    elif blocked == "paused":
        monkeypatch.setattr(main.abuse, "paused", lambda *args: True)
    else:
        def private(site):
            raise ValueError("site resolves to a private address")
        monkeypatch.setattr(main.fetch, "assert_public", private)
    assert TestClient(main.app).post("/scans", json={"site": cached["site"]}).status_code == 422


def test_cache_hit_still_counts_address_limit(monkeypatch, cached):
    monkeypatch.setattr(main, "SCAN_LIMIT", 1)
    client = TestClient(main.app)
    assert client.post("/scans", json={"site": cached["site"]}).status_code == 200
    assert client.post("/scans", json={"site": cached["site"]}).status_code == 429


@pytest.mark.parametrize("change", [
    {"public": False}, {"user_id": "owner"}, {"tier": "paid"},
    {"kind": "compare_part"}, {"kind": "watch"}, {"kind": "test"},
    {"status": "running"}, {"status": "failed"}, {"report": None},
    {"age": 601}, {"site": "https://example.test/other"},
    {"site": "https://example.test/?q=other"}, {"site": "http://example.test/"},
])
def test_ineligible_rows_trigger_a_fresh_scan(monkeypatch, fake_db, change):
    row = {"id": "old", "site": "https://example.test/", "kind": "scan", "tier": "free",
           "user_id": None, "public": True, "status": "done", "report": {"summary": "Old"},
           "created_at": (datetime.now(UTC) - timedelta(seconds=change.get("age", 1))).isoformat()}
    row.update({k: v for k, v in change.items() if k != "age"})
    fake_db["old"] = row
    monkeypatch.setattr(main.fetch, "assert_public", lambda site: None)
    scans = []
    def scan(site):
        scans.append(site)
        return "new", {"site": site, "report": {"summary": "Fresh"}}
    monkeypatch.setattr(main, "run_scan", scan)
    response = TestClient(main.app).post("/scans", json={"site": "https://example.test/"})
    assert response.status_code == 200
    assert response.json()["run_id"] == "new"
    assert scans == ["https://example.test/"]


def test_newest_match_reused_without_extending_expiry(monkeypatch, fake_db):
    for name, age in [("older", 500), ("newer", 10)]:
        fake_db[name] = {"id": name, "site": "https://example.test/", "kind": "scan", "tier": "free",
                         "user_id": None, "public": True, "status": "done", "report": {"summary": name},
                         "created_at": (datetime.now(UTC) - timedelta(seconds=age)).isoformat()}
    original = fake_db["newer"].copy()
    monkeypatch.setattr(main.fetch, "assert_public", lambda site: None)
    monkeypatch.setattr(main, "run_scan", lambda site: pytest.fail("started new scan"))
    response = TestClient(main.app).post("/scans", json={"site": "https://EXAMPLE.test"})
    assert response.json()["run_id"] == "newer"
    assert fake_db["newer"] == original
    assert len(fake_db) == 2
