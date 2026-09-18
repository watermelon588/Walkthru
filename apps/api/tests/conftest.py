"""Shared fakes: in-memory runs table and a fixed signed-in user. Tests never touch Supabase."""

import pytest

from app import db
from app.auth import require_user
from app.main import app

USER = "00000000-0000-0000-0000-000000000001"


@pytest.fixture(autouse=True)
def fake_db(monkeypatch):
    rows: dict[str, dict] = {}

    def insert_run(run_id, user_id, site, goal, persona, tier, logged_in):
        rows[run_id] = {"id": run_id, "user_id": user_id, "site": site, "goal": goal, "persona": persona, "tier": tier, "logged_in": logged_in, "status": "running", "steps": []}

    def update_run(run_id, status, steps):
        rows[run_id] |= {"status": status, "steps": steps}

    monkeypatch.setattr(db, "insert_run", insert_run)
    monkeypatch.setattr(db, "get_run", rows.get)
    monkeypatch.setattr(db, "update_run", update_run)
    return rows


@pytest.fixture(autouse=True)
def signed_in():
    app.dependency_overrides[require_user] = lambda: USER
    yield
    app.dependency_overrides.clear()
