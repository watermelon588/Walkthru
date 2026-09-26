"""Items 5 of docs/agent-safety-plan.md: honest failure (agent_lost), bot walls, and one table of stop reasons."""

from fastapi.testclient import TestClient

from app.agent import policy
from app.agent.report import grounded_ux, problem_steps
from app.agent.schema import Finding, PersonaStep
from app.main import app
from tests.test_persona import observe, page, start, use


def step(action, target=None):
    return PersonaStep(thought="next", action=action, target_id=target, confusion=1)


HOME = page("https://fixture.test/", [{"id": 1, "tag": "a", "text": "Pricing"}])


def test_every_stop_code_has_a_panel_message_and_a_report_line():
    for code, (panel, report) in policy.STOP_REASONS.items():
        assert panel and report, code
        assert "—" not in panel + report  # no em dashes in user-facing copy
    assert policy.stop_reason("bot_wall")["message"].startswith("The site asked for a human check")


def test_a_bot_wall_stops_the_run_and_says_it_is_not_a_usability_problem(monkeypatch):
    use([step("click", 1), step("click", 1)], monkeypatch)
    c = TestClient(app)
    r = start(c, HOME)
    wall = page("https://fixture.test/pricing", [], note="bot wall detected")
    done = observe(c, r["run_id"], wall).json()
    assert done["status"] == "bot_wall" and done["code"] == "bot_wall" and "not a usability problem" in done["report"]


def test_a_captcha_still_stops_as_captcha(monkeypatch):
    use([step("click", 1), step("click", 1)], monkeypatch)
    c = TestClient(app)
    r = start(c, HOME)
    done = observe(c, r["run_id"], page("https://fixture.test/pricing", [], note="captcha detected")).json()
    assert done["status"] == "captcha" and done["code"] == "captcha"


def test_giving_up_after_picking_a_missing_element_is_walkthrus_limit_not_the_sites(monkeypatch):
    use([step("click", 9), step("give_up")], monkeypatch)  # #9 was never on the page
    c = TestClient(app)
    r = start(c, HOME)
    assert "does not exist" in r["action"]["thought"]
    done = observe(c, r["run_id"], HOME).json()
    assert done["status"] == "agent_lost" and done["code"] == "agent_lost" and "may not affect people" in done["report"]


def test_an_ordinary_give_up_stays_gave_up(monkeypatch):
    use([step("click", 1), step("give_up")], monkeypatch)
    c = TestClient(app)
    r = start(c, HOME)
    done = observe(c, r["run_id"], page("https://fixture.test/pricing", [{"id": 1, "tag": "a", "text": "Pricing"}])).json()
    assert done["status"] == "gave_up" and "code" not in done


def test_a_visitor_mode_stop_carries_its_code_and_message(monkeypatch):
    use([PersonaStep(thought="sign up", action="type", target_id=1, text="a@b.c", confusion=0)], monkeypatch)
    r = start(TestClient(app), page("https://fixture.test/signup", [{"id": 1, "tag": "input", "type": "email", "text": "Email"}]))
    assert r["status"] == "safe_stop" and r["code"] == "visitor_mode_limit" and "Verify this domain" in r["message"]


def test_walkthrus_own_misses_never_become_ux_evidence():
    steps = [
        {"action": "click", "thought": "open menu (element #9 does not exist)", "confusion": 2, "url": "u"},
        {"action": "click", "thought": "try", "confusion": 0, "url": "u", "note_after": "element #4 not found"},
        {"action": "click", "thought": "dead button", "confusion": 0, "url": "u", "no_change": True},
    ]
    assert problem_steps(steps) == {3}  # only the dead button, which a person would also hit
    bot = Finding(kind="ux", severity="high", title="Site blocks users with a bot check", detail="d", fix="f", evidence="step 3")
    assert grounded_ux([bot], [], steps) == []
