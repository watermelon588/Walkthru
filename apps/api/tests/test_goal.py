"""Goal intent and loop guards: the test user follows a checklist, code ends the run when it is complete,
and Walkthru stops circles itself instead of blaming the site (a real portfolio run looped through
four "NEXT CASE" pages for 11 steps)."""

from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import MemorySaver

from app.agent import goal, runtime
from app.agent.persona import build_graph
from app.agent.report import problem_steps
from app.agent.schema import PersonaStep
from app.main import app

SITE = "https://fixture.test"


class Script:
    def __init__(self, steps):
        self.steps = list(steps)

    def invoke(self, messages):
        self.last = messages
        return self.steps.pop(0) if len(self.steps) > 1 else self.steps[0]


def use(monkeypatch, steps):
    model = Script(steps)
    g = build_graph(model, MemorySaver())
    monkeypatch.setattr(runtime, "graph", lambda tier: g)
    return model


def page(path, elements=(), **extra):
    return {"url": SITE + path, "title": "t", "elements": list(elements), "text": f"page {path}", **extra}


def planned(monkeypatch, *checkpoints, intent="check the flow", feasible=True, refusal=None):
    monkeypatch.setattr(goal, "plan", lambda site, g, obs: {
        "intent": intent, "checkpoints": [{"description": d, "url_contains": u} for d, u in checkpoints], "feasible": feasible, "refusal": refusal})


def start(c, obs, **kw):
    return c.post("/runs", json={"site": SITE, "goal": "go to skyguide then click next project", "observation": obs} | kw)


def observe(c, run_id, obs):
    return c.post(f"/runs/{run_id}/observe", json={"observation": obs}).json()


NEXT = {"id": 1, "tag": "a", "text": "NEXT CASE"}


def test_going_in_circles_is_stopped_by_walkthru(monkeypatch):
    planned(monkeypatch, ("open a case and keep reading", None))
    use(monkeypatch, [PersonaStep(thought="next case", action="click", target_id=1, confusion=0)])
    c = TestClient(app)
    r = start(c, page("/work/a", [NEXT])).json()
    cycle = ["/work/b", "/work/c", "/work/a", "/work/b", "/work/c", "/work/a"]
    for path in cycle:
        r = observe(c, r["run_id"], page(path, [NEXT]))
        if r["status"] != "running":
            break
    assert r["status"] == "looping"  # third visit to /work/a, not the 30-step budget
    assert len(r["steps"]) == 6


def test_checkpoint_url_finishes_the_run_in_code(monkeypatch):
    planned(monkeypatch, ("open the Skyguide AI project", "/work/skyguide"), ("click the next project link", None))
    use(monkeypatch, [PersonaStep(thought="open it", action="click", target_id=1, confusion=0)])
    c = TestClient(app)
    r = start(c, page("/", [{"id": 1, "tag": "a", "text": "Skyguide AI"}])).json()
    r = observe(c, r["run_id"], page("/work/skyguide-ai", [NEXT]))
    assert r["status"] == "running"  # first checkpoint reached by URL, one left


def test_model_progress_on_the_last_checkpoint_ends_the_run(monkeypatch):
    planned(monkeypatch, ("open the Skyguide AI project", None), ("click the next project link", None))
    use(monkeypatch, [
        PersonaStep(thought="open it", action="click", target_id=1, confusion=0, progress=0),
        PersonaStep(thought="now next case", action="click", target_id=1, confusion=0, progress=1),
        PersonaStep(thought="there is another next case", action="click", target_id=1, confusion=0, progress=2),
    ])
    c = TestClient(app)
    r = start(c, page("/", [{"id": 1, "tag": "a", "text": "Skyguide AI"}])).json()
    r = observe(c, r["run_id"], page("/work/skyguide-ai", [NEXT]))
    r = observe(c, r["run_id"], page("/work/neuron", [NEXT]))
    assert r["status"] == "done" and len(r["steps"]) == 3
    assert r["steps"][-1]["action"] == "done" and "every checkpoint" in r["steps"][-1]["thought"]


def test_the_persona_sees_the_checklist_and_where_each_step_led(monkeypatch):
    planned(monkeypatch, ("open the project", None), ("click next", None), intent="see if case studies link onward")
    model = use(monkeypatch, [PersonaStep(thought="open", action="click", target_id=1, confusion=0)])
    c = TestClient(app)
    r = start(c, page("/", [{"id": 1, "tag": "a", "text": "Skyguide AI"}])).json()
    observe(c, r["run_id"], page("/work/skyguide-ai", [NEXT]))
    system, human = model.last[0][1], model.last[1][1]
    assert "see if case studies link onward" in system and "1. open the project" in system
    assert "led to https://fixture.test/work/skyguide-ai" in human


def test_unsafe_goal_is_refused_before_a_run_is_used(monkeypatch, fake_db):
    planned(monkeypatch, ("delete the account", None), feasible=False, refusal="it asks to delete an account")
    use(monkeypatch, [PersonaStep(thought="x", action="scroll", confusion=0)])
    r = start(TestClient(app), page("/"))
    assert r.status_code == 422 and "delete an account" in r.json()["detail"]
    assert not fake_db


def test_planner_outage_falls_back_to_the_typed_goal(monkeypatch):
    def down(schema, messages, fast=False):
        raise RuntimeError("all models busy")

    monkeypatch.setattr(runtime, "call", down)
    plan = goal.plan(SITE, "sign up", page("/"))
    assert plan["feasible"] and plan["checkpoints"][0]["description"] == "sign up"


def test_scrolling_down_is_progress_but_scrolling_at_the_end_is_stuck(monkeypatch):
    planned(monkeypatch, ("read to the end", None))
    use(monkeypatch, [PersonaStep(thought="scroll", action="scroll", confusion=0)])
    c = TestClient(app)
    r = start(c, page("/work/a", scroll_pct=10, at_end=False)).json()
    for pct in (40, 70, 100):
        r = observe(c, r["run_id"], page("/work/a", scroll_pct=pct, at_end=pct == 100))
    assert r["status"] == "running"
    for _ in range(3):
        r = observe(c, r["run_id"], page("/work/a", scroll_pct=100, at_end=True))
        if r["status"] != "running":
            break
    assert r["status"] == "stuck"


def test_a_click_that_changes_nothing_is_recorded(monkeypatch):
    planned(monkeypatch, ("open it", None))
    use(monkeypatch, [PersonaStep(thought="click", action="click", target_id=1, confusion=0)])
    c = TestClient(app)
    same = page("/work", [{"id": 1, "tag": "a", "text": "Skyguide AI"}])
    r = start(c, same).json()
    r = observe(c, r["run_id"], same)
    assert r["status"] == "running"
    from app.main import runtime as rt
    steps = rt.get_state("free", {"configurable": {"thread_id": r["run_id"]}}).values["steps"]
    assert steps[0].get("no_change") is True


def test_owner_stop_and_walkthru_loop_are_not_site_problems():
    steps = [
        {"action": "click", "confusion": 0, "url": "a", "result_url": "b"},
        {"action": "click", "confusion": 0, "url": "b", "result_url": "c"},
        {"action": "click", "confusion": 0, "url": "c", "interrupted": True, "note_after": "the site owner pressed Stop"},
    ]
    assert problem_steps(steps, "stopped") == set()
    assert problem_steps(steps[:2], "looping") == set()
