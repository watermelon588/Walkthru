"""Shared fakes: in-memory runs table and a fixed signed-in user. Tests never touch Supabase."""

import os

import pytest

os.environ["RETENTION_JOB"] = "0"  # before app.main is imported

from app import db
from app.auth import require_user
from app.main import app

USER = "00000000-0000-0000-0000-000000000001"


@pytest.fixture(autouse=True)
def fake_db(monkeypatch):
    rows: dict[str, dict] = {}

    def insert_run(run_id, user_id, site, goal, persona, tier, logged_in, *, kind="test", email=None, public=False):
        rows[run_id] = {"id": run_id, "user_id": user_id, "site": site, "goal": goal, "persona": persona, "tier": tier, "logged_in": logged_in, "status": "running", "steps": [], "kind": kind, "email": email, "public": public, "report": None, "tokens": 0}

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
    return rows


@pytest.fixture(autouse=True)
def no_background(monkeypatch):
    """Report generation runs in the background in prod; tests call it explicitly."""
    from app import main

    monkeypatch.setattr(main, "finish_run", lambda run_id, values: None)


@pytest.fixture(autouse=True)
def signed_in():
    app.dependency_overrides[require_user] = lambda: {"id": USER, "email": "tester@example.com"}
    yield
    app.dependency_overrides.clear()
