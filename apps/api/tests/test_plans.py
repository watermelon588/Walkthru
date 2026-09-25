"""The server owns the plan: whatever the client sends, limits come from the caller's entitlement."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import MemorySaver

from app import plans
from app.agent import runtime
from app.agent.persona import build_graph
from app.agent.schema import PersonaStep
from app.main import app
from tests.conftest import USER


class Scroller:
    def invoke(self, messages):
        return PersonaStep(thought="looking around", action="scroll", confusion=0)


def graph(monkeypatch):
    g = build_graph(Scroller(), MemorySaver())
    monkeypatch.setattr(runtime, "graph", lambda tier: g)
    return g


def start(client, site="https://fixture.test", **kw):
    obs = {"url": site + "/", "title": "t", "elements": [], "text": "hello"}
    return client.post("/runs", json={"site": site, "goal": "sign up", "observation": obs} | kw)


def grant(passes, plan, days=30, runs=None, started_days_ago=0):
    now = datetime.now(UTC)
    passes.append({"user_id": USER, "plan": plan, "starts_at": (now - timedelta(days=started_days_ago)).isoformat(),
                   "expires_at": (now + timedelta(days=days)).isoformat(), "runs_granted": runs or plans.PLANS[plan].runs})


def test_free_user_cannot_test_logged_in_pages(monkeypatch):
    graph(monkeypatch)
    r = start(TestClient(app), logged_in=True)
    assert r.status_code == 403
    assert "paid plan" in r.json()["detail"]


def test_free_user_gets_the_first_time_visitor_only(monkeypatch):
    graph(monkeypatch)
    assert start(TestClient(app), persona="skeptic").status_code == 403
    assert start(TestClient(app), persona="first_timer").status_code == 200


def test_client_tier_is_ignored(monkeypatch, fake_db):
    graph(monkeypatch)
    run_id = start(TestClient(app), tier="paid").json()["run_id"]
    assert fake_db[run_id]["tier"] == "free"


def test_free_steps_are_capped_at_12_whatever_the_client_asks(monkeypatch):
    g = graph(monkeypatch)
    run_id = start(TestClient(app), max_steps=25).json()["run_id"]
    assert g.get_state({"configurable": {"thread_id": run_id}}).values["max_steps"] == 12


def test_fourth_free_run_in_a_month_is_refused(monkeypatch):
    graph(monkeypatch)
    c = TestClient(app)
    for _ in range(3):
        assert start(c).status_code == 200
    r = start(c)
    assert r.status_code == 402
    assert "3 test runs" in r.json()["detail"]


def test_free_plan_covers_one_site_but_local_servers_do_not_count(monkeypatch):
    graph(monkeypatch)
    c = TestClient(app)
    assert start(c, "https://mine.example").status_code == 200
    assert start(c, "http://localhost:5173").status_code == 200
    r = start(c, "https://other.example")
    assert r.status_code == 403
    assert "1 site" in r.json()["detail"]


def test_free_capacity_guard_stops_free_runs_only(monkeypatch, passes):
    graph(monkeypatch)
    monkeypatch.setattr(plans, "FREE_RUNS_PER_DAY", 0)
    r = start(TestClient(app))
    assert r.status_code == 429
    grant(passes, "pro")
    assert start(TestClient(app)).status_code == 200


def test_pro_pass_unlocks_logged_in_pages_personas_and_30_steps(monkeypatch, passes, fake_db):
    g = graph(monkeypatch)
    grant(passes, "pro")
    r = start(TestClient(app), logged_in=True, persona="skeptic", max_steps=30)
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    assert fake_db[run_id]["tier"] == "paid"
    assert g.get_state({"configurable": {"thread_id": run_id}}).values["max_steps"] == 30


def test_pass_counts_only_runs_since_it_started(monkeypatch, passes):
    graph(monkeypatch)
    c = TestClient(app)
    for _ in range(3):
        start(c)
    grant(passes, "launch", runs=1)  # starts now: earlier free runs do not use the pass
    assert start(c).status_code == 200
    assert start(c).status_code == 402


def test_expired_pass_falls_back_to_free(monkeypatch, passes):
    graph(monkeypatch)
    grant(passes, "plus", days=-1, started_days_ago=31)
    assert start(TestClient(app), logged_in=True).status_code == 403


def test_me_plan_reports_limits_and_runs_left(monkeypatch):
    graph(monkeypatch)
    c = TestClient(app)
    before = c.get("/me/plan").json()
    assert before["plan"] == "free" and before["runs_left"] == 3 and before["max_steps"] == 12
    assert before["logged_in"] is False and before["personas"] == ["first_timer"]
    start(c)
    assert c.get("/me/plan").json()["runs_left"] == 2


def test_me_plan_shows_an_active_pass(passes):
    grant(passes, "pro")
    plan = TestClient(app).get("/me/plan").json()
    assert plan["plan"] == "pro" and plan["runs_left"] == 40 and plan["logged_in"] is True and plan["expires_at"]
