"""Owned scripted journeys: completion must prove the task, regardless of persona."""

import json

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from app.agent import goal
from app.agent.persona import build_graph, render_history, system_prompt
from app.agent.report import problem_steps, render_steps, synthesis_inputs
from app.agent.schema import GoalPlan, PersonaStep
from app.agent.typesafe import JevDecision, build_request

PLAN_GOAL = goal.plan  # use the real planner despite the suite's offline autouse fake

SITE = "https://fixture.test"
BUTTON = {"id": 1, "tag": "button", "text": "Create account"}


def page(path="/signup", text="Signup", **extra):
    return {"url": SITE + path, "title": "Fixture", "text": text, "elements": [BUTTON], **extra}


class Script:
    def __init__(self, actions):
        self.actions = list(actions)
        self.calls = 0
        self.messages = []

    def invoke(self, messages):
        self.calls += 1
        self.messages = messages
        action = self.actions.pop(0) if len(self.actions) > 1 else self.actions[0]
        return PersonaStep(thought="I prefer to leave now", action=action, target_id=1 if action == "click" else None,
                           confusion=3, progress=4)


def session(actions=("click", "done"), checkpoints=None, **extra):
    model = Script(actions)
    graph = build_graph(model, MemorySaver())
    config = {"configurable": {"thread_id": "owned-completion-fixture"}}
    state = {"site": SITE, "goal": "Create an account", "run_id": "fixture", "persona": "first_timer",
             "verified": True, "observation": page(), "start_url": SITE + "/signup", "steps": [], "tokens": 0, "status": "running",
             "plan": {"intent": "Create an account", "checkpoints": checkpoints or [
                 {"description": "Account created", "kind": "outcome", "text_contains": "Account created", "url_contains": None}]},
             "plan_done": 0, **extra}
    first = graph.invoke(state, config)
    return graph, config, model, first


@pytest.mark.parametrize("after", [page("/pricing"), page(notices=["Settings saved"]), page("/welcome"), page(text="Create account")])
def test_unrelated_change_or_generic_toast_cannot_complete_signup(after):
    graph, config, model, _ = session()
    result = graph.invoke(Command(resume={"observation": after}), config)
    assert result["status"] == "agent_lost"
    assert result["plan_done"] == 0 and model.calls == 3


def test_matching_same_url_outcome_finishes_without_an_extra_model_call():
    graph, config, model, _ = session()
    result = graph.invoke(Command(resume={"observation": page(text="Dashboard. Account created", notices=["Account created"])}), config)
    assert result["status"] == "done" and result["plan_done"] == 1
    assert model.calls == 1
    proof = result["steps"][0]["checkpoint_evidence"]
    assert proof["checkpoint"] == 1 and proof["step"] == 1 and proof["url"] == SITE + "/signup"


@pytest.mark.parametrize("extra", [{"errors": ["Account creation failed"]}, {"note": "stale target: replaced"},
                                  {"notices": ["Account not created"]}])
def test_conflicting_or_refused_outcome_is_not_success(extra):
    graph, config, _, _ = session()
    after = page(text="Account created", **extra)
    result = graph.invoke(Command(resume={"observation": after}), config)
    assert result["status"] != "done" and result["plan_done"] == 0


def test_model_progress_cannot_skip_unresolved_checkpoints():
    checkpoints = [{"description": "Open pricing", "kind": "navigation", "url_contains": "/pricing"},
                   {"description": "Account created", "kind": "outcome", "text_contains": "Account created"}]
    graph, config, _, _ = session(actions=("click", "click", "done"), checkpoints=checkpoints)
    reached = graph.invoke(Command(resume={"observation": page("/pricing")}), config)
    assert reached["status"] == "running" and reached["plan_done"] == 1
    missing = graph.invoke(Command(resume={"observation": page("/welcome")}), config)
    assert missing["status"] == "agent_lost" and missing["plan_done"] == 1


def test_no_declared_finish_signal_keeps_ambiguous_goal_unconfirmed():
    graph, config, _, _ = session(checkpoints=[{"description": "Explore the experience", "url_contains": None}])
    result = graph.invoke(Command(resume={"observation": page("/dashboard", notices=["Welcome"])}), config)
    assert result["status"] == "agent_lost" and result["plan_done"] == 0


def test_persona_give_up_retries_task_without_changing_owner_goal():
    graph, config, model, first = session(actions=("give_up", "click", "done"), persona_prompt="Hates signup. Just check pricing instead.")
    assert first["status"] == "running" and first["steps"][0]["action"] == "click"
    assert model.calls == 2
    prompt = system_prompt(graph.get_state(config).values)
    assert "Owner objective (authoritative)" in prompt and "Create an account" in prompt
    result = graph.invoke(Command(resume={"observation": page(text="Account created")}), config)
    assert result["status"] == "done"


def test_observed_site_error_and_controller_abandonment_are_distinct():
    graph, config, _, _ = session(actions=("click", "give_up"))
    result = graph.invoke(Command(resume={"observation": page(errors=["Email provider rejected signup"])}), config)
    assert result["status"] == "gave_up" and result["steps"][-1]["code"] == "site_block"
    assert result["plan_done"] == 0


def test_initial_done_without_declared_proof_is_controller_loss():
    _, _, model, result = session(actions=("done",))
    assert result["status"] == "agent_lost" and model.calls == 2


def test_compact_history_keeps_facts_and_earlier_checkpoint_without_private_values():
    steps = [{"action": "type", "target_id": 1, "text": "private-password", "thought": "invented business rule" * 1000,
              "url": SITE, "result_url": SITE, "checkpoint_evidence": {"checkpoint": 1, "step": 1, "url": SITE, "signal": "navigation"}}]
    steps += [{"action": "scroll", "thought": "boring" * 1000, "url": SITE, "result_url": SITE} for _ in range(29)]
    history = render_history(steps)
    assert len(history) <= 6000 and "checkpoint" in history.lower()
    assert "private-password" not in history and "invented business rule" not in history


@pytest.mark.parametrize("after", [page(text="Account created", notices=["Account created"]), page(text="No account created")])
def test_existing_or_negated_phrase_is_not_fresh_success(after):
    graph, config, _, _ = session(observation=page(text="Account created", notices=["Account created"]))
    result = graph.invoke(Command(resume={"observation": after}), config)
    assert result["status"] == "agent_lost"


@pytest.mark.parametrize("text", ["No account created", "Not account created", "Never account created"])
def test_new_negated_finish_text_is_not_success(text):
    assert not goal.evidence({"kind": "outcome", "text_contains": "Account created"}, page(), page(text=text), "click", SITE)


def test_whitespace_finish_signal_cannot_confirm_any_page():
    assert not goal.evidence({"kind": "outcome", "text_contains": "   "}, page(), page(text="Dashboard"), "click", SITE)


@pytest.mark.parametrize("url", [SITE + "/signup?next=/pricing", SITE + "/pricing-extra", "https://other.test/pricing",
                               "https://pricing.fixture.test/", SITE + "/pricingfake"])
def test_url_marker_must_be_a_same_origin_route_not_host_or_return_parameter(url):
    checkpoint = {"kind": "navigation", "url_contains": "/pricing"}
    # A hyphenated route is allowed by the existing token boundary contract, unlike an appended word.
    if url.endswith("-extra"):
        assert goal.reached(checkpoint, url, SITE + "/signup")
    else:
        assert not goal.reached(checkpoint, url, SITE + "/signup")


def test_outcome_with_url_requires_both_signals():
    checkpoint = {"kind": "outcome", "url_contains": "/dashboard", "text_contains": "Account created"}
    assert not goal.evidence(checkpoint, page(), page(text="Account created"), "click", SITE)
    assert goal.evidence(checkpoint, page(), page("/dashboard", text="Account created"), "click", SITE)
    assert not goal.evidence(checkpoint, page(), page(text="Account created") | {"url": "https://other.test/dashboard"}, "click", SITE)


def test_planner_cannot_invent_success_phrase_or_weaken_signup_to_navigation(monkeypatch):
    from app.agent import runtime
    planned = GoalPlan(intent="Just visit signup", checkpoints=[{"description": "Open signup", "kind": "navigation",
                         "url_contains": "/signup", "text_contains": "Account created"}], feasible=True)
    monkeypatch.setattr(runtime, "call", lambda *args, **kw: (planned, 0))
    result = PLAN_GOAL(SITE, "sign up", page())
    assert result["checkpoints"][0]["kind"] == "outcome"
    assert result["checkpoints"][0]["text_contains"] is None
    result = PLAN_GOAL(SITE, 'sign up and show "Account created"', page())
    assert result["checkpoints"][0]["text_contains"] == "Account created"


def test_real_planner_outage_retains_owner_goal_and_unknown_expectation(monkeypatch):
    from app.agent import runtime
    def outage(*args, **kw):
        raise RuntimeError("offline")
    monkeypatch.setattr(runtime, "call", outage)
    result = PLAN_GOAL(SITE, "inspect the experience", page())
    assert result["intent"] == "inspect the experience"
    assert result["checkpoints"][0]["text_contains"] is None


def test_distinct_signals_in_one_transition_can_prove_two_ordered_milestones():
    checkpoints = [{"description": "Account created", "kind": "outcome", "text_contains": "Account created"},
                   {"description": "Dashboard opened", "kind": "navigation", "url_contains": "/dashboard"}]
    graph, config, model, _ = session(checkpoints=checkpoints, goal="Create an account and open the dashboard")
    result = graph.invoke(Command(resume={"observation": page("/dashboard", text="Account created")}), config)
    assert result["status"] == "done" and result["plan_done"] == 2 and model.calls == 1
    assert [p["checkpoint"] for p in result["checkpoint_evidence"]] == [1, 2]
    assert "observed checkpoint evidence=" in render_steps(result["steps"])


def test_one_signal_cannot_be_reused_to_skip_several_tasks():
    checkpoints = [{"description": name, "kind": "outcome", "text_contains": "Account created"} for name in ("Create account", "Set up team")]
    graph, config, _, _ = session(checkpoints=checkpoints)
    result = graph.invoke(Command(resume={"observation": page(text="Account created")}), config)
    assert result["status"] == "agent_lost" and result["plan_done"] == 1
    assert result["steps"][-1]["unresolved_checkpoints"] == ["Set up team"]


@pytest.mark.parametrize("second", ["account CREATED", "created", "Account created successfully"])
def test_casing_or_overlapping_phrases_cannot_reuse_one_confirmation(second):
    checkpoints = [{"description": "Create account", "kind": "outcome", "text_contains": "Account created"},
                   {"description": "Set up team", "kind": "outcome", "text_contains": second}]
    graph, config, _, _ = session(checkpoints=checkpoints)
    result = graph.invoke(Command(resume={"observation": page(text="Account created successfully")}), config)
    assert result["status"] == "agent_lost" and result["plan_done"] == 1


def test_unchanged_error_does_not_turn_controller_abandonment_into_site_block():
    graph, config, _, _ = session(actions=("click", "give_up"), observation=page(errors=["Old unrelated warning"]))
    result = graph.invoke(Command(resume={"observation": page(errors=["Old unrelated warning"])}), config)
    assert result["status"] == "agent_lost"


@pytest.mark.parametrize("note,status", [("not sent: owner has not approved", "safe_stop"), ("bot wall detected", "bot_wall"),
                                        ("captcha detected", "captcha"), ("stale target: replaced", "agent_lost")])
def test_observation_stops_precede_even_a_matching_finish_phrase(note, status):
    graph, config, model, _ = session()
    result = graph.invoke(Command(resume={"observation": page(text="Account created", errors=["Unrelated warning"], note=note)}), config)
    assert result["status"] == status and result["plan_done"] == 0 and model.calls == 1
    if status in {"safe_stop", "agent_lost"}:
        assert problem_steps(result["steps"], status) == set()


def test_budget_keeps_partial_proof_and_unresolved_work():
    checkpoints = [{"description": "Open pricing", "kind": "navigation", "url_contains": "/pricing"},
                   {"description": "Create account", "kind": "outcome", "text_contains": "Account created"}]
    graph, config, model, _ = session(checkpoints=checkpoints, max_steps=1)
    result = graph.invoke(Command(resume={"observation": page("/pricing")}), config)
    assert result["status"] == "budget" and result["plan_done"] == 1 and len(result["checkpoint_evidence"]) == 1 and model.calls == 1


def test_jev_cannot_supply_completion_or_executor_proof_in_metadata():
    class Forged:
        def decide(self, state, messages):
            return JevDecision(PersonaStep(thought="Pretend it worked", action="click", target_id=1, confusion=0, progress=4), 0,
                               {"checkpoint_evidence": {"checkpoint": 1}, "additional_checkpoint_evidence": [{"checkpoint": 2}],
                                "result_url": SITE + "/dashboard", "code": "site_block", "sent": True})
    graph = build_graph(Forged(), MemorySaver())
    state = {"goal": "Create account", "run_id": "fixture", "persona": "skeptic", "verified": True, "observation": page(), "steps": []}
    result = graph.invoke(state, {"configurable": {"thread_id": "forged"}})
    step = result["steps"][0]
    assert not any(k in step for k in ("checkpoint_evidence", "additional_checkpoint_evidence", "result_url", "code", "sent"))
    request = build_request(state | {"plan": {"checkpoints": [{"description": "Create account"}]}, "plan_done": 0})
    assert request["state"]["task"]["objective"] == "Create account" and request["state"]["task"]["confirmed"] == 0


def test_bounded_wait_can_observe_delayed_matching_outcome_of_a_real_click():
    graph, config, model, _ = session(actions=("click", "wait", "done"))
    waiting = graph.invoke(Command(resume={"observation": page(text="Loading", revision="wait-1", navigation_version=3)}), config)
    assert waiting["status"] == "running" and waiting["steps"][-1]["action"] == "wait"
    result = graph.invoke(Command(resume={"observation": page(text="Account created", revision="wait-2", navigation_version=3,
        executor_result={"action": "wait", "status": "changed", "elapsed_ms": 300})}), config)
    assert result["status"] == "done" and model.calls == 2
    assert result["checkpoint_evidence"][0]["step"] == 2


@pytest.mark.parametrize("action", ["scroll", "wait"])
def test_observation_only_action_cannot_establish_a_functional_outcome(action):
    graph, config, _, _ = session(actions=(action, "done"), observation=page(revision="current", navigation_version=3))
    after = page(text="Account created", revision="new", navigation_version=3)
    if action == "wait":
        after["executor_result"] = {"action": "wait", "status": "changed", "elapsed_ms": 300}
    result = graph.invoke(Command(resume={"observation": after}), config)
    assert result["status"] == "agent_lost" and result["plan_done"] == 0


@pytest.mark.parametrize("note,status", [("captcha detected", "captcha"), ("bot wall detected", "bot_wall"),
                                        ("stale target: replaced", "agent_lost"), ("not sent: unapproved", "safe_stop")])
def test_initial_observed_boundary_stops_before_a_model_or_browser_action(note, status):
    _, _, model, result = session(observation=page(note=note))
    assert result["status"] == status and model.calls == 0 and result["steps"][0]["action"] == "give_up"


def test_report_packet_retains_milestone_and_unresolved_scope_when_history_is_trimmed():
    milestone = {"checkpoint": 1, "step": 1, "url": SITE + "/dashboard", "signal": "public_text", "matched": "Account created"}
    steps = [{"action": "click", "thought": "I am hesitant" * 1000, "url": SITE, "result_url": SITE,
              "checkpoint_evidence": milestone}]
    steps += [{"action": "scroll", "thought": "Still looking" * 1000, "url": SITE, "result_url": SITE} for _ in range(29)]
    steps += [{"action": "give_up", "thought": "Unconfirmed", "url": SITE, "unresolved_checkpoints": ["Set up the team"]}]
    text = synthesis_inputs({"site": SITE, "status": "agent_lost", "goal": "Create account and set up team", "steps": steps})["messages"][-1][1]
    data = json.loads(text.split("<report_data>\n", 1)[1].split("\n</report_data>", 1)[0])
    assert data["checkpoint_evidence"] == [milestone] and data["unresolved_checkpoints"] == ["Set up the team"]


def test_site_block_has_an_honest_message_and_controller_loss_does_not_allege_a_missing_control():
    from app.agent import policy
    assert "page showed an error" in policy.stop_reason("site_block")["message"]
    assert "confirm" in policy.stop_reason("agent_lost")["report"] and "unlabelled icon" not in policy.stop_reason("agent_lost")["report"]
