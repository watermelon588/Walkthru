"""The job worker (app/jobs.py): outcomes, retries, periodic windows and the handlers' run-twice safety. The claim SQL
itself is tested in test_jobs_sql.py."""

from datetime import UTC, datetime

import pytest

from app import db, jobs, main, plans, watch

REAL_FINISH_RUN = main.finish_run  # conftest swaps it for a recorder in every test


@pytest.fixture
def queue(monkeypatch):
    """One claimable job at a time, and every enqueue and outcome recorded."""
    state = {"due": [], "finished": [], "queued": []}
    monkeypatch.setattr(db, "claim_job", lambda lease: state["due"].pop(0) if state["due"] else None)
    monkeypatch.setattr(db, "finish_job", lambda job_id, lease, values: state["finished"].append((job_id, lease, values)))
    monkeypatch.setattr(db, "enqueue_job", lambda kind, payload, *, max_attempts, dedupe_key: state["queued"].append((kind, payload, dedupe_key)))
    return state


def job(kind="retention", attempts=1, max_attempts=3, payload=None) -> dict:
    return {"id": 7, "kind": kind, "payload": payload or {}, "attempts": attempts, "max_attempts": max_attempts, "lease": "L1"}


def test_nothing_due(queue):
    assert jobs.run_one() is False and queue["finished"] == []


def test_a_finished_job_is_marked_done_under_its_lease(queue, monkeypatch):
    ran = []
    monkeypatch.setattr(jobs, "handle", lambda kind, p: ran.append(kind))
    queue["due"].append(job())
    assert jobs.run_one() is True and ran == ["retention"]
    assert queue["finished"] == [(7, "L1", {"status": "done", "locked_until": None, "last_error": None})]


def test_a_failure_is_retried_later_then_recorded_as_failed(queue, monkeypatch):
    def boom(kind, p):
        raise RuntimeError("provider down")

    monkeypatch.setattr(jobs, "handle", boom)
    queue["due"] += [job(attempts=1), job(attempts=3)]
    jobs.run_one()
    retry = queue["finished"][0][2]
    assert retry["status"] == "queued" and retry["last_error"] == "RuntimeError: provider down"
    assert retry["run_after"] > datetime.now(UTC).isoformat()
    jobs.run_one()
    assert queue["finished"][1][2]["status"] == "failed" and "run_after" not in queue["finished"][1][2]


def test_backoff_doubles_with_jitter_and_caps_at_an_hour():
    assert 15 <= jobs.backoff(1) <= 30 and 60 <= jobs.backoff(3) <= 120 and 1800 <= jobs.backoff(20) <= 3600


def test_periodic_passes_are_queued_once_per_window(queue):
    jobs.schedule(now=6 * 3600 * 10 + 5)
    jobs.schedule(now=6 * 3600 * 10 + 1700)  # same windows: same keys, so the table keeps one of each
    jobs.schedule(now=6 * 3600 * 10 + 1900)  # the next 30-minute window: only a new watch pass
    keys = [key for _, _, key in queue["queued"]]
    assert keys[:2] == keys[2:4] and len(set(keys)) == 3 and {k.split(":")[0] for k in keys} == {"retention", "watch_due"}


def test_unknown_kinds_are_refused_at_the_door(queue):
    with pytest.raises(ValueError):
        jobs.enqueue("mine_bitcoin")
    assert queue["queued"] == []


def test_a_report_job_run_twice_writes_the_report_once(monkeypatch, fake_db):
    calls = []
    monkeypatch.setattr(main, "finish_run", lambda run_id, values: calls.append(run_id))
    db.insert_run("r1", "u", "https://site.test", "g", "first_timer", "free", False)
    jobs.handle("finish_run", {"run_id": "r1", "values": {}})
    fake_db["r1"]["report"] = {"findings": []}
    jobs.handle("finish_run", {"run_id": "r1", "values": {}})  # the lease ran out after the report was saved
    assert calls == ["r1"]


def test_the_report_job_keeps_only_what_finish_run_reads(queue):
    state = {"status": "done", "steps": [{"action": "done"}], "tokens": 5, "first_text": "Welcome", "plan": {"intent": "sign up"},
             "observation": {"url": "https://site.test/", "text": "page text " * 500, "elements": [{"tag": "button", "text": "Go"}]},
             "persona_prompt": "an owner's private description"}
    main._finish_later("r1", state)
    kind, payload, key = queue["queued"][0]
    assert key == "report:r1"
    assert kind == "finish_run" and payload["values"]["observation"] == {"elements": [{"tag": "button", "text": "Go"}]}
    assert set(payload["values"]) == {"status", "steps", "tokens", "first_text", "plan", "observation"}


def test_weekly_watch_queues_one_job_per_site_and_due_time(queue, monkeypatch):
    site = {"id": "s1", "user_id": "u", "site": "https://site.test/", "next_check_at": "2026-09-27T10:00:00+00:00"}
    monkeypatch.setattr(db, "due_sites", lambda now: [site])
    monkeypatch.setattr(plans, "current", lambda uid: {"plan": plans.PLANS["plus"]})
    assert watch.run_due() == 1 and watch.run_due() == 1
    assert [q[2] for q in queue["queued"]] == ["watch:s1:2026-09-27T10:00:00+00:00"] * 2  # the same key: one job


def test_a_failed_weekly_check_comes_back_in_six_hours(monkeypatch):
    updates = []
    monkeypatch.setattr(watch, "check", lambda site, reason="weekly": (_ for _ in ()).throw(RuntimeError("down")))
    monkeypatch.setattr(db, "update_site", lambda site_id, values: updates.append(values["next_check_at"]))
    watch.check_due({"id": "s1", "site": "https://site.test/"})
    assert updates and updates[0] > datetime.now(UTC).isoformat()


def test_a_failed_report_is_retried_not_marked_done(queue, monkeypatch):
    """finish_run used to swallow its error, so the job was 'done', the run had no report and the page waited forever."""
    monkeypatch.setattr(db, "get_run", lambda run_id: {"id": run_id, "site": "https://example.com", "goal": "Sign up", "persona": "first_timer",
                                                       "status": "done", "user_id": None, "tier": "free", "report": None})

    def down(*a, **k):
        raise RuntimeError("every model failed")

    monkeypatch.setattr(main.report, "run_report", down)
    monkeypatch.setattr(main, "finish_run", REAL_FINISH_RUN)
    queue["due"].append(job(kind="finish_run", attempts=1, payload={"run_id": "r1", "values": {"status": "done", "steps": []}}))
    jobs.run_one()
    outcome = queue["finished"][0][2]
    assert outcome["status"] == "queued" and outcome["last_error"] == "RuntimeError: every model failed"
