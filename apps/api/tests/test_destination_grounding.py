"""Observed navigation contracts, with no site-specific routes or model calls."""
import pytest

from app.agent import goal, harness, runtime
from app.agent.persona import render_observation
from app.agent.schema import Element, GoalPlan, Observation
from app.agent.typesafe import build_request

PLAN = goal.plan
SITE = "https://fixture.test"


def page(destination=None, path="/"):
    return {"url": SITE + path, "title": "Fixture", "text": "Explore", "elements": [
        {"id": 1, "tag": "a", "text": "Explore", "destination": destination}]}


@pytest.mark.parametrize("destination", ["//evil.test/path", "/work?token=secret", "/work#token=secret", "/person%40email.test", "https://evil.test/path"])
def test_api_discards_unsafe_or_ambiguous_destinations(destination):
    assert Element(id=1, tag="a", destination=destination).destination is None


def test_destination_reaches_both_provider_formats():
    obs = page("/work")
    assert '"destination": "/work"' in render_observation(obs)
    request = build_request({"observation": obs, "goal": "Explore", "persona": "skeptic"})
    assert request["state"]["page"]["elements"][0]["destination"] == "/work"


def test_context_budget_drops_whole_destinations_instead_of_truncating_into_another_route():
    obs = Observation(url=SITE, elements=[Element(id=i, tag="a", destination="/" + "abc/" * 49 + "abc") for i in range(40)])
    assert obs.context_truncated
    assert sum(len(e.destination or "") for e in obs.elements) == 6000
    assert all(e.destination is None or len(e.destination) == 200 for e in obs.elements)


def test_planner_route_is_a_hypothesis_until_observed(monkeypatch):
    monkeypatch.setattr(runtime, "call", lambda *a, **k: (GoalPlan(intent="Explore", feasible=True, checkpoints=[
        {"description": "Open work", "kind": "navigation", "url_contains": "/work"}]), 0))
    plan = PLAN(SITE, "Explore the work", page())
    checkpoint = plan["checkpoints"][0]
    assert checkpoint["requires_observed_destination"] is True
    assert goal.evaluate_evidence(checkpoint, page(), page(path="/work"), "click", SITE)[1] == "unobserved_navigation_target"
    assert goal.evaluate_evidence(checkpoint, page("/work"), page(path="/work"), "click", SITE)[1] == "checkpoint_confirmed"
    context = harness.context({"plan": plan, "observation": page()})
    assert context["predicate_problem"] == "unobserved_navigation_target"


def test_explicit_owner_route_and_legacy_contract_keep_existing_semantics(monkeypatch):
    monkeypatch.setattr(runtime, "call", lambda *a, **k: (GoalPlan(intent="Open work", feasible=True, checkpoints=[
        {"description": "Open work", "kind": "navigation", "url_contains": "/work"}]), 0))
    checkpoint = PLAN(SITE, "Open /work", page())["checkpoints"][0]
    assert checkpoint["requires_observed_destination"] is False
    assert goal.evidence(checkpoint, page(), page(path="/work"), "click", SITE)
    checkpoint.pop("requires_observed_destination")
    assert goal.evidence(checkpoint, page(), page(path="/work"), "click", SITE)


def test_fragment_does_not_become_page_or_functional_completion():
    checkpoint = {"kind": "navigation", "url_contains": "/#destinations", "requires_observed_destination": True}
    assert goal.evaluate_evidence(checkpoint, page("/#destinations"), page(path="/#destinations"), "click", SITE)[1] == "section_evidence_required"
    checkpoint = {"kind": "outcome", "text_contains": None}
    assert goal.evaluate_evidence(checkpoint, page("/work"), page(path="/work"), "click", SITE)[1] == "missing_outcome_expectation"
