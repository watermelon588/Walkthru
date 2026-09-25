"""Signup funnel numbers (todo P0.2): counted from stored steps, never guessed."""

from app.agent import funnel, report
from app.agent.schema import Report
from app.main import finish_run as real_finish_run
from tests.conftest import USER


def step(action, progress=0, at=None, errors=(), safe=False):
    return {"action": action, "progress": progress, "errors_after": list(errors), "safe_stop": safe,
            "evidence": {"captured_at": at} if at else None}


def test_counts_a_signup_that_reached_the_goal():
    steps = [
        step("click", at="2026-09-25T10:00:00+00:00"),
        step("type", errors=["Email is required"]),
        step("type", errors=["Email is required"]),  # the same error twice counts once
        step("click", progress=1, at="2026-09-25T10:00:42+00:00"),
        step("done", progress=2),
    ]
    assert funnel.metrics(steps, "done") == {"steps_to_goal": 5, "fields_typed": 2, "errors_seen": 1, "safe_stops": 0,
                                              "first_useful_step": 4, "seconds_to_first_useful": 42}


def test_unfinished_runs_and_missing_screenshots_say_so_instead_of_guessing():
    m = funnel.metrics([step("type"), step("click", safe=True)], "safe_stop")
    assert m["steps_to_goal"] is None and m["first_useful_step"] is None and m["seconds_to_first_useful"] is None
    assert m["safe_stops"] == 1 and m["fields_typed"] == 1


def test_retyping_one_field_counts_one_field_and_repeated_errors_count_once():
    steps = [step("type", errors=[" Email is required "]) | {"url": "https://site.test/signup", "target_id": 2},
             step("type", errors=["email IS required"]) | {"url": "https://site.test/signup", "target_id": 2},
             step("type") | {"url": "https://site.test/signup", "target_id": 3}]
    result = funnel.metrics(steps, "done")
    assert result["fields_typed"] == 2 and result["errors_seen"] == 1


def test_paid_rerun_saves_current_and_previous_funnel(monkeypatch, fake_db):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.setattr(report, "run_report", lambda *args, **kwargs: Report(summary="done", findings=[], top_fixes=[]))
    old_steps = [step("click", at="2026-09-25T10:00:00+00:00"), step("click", progress=1, at="2026-09-25T10:01:00+00:00")]
    fake_db["old"] = {"id": "old", "user_id": USER, "site": "https://site.test/", "goal": "Sign up", "kind": "test",
                      "tier": "paid", "status": "done", "report": {"findings": [], "funnel": funnel.metrics(old_steps, "done")},
                      "created_at": "2026-09-24T00:00:00+00:00"}
    fake_db["new"] = {"id": "new", "user_id": USER, "site": "https://site.test/", "goal": "Sign up", "kind": "test",
                      "persona": "first_timer", "tier": "paid", "status": "done", "report": None,
                      "created_at": "2026-09-25T00:00:00+00:00"}
    new_steps = [step("click", at="2026-09-25T11:00:00+00:00"), step("click", progress=1, at="2026-09-25T11:00:30+00:00")]
    real_finish_run("new", {"steps": new_steps, "status": "done"})
    saved = fake_db["new"]["report"]
    assert saved["comparison"]["previous_run_id"] == "old"
    assert saved["funnel"]["seconds_to_first_useful"] == 30
    assert saved["funnel"]["previous"]["seconds_to_first_useful"] == 60
