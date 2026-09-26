"""Drives persona_session with a scripted fake model through the HTTP step API."""

import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import MemorySaver
from psycopg import OperationalError

from app import db, main
from app.agent import runtime
from app.agent.persona import build_graph
from app.agent.safety import is_dangerous
from app.agent.schema import PersonaStep
from app.agent.typesafe import JevDecision
from app.main import app
from tests.conftest import USER


class FakeModel:
    def __init__(self, script):
        self.script = list(script)
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        return self.script.pop(0)


class FakeDecisionModel:
    def decide(self, state, messages):
        return JevDecision(
            step=PersonaStep(thought="Sign up is the next step", action="click", target_id=2, confusion=0),
            tokens=321,
            metadata={"provider": "jev", "decision_confidence": 0.91},
        )


def page(url, elements, note=None):
    return {"url": url, "title": "t", "elements": elements, "text": "hello", "note": note}


def use(script, monkeypatch):
    fake = FakeModel(script)
    g = build_graph(fake, MemorySaver())
    monkeypatch.setattr(runtime, "graph", lambda tier: g)
    return fake


def start(client, obs, **kw):
    body = {"site": "https://fixture.test", "goal": "sign up", "observation": obs} | kw
    return client.post("/runs", json=body).json()


def observe(client, run_id, obs, evidence=None):
    body = {"observation": obs}
    if evidence:
        body["evidence"] = evidence
    return client.post(f"/runs/{run_id}/observe", json=body)


def test_database_outage_returns_retryable_cors_response(monkeypatch):
    def fail_insert(*args, **kwargs):
        raise OperationalError("connection closed")

    monkeypatch.setattr(db, "insert_run", fail_insert)
    response = TestClient(app).post(
        "/runs",
        headers={"Origin": "chrome-extension://walkthru-test"},
        json={"site": "https://fixture.test", "goal": "sign up", "observation": page("https://fixture.test", [])},
    )

    assert response.status_code == 503
    assert response.headers["access-control-allow-origin"] == "chrome-extension://walkthru-test"
    assert response.json()["detail"].startswith("Walkthru could not reach its database")


@pytest.mark.parametrize("origin", ["http://localhost:5173", "http://127.0.0.1:5173"])
def test_local_web_origins_pass_cors_preflight(origin):
    response = TestClient(app).options(
        "/runs/example/share",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


def test_click_then_done(monkeypatch):
    fake = use(
        [
            PersonaStep(thought="Sign up looks right", action="click", target_id=2, confusion=0),
            PersonaStep(thought="I am in", action="done", confusion=0),
        ],
        monkeypatch,
    )
    c = TestClient(app)
    home = page("https://fixture.test/", [{"id": 1, "tag": "a", "text": "Docs"}, {"id": 2, "tag": "a", "text": "Sign up"}])
    r = start(c, home)
    assert r["status"] == "running"
    assert r["action"]["action"] == "click" and r["action"]["target_id"] == 2
    r = observe(c, r["run_id"], page("https://fixture.test/app", [])).json()
    assert r["status"] == "done" and len(r["steps"]) == 2
    assert fake.calls == 2  # interrupt/resume never re-runs the LLM
    assert observe(c, r["run_id"], page("x", [])).status_code == 409
    assert c.get(f"/runs/{r['run_id']}").json()["status"] == "done"


def test_observation_attaches_visual_evidence_to_previous_step(monkeypatch):
    use(
        [
            PersonaStep(thought="Open signup", action="click", target_id=2, confusion=1),
            PersonaStep(thought="Signup is open", action="done", confusion=0),
        ],
        monkeypatch,
    )
    client = TestClient(app)
    first = start(client, page("https://fixture.test/", [{"id": 2, "tag": "a", "text": "Sign up"}]))
    evidence = {
        "screenshot_path": f"{first['run_id']}/step-01.jpg",
        "captured_at": "2026-09-20T10:15:30Z",
        "result_url": "https://fixture.test/signup",
        "width": 1440,
        "height": 900,
        "note": "navigation completed",
    }

    result = observe(client, first["run_id"], page("https://fixture.test/signup", []), evidence).json()

    assert result["steps"][0]["evidence"] == evidence


def test_observation_attaches_browser_diagnostics_to_previous_step(monkeypatch):
    use(
        [
            PersonaStep(thought="Open signup", action="click", target_id=2, confusion=1),
            PersonaStep(thought="Signup is open", action="done", confusion=0),
        ],
        monkeypatch,
    )
    client = TestClient(app)
    first = start(client, page("https://fixture.test/", [{"id": 2, "tag": "a", "text": "Sign up"}]))
    observed = page("https://fixture.test/signup", [])
    observed["diagnostics"] = {
        "captured_at": "2026-09-21T10:15:30Z",
        "accessibility": {
            "status": "complete",
            "total": 1,
            "issues": [
                {
                    "rule": "label",
                    "severity": "high",
                    "message": "Form elements must have labels",
                    "target": "#email",
                }
            ],
        },
        "web_vitals": {"lcp_ms": 1840, "cls": 0.031, "inp_ms": 72},
    }

    result = observe(client, first["run_id"], observed).json()

    assert result["steps"][0]["diagnostics"] == observed["diagnostics"]


def test_observation_rejects_evidence_from_another_run(monkeypatch):
    use([PersonaStep(thought="Open signup", action="click", target_id=2, confusion=0)], monkeypatch)
    client = TestClient(app)
    first = start(client, page("https://fixture.test/", [{"id": 2, "tag": "a", "text": "Sign up"}]))

    response = observe(
        client,
        first["run_id"],
        page("https://fixture.test/signup", []),
        {
            "screenshot_path": "ffffffffffffffffffffffffffffffff/step-01.jpg",
            "captured_at": "2026-09-20T10:15:30Z",
            "result_url": "https://fixture.test/signup",
            "width": 1440,
            "height": 900,
        },
    )

    assert response.status_code == 422


def test_owner_can_end_running_run_and_generate_partial_report_once(monkeypatch, fake_db):
    use([PersonaStep(thought="Open signup", action="click", target_id=2, confusion=1)], monkeypatch)
    finished = []
    monkeypatch.setattr(main, "finish_run", lambda run_id, values: finished.append((run_id, values)))
    client = TestClient(app)
    first = start(client, page("https://fixture.test/", [{"id": 2, "tag": "a", "text": "Sign up"}]))

    response = client.post(f"/runs/{first['run_id']}/stop")

    assert response.status_code == 200
    assert response.json()["status"] == "stopped"
    assert response.json()["report_status"] == "generating"
    assert response.json()["steps"][-1]["interrupted"] is True
    assert fake_db[first["run_id"]]["status"] == "stopped"
    assert finished[0][1]["status"] == "stopped"

    repeated = client.post(f"/runs/{first['run_id']}/stop")
    assert repeated.status_code == 200
    assert repeated.json()["status"] == "stopped"
    assert len(finished) == 1


def test_decision_provider_metadata_is_recorded(monkeypatch):
    g = build_graph(FakeDecisionModel(), MemorySaver())
    monkeypatch.setattr(runtime, "graph", lambda tier: g)
    c = TestClient(app)
    home = page("https://fixture.test/", [{"id": 2, "tag": "a", "text": "Sign up"}])

    result = start(c, home)

    assert result["action"]["provider"] == "jev"
    assert result["action"]["decision_confidence"] == 0.91
    values = g.get_state({"configurable": {"thread_id": result["run_id"]}}).values
    assert values["tokens"] == 321


def test_step_budget(monkeypatch):
    use([PersonaStep(thought="scrolling", action="scroll", confusion=1)] * 3, monkeypatch)
    c = TestClient(app)
    r = start(c, page("https://fixture.test/", []), max_steps=2)
    r = observe(c, r["run_id"], page("https://fixture.test/", [])).json()
    assert r["status"] == "running"  # 2nd action issued
    r = observe(c, r["run_id"], page("https://fixture.test/", [])).json()
    assert r["status"] == "budget" and len(r["steps"]) == 2


def test_stuck_loop(monkeypatch):
    use([PersonaStep(thought="click it", action="click", target_id=1, confusion=2)] * 4, monkeypatch)
    c = TestClient(app)
    obs = page("https://fixture.test/", [{"id": 1, "tag": "button", "text": "Go"}])
    r = start(c, obs)
    for _ in range(3):
        r = observe(c, r["run_id"], obs).json()
    assert r["status"] == "stuck" and len(r["steps"]) == 3


def test_safe_mode_blocks_dangerous_click(monkeypatch, passes):
    passes.append({"user_id": USER, "plan": "pro", "starts_at": "2000-01-01T00:00:00+00:00", "expires_at": "2999-01-01T00:00:00+00:00", "runs_granted": 40})  # logged-in pages need a paid plan
    monkeypatch.setattr(main, "_verified", lambda site, user_id: True)  # signed-in pages need a verified domain
    use([PersonaStep(thought="delete", action="click", target_id=1, confusion=0)], monkeypatch)
    c = TestClient(app)
    settings = page("https://fixture.test/settings", [{"id": 1, "tag": "button", "text": "Delete account"}])
    r = start(c, settings, logged_in=True)
    assert r["status"] == "gave_up" and "safe mode" in r["steps"][0]["thought"]


def test_missing_element_becomes_scroll(monkeypatch):
    use([PersonaStep(thought="click 9", action="click", target_id=9, confusion=0)], monkeypatch)
    c = TestClient(app)
    r = start(c, page("https://fixture.test/", []))
    assert r["action"]["action"] == "scroll" and r["action"]["confusion"] == 2


def test_captcha_stops(monkeypatch):
    use([PersonaStep(thought="go", action="click", target_id=1, confusion=0)], monkeypatch)
    c = TestClient(app)
    r = start(c, page("https://fixture.test/", [{"id": 1, "tag": "a", "text": "Sign up"}]))
    r = observe(c, r["run_id"], page("https://fixture.test/signup", [], note="captcha detected")).json()
    assert r["status"] == "captcha"


def test_unknown_run():
    assert TestClient(app).get("/runs/nope").status_code == 404


def test_danger_words():
    assert is_dangerous("Cancel subscription") and not is_dangerous("Continue")


def test_public_page_blocks_send_button_but_allows_links(monkeypatch):
    use([PersonaStep(thought="send it", action="click", target_id=1, confusion=0)], monkeypatch)
    c = TestClient(app)
    contact = page("https://fixture.test/contact", [{"id": 1, "tag": "button", "text": "Send message"}, {"id": 2, "tag": "a", "text": "Buy now"}])
    r = start(c, contact)
    assert r["status"] == "safe_stop" and "only sends real messages on a domain the owner" in r["steps"][0]["thought"]
    assert r["steps"][0]["safe_stop"] is True
    use([PersonaStep(thought="see pricing", action="click", target_id=2, confusion=0)], monkeypatch)
    r = start(c, contact)
    assert r["status"] == "running" and r["action"]["target_id"] == 2


def test_verified_owner_may_send_but_never_destroy(monkeypatch):
    from app import main

    monkeypatch.setattr(main, "_verified", lambda site, user_id: True)
    contact = page("https://fixture.test/contact", [{"id": 1, "tag": "button", "text": "Submit contact form and send email"}, {"id": 2, "tag": "button", "text": "Delete account"}])
    c = TestClient(app)
    use([PersonaStep(thought="send it", action="click", target_id=1, confusion=0)], monkeypatch)
    r = start(c, contact)
    assert r["status"] == "running" and r["action"]["target_id"] == 1 and r["verified"] is True  # extension asks the owner first
    use([PersonaStep(thought="delete", action="click", target_id=2, confusion=0)], monkeypatch)
    r = start(c, contact)
    assert r["status"] == "safe_stop" and "never pays, deletes or cancels" in r["steps"][0]["thought"]


def test_field_state_is_shown_and_step_outcomes_are_recorded(monkeypatch):
    from app.agent.persona import render_observation
    from app.agent.report import render_steps

    shown = render_observation(page("https://fixture.test/contact", [{"id": 1, "tag": "input", "type": "text", "state": "filled", "text": "What's your name?"}]))
    assert "[1] input (text) [filled]: What's your name?" in shown

    monkeypatch.setattr(main, "_verified", lambda site, user_id: True)  # typing into forms needs a verified domain
    use([PersonaStep(thought="contact", action="click", target_id=1, confusion=0), PersonaStep(thought="type", action="type", target_id=2, text="Test Walker", confusion=0), PersonaStep(thought="ok", action="done", confusion=0),
         PersonaStep(thought="ok", action="done", confusion=0)], monkeypatch)  # asked twice: done right after typing needs proof
    c = TestClient(app)
    home = page("https://fixture.test/", [{"id": 1, "tag": "a", "text": "Contact"}])
    contact = page("https://fixture.test/contact", [{"id": 2, "tag": "input", "type": "text", "state": "empty", "text": "Name"}])
    r = start(c, home)
    r = observe(c, r["run_id"], contact).json()
    after = contact | {"errors": ["Failed to fetch"], "elements": [{"id": 2, "tag": "input", "type": "text", "state": "filled", "text": "Name"}]}
    r = observe(c, r["run_id"], after).json()
    steps = r["steps"]
    assert steps[0]["result_url"] == "https://fixture.test/contact"
    assert steps[1]["errors_after"] == ["Failed to fetch"]
    text = render_steps(steps)
    assert "ended on https://fixture.test/contact (navigation worked)" in text and "page then showed: Failed to fetch" in text


def test_stop_reason_is_recorded_for_the_report(monkeypatch, fake_db):

    fake_db["r9"] = {"id": "r9", "user_id": USER, "status": "running", "tier": "free", "tokens": 0,
                     "steps": [{"thought": "send", "action": "click", "target_id": 5, "text": None, "confusion": 0, "url": "https://fixture.test/contact"}]}
    from app import db
    monkeypatch.setattr(db, "mark_run_stopped", lambda run_id, steps, tokens=0: fake_db[run_id].update(status="stopped", steps=steps) or True)
    r = TestClient(app).post("/runs/r9/stop", json={"reason": "the last click led away from the site, to https://fixture.test/api"})
    last = r.json()["steps"][-1]
    assert last["interrupted"] is True and last["note_after"].startswith("the last click led away")
    assert TestClient(app).post("/runs/r9/stop").status_code == 200  # no body still works (web app)


def test_confirmations_reach_the_agent_and_a_second_send_is_refused(monkeypatch):
    from app import main
    from app.agent.persona import render_observation
    from app.agent.report import render_steps

    obs = page("https://fixture.test/contact", []) | {"notices": ["Thanks! Your message was sent."]}
    assert "Visible confirmations: Thanks! Your message was sent." in render_observation(obs)

    monkeypatch.setattr(main, "_verified", lambda site, user_id: True)
    send = PersonaStep(thought="send", action="click", target_id=5, confusion=0)
    use([send, send], monkeypatch)
    c = TestClient(app)
    form = page("https://fixture.test/contact", [{"id": 5, "tag": "button", "text": "Send message"}])
    r = start(c, form)
    assert r["status"] == "running"  # first send allowed (owner confirms in the panel)
    r = observe(c, r["run_id"], form | {"notices": ["Thanks! Your message was sent."]}).json()
    assert r["status"] == "done" and "never sends twice" in r["steps"][-1]["thought"]
    assert r["steps"][0]["sent"] is True
    assert "page then confirmed: Thanks! Your message was sent." in render_steps(r["steps"])


def test_type_without_text_uses_the_test_identity(monkeypatch):
    monkeypatch.setattr(main, "_verified", lambda site, user_id: True)  # typing into forms needs a verified domain
    use([PersonaStep(thought="email", action="type", target_id=4, text=None, confusion=0)], monkeypatch)
    form = page("https://fixture.test/signup", [{"id": 4, "tag": "input", "type": "email", "state": "empty", "text": "Email"}])
    r = start(TestClient(app), form)
    assert r["action"]["text"].startswith("walkthru.tester+") and r["action"]["text"].endswith("@example.com")
