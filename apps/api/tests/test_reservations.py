"""R-S8 wiring: with RESERVATIONS=postgres a run is admitted only after its credit and maximum cost are reserved,
provider work is marked before the first model call, and every exit records an honest settlement. Off by default."""

import httpx
import pytest
from fastapi.testclient import TestClient

from app import db, jobs, main, reservations
from app.main import app
from tests.conftest import USER
from tests.test_plans import graph, start


@pytest.fixture
def ledger(monkeypatch):
    """The reservation RPCs in memory, recording every call in order with the goal planner."""
    calls, state = [], {"status": "reserved"}

    def reserve_run(user, key, window_start, window_end, allowed, max_cost, price):
        calls.append(("reserve", key, allowed, max_cost, price))
        if isinstance(state["status"], Exception):
            raise state["status"]
        return {"status": state["status"], "id": "res-1"} if state["status"] in ("reserved", "replayed") else {"status": state["status"]}

    def mark(rid):
        calls.append(("dispatched", rid))
        if state.get("mark_fails"):
            raise httpx.ConnectError("down")
        return True

    def finish(rid, outcome):
        calls.append(("finish", rid, outcome))
        return True

    monkeypatch.setattr(db, "reserve_run", reserve_run)
    monkeypatch.setattr(db, "mark_reservation_dispatched", mark)
    monkeypatch.setattr(db, "finish_reservation", finish)
    monkeypatch.setattr(db, "reservation_for", lambda user, key: {"id": "res-1"})
    original = main.goal.plan
    monkeypatch.setattr(main.goal, "plan", lambda *a, **k: calls.append(("planner",)) or original(*a, **k))
    monkeypatch.setenv("RESERVATIONS", "postgres")
    return calls, state


def test_off_by_default_makes_no_reservation_requests(monkeypatch):
    graph(monkeypatch)
    for name in ("reserve_run", "mark_reservation_dispatched", "finish_reservation", "reservation_for"):
        monkeypatch.setattr(db, name, lambda *a, **k: pytest.fail("reservation request while RESERVATIONS is off"))
    assert start(TestClient(app)).status_code == 200
    assert reservations.enabled() is False


def test_reservation_and_dispatch_mark_precede_the_first_model_call(monkeypatch, ledger):
    calls, _ = ledger
    graph(monkeypatch)
    assert start(TestClient(app)).status_code == 200
    names = [c[0] for c in calls]
    assert names[:3] == ["reserve", "dispatched", "planner"]
    reserve = calls[0]
    assert reserve[2] == 3 and reserve[3] == 0 and reserve[4] == reservations.PRICE_VERSION  # free plan: 3 runs, free models


@pytest.mark.parametrize("status,code", [("no_credits", 402), ("budget", 503), ("unfunded", 503), ("conflict", 409),
                                         (db.DatabaseUnavailable("down"), 503), (httpx.ReadTimeout("lost"), 503)])
def test_refused_or_unconfirmed_reservations_fail_closed_before_any_model_call(monkeypatch, ledger, fake_db, status, code):
    calls, state = ledger
    state["status"] = status
    graph(monkeypatch)
    assert start(TestClient(app)).status_code == code
    assert [c[0] for c in calls] == ["reserve"] and not [r for r in fake_db.values() if r.get("kind") == "test"]


def test_unrecorded_dispatch_releases_and_starts_nothing(monkeypatch, ledger):
    calls, state = ledger
    state["mark_fails"] = True
    graph(monkeypatch)
    assert start(TestClient(app)).status_code == 503
    assert [c[0] for c in calls] == ["reserve", "dispatched", "finish"]
    assert calls[2][2] == {"state": "released", "actual_cost_microusd": 0, "reason": "not_dispatched", "credit": 0}


def test_refused_goal_gives_the_credit_back_and_keeps_the_cost(monkeypatch, ledger):
    calls, _ = ledger
    graph(monkeypatch)
    monkeypatch.setattr(main.goal, "plan", lambda *a, **k: calls.append(("planner",)) or {"feasible": False, "refusal": "bulk sign-ups"})
    assert start(TestClient(app)).status_code == 422
    assert calls[-1] == ("finish", "res-1", {"state": "settled", "actual_cost_microusd": None, "reason": "refused", "credit": 0})


def test_a_failure_after_dispatch_settles_without_using_the_credit(monkeypatch, ledger):
    calls, _ = ledger
    graph(monkeypatch)
    def broken(*a, **k):
        raise db.DatabaseUnavailable("insert failed")
    monkeypatch.setattr(db, "insert_run", broken)
    assert start(TestClient(app)).status_code == 503
    assert calls[-1] == ("finish", "res-1", {"state": "settled", "actual_cost_microusd": None, "reason": "failed", "credit": 0})


def test_report_job_settles_the_used_credit_on_every_attempt(monkeypatch, ledger, fake_db):
    calls, _ = ledger
    fake_db["r1"] = {"id": "r1", "user_id": USER, "report": {"summary": "done"}}
    jobs.handle("finish_run", {"run_id": "r1", "values": {}})
    jobs.handle("finish_run", {"run_id": "r1", "values": {}})  # a retried job sends the identical outcome
    completed = {"state": "settled", "actual_cost_microusd": None, "reason": "completed", "credit": 1}
    assert [c for c in calls if c[0] == "finish"] == [("finish", "res-1", completed)] * 2


def test_settlement_failure_leaves_the_reservation_counted(monkeypatch, ledger, caplog):
    def down(*a):
        raise db.DatabaseUnavailable("down")
    monkeypatch.setattr(db, "finish_reservation", down)
    reservations.settle(USER, "r1", "completed")  # does not raise: the run already happened
    assert "not settled yet" in caplog.text


def test_configuration_is_validated(monkeypatch):
    monkeypatch.setenv("RESERVATIONS", "on")
    with pytest.raises(RuntimeError):
        reservations.enabled()
    monkeypatch.setenv("RUN_MAX_COST_MICROUSD_PRO", "1.5")
    with pytest.raises(RuntimeError):
        reservations.max_cost("pro")
    monkeypatch.setenv("RUN_MAX_COST_MICROUSD_PRO", "250000")
    assert reservations.max_cost("pro") == 250000 and reservations.max_cost("free") == 0
