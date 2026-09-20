"""persona_session graph: decide -> act (interrupt for observation) -> check -> decide.

One HTTP call per step. The extension sends an Observation, we resume the thread
and return the next PersonaStep. The LLM is only called inside `decide`, so an
interrupt/resume never repeats a model call.
"""

from __future__ import annotations

import json
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.agent.safety import LOOP_LIMIT, MAX_STEPS, is_dangerous
from app.agent.schema import Observation, PersonaStep

Status = Literal["running", "done", "gave_up", "budget", "stuck", "captcha"]

PERSONAS = {
    "first_timer": "a first-time visitor who has never heard of this product, skims, and gets impatient fast",
    "phone_user": "a user on a small phone screen who taps big obvious things and hates long forms",
    "buyer": "a small-business owner evaluating whether to pay; cares about pricing, trust and what happens next",
    "skeptic": "a cautious developer who reads error messages, checks links and distrusts vague copy",
}

TEST_IDENTITY = "Name: Test Walker. Email: walkthru.tester+{run_id}@example.com. Password: Walk-thru-2026!"


class SessionState(TypedDict, total=False):
    run_id: str
    site: str
    goal: str
    persona: str
    logged_in: bool
    max_steps: int
    observation: dict  # latest Observation
    first_text: str  # page text of the first observation, kept for the report
    steps: list[dict]  # PersonaStep dumps + url
    status: Status
    tokens: int  # LLM tokens used so far


def system_prompt(state: SessionState) -> str:
    who = PERSONAS.get(state["persona"], state["persona"])
    identity = TEST_IDENTITY.format(run_id=state["run_id"])
    return (
        f"You are {who}. You are trying to: {state['goal']}\n"
        "You see a text snapshot of the current page with numbered interactive elements. "
        "Think aloud in character, then choose exactly one action. Prefer the obvious path a real "
        "person would take. Do not repeat an action that already failed. If you reach the goal, "
        "answer done. If you are lost after honest attempts, answer give_up and say why.\n"
        f"If a form asks for identity, use this test identity: {identity}\n"
        "Never click anything that pays, deletes, sends or invites."
    )


def render_observation(obs: dict) -> str:
    o = Observation.model_validate(obs)
    lines = [f"URL: {o.url}", f"Title: {o.title}"]
    if o.note:
        lines.append(f"Executor note: {o.note}")
    if o.errors:
        lines.append("Visible errors: " + " | ".join(o.errors))
    lines.append("Elements:")
    for e in o.elements:
        kind = f" ({e.type})" if e.type else ""
        lines.append(f"  [{e.id}] {e.tag}{kind}: {e.text}")
    lines.append("Page text:\n" + o.text[:4000])
    return "\n".join(lines)


def render_history(steps: list[dict]) -> str:
    if not steps:
        return "No steps yet."
    out = []
    for i, s in enumerate(steps):
        line = f"{i + 1}. {s['action']}"
        if s.get("target_id") is not None:
            line += f" #{s['target_id']}"
        if s.get("text"):
            line += f' "{s["text"]}"'
        line += f" on {s.get('url', '?')}: {s['thought']}"
        out.append(line)
    return "\n".join(out)


def build_graph(model: Any, checkpointer: Any):
    """Build the loop around either a decision provider or a structured-output LLM."""

    def decide(state: SessionState) -> dict:
        history = render_history(state.get("steps", []))
        page = render_observation(state["observation"])
        messages = [
            ("system", system_prompt(state)),
            ("human", f"What you did so far:\n{history}\n\nCurrent page:\n{page}"),
        ]
        from app.agent.runtime import unwrap  # local import: runtime imports this module

        if hasattr(model, "decide"):
            decision = model.decide(state, messages)
            step, used, metadata = decision.step, decision.tokens, decision.metadata
        else:
            step, used = unwrap(model.invoke(messages))
            metadata = {"provider": "llm"}
        step = _enforce(step, state)
        record = step.model_dump() | {"url": state["observation"]["url"]} | metadata
        return {"steps": state.get("steps", []) + [record], "tokens": state.get("tokens", 0) + used}

    def act(state: SessionState) -> dict:
        resumed = interrupt(state["steps"][-1])
        if "observation" not in resumed:  # old extension contract
            return {"observation": resumed}
        steps = list(state["steps"])
        if resumed.get("evidence"):
            steps[-1] = steps[-1] | {"evidence": resumed["evidence"]}
        return {"observation": resumed["observation"], "steps": steps}

    def check(state: SessionState) -> dict:
        steps = state["steps"]
        last = steps[-1]
        if last["action"] == "done":
            return {"status": "done"}
        if last["action"] == "give_up":
            return {"status": "gave_up"}
        if len(steps) >= state.get("max_steps", MAX_STEPS):
            return {"status": "budget"}
        note = (state["observation"].get("note") or "").lower()
        if "captcha" in note:
            return {"status": "captcha"}
        tail = steps[-LOOP_LIMIT:]
        keys = {json.dumps({k: s.get(k) for k in ("action", "target_id", "text", "url")}) for s in tail}
        if len(tail) == LOOP_LIMIT and len(keys) == 1:
            return {"status": "stuck"}
        return {"status": "running"}

    def after_decide(state: SessionState) -> str:
        return "check" if state["steps"][-1]["action"] in ("done", "give_up") else "act"

    def after_check(state: SessionState) -> str:
        return "decide" if state["status"] == "running" else END

    g = StateGraph(SessionState)
    g.add_node("decide", decide)
    g.add_node("act", act)
    g.add_node("check", check)
    g.add_edge(START, "decide")
    g.add_conditional_edges("decide", after_decide)
    g.add_edge("act", "check")
    g.add_conditional_edges("check", after_check)
    return g.compile(checkpointer=checkpointer)


def _enforce(step: PersonaStep, state: SessionState) -> PersonaStep:
    """Code-level safety: replace unsafe or invalid choices instead of trusting the prompt."""
    elements = {e["id"]: e for e in state["observation"].get("elements", [])}
    if step.action in ("click", "type"):
        el = elements.get(step.target_id)
        if el is None:
            thought = f"{step.thought} (element #{step.target_id} does not exist)"
            return PersonaStep(thought=thought, action="scroll", confusion=max(step.confusion, 2))
        label = el.get("text", "")
        if state.get("logged_in") and is_dangerous(label):
            thought = f"{step.thought} (blocked by safe mode: '{label}')"
            return PersonaStep(thought=thought, action="give_up", confusion=step.confusion)
    return step
