"""Shared fakes: in-memory runs table and a fixed signed-in user. Tests never touch Supabase."""

import os
from datetime import UTC, datetime

import pytest

os.environ["RETENTION_JOB"] = "0"  # before app.main is imported
os.environ["WARMUP"] = "0"

from app import db
from app.auth import require_user
from app.main import app

USER = "00000000-0000-0000-0000-000000000001"


@pytest.fixture(autouse=True)
def fake_db(monkeypatch):
    rows: dict[str, dict] = {}

    def insert_run(run_id, user_id, site, goal, persona, tier, logged_in, *, kind="test", email=None, public=False):
        rows[run_id] = {"id": run_id, "user_id": user_id, "site": site, "goal": goal, "persona": persona, "tier": tier, "logged_in": logged_in, "status": "running", "steps": [], "kind": kind, "email": email, "public": public, "report": None, "tokens": 0, "created_at": datetime.now(UTC).isoformat()}

    def test_runs_since(user_id, since):
        start = datetime.fromisoformat(since)
        return [r for r in rows.values() if r.get("user_id") == user_id and r.get("kind") == "test" and datetime.fromisoformat(r.get("created_at", since)) >= start]

    def free_runs_today():
        return sum(1 for r in rows.values() if r.get("kind") == "test" and r.get("tier") == "free")

    def update_run(run_id, status, steps, tokens=0):
        rows[run_id] |= {"status": status, "steps": steps, "tokens": tokens}

    def mark_run_stopped(run_id, steps, tokens=0):
        if rows[run_id]["status"] != "running":
            return False
        rows[run_id] |= {"status": "stopped", "steps": steps, "tokens": tokens}
        return True

    def set_report(run_id, report, status=None):
        rows[run_id] |= {"report": report, "tokens": report.get("tokens", 0), "status": status or rows[run_id]["status"]}

    monkeypatch.setattr(db, "insert_run", insert_run)
    monkeypatch.setattr(db, "get_run", rows.get)
    monkeypatch.setattr(db, "update_run", update_run)
    monkeypatch.setattr(db, "mark_run_stopped", mark_run_stopped)
    monkeypatch.setattr(db, "set_report", set_report)
    monkeypatch.setattr(db, "set_public", lambda run_id, public=True: rows[run_id].__setitem__("public", public))
    monkeypatch.setattr(db, "test_runs_since", test_runs_since)
    monkeypatch.setattr(db, "free_runs_today", free_runs_today)
    return rows


@pytest.fixture(autouse=True)
def passes(monkeypatch):
    """In-memory entitlements table: tests append {user_id, plan, starts_at, expires_at, runs_granted}."""
    table: list[dict] = []

    def active_entitlement(user_id, now):
        live = [p for p in table if p["user_id"] == user_id and p["starts_at"] <= now < p["expires_at"]]
        return max(live, key=lambda p: p["expires_at"], default=None)

    monkeypatch.setattr(db, "active_entitlement", active_entitlement)
    monkeypatch.setattr(db, "entitlements_for_user", lambda user_id: [p for p in table if p["user_id"] == user_id])
    return table


@pytest.fixture(autouse=True)
def no_background(monkeypatch):
    """Report generation runs in the background in prod; tests call it explicitly."""
    from app import main

    monkeypatch.setattr(main, "finish_run", lambda run_id, values: None)
    monkeypatch.setattr(main, "_verified", lambda site, user_id: False)  # no network in tests


@pytest.fixture(autouse=True)
def signed_in():
    app.dependency_overrides[require_user] = lambda: {"id": USER, "email": "tester@example.com"}
    yield
    app.dependency_overrides.clear()
