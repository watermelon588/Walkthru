"""Drives persona_session with a scripted fake model through the HTTP step API."""

from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import MemorySaver

from app.agent import runtime
from app.agent.persona import build_graph
from app.agent.safety import is_dangerous
from app.agent.schema import PersonaStep
from app.main import app


class FakeModel:
    def __init__(self, script):
        self.script = list(script)
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        return self.script.pop(0)


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


def observe(client, run_id, obs):
    return client.post(f"/runs/{run_id}/observe", json={"observation": obs})


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


def test_safe_mode_blocks_dangerous_click(monkeypatch):
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
