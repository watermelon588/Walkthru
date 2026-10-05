"""R-S3 bounded navigation: observable motion is not completion or a website defect."""

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from pydantic import ValidationError

from app.agent.persona import _confirmed, build_graph, render_history, render_observation
from app.agent.report import problem_steps
from app.agent.schema import ExecutorResult, Observation, PersonaStep
from app.agent.typesafe import JevDecision, JevFallback, build_request
from tests.test_typesafe import client_with, response, state


def pane(id=1, **extra):
    return {"id": id, "label": "Projects", "top": 0, "left": 0, "scroll_height": 2000, "client_height": 400,
            "scroll_width": 400, "client_width": 400, "in_view": True, "occluded": False,
            "can_down": True, "can_up": False, "can_left": False, "can_right": False, **extra}


def page(**extra):
    return {"url": "https://fixture.test/", "title": "Projects", "text": "Projects", "elements": [], "revision": "current",
            "navigation_version": 3, "scroll_containers": [pane(0), pane()], **extra}


def outcome(action="scroll", status="moved", container_id=1, top=300, **extra):
    return {"action": action, "status": status, "container_id": container_id, "elapsed_ms": 200,
            "before": {"top": top - 300, "left": 0}, "after": {"top": top, "left": 0}, **extra}


class Script:
    def __init__(self, choices):
        self.choices, self.calls = list(choices), 0

    def invoke(self, messages):
        self.calls += 1
        return self.choices.pop(0) if len(self.choices) > 1 else self.choices[0]


def session(choices, observation=None, **extra):
    model = Script(choices)
    graph = build_graph(model, MemorySaver())
    config = {"configurable": {"thread_id": "navigation"}}
    started = graph.invoke({"run_id": "fixture", "goal": "inspect the project", "persona": "skeptic", "verified": True,
                            "observation": observation or page(), "steps": [], "start_url": "https://fixture.test/",
                            "plan": {"intent": "inspect", "checkpoints": [{"description": "inspect", "url_contains": None}]}, **extra}, config)
    return graph, config, model, started


def step(action="scroll", **extra):
    return PersonaStep(thought="Inspect the project", action=action, confusion=0, **extra)


@pytest.mark.parametrize("changes", [
    {"navigation_version": 4}, {"scroll_containers": [pane()] * 13}, {"scroll_containers": [pane(), pane()]},
    {"scroll_containers": [pane(label="x" * 161)]}, {"scroll_containers": [pane(top=float("inf"))]},
    {"scroll_containers": [pane(left=float("nan"))]}, {"scroll_containers": [pane(scroll_height=-1)]},
    {"scroll_containers": [pane(client_width=10_000_001)]},
])
def test_observation_bounds(changes):
    with pytest.raises(ValidationError):
        Observation.model_validate(page(**changes))


@pytest.mark.parametrize("changes", [{"scroll_distance": 0}, {"scroll_distance": 1001}, {"scroll_direction": "diagonal"},
                                     {"scroll_container_id": -1}, {"wait_timeout_ms": 99}, {"wait_timeout_ms": 5001},
                                     {"wait_condition": "css_selector"}])
def test_action_bounds(changes):
    with pytest.raises(ValidationError):
        step(**changes)


@pytest.mark.parametrize("changes", [{"status": "timeout"}, {"elapsed_ms": 600_001}, {"before": {"top": float("nan"), "left": 0}},
                                     {"action": "wait", "status": "settled"}])
def test_executor_result_bounds_and_action_semantics(changes):
    with pytest.raises(ValidationError):
        ExecutorResult.model_validate(outcome(**changes))


def test_measured_wait_overrun_is_preserved_while_requested_deadline_stays_bounded():
    result = ExecutorResult.model_validate(outcome("wait", "timeout", None, elapsed_ms=6500))
    assert result.elapsed_ms == 6500
    with pytest.raises(ValidationError):
        step("wait", wait_timeout_ms=6500)


def test_signed_rtl_reverse_positions_and_masked_shared_context():
    obs = Observation.model_validate(page(scroll_containers=[pane(left=-300, top=-250, label="Owner private@example.com")],
                                         elements=[{"id": i, "tag": "a", "row": "Project row " * 13} for i in range(40)]))
    assert obs.scroll_containers[0].left == -300 and obs.scroll_containers[0].top == -250
    assert sum(len(e.row or "") for e in obs.elements) + len(obs.scroll_containers[0].label) == 6000
    assert obs.context_truncated and "private@example.com" not in render_observation(obs.model_dump())


@pytest.mark.parametrize("choice,revision", [(step(), None), (step(scroll_container_id=0), "current"),
                                             (step(scroll_container_id=1), "current"), (step("wait"), "current")])
def test_actual_action_revision_and_legacy_window(choice, revision):
    _, _, _, begun = session([choice])
    assert begun["__interrupt__"][0].value["observation_revision"] == revision


@pytest.mark.parametrize("choice,observation", [(step("wait"), page(navigation_version=None)),
    (step(scroll_container_id=1), page(revision=None)), (step(scroll_container_id=9), page()),
    (step(scroll_container_id=1), page(scroll_containers=[pane(occluded=True)])),
    (step(scroll_direction="up"), page(navigation_version=None)), (step(scroll_distance=100), page(navigation_version=None))])
def test_incompatible_or_missing_navigation_stops_without_dispatch(choice, observation):
    _, _, model, final = session([choice], observation)
    assert final["status"] == "agent_lost" and model.calls == 1
    assert "__interrupt__" not in final and final["steps"][-1]["observation_revision"] is None


def test_provider_metadata_cannot_replace_bounded_navigation_action():
    class Spoof:
        def decide(self, state, messages):
            return JevDecision(step(scroll_container_id=1), 0, {"action": "click", "scroll_container_id": 9,
                                "scroll_distance": 99999, "observation_revision": "forged", "executor_result": {"status": "aborted"}})
    graph = build_graph(Spoof(), MemorySaver())
    result = graph.invoke({"run_id": "fixture", "goal": "inspect", "persona": "skeptic", "observation": page(), "steps": []},
                          {"configurable": {"thread_id": "spoof"}})["__interrupt__"][0].value
    assert (result["action"], result["scroll_container_id"], result["scroll_distance"], result["observation_revision"]) == ("scroll", 1, None, "current")
    assert "executor_result" not in result


def test_modern_implicit_window_direction_is_bound_to_observed_window():
    _, _, _, begun = session([step(scroll_direction="up")])
    actual = begun["__interrupt__"][0].value
    assert actual["scroll_container_id"] == 0 and actual["observation_revision"] == "current" and actual["scroll_direction"] == "up"


@pytest.mark.parametrize("action,status,container", [("scroll", "no_progress", 1), ("wait", "timeout", None), ("wait", "settled", None)])
def test_repeated_navigation_exhaustion_stops_without_site_blame(action, status, container):
    graph, config, model, _ = session([step(action, scroll_container_id=container)])
    result = None
    for _ in range(3):
        result = graph.invoke(Command(resume={"observation": page(executor_result=outcome(action, status, container))}), config)
    assert result["status"] == "agent_lost" and model.calls == 3
    assert problem_steps(result["steps"], result["status"]) == set()
    assert status in render_history(result["steps"])


def test_nested_and_infinite_scroll_progress_continues_until_step_budget():
    graph, config, _, _ = session([step(scroll_container_id=1, progress=1)], max_steps=4)
    for i in range(4):
        # Window and public text stay unchanged; the chosen pane really moved.
        result = graph.invoke(Command(resume={"observation": page(scroll_containers=[pane(0), pane(top=300 * (i + 1), scroll_height=3000 + i * 100)],
            executor_result=outcome(top=300 * (i + 1)))}), config)
        if i < 3:
            assert result["status"] == "running" and result["plan_done"] == 0
    assert result["status"] == "budget" and len(result["steps"]) == 4


def test_scroll_then_done_is_questioned_and_wait_preserves_real_click_proof():
    graph, config, model, _ = session([step(scroll_container_id=1), step("done"), step("done")])
    result = graph.invoke(Command(resume={"observation": page(executor_result=outcome())}), config)
    assert result["status"] == "agent_lost" and model.calls == 3
    assert not _confirmed({"steps": [{"action": "wait", "notices_after": ["Welcome"]}]})
    assert not _confirmed({"steps": [{"action": "click", "url": "a", "result_url": "a"},
                                {"action": "wait", "url": "a", "result_url": "b", "notices_after": ["Welcome"]}]})


def test_aborted_wait_stops_without_another_decision_or_mutation():
    graph, config, model, _ = session([step("wait")])
    result = graph.invoke(Command(resume={"observation": page(executor_result=outcome("wait", "aborted", None))}), config)
    assert result["status"] == "agent_lost" and model.calls == 1 and len(result["steps"]) == 1


def test_no_scroll_progress_does_not_make_existing_errors_causal_but_prior_click_failure_survives():
    steps = [{"action": "click", "errors_after": ["Actual earlier failure"]},
             {"action": "scroll", "errors_after": ["Existing unrelated error"], "executor_result": outcome(status="no_progress")},
             {"action": "wait", "errors_after": ["Existing unrelated error"], "executor_result": outcome("wait", "timeout", None)}]
    assert problem_steps(steps, "agent_lost") == {1}


@pytest.mark.parametrize("choice,result", [(step("click", target_id=1), outcome("wait", "aborted", None)),
                                          (step(scroll_container_id=1), outcome(container_id=2))])
def test_mismatched_executor_feedback_cannot_control_pending_action(choice, result):
    graph, config, _, _ = session([choice], page(elements=[{"id": 1, "tag": "a", "text": "Project"}]))
    after = graph.invoke(Command(resume={"observation": page(executor_result=result)}), config)
    assert "executor_result" not in after["steps"][0] and "executor_result" not in after["observation"] and after["status"] == "running"


def test_jev_has_observed_panes_directions_and_capped_wait_choices():
    current = state()
    current["observation"].update(page(scroll_containers=[pane(0), pane(1), pane(2, occluded=True)]))
    request = build_request(current)
    assert set(request["questions"]["scroll_target"]["criteria"]) == {"none", "c0", "c1"}
    body = response(operation="scroll")
    body["answers"].update(scroll_target={"choice": "c1", "confidence": .9}, scroll_direction={"choice": "down", "confidence": .9})
    chosen = client_with(body).decide(current).step
    assert chosen.scroll_container_id == 1 and chosen.scroll_distance is None
    body = response(operation="wait")
    body["answers"]["wait_condition"] = {"choice": "text_changed", "confidence": .9}
    chosen = client_with(body).decide(current).step
    assert chosen.wait_condition == "text_changed" and chosen.wait_timeout_ms == 1000


@pytest.mark.parametrize("aux", [None, {"choice": "c999", "confidence": .9}, {"choice": "c1", "confidence": .1},
                                 {"choice": "c1", "confidence": float("nan")}, {"choice": ["c1"], "confidence": .9}])
def test_jev_bad_navigation_choices_fall_back_instead_of_guessing(aux):
    current = state()
    current["observation"].update(page())
    body = response(operation="scroll")
    if aux:
        body["answers"]["scroll_target"] = aux
    body["answers"]["scroll_direction"] = {"choice": "down", "confidence": .9}
    with pytest.raises(JevFallback):
        client_with(body).decide(current)
