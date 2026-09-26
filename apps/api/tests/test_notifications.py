"""In-app notifications (app/notify.py): the events that create them, the sidebar counts, and marking them read."""

from fastapi.testclient import TestClient

from app import db, notify
from app.main import app
from tests.conftest import USER

OTHER = "00000000-0000-0000-0000-000000000009"


def test_counts_per_section_only_for_the_caller_and_read_by_section(fake_db):
    notify.pass_granted(USER, "plus", 30)
    notify.report_ready(USER, "a" * 32, "https://acme.test", "Sign up for an account")
    notify.report_ready(OTHER, "b" * 32, "https://other.test", "Theirs")
    c = TestClient(app)
    body = c.get("/me/notifications").json()
    assert body["counts"] == {"runs": 1, "team": 0, "compare": 0, "watch": 0, "billing": 1, "visibility": 0}
    assert {n["title"] for n in body["recent"]} == {"Your Plus plan is active", "Report ready: Sign up for an account"}
    assert c.post("/me/notifications/read", json={"section": "billing"}).status_code == 200
    assert c.get("/me/notifications").json()["counts"]["billing"] == 0
    assert c.post("/me/notifications/read", json={"section": "nope"}).status_code == 422
    c.post("/me/notifications/read", json={})
    assert sum(c.get("/me/notifications").json()["counts"].values()) == 0
    assert next(n for n in fake_db.notes if n["user_id"] == OTHER)["read_at"] is None  # never someone else's


def test_links_stay_inside_the_app_and_unknown_sections_are_dropped(fake_db):
    notify.send(USER, "billing", "x", "t", link="https://evil.example")
    notify.send(USER, "nowhere", "x", "t")
    notify.send(None, "runs", "x", "t")
    assert [n["link"] for n in fake_db.notes] == [""]


def test_a_failing_store_never_breaks_the_action(monkeypatch):
    monkeypatch.setattr(db, "add_notification", lambda row: (_ for _ in ()).throw(RuntimeError("down")))
    notify.pass_granted(USER, "pro", 30)  # no exception


def test_a_paid_dodo_pass_tells_the_buyer(fake_db, monkeypatch):
    from app import billing

    monkeypatch.setattr(db, "grant_paid_entitlement", lambda row: True)
    billing._grant({"user_id": USER, "plan": "pro", "days": 30, "runs": 40, "id": "o1"}, "pay_1")
    assert fake_db.notes[-1]["title"] == "Payment confirmed. Pro is active" and fake_db.notes[-1]["link"] == "/app/billing"


def test_the_admin_grant_tells_the_user_live(fake_db, monkeypatch):
    from admin import app as admin_app

    monkeypatch.setattr(admin_app, "_users", lambda: [{"id": USER, "email": "me@example.com"}])
    monkeypatch.setattr(db, "grant_entitlement", lambda *a: None)
    monkeypatch.setattr(db, "audit", lambda *a: None)
    assert admin_app._grant("me@example.com", "plus", 30, None, "founder") == "granted"
    assert fake_db.notes[-1]["section"] == "billing" and fake_db.notes[-1]["title"] == "Your Plus plan is active"
