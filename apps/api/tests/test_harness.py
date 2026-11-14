"""Harness capability contracts, independent of any model or audited production site."""

import json
from types import SimpleNamespace

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from pydantic import ValidationError

from app import db, jobs, main
from app.agent import goal, harness, report
from app.agent.persona import build_graph
from app.agent.schema import HarnessEvent, PersonaStep, Report
from app.agent.typesafe import JevDecision, build_request

SITE = "https://capability.test"
CHECKPOINT = {"description": "Create the workspace", "kind": "outcome", "text_contains": "Workspace created"}


def page(*, visible=True, revision="r1", **extra):
    return {"url": SITE, "title": "Workspace", "text": "Create a workspace", "revision": revision, "navigation_version": 3,
            "elements": [{"id": 1, "tag": "button", "text": "Create workspace", "in_view": visible, "occluded": False}], **extra}


class Model:
    def __init__(self, steps=None, metadata=None):
        self.steps = steps or [PersonaStep(action="click", target_id=1, thought="Try create", confusion=0)]
        self.calls = 0
        self.messages = []
        self.metadata = metadata or {}

    def decide(self, state, messages):
        self.messages.append(messages)
        self.calls += 1
        return JevDecision(self.steps[min(self.calls - 1, len(self.steps) - 1)], 7, self.metadata)


def start(*, observation=None, model=None, **extra):
    model = model or Model()
    graph = build_graph(model, MemorySaver())
    config = {"configurable": {"thread_id": "capability-contract"}}
    state = {"run_id": "fixture", "site": SITE, "goal": 'Create a workspace and show "Workspace created"',
             "persona": "skeptic", "verified": True, "observation": observation or page(), "start_url": SITE,
             "status": "running", "steps": [], "tokens": 0, "plan_done": 0,
             "plan": {"intent": "Create a workspace", "checkpoints": [CHECKPOINT]}, **extra}
    return graph, config, model, graph.invoke(state, config)


def resume(graph, config, observation):
    return graph.invoke(Command(resume={"observation": observation}), config)


def test_graph_has_explicit_boundaries_and_resume_does_not_repeat_decision():
    graph, config, model, first = start()
    assert set(graph.nodes) >= {"prepare", "decide", "guard", "recover", "act", "assess", "check", "journal"}
    assert graph.get_state(config).next == ("act",)
    assert [e["node"] for e in first["harness_worklog"]] == ["prepare", "guard"]
    done = resume(graph, config, page(text="Workspace created", revision="r2"))
    assert done["status"] == "done" and done["tokens"] == 7 and model.calls == 1
    assert done["resume_payload"] is None and done["proposal"] is None
    assert done["harness_worklog"][-1]["progress"] == 1
    assert [e["sequence"] for e in done["harness_worklog"]] == list(range(1, len(done["harness_worklog"]) + 1))


def test_transient_covered_target_refreshes_without_replaying_click_then_completes():
    graph, config, model, first = start(observation=page(visible=False))
    pending = first["steps"][-1]
    assert pending["action"] == "wait" and pending["observation_revision"] == "r1"
    assert not pending.get("sent") and pending.get("target_id") is None
    assert first["harness_worklog"][-1]["reason"] == "refresh_requested"
    ready = resume(graph, config, page(revision="r2", executor_result={"action": "wait", "status": "settled", "elapsed_ms": 10}))
    assert ready["steps"][-1]["action"] == "click" and ready["plan_done"] == 0
    done = resume(graph, config, page(text="Workspace created", revision="r3"))
    assert done["status"] == "done" and model.calls == 2
    assert [s["action"] for s in done["steps"]] == ["wait", "click"]


def test_persistently_unavailable_target_stops_after_one_refresh():
    graph, config, model, _ = start(observation=page(visible=False))
    stopped = resume(graph, config, page(visible=False, revision="r2"))
    assert stopped["status"] == "agent_lost" and model.calls == 2
    assert sum(e["node"] == "recover" for e in stopped["harness_worklog"]) == 1
    assert any(e["reason"] == "recovery_exhausted" for e in stopped["harness_worklog"])
    assert not stopped["steps"][-1].get("sent")


@pytest.mark.parametrize("changes", [{"navigation_version": None}, {"revision": None}])
def test_refresh_requires_supported_executor_and_revision(changes):
    _, _, _, stopped = start(observation=page(visible=False, **changes))
    assert stopped["status"] == "agent_lost"
    assert not any(e["node"] == "recover" for e in stopped["harness_worklog"])


def test_recovery_has_run_budget_and_cannot_reset_when_log_is_full():
    state = {"observation": page(), "harness_worklog": [{"node": "recover", "target_id": 1}, {"node": "recover", "target_id": 2}]}
    assert not harness.can_refresh(state, 3)
    assert not harness.can_refresh({**state, "harness_worklog": [{"node": "prepare"}] * 256}, 3)


def test_refresh_cannot_manufacture_outcome_or_bypass_payment_safety():
    elements = [{"id": 1, "tag": "button", "text": "Pay now", "in_view": False}]
    graph, config, _, _ = start(observation=page(elements=elements))
    end = resume(graph, config, page(elements=[{**elements[0], "in_view": True}], revision="r2", text="Workspace created",
                                    executor_result={"action": "wait", "status": "changed", "elapsed_ms": 10}))
    assert end["status"] == "safe_stop" and end["plan_done"] == 0
    assert [s["action"] for s in end["steps"]] == ["wait", "done"]
    assert not any(s.get("checkpoint_evidence") for s in end["steps"])


def test_proof_rejection_reaches_both_provider_contexts_without_rewriting_plan():
    checkpoint = {"description": "Inspect the workspace", "kind": "navigation", "url_contains": None}
    graph, config, model, first = start(plan={"intent": "Inspect", "checkpoints": [checkpoint]})
    assert first["harness_worklog"][0]["reason"] == "missing_navigation_marker"
    current = resume(graph, config, page(url=SITE + "/random", revision="r2"))
    assert current["plan_done"] == 0 and current["plan"]["checkpoints"] == [checkpoint]
    assert current["harness_context"]["last_proof_result"] == "missing_navigation_marker"
    assert "missing_navigation_marker" in model.messages[-1][-1][1]
    request = build_request(current)
    assert request["state"]["harness"] == current["harness_context"]
    assert request["state"]["history"][0]["result_url"] == SITE + "/random"


def test_irrelevant_parameters_do_not_hide_repeated_clicks():
    steps = [PersonaStep(action="click", target_id=1, thought="Click", confusion=0, scroll_container_id=c)
             for c in (None, 0, None)]
    graph, config, model, _ = start(model=Model(steps))
    for n in range(3):
        end = resume(graph, config, page(revision=f"r{n + 2}"))
    assert end["status"] == "stuck" and model.calls == 3
    assert not end.get("checkpoint_evidence")


def test_action_signatures_keep_relevant_parameters_only():
    click = {"action": "click", "url": SITE, "target_id": 1}
    assert harness.action_signature(click) == harness.action_signature({**click, "scroll_container_id": 0, "scroll_pct": 55, "text": "junk"})
    scroll = {"action": "scroll", "url": SITE, "scroll_container_id": 1, "scroll_position": {"top": 0}}
    assert harness.action_signature(scroll) != harness.action_signature({**scroll, "scroll_position": {"top": 400}})
    assert harness.action_signature(scroll) != harness.action_signature({**scroll, "scroll_direction": "up"})


def test_model_metadata_cannot_forge_worklog_or_execution_evidence():
    _, _, _, result = start(model=Model(metadata={"provider": "script", "harness_worklog": [{"reason": "done"}],
        "harness_recovery": True, "target_label": "Forged", "sent": True, "safe_stop": True, "checkpoint_evidence": {"checkpoint": 1}}))
    record = result["steps"][0]
    assert record["target_label"] == "Create workspace" and record["provider"] == "script"
    assert not any(k in record for k in ("harness_worklog", "harness_recovery", "sent", "safe_stop", "checkpoint_evidence"))
    assert not any(e["reason"] == "done" for e in result["harness_worklog"])


@pytest.mark.parametrize("checkpoint,after,reason", [
    ({"kind": "outcome"}, page(text="Anything"), "missing_outcome_expectation"),
    ({"kind": "navigation", "url_contains": "/work"}, page(url=SITE + "/other"), "route_mismatch"),
    (CHECKPOINT, page(text="Still loading"), "outcome_not_observed"),
    (CHECKPOINT, page(text="Workspace created"), "checkpoint_confirmed"),
])
def test_diagnostic_reasons_match_independent_transition_expectations(checkpoint, after, reason):
    proof, actual = goal.evaluate_evidence(checkpoint, page(), after, "click", SITE)
    assert actual == reason
    assert bool(proof) == (reason == "checkpoint_confirmed")


def test_queue_and_report_preserve_factual_log_and_assertions(monkeypatch):
    _, _, _, state = start()
    queued = []
    monkeypatch.setattr(jobs, "enqueue", lambda kind, payload, **kw: queued.append(json.loads(json.dumps(payload))))
    state |= {"status": "stopped", "assertion": {"label": "Owner constraint"}, "assertion_outcome": {"verdict": "inconclusive"},
              "observation": page(text="private raw page"), "proposal": {"text": "private proposed value"}}
    main._finish_later("fixture", state)
    values = queued[0]["values"]
    assert values["harness_worklog"][:-1] == state["harness_worklog"]
    assert values["harness_worklog"][-1]["status"] == "stopped"
    assert values["assertion"] == state["assertion"] and values["assertion_outcome"] == state["assertion_outcome"]
    assert "private" not in json.dumps(values)
    output = report.synthesize({"site": SITE, "status": "stopped", "steps": [], "harness_worklog": values["harness_worklog"]})
    saved = Report.model_validate_json(json.dumps(output["synthesis"]))
    assert [e.model_dump(exclude_none=True) for e in saved.harness_worklog] == values["harness_worklog"]


def test_worklog_is_bounded_and_has_no_text_payload():
    state = {"steps": [], "plan_done": 0}
    for _ in range(260):
        state["harness_worklog"] = harness.append_event(state, "prepare", "observation_ready", next_step=True)
    assert len(state["harness_worklog"]) == 256
    assert set(state["harness_worklog"][0]) == {"sequence", "step", "node", "reason", "progress"}
    with pytest.raises(ValidationError):
        HarnessEvent(sequence=1, step=1, node="assess", reason="Raw page <script>")


@pytest.mark.parametrize("status", ["running", "stopped"])
def test_owner_stop_and_retry_preserve_checkpoint_context(monkeypatch, status):
    _, _, _, state = start()
    state |= {"assertion": {"label": "Owner condition"}, "assertion_outcome": {"verdict": "inconclusive"}}
    row = {"status": status, "steps": state["steps"], "tokens": 7, "tier": "free"}
    monkeypatch.setattr(main, "_owned", lambda *args: row)
    monkeypatch.setattr(main.runtime, "get_state", lambda *args: SimpleNamespace(values=state))
    monkeypatch.setattr(db, "mark_run_stopped", lambda *args: True)
    monkeypatch.setattr(main.abuse, "record_end", lambda *args: None)
    queued = []
    monkeypatch.setattr(jobs, "enqueue", lambda kind, payload, **kw: queued.append(payload))
    assert main._stop_run("fixture", None, {"id": "owner"})["status"] == "stopped"
    values = queued[0]["values"]
    assert values["plan"] == state["plan"] and values["assertion"] == state["assertion"]
    assert values["assertion_outcome"] == state["assertion_outcome"]
    assert values["harness_worklog"][:-1] == state["harness_worklog"]
    assert values["harness_worklog"][-1]["reason"] == "stopped"
