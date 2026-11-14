"""Independent H4 contract cases: grounded navigation is distinct from business completion."""
from copy import deepcopy

import pytest

from app.agent import goal
from app.agent.report_contract import build_assessment
from app.agent.schema import HarnessEvent, Observation, PersonaStep
from tests.test_harness import Model, resume, start

SITE = "https://capability.test"


def section_page(*, visible=False, document="doc-one", route="/", key="destinations", label="Destinations", **extra):
    return {"url": SITE + route, "title": "Fixture", "text": "Explore", "document_id": document,
            "revision": "snapshot-one", "navigation_version": 3,
            "elements": [{"id": 1, "tag": "a", "text": label, "section_target": key, "destination": "/#" + key,
                          "in_view": True, "occluded": False}],
            "sections": [{"key": key, "label": label, "in_view": visible, "occluded": False}], **extra}


def plan(**checkpoint_changes):
    return {"contract_version": 2, "intent": "Open Destinations", "checkpoints": [
        {"description": "Open Destinations", "kind": "navigation", "url_contains": "/invented",
         "requires_observed_destination": True, **checkpoint_changes}]}


def bound():
    return {"kind": "section", "section_key": "destinations", "bound_document": "doc-one", "bound_route": SITE + "/"}


def test_section_revision_preserves_owner_task_and_completes_only_on_new_visible_evidence():
    graph, config, model, first = start(observation=section_page(), goal="Open Destinations", plan=plan())
    assert first["plan"]["checkpoints"][0]["kind"] == "section"
    assert first["goal"] == "Open Destinations" and first["plan_done"] == 0
    event = next(e for e in first["harness_worklog"] if e["node"] == "revise")
    assert event["before_target"] == "/invented" and event["after_target"] == "/#destinations"
    done = resume(graph, config, section_page(visible=True, route="/#destinations", revision="snapshot-two"))
    assert done["status"] == "done" and model.calls == 1
    proof = done["checkpoint_evidence"][0]
    assert proof["signal"] == "section_visibility" and proof["document_id"] == "doc-one"
    assessment = build_assessment({"status": "done", "goal": done["goal"], "steps": done["steps"],
                                   "checkpoints": done["plan"]["checkpoints"]}, [], [], {})
    assert assessment.outcome == "completed" and assessment.checkpoints[0].status == "passed"


@pytest.mark.parametrize("after,action,target,reason", [
    (section_page(visible=False, route="/#destinations"), "click", 1, "section_not_newly_visible"),
    (section_page(visible=True, document="new-document"), "click", 1, "document_changed"),
    (section_page(visible=True, route="/different"), "click", 1, "document_changed"),
    (section_page(visible=True), "click", 99, "section_action_unconfirmed"),
    (section_page(visible=True), "wait", 1, "section_action_unconfirmed"),
    (section_page(visible=True), "scroll", 1, "ineligible_action"),
    (section_page(visible=True, label="Other section"), "click", 1, "section_identity_changed"),
])
def test_section_negative_controls(after, action, target, reason):
    proof, actual = goal.evaluate_evidence(bound(), section_page(), after, action, SITE, target)
    assert proof is None and actual == reason


def test_section_coverage_unknown_occluded_preexisting_or_duplicate_never_passes():
    before, after = section_page(), section_page(visible=True)
    for changed in [dict(after, sections=[]), dict(after, sections=after["sections"] * 2),
                    dict(after, sections=[{"key": "destinations", "label": "Destinations"}]),
                    dict(after, sections=[{**after["sections"][0], "occluded": True}])]:
        assert goal.evaluate_evidence(bound(), before, changed, "click", SITE, 1)[0] is None
    assert goal.evaluate_evidence(bound(), after, after, "click", SITE, 1)[0] is None


@pytest.mark.parametrize("changes", [{"text_contains": "Required evidence"}, {"kind": "outcome"},
                                     {"requires_observed_destination": False}])
def test_revision_never_clears_stronger_or_owner_declared_expectations(changes):
    state = {"goal": "Open Destinations", "plan": plan(**changes), "observation": section_page()}
    original = deepcopy(state)
    assert goal.revision_candidate(state)[0] is None
    assert state == original


def test_ambiguous_controls_and_functional_objectives_do_not_get_reinterpreted():
    obs = section_page()
    obs["elements"] += [{**obs["elements"][0], "id": 2}]
    assert goal.revision_candidate({"goal": "Open Destinations", "plan": plan(), "observation": obs})[0] is None
    assert goal.revision_candidate({"goal": "Open Destinations and book a trip", "plan": plan(), "observation": section_page()})[0] is None


def test_unknown_functional_contract_stops_after_two_discovery_actions_without_more_model_calls():
    graph, config, model, _ = start(plan={"contract_version": 2, "intent": "Create workspace", "checkpoints": [
        {"description": "Create workspace", "kind": "outcome", "text_contains": None}]})
    current = resume(graph, config, section_page())
    assert current["status"] == "running"
    end = resume(graph, config, section_page(revision="next"))
    assert end["status"] == "agent_lost" and model.calls == 2 and end["plan_done"] == 0
    assert end["harness_context"]["stop_reason"] == "contract_unresolved"
    assert any(e["reason"] == "contract_unresolved" for e in end["harness_worklog"])


def test_unique_route_binding_is_reviewable_and_does_not_accept_an_unrelated_child_route():
    obs = section_page(elements=[{"id": 1, "tag": "a", "text": "Destinations", "destination": "/places"}])
    _graph, _config, _, first = start(observation=obs, goal="Open Destinations", plan=plan())
    assert first["plan"]["checkpoints"][0]["url_contains"] == "/places"
    checkpoint = first["plan"]["checkpoints"][0]
    assert goal.evaluate_evidence(checkpoint, obs, {**obs, "url": SITE + "/places/other"}, "click", SITE)[0] is None
    assert goal.evaluate_evidence(checkpoint, obs, {**obs, "url": SITE + "/places"}, "click", SITE)[0]


def test_unknown_target_refresh_is_bounded_and_measured_reveal_never_replays_action():
    unknown = Model([PersonaStep(action="click", target_id=99, thought="Try", confusion=0)])
    graph, config, model, first = start(observation=section_page(), model=unknown)
    assert first["steps"][-1]["action"] == "wait"
    stopped = resume(graph, config, section_page(revision="next"))
    assert stopped["status"] == "agent_lost" and model.calls == 2
    obs = section_page(elements=[{"id": 1, "tag": "a", "text": "Destinations", "in_view": False, "occluded": False,
                                 "reveal": {"container_id": 0, "direction": "down"}}], scroll_containers=[
        {"id": 0, "label": "Window", "top": 0, "left": 0, "scroll_height": 2000, "client_height": 600,
         "scroll_width": 800, "client_width": 800, "at_start": True, "at_end": False,
         "can_down": True, "can_up": False, "can_left": False, "can_right": False, "in_view": True, "occluded": False}])
    _, _, _, first = start(observation=obs)
    assert first["steps"][-1]["action"] == "scroll"
    assert first["steps"][-1]["scroll_container_id"] == 0 and first["steps"][-1]["target_id"] is None


def test_schema_bounds_and_revision_event_redaction():
    with pytest.raises(ValueError, match="unique"):
        Observation.model_validate(section_page(sections=section_page()["sections"] * 2))
    event = HarnessEvent(sequence=1, step=1, node="revise", reason="contract_revised", before_target="/reset?token=secret",
                         after_target="/places")
    assert event.before_target is None and event.after_target == "/places"


def test_section_report_rejects_wrong_source_document():
    graph, config, _, _ = start(observation=section_page(), goal="Open Destinations", plan=plan())
    done = resume(graph, config, section_page(visible=True))
    done["steps"][0]["document_id"] = "different-document"
    assessment = build_assessment({"status": "done", "steps": done["steps"], "checkpoints": done["plan"]["checkpoints"]}, [], [], {})
    assert assessment.outcome != "completed" and assessment.checkpoints[0].status == "unconfirmed"


def test_private_section_identity_is_omitted_without_rejecting_the_page():
    data = section_page(key="sk_example123", label="Public panel")
    obs = Observation.model_validate(data)
    assert obs.sections == [] and obs.sections_truncated
    assert obs.elements[0].section_target is None
    assert data["sections"][0]["key"] == "sk_example123"  # validation does not mutate caller input
    labelled = Observation.model_validate(section_page(label="Contact owner@example.test"))
    assert labelled.sections[0].label == "Contact [email]"
    with pytest.raises(ValueError):
        Observation.model_validate(section_page(key="unsafe key"))


@pytest.mark.xfail(reason="pending (docs/harness-rebuild-plan.md): an empty planner result still drops its token count on fallback", strict=True)
def test_planner_empty_result_retains_usage_when_falling_back(monkeypatch):
    from app.agent import runtime
    from app.agent.schema import GoalPlan
    from tests.test_destination_grounding import PLAN

    monkeypatch.setattr(runtime, "call", lambda *a, **k: (GoalPlan(intent="Explore", checkpoints=[], feasible=True), 17))
    result = PLAN(SITE, "Explore", section_page())
    assert result["planner_tokens"] == 17 and result["checkpoints"][0]["text_contains"] is None


def test_recovery_target_identity_is_document_scoped_with_a_run_wide_cap():
    from app.agent.harness import can_refresh
    state = {"observation": section_page(document="new-document"), "harness_worklog": [
        {"node": "recover", "target_id": 1, "document_id": "old-document"}]}
    assert can_refresh(state, 1)
    state["observation"]["document_id"] = "old-document"
    assert not can_refresh(state, 1)
    state["observation"]["document_id"] = "new-document"
    state["harness_worklog"].append({"node": "recover", "target_id": 2, "document_id": "old-document"})
    assert not can_refresh(state, 3)


def test_revision_budget_never_resets_or_drops_unresolved_milestones():
    original = plan()
    original["revision_count"] = 2
    original["checkpoints"].append({"description": "Inspect Gallery", "kind": "navigation", "url_contains": "/gallery"})
    state = {"goal": "Open Destinations then inspect Gallery", "plan": original, "observation": section_page()}
    saved = deepcopy(state)
    assert goal.revision_candidate(state) == (None, "revision_unavailable")
    assert state == saved
