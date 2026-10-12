"""R-S10: quotes pin a run's scope and terms before it starts; acceptance binds the run to them and refuses anything
stale or different; usage history explains every credit and reserved cost; MCP gets the same text."""

import pytest
from fastapi.testclient import TestClient

from app import db, mcp_server, quotes, reservations
from app.main import app
from tests.conftest import USER
from tests.test_plans import grant, graph, start

SITE = "https://fixture.test"


def quote(client, **body):
    r = client.post("/runs/quote", json={"site": SITE, **body})
    assert r.status_code == 200, r.text
    return r.json()


def test_quote_pins_scope_caps_credits_price_and_route():
    q = quote(TestClient(app), max_steps=30)
    t = q["terms"]
    assert t["site"] == SITE and t["plan"] == "free" and t["max_steps"] == 12 and t["max_minutes"] == 4  # clamped to the plan
    assert t["runs_left_before"] == 3 and t["runs"] == 1 and t["price_version"] == reservations.PRICE_VERSION
    assert t["max_cost_microusd_per_run"] == 0 and t["ledger"] == "plan_count" and t["model_route"]
    assert "up to 12 steps and 4 minutes" in q["summary"] and "No card is charged per run" in q["summary"]
    assert any("never continues past them" in r for r in q["rules"]) and any("cheaper route is never substituted" in r for r in q["rules"])


def test_quote_refuses_what_the_plan_would_refuse(passes):
    client = TestClient(app)
    assert client.post("/runs/quote", json={"site": SITE, "logged_in": True}).status_code == 403
    grant(passes, "pro", runs=1)
    assert client.post("/runs/quote", json={"site": SITE, "personas": ["first_timer", "buyer"]}).status_code == 402


def test_an_accepted_quote_starts_the_run(monkeypatch):
    graph(monkeypatch)
    client = TestClient(app)
    token = quote(client)["token"]
    assert start(client, quote=token, max_steps=12).status_code == 200
    assert start(client).status_code == 200  # older clients without a quote still work by default


@pytest.mark.parametrize("change", [{"site": "https://other.test"}, {"persona": "buyer"}, {"logged_in": True}])
def test_a_run_asking_for_more_than_its_quote_is_refused(monkeypatch, passes, change):
    graph(monkeypatch)
    grant(passes, "pro")  # the plan allows each change; only the quote does not
    client = TestClient(app)
    token = quote(client)["token"]
    r = start(client, quote=token, **change)
    assert r.status_code == 409 and "more than its quote" in r.json()["detail"]
    with pytest.raises(quotes.HTTPException, match="409"):
        quotes.accept(token, USER, site=SITE, persona="first_timer", logged_in=False, max_steps=12, assertion=True)


def test_a_run_never_exceeds_the_quoted_step_cap(monkeypatch):
    graph(monkeypatch)
    client = TestClient(app)
    seen = []
    original = __import__("app.main", fromlist=["runtime"]).runtime.invoke
    monkeypatch.setattr("app.main.runtime.invoke", lambda tier, state, cfg: seen.append(state["max_steps"]) or original(tier, state, cfg))
    token = quote(client, max_steps=5)["token"]
    assert start(client, quote=token, max_steps=30).status_code == 200
    assert seen == [5]


def test_expired_tampered_or_foreign_quotes_are_refused(monkeypatch):
    graph(monkeypatch)
    client = TestClient(app)
    token = quote(client)["token"]
    payload = token.rsplit(".", 1)[0]
    assert "not valid" in start(client, quote=payload + "." + "0" * 64).json()["detail"]
    assert start(client, quote="garbage").status_code == 409
    with monkeypatch.context() as later:  # scoped: undoing everything would also drop the offline database fakes
        later.setattr(quotes.time, "time", lambda: 10**12)
        assert "expired" in start(client, quote=token).json()["detail"]
    other = quotes.issue(quotes.terms(USER, SITE, personas=["first_timer"], logged_in=False, max_steps=12, assertion=False) | {"user": "someone-else"})
    assert "different account" in start(client, quote=other["token"]).json()["detail"]


@pytest.mark.parametrize("change", ["price_version", "cap", "plan"])
def test_changed_server_terms_make_the_quote_stale(monkeypatch, passes, change):
    graph(monkeypatch)
    client = TestClient(app)
    token = quote(client)["token"]
    if change == "price_version":
        monkeypatch.setattr(reservations, "PRICE_VERSION", "run-caps-2027-01-01")
    elif change == "cap":
        monkeypatch.setitem(reservations.CAP_ENV, "free", "RUN_MAX_COST_MICROUSD_FREE_TEST")
        monkeypatch.setenv("RUN_MAX_COST_MICROUSD_FREE_TEST", "5000")
    else:
        grant(passes, "pro")
    r = start(client, quote=token)
    assert r.status_code == 409 and r.json()["detail"] == quotes.STALE


def test_quotes_can_be_required(monkeypatch):
    graph(monkeypatch)
    monkeypatch.setenv("RUN_QUOTES", "required")
    client = TestClient(app)
    assert start(client).status_code == 428
    assert start(client, quote=quote(client)["token"]).status_code == 200


ROWS = [
    {"operation": "run", "operation_key": "r1", "state": "settled", "units": 1, "dispatched": True, "max_cost_microusd": 250000,
     "actual_cost_microusd": None, "price_version": "v", "outcome": {"credit": 1, "reason": "completed"}, "created_at": "2026-10-07T01:00:00Z"},
    {"operation": "run", "operation_key": "r2", "state": "released", "units": 1, "dispatched": False, "max_cost_microusd": 250000,
     "actual_cost_microusd": 0, "price_version": "v", "outcome": {"credit": 0, "reason": "not_dispatched"}, "created_at": "2026-10-07T02:00:00Z"},
    {"operation": "run", "operation_key": "r3", "state": "settled", "units": 1, "dispatched": True, "max_cost_microusd": 0,
     "actual_cost_microusd": None, "price_version": "v", "outcome": {"credit": 0, "reason": "refused"}, "created_at": "2026-10-07T03:00:00Z"},
    {"operation": "scan", "operation_key": "s1", "state": "reserved", "units": 3, "dispatched": True, "max_cost_microusd": 0,
     "actual_cost_microusd": None, "price_version": "v", "outcome": None, "created_at": "2026-10-07T04:00:00Z"},
    {"operation": "run", "operation_key": "r4", "state": "refunded", "units": 1, "dispatched": True, "max_cost_microusd": 0, "actual_cost_microusd": 80,
     "price_version": "v", "outcome": {"credit": 1, "reason": "completed", "refund": {"actor": "founder", "reason": "Customer refund"}}, "created_at": "2026-10-07T05:00:00Z"},
    {"operation": "public_scan", "operation_key": "p", "state": "settled", "units": 1, "dispatched": True, "max_cost_microusd": 0,
     "actual_cost_microusd": None, "price_version": "v", "outcome": {"credit": 1, "reason": "completed"}, "created_at": "2026-10-07T06:00:00Z"},
]


def test_usage_history_explains_every_outcome(monkeypatch):
    client = TestClient(app)
    assert client.get("/me/usage").json()["ledger"] == "off"
    monkeypatch.setenv("RESERVATIONS", "postgres")
    monkeypatch.setattr(db, "reservations_for", lambda user, limit=50: ROWS)
    items = client.get("/me/usage").json()["items"]
    texts = [i["text"] for i in items]
    assert len(items) == 5  # anonymous Instant Scans are not this account's usage
    assert texts[0] == "Used 1 test run (completed)." and "reserved maximum of $0.25" in items[0]["cost"]
    assert texts[1].startswith("Returned: the work never started") and items[1]["cost"] == ""
    assert texts[2] == "Not counted: the goal was refused before the test started, so 1 test run returned."
    assert texts[3] == "In progress or awaiting its result: 3 scans or finding checks counted until it settles."
    assert items[3]["cost"] == "No provider cost reserved."
    assert texts[4] == "Refunded by Walkthru (Customer refund): 1 test run returned." and items[4]["cost"] == "Provider cost $0.00008."


def test_run_usage_is_owner_only_and_reports_steps(monkeypatch, fake_db):
    fake_db["run-1"] = {"id": "run-1", "user_id": USER, "status": "budget", "steps": [{"action": "click"}, {"action": "done"}], "site": SITE}
    client = TestClient(app)
    off = client.get("/runs/run-1/usage").json()
    assert off == {"run_id": "run-1", "status": "budget", "steps_recorded": 1, "ledger": "off"}
    monkeypatch.setenv("RESERVATIONS", "postgres")
    monkeypatch.setattr(db, "run_usage", lambda user, run: ROWS[0])
    assert client.get("/runs/run-1/usage").json()["usage"]["text"] == "Used 1 test run (completed)."
    fake_db["run-2"] = fake_db["run-1"] | {"id": "run-2", "user_id": "someone-else"}
    assert client.get("/runs/run-2/usage").status_code == 404


def test_mcp_gets_the_same_quote_and_usage_text(monkeypatch):
    token = mcp_server._user.set(USER)
    try:
        text = mcp_server.get_run_quote("fixture.test")
        assert text.startswith("https://fixture.test: one test user, one run") and "Walkthru Chrome extension" in text
        assert "never continues past them" in text
        with pytest.raises(mcp_server.ToolError, match="paid plan"):
            mcp_server.get_run_quote("fixture.test", logged_in=True)
        assert "ledger is not active" in mcp_server.get_usage()
        monkeypatch.setenv("RESERVATIONS", "postgres")
        monkeypatch.setattr(db, "reservations_for", lambda user, limit=50: ROWS[:2])
        assert "Used 1 test run (completed)." in mcp_server.get_usage()
    finally:
        mcp_server._user.reset(token)
