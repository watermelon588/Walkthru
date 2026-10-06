"""R-S9 wiring: with RESERVATIONS=postgres every model/data entry point reserves in the shared ledger before dispatch,
as the right owner, and records an honest exit. Off by default. Coverage matrix: docs/work-admission.md."""

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import citations, db, main, mcp_server, plans, reservations, scout, teams, watch
from tests.conftest import USER
from tests.test_citations import store  # noqa: F401 - the in-memory citation tables, a fixture
from tests.test_mcp import _call, fake_keys, fresh_transport, plus  # noqa: F401 - fresh_transport is an autouse fixture
from tests.test_watch_compare import fake_sites

SITE = "https://example.test/"
COMPLETED = {"state": "settled", "actual_cost_microusd": None, "reason": "completed", "credit": 1}
FAILED = {"state": "settled", "actual_cost_microusd": None, "reason": "failed", "credit": 0}
RELEASED = {"state": "released", "actual_cost_microusd": 0, "reason": "not_dispatched", "credit": 0}


@pytest.fixture
def ledger(monkeypatch):
    """The reservation RPCs in memory, recording every call in order with the model calls they guard."""
    calls, state = [], {"status": "reserved"}

    def reserve_work(owner, operation, key, since, until, allowed, units, max_cost, price):
        calls.append(("reserve", operation, owner, allowed, units, max_cost))
        if isinstance(state["status"], Exception):
            raise state["status"]
        return {"status": state["status"], "id": "res-1", **({"state": state["state"]} if "state" in state else {})}

    monkeypatch.setattr(db, "reserve_work", reserve_work)
    monkeypatch.setattr(db, "mark_reservation_dispatched", lambda rid: calls.append(("dispatched", rid)) or True)
    monkeypatch.setattr(db, "finish_reservation", lambda rid, outcome: calls.append(("finish", outcome)) or True)
    monkeypatch.setattr(db, "reservation_for", lambda owner, key: calls.append(("lookup", owner, key)) or {"id": "res-1"})
    monkeypatch.setenv("RESERVATIONS", "postgres")
    return calls, state


@pytest.fixture
def site(monkeypatch):
    """A public page that answers, and a report graph that records its (model) call."""
    calls = []

    class Page:
        status_code, url, text = 200, SITE, "<h1>Hello</h1>"

    monkeypatch.setattr(main.fetch, "assert_public", lambda url: None)
    monkeypatch.setattr(main.fetch, "get", lambda client, url: Page())
    monkeypatch.setattr(main, "_verified", lambda url, uid: False)
    monkeypatch.setattr(main.report, "run_report", lambda *a, **k: calls.append(("model",)) or main.report.Report(summary="ok", findings=[], top_fixes=[]))
    return calls


def names(calls):
    return [c[0] for c in calls]


def scan(**body):
    return TestClient(main.app).post("/scans", json={"site": SITE, **body})


def test_off_by_default_no_entry_point_makes_reservation_requests(monkeypatch, site):
    for name in ("reserve_work", "mark_reservation_dispatched", "finish_reservation", "reservation_for"):
        monkeypatch.setattr(db, name, lambda *a, **k: pytest.fail("reservation request while RESERVATIONS is off"))
    assert scan().status_code == 200 and site == [("model",)]
    with reservations.work("scout", USER, "k", 1) as dispatch:
        dispatch()


def test_instant_scan_reserves_the_public_pool_before_the_model_and_settles(ledger, site):
    calls, _ = ledger
    assert scan().status_code == 200 and site == [("model",)]
    assert names(calls) == ["reserve", "dispatched", "finish"] and calls[-1][1] == COMPLETED
    assert calls[0][1:] == ("public_scan", reservations.PUBLIC, plans.FREE_SCANS_PER_DAY, 1, 0)  # free models: cost 0


def test_dispatch_is_marked_before_the_report_model_call(ledger, site, monkeypatch):
    calls, _ = ledger
    monkeypatch.setattr(main.report, "run_report", lambda *a, **k: calls.append(("model",)) or main.report.Report(summary="ok", findings=[], top_fixes=[]))
    assert scan().status_code == 200
    assert names(calls) == ["reserve", "dispatched", "model", "finish"]


def test_a_reused_scan_reserves_nothing(ledger, site, fake_db):
    from tests.test_scan_reuse import saved

    calls, _ = ledger
    saved(fake_db, age=5)
    assert scan().json()["reuse"]["status"] == "reused"
    assert calls == [] and site == []  # sending a stored report never regenerates or debits it


@pytest.mark.parametrize("status,code", [("no_credits", 429), ("budget", 503), ("unfunded", 503), ("conflict", 409),
                                         (db.DatabaseUnavailable("down"), 503), (httpx.ReadTimeout("lost"), 503)])
def test_refused_or_unconfirmed_scans_fail_closed_before_any_fetch_or_model(ledger, site, fake_db, status, code):
    calls, state = ledger
    state["status"] = status
    assert scan().status_code == code
    assert names(calls) == ["reserve"] and site == [] and not [r for r in fake_db.values() if r.get("kind") == "scan"]


def test_a_settled_replay_is_never_executed_again(ledger, site):
    _, state = ledger
    state.update(status="replayed", state="settled")
    assert scan().status_code == 409 and site == []
    state["state"] = "reserved"  # the same admitted work, retried (another page: the refusal still holds this one's claim)
    assert scan(site="https://example.test/other").status_code == 200 and site == [("model",)]


def test_a_site_that_does_not_answer_releases_without_dispatch(ledger, site, monkeypatch):
    calls, _ = ledger
    monkeypatch.setattr(main.fetch, "get", lambda client, url: None)
    assert scan().status_code == 422
    assert names(calls) == ["reserve", "finish"] and calls[-1][1] == RELEASED and site == []


def test_a_failure_after_dispatch_keeps_the_cost_and_returns_the_credit(ledger, site, monkeypatch):
    calls, _ = ledger
    monkeypatch.setattr(main.report, "run_report", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("model died")))
    with pytest.raises(RuntimeError):
        scan()
    assert names(calls) == ["reserve", "dispatched", "finish"] and calls[-1][1] == FAILED


def test_mcp_scans_and_checks_reserve_as_the_keys_owner(ledger, site, monkeypatch, passes, fake_db):
    calls, state = ledger
    fake_keys(monkeypatch)
    plus(passes)
    with TestClient(main.app) as c:
        key = c.post("/me/api-keys", json={"name": "agent"}).json()["key"]
        error, _ = _call(c, key, "scan_site", {"url": SITE})
        assert not error and calls[0][1:] == ("scan", USER, mcp_server.SCANS_PER_DAY, 1, 0) and calls[-1][1] == COMPLETED
        calls.clear()
        state["status"] = "no_credits"
        error, text = _call(c, key, "scan_site", {"url": SITE})
        assert error and "today's scans" in text and names(calls) == ["reserve"]


def test_mcp_finding_check_reserves_before_rechecking(ledger, monkeypatch, passes, fake_db):
    from tests.test_mcp_tools import RUN, _session

    calls, state = ledger
    _session(monkeypatch, passes, fake_db)
    monkeypatch.setattr(main, "polite", lambda site: None)
    monkeypatch.setattr(main, "_verified", lambda url, uid: False)
    monkeypatch.setattr(mcp_server, "recheck", lambda *a, **k: calls.append(("recheck",)) or "Fixed: it")
    with TestClient(main.app) as c:
        key = c.post("/me/api-keys", json={"name": "agent"}).json()["key"]
        error, text = _call(c, key, "verify_finding", {"run_id": RUN, "rule": "sec.nosniff"})
        assert not error and names(calls) == ["reserve", "dispatched", "recheck", "finish"] and calls[0][2] == USER
        calls.clear()
        state["status"] = "budget"
        error, text = _call(c, key, "verify_finding", {"run_id": RUN, "rule": "sec.nosniff"})
        assert error and "capacity" in text and names(calls) == ["reserve"]


def test_comparison_reserves_every_site_then_the_job_dispatches_and_settles(ledger, site, monkeypatch, passes, fake_db):
    from tests.test_watch_compare import grant

    calls, state = ledger
    grant(passes, "pro")
    body = {"site": "https://site.test", "competitors": ["https://rival.test", "https://other.test"]}
    got = TestClient(main.app).post("/compare", json=body)
    assert got.status_code == 200 and calls[0][1:] == ("scan", USER, mcp_server.SCANS_PER_DAY, 3, 0)
    assert names(calls) == ["reserve", "dispatched", "finish"] and calls[-1][1] == COMPLETED  # jobs run inline in tests
    assert site == [("model",)] * 3  # the parts are covered by the comparison's reservation, not reserved again
    calls.clear()
    state["status"] = "no_credits"
    before = len(fake_db)
    assert TestClient(main.app).post("/compare", json=body).status_code == 429
    assert names(calls) == ["reserve"] and len(fake_db) == before  # no run row, nothing queued


def test_watch_checks_reserve_for_the_sites_owner(ledger, site, monkeypatch, fake_db):
    calls, state = ledger
    fake_sites(monkeypatch)
    row = db.add_site("owner-2", "https://site.test/")
    watch.check(row, "weekly")
    assert calls[0][1:] == ("watch", "owner-2", watch.CHECKS_PER_DAY, 1, 0) and calls[-1][1] == COMPLETED
    calls.clear()
    site.clear()
    state["status"] = "no_credits"
    with pytest.raises(HTTPException):
        watch.check(row, "manual")
    assert names(calls) == ["reserve"] and site == []
    before = row["next_check_at"]
    watch.check_due(row)  # the weekly job reschedules in 6 hours instead of retrying at once
    assert row["next_check_at"] < before and site == []  # in 6 hours, sooner than the week the last check set


def test_answer_batches_reserve_one_unit_per_answer_and_settle_when_done(ledger, store, monkeypatch, passes):  # noqa: F811
    from tests.test_watch_compare import grant

    calls, state = ledger
    grant(passes, "plus")
    queued = []
    monkeypatch.setattr(db, "queue_citation_batch", lambda site_id, batch, rows, caps, weekly: queued.append(rows) or "ok")
    site_row = {"id": "s1", "user_id": USER, "site": SITE, "brand": "Example", "competitors": []}
    prompts = [{"id": f"p{i}", "prompt": f"best notes app {i}"} for i in range(3)]
    citations.queue_batch(site_row, prompts, ("web", "memory"))
    lim = citations.LIMITS["plus"]
    assert calls[0][1:] == ("citations", USER, lim.sites * lim.prompts * 2, 6, 0)
    assert names(calls) == ["reserve", "dispatched"] and len(queued[0]) == 6  # dispatched before the queue accepts it
    calls.clear()
    monkeypatch.setattr(db, "queue_citation_batch", lambda *a: "pending")
    with pytest.raises(citations.QueueFull):
        citations.queue_batch(site_row, prompts, ("web",))
    assert names(calls) == ["reserve", "dispatched", "finish"] and calls[-1][1] == FAILED
    calls.clear()
    state["status"] = "no_credits"
    with pytest.raises(HTTPException) as refused:
        citations.queue_batch(site_row, prompts, ("web",))
    assert refused.value.status_code == 429 and names(calls) == ["reserve"]


def test_last_answer_of_a_batch_settles_its_reservation(ledger, monkeypatch):
    calls, _ = ledger
    batch = [{"batch_id": "b1", "status": "done", "result": {"brands": []}}, {"batch_id": "b1", "status": "failed"}]
    monkeypatch.setattr(db, "citation_checks_for", lambda site_id, limit=200: batch)
    monkeypatch.setattr(db, "citation_site", lambda site_id: {"user_id": USER, "brand": "Example"})
    monkeypatch.setattr(citations.notify, "send", lambda *a, **k: None)
    citations._maybe_announce({"site_id": "s1", "batch_id": "b1"})
    assert calls == [("lookup", USER, "citations-b1"), ("finish", COMPLETED)]


def test_scout_reserves_for_the_workspace_and_answers_the_limit_plainly(ledger, monkeypatch):
    calls, state = ledger
    posted = []
    monkeypatch.setattr(scout, "answers_today", lambda team_id: 0)
    monkeypatch.setattr(scout, "key", lambda: "k")
    monkeypatch.setattr(db, "team_members", lambda team_id: [])
    monkeypatch.setattr(db, "team_runs", lambda team_id, limit=0: [])
    monkeypatch.setattr(db, "runs_brief", lambda ids: [])
    monkeypatch.setattr(teams, "_board", lambda *a: [])
    monkeypatch.setattr(scout, "context", lambda *a: "workspace data")  # offline: no chat history read
    monkeypatch.setattr(scout, "ask", lambda question, data: calls.append(("model",)) or "Two open findings")
    monkeypatch.setattr(db, "insert_message", lambda row: posted.append(row["body"]))
    scout.reply("team-1", "general", "@Scout what is open?", {"id": USER})
    assert names(calls) == ["reserve", "dispatched", "model", "finish"] and calls[0][1:3] == ("scout", "team-1")
    calls.clear()
    state["status"] = "no_credits"
    scout.reply("team-1", "general", "@Scout again?", {"id": USER})
    assert names(calls) == ["reserve"] and "daily limit" in posted[-1]


def test_work_cost_configuration_is_validated(monkeypatch):
    monkeypatch.setenv("WORK_MAX_COST_MICROUSD_SCAN", "12")
    assert reservations.work_cost("scan") == 12
    monkeypatch.setenv("WORK_MAX_COST_MICROUSD_SCAN", "-1")
    with pytest.raises(RuntimeError):
        reservations.work_cost("scan")
