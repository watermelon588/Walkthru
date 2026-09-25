"""Signup funnel numbers (todo P0.2): counted from stored steps, never guessed."""

from app.agent import funnel


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
