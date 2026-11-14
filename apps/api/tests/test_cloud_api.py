"""The live-run routes queue, report and stop; they never drive a browser themselves (docs/in-app-runner-plan.md, T6)."""

import uuid

import pytest
from fastapi.testclient import TestClient

from app import cloud, db, plans
from app.main import app
from tests.conftest import USER

client = TestClient(app)


@pytest.fixture
def queue(monkeypatch):
    rows: list[dict] = []
    monkeypatch.setenv("CLOUD_RUNNER", "on")
    monkeypatch.setenv("ALLOW_LOCAL_SCANS", "1")  # no DNS in tests; the address rule has its own test below

    def add(new):
        for row in new:
            rows.append(row | {"id": str(uuid.uuid4()), "status": "queued", "run_id": None, "error": None,
                               "created_at": f"2026-11-12T00:00:{len(rows):02d}+00:00", "updated_at": "2026-11-12T00:00:00+00:00"})
        return rows[-len(new):]

    def stop(group_id, user_id):
        hit = [r for r in rows if r["group_id"] == group_id and r["user_id"] == user_id and r["status"] in ("queued", "running")]
        for row in hit:
            row["status"] = "stopped"
        return hit

    monkeypatch.setattr(db, "queue_cloud_runs", add)
    monkeypatch.setattr(db, "cloud_runs_in_group", lambda group_id, user_id: [r for r in rows if r["group_id"] == group_id and r["user_id"] == user_id])
    monkeypatch.setattr(db, "active_cloud_runs", lambda user_id: sum(r["user_id"] == user_id and r["status"] in ("queued", "running") for r in rows))
    monkeypatch.setattr(db, "cloud_runs_ahead", lambda created_at: sum(r["status"] in ("queued", "running") and r["created_at"] < created_at for r in rows))
    monkeypatch.setattr(db, "stop_cloud_runs", stop)
    return rows


def plan(monkeypatch, name, used=0):
    chosen = plans.PLANS[name]
    monkeypatch.setattr(plans, "current", lambda user_id: {"plan": chosen, "used": used, "allowed": chosen.runs, "sites": set()})


def start(**kw):
    return client.post("/cloud-runs", json={"site": "https://shop.example", "goal": "find pricing"} | kw)


def test_off_by_default(monkeypatch):
    monkeypatch.delenv("CLOUD_RUNNER", raising=False)
    r = start()
    assert r.status_code == 403 and "extension" in r.json()["detail"]


def test_a_test_user_is_queued_without_verifying_the_site(queue, monkeypatch):
    plan(monkeypatch, "free")
    r = start(max_steps=25)
    assert r.status_code == 200
    card = r.json()["runs"][0]
    assert card["status"] == "queued" and card["ahead"] == 0 and card["steps"] == []
    assert queue[0]["max_steps"] == plans.PLANS["free"].max_steps  # clamped to the plan
    assert queue[0]["user_id"] == USER


def test_private_addresses_are_refused_with_the_extension_as_the_way(queue, monkeypatch):
    plan(monkeypatch, "free")
    monkeypatch.delenv("ALLOW_LOCAL_SCANS")
    r = start(site="http://127.0.0.1:3000")
    assert r.status_code == 422 and "extension" in r.json()["detail"] and queue == []


def test_plan_rules_apply_before_anything_is_queued(queue, monkeypatch):
    plan(monkeypatch, "free")
    assert start(personas=["skeptic"]).status_code == 403  # a paid test user
    assert start(personas=["first_timer", "skeptic"]).status_code == 403  # several test users
    assert start(personas=["custom:" + str(uuid.uuid4())]).status_code == 403
    plan(monkeypatch, "free", used=3)
    assert start().status_code == 402
    plan(monkeypatch, "plus", used=149)
    r = start(personas=["first_timer", "skeptic"])
    assert r.status_code == 402 and "needs 2 runs" in r.json()["detail"]
    assert queue == []


def test_one_account_holds_at_most_three_places_in_the_queue(queue, monkeypatch):
    plan(monkeypatch, "plus")
    first = start(personas=["first_timer", "skeptic", "buyer"])
    assert first.status_code == 200
    assert [c["ahead"] for c in first.json()["runs"]] == [0, 1, 2]
    again = start()
    assert again.status_code == 429 and "3 test users" in again.json()["detail"]
    client.post(f"/cloud-runs/{first.json()['group_id']}/stop")
    assert start().status_code == 200


def test_watching_shows_steps_only_from_the_owners_own_run(queue, fake_db, monkeypatch):
    plan(monkeypatch, "free")
    group = start().json()["group_id"]
    fake_db["a" * 32] = {"id": "a" * 32, "user_id": USER, "status": "running", "persona": "first_timer", "report": None,
                         "steps": [{"thought": "Looking", "action": "scroll", "confusion": 0, "tokens": 9, "observation_revision": "x",
                                    "evidence": {"screenshot_path": "a" * 32 + "/step-01.jpg", "label": "Scrolled down"}}]}
    fake_db["b" * 32] = {"id": "b" * 32, "user_id": str(uuid.uuid4()), "status": "running", "steps": [{"thought": "someone else's"}]}
    monkeypatch.setattr(db, "get_run", lambda run_id: fake_db.get(run_id))
    queue[0] |= {"status": "running", "run_id": "a" * 32}
    card = client.get(f"/cloud-runs/{group}").json()["runs"][0]
    assert card["run_status"] == "running" and card["report_ready"] is False
    assert card["steps"] == [{"thought": "Looking", "action": "scroll", "confusion": 0, "evidence": {"screenshot_path": "a" * 32 + "/step-01.jpg", "label": "Scrolled down"}}]
    queue[0]["run_id"] = "b" * 32
    assert client.get(f"/cloud-runs/{group}").json()["runs"][0]["steps"] == []


def test_another_accounts_test_is_not_found(queue, monkeypatch):
    plan(monkeypatch, "free")
    group = start().json()["group_id"]
    queue[0]["user_id"] = str(uuid.uuid4())
    assert client.get(f"/cloud-runs/{group}").status_code == 404
    assert client.post(f"/cloud-runs/{group}/stop").status_code == 404
    assert client.get("/cloud-runs/not-a-uuid").status_code == 422


def test_stop_ends_queued_and_running_test_users(queue, monkeypatch):
    plan(monkeypatch, "plus")
    group = start(personas=["first_timer", "skeptic"]).json()["group_id"]
    queue[0]["status"] = "running"
    assert client.post(f"/cloud-runs/{group}/stop").json() == {"stopped": 2}
    assert {r["status"] for r in queue} == {"stopped"}
    assert cloud.MAX_PERSONAS == 3
