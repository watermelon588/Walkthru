"""R-S2: current targets, bounded contextual labels and truthful rejected execution."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import main
from app.agent import report, runtime
from app.agent.persona import render_observation
from app.agent.schema import Observation, PersonaStep
from app.agent.typesafe import JevDecision, build_request
from tests.test_persona import page, start, use


def current(revision="snapshot-1"):
    return page("https://fixture.test/", [
        {"id": 1, "tag": "a", "text": "Edit", "region": "Projects", "row": "Alpha", "in_view": True, "occluded": False},
        {"id": 2, "tag": "a", "text": "Edit", "region": "Projects", "row": "Beta", "in_view": True, "occluded": False},
    ]) | {"revision": revision, "elements_truncated": True, "candidate_limit_reached": True, "omitted_elements": 17}


def test_context_reaches_both_decision_paths_without_private_labels():
    raw = current()
    raw["elements"][1]["row"] = "Beta private@example.com +91 9876543210 sk_test_abcdefghijklmnop"
    observation = Observation.model_validate(raw).model_dump()
    rendered = render_observation(observation)
    payload = build_request({"observation": observation, "goal": "Edit Beta", "persona": "skeptic"})
    assert "Alpha" in rendered and "Beta" in rendered and "Projects" in rendered
    assert "17" in rendered and "limit" in rendered.lower()
    assert payload["state"]["page"]["revision"] == "snapshot-1"
    assert "Beta" in payload["questions"]["click_target"]["criteria"]["e2"]
    assert "Alpha" in payload["questions"]["click_target"]["criteria"]["e1"]
    for private in ("private@example.com", "9876543210", "abcdefghijklmnop"):
        assert private not in rendered and private not in str(payload)


@pytest.mark.parametrize("changes", [
    {"revision": "x" * 65}, {"revision": "invalid revision"}, {"omitted_elements": -1},
    {"elements": [{"id": 1, "tag": "a", "region": "r" * 161}]},
    {"elements": [{"id": 1, "tag": "a", "row": "r" * 161}]},
])
def test_context_contract_refuses_unbounded_or_invalid_data(changes):
    with pytest.raises(ValidationError):
        Observation.model_validate(current() | changes)


def test_aggregate_context_is_capped_in_order_with_explicit_omission():
    label = "Project context row " * 7
    observation = Observation.model_validate(current() | {"elements": [{"id": i, "tag": "a", "row": label} for i in range(50)]})
    assert sum(len(e.row or "") + len(e.region or "") for e in observation.elements) == 6000
    assert observation.context_truncated is True
    assert observation.elements[0].row == label and observation.elements[-1].row is None


def test_context_masking_stays_bounded_and_preserves_dates_and_network_context():
    raw = current()
    raw["elements"][0]["row"] = "a@b.co " * 22
    raw["elements"][1]["row"] = "2026-10-04 192.168.100.100 https://admin:shortpass@example.test/path?session=shortsecret#private"
    observation = Observation.model_validate(raw)
    assert len(observation.elements[0].row) <= 160
    assert "2026-10-04" in observation.elements[1].row and "192.168.100.100" in observation.elements[1].row
    assert not any(value in observation.elements[1].row for value in ("shortpass", "shortsecret", "private"))


@pytest.mark.parametrize("revision", [None, "snapshot-1"])
@pytest.mark.parametrize("action", ["click", "scroll", "done"])
def test_final_action_revision_is_deterministic_and_legacy_optional(monkeypatch, revision, action):
    use([PersonaStep(thought="Use Beta", action=action, target_id=2 if action == "click" else None, confusion=0)], monkeypatch)
    result = start(TestClient(main.app), current(revision))
    record = result["action"] if action != "done" else result["steps"][-1]
    assert record.get("observation_revision") == (revision if action == "click" else None)


def test_jev_metadata_cannot_forge_dispatched_revision(monkeypatch):
    from langgraph.checkpoint.memory import MemorySaver

    from app.agent.persona import build_graph

    class Decision:
        def decide(self, state, messages):
            return JevDecision(PersonaStep(thought="Edit Beta", action="click", target_id=2, confusion=0), 0,
                               {"provider": "jev", "observation_revision": "forged"})

    graph = build_graph(Decision(), MemorySaver())
    monkeypatch.setattr(runtime, "graph", lambda tier: graph)
    assert start(TestClient(main.app), current())["action"]["observation_revision"] == "snapshot-1"


@pytest.mark.parametrize("prefix", ["human check; ", "x" * 250])
def test_stale_target_stops_without_causal_error_or_completion_credit(monkeypatch, prefix):
    fake = use([PersonaStep(thought="Edit Beta", action="click", target_id=2, confusion=0)], monkeypatch)
    client = TestClient(main.app)
    begun = start(client, current())
    after = current("snapshot-2") | {"note": prefix + "stale target: changed before execution", "errors": ["Unrelated existing error"],
                                     "notices": ["Account created"], "url": "https://fixture.test/signup"}
    result = client.post(f"/runs/{begun['run_id']}/observe", json={"observation": after}).json()
    assert result["status"] == "agent_lost" and fake.calls == 1
    step = result["steps"][-1]
    assert step["interrupted"] and step["code"] == "agent_lost"
    assert not any(step.get(k) for k in ("errors_after", "notices_after", "no_change", "result_url"))
    assert report.problem_steps(result["steps"], result["status"]) == set()


@pytest.mark.parametrize("flag", ["occluded", "in_view"])
def test_unusable_observed_target_is_not_dispatched(monkeypatch, flag):
    use([PersonaStep(thought="Edit Beta", action="click", target_id=2, confusion=0)], monkeypatch)
    observation = current()
    observation["elements"][1][flag] = flag == "occluded"
    result = start(TestClient(main.app), observation)
    assert result["status"] == "agent_lost" and result["steps"][-1]["action"] == "give_up"
    assert result["steps"][-1].get("observation_revision") is None


def test_stale_feedback_never_establishes_a_site_problem_even_with_legacy_errors():
    steps = [{"action": "click", "errors_after": ["Real earlier failure"]},
             {"action": "click", "note_after": "stale target: refresh needed", "errors_after": ["Unrelated error"], "no_change": True}]
    assert report.problem_steps(steps, "agent_lost") == {1}


def test_type_default_retains_revision_but_safety_replacement_clears_it(monkeypatch):
    from langgraph.checkpoint.memory import MemorySaver

    from app.agent.persona import _enforce, build_graph
    from tests.test_persona import FakeModel

    observation = current()
    observation["elements"][1].update(tag="input", type="email", text="Email")
    chosen, _ = _enforce(PersonaStep(thought="Enter email", action="type", target_id=2, confusion=0),
                         {"observation": observation, "verified": True, "run_id": "fixture"})
    assert chosen.text == "walkthru.tester+fixture@example.com"
    graph = build_graph(FakeModel([PersonaStep(thought="Enter email", action="type", target_id=2, confusion=0)]), MemorySaver())
    dispatched = graph.invoke({"run_id": "fixture", "goal": "Enter email", "persona": "first_timer", "observation": observation,
                               "verified": True, "steps": []}, {"configurable": {"thread_id": "default-text"}})["__interrupt__"][0].value
    assert dispatched["observation_revision"] == "snapshot-1" and dispatched["text"] == chosen.text
    use([PersonaStep(thought="Enter email", action="type", target_id=2, confusion=0)], monkeypatch)
    result = start(TestClient(main.app), observation)
    assert result["status"] == "safe_stop" and result["steps"][-1]["observation_revision"] is None


def test_context_or_revision_change_alone_does_not_confirm_the_goal(monkeypatch):
    fake = use([PersonaStep(thought="Edit Beta", action="click", target_id=2, confusion=0),
                PersonaStep(thought="It worked", action="done", confusion=0),
                PersonaStep(thought="I cannot confirm it", action="give_up", confusion=0)], monkeypatch)
    client = TestClient(main.app)
    begun = start(client, current())
    after = current("snapshot-2")
    after["elements"][1]["region"] = "Expanded projects"
    result = client.post(f"/runs/{begun['run_id']}/observe", json={"observation": after}).json()
    assert result["status"] == "gave_up" and fake.calls == 3


def test_jev_criteria_excludes_unavailable_controls():
    observation = current()
    observation["elements"][1]["occluded"] = True
    payload = build_request({"observation": observation, "goal": "Edit Beta", "persona": "skeptic"})
    assert "e1" in payload["questions"]["click_target"]["criteria"]
    assert "e2" not in payload["questions"]["click_target"]["criteria"]


def test_stale_rejection_preserves_a_real_failure_from_an_earlier_action(monkeypatch):
    fake = use([PersonaStep(thought="Edit Alpha", action="click", target_id=1, confusion=0),
                PersonaStep(thought="Try Beta", action="click", target_id=2, confusion=0)], monkeypatch)
    client = TestClient(main.app)
    begun = start(client, current())
    first_outcome = current("snapshot-2") | {"errors": ["Server failed to load Alpha"]}
    pending = client.post(f"/runs/{begun['run_id']}/observe", json={"observation": first_outcome}).json()
    assert pending["action"]["observation_revision"] == "snapshot-2"
    stale = current("snapshot-3") | {"note": "stale target: Beta row was replaced", "errors": ["Unrelated existing error"]}
    result = client.post(f"/runs/{begun['run_id']}/observe", json={"observation": stale}).json()
    assert result["status"] == "agent_lost" and fake.calls == 2
    assert result["steps"][0]["errors_after"] == ["Server failed to load Alpha"]
    assert "errors_after" not in result["steps"][1]
    assert report.problem_steps(result["steps"], result["status"]) == {1}
