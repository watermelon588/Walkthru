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

from app.agent.safety import LOOP_LIMIT, MAX_STEPS, is_destructive, is_sending
from app.agent.schema import Observation, PersonaStep

Status = Literal["running", "done", "gave_up", "budget", "stuck", "captcha", "safe_stop"]

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
    verified: bool  # the signed-in owner proved control of this domain
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
        "If the page shows a confirmation that your goal succeeded (for example 'message sent'), answer done at once; never repeat a send.\n"
        "Form fields show [filled] or [empty]. A [filled] field already holds what you typed; never retype it, "
        "move to the next [empty] field. When the fields you need are filled, press the button that submits the form "
        "(it may sit away from the fields; read the button labels).\n"
        f"If a form asks for identity, use this test identity: {identity}\n"
        "Never click anything that pays, deletes or cancels. If the goal is to send a message, press the send button; "
        "Walkthru decides whether it is safe to actually send."
    )


def render_observation(obs: dict) -> str:
    o = Observation.model_validate(obs)
    lines = [f"URL: {o.url}", f"Title: {o.title}"]
    if o.note:
        lines.append(f"Executor note: {o.note}")
    if o.errors:
        lines.append("Visible errors: " + " | ".join(o.errors))
    if o.notices:
        lines.append("Visible confirmations: " + " | ".join(o.notices))
    lines.append("Elements:")
    for e in o.elements:
        kind = f" ({e.type})" if e.type else ""
        state = f" [{e.state}]" if e.state else ""
        lines.append(f"  [{e.id}] {e.tag}{kind}{state}: {e.text}")
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
        step, safe_stop = _enforce(step, state)
        record = step.model_dump() | {"url": state["observation"]["url"]} | metadata | ({"safe_stop": True} if safe_stop else {})
        if step.action == "click" and state.get("verified"):
            target = next((e for e in state["observation"].get("elements", []) if e["id"] == step.target_id), {})
            if is_sending(target.get("text", "")) and target.get("tag") != "a":
                record["sent"] = True  # the owner still confirms in the side panel; this marks the one allowed send
        return {"steps": state.get("steps", []) + [record], "tokens": state.get("tokens", 0) + used}

    def act(state: SessionState) -> dict:
        resumed = interrupt(state["steps"][-1])
        if "observation" not in resumed:  # old extension contract
            return {"observation": resumed}
        steps = list(state["steps"])
        after = resumed["observation"]
        # What the step led to, so the report states what worked instead of guessing.
        outcome = {"result_url": after.get("url")}
        if after.get("errors"):
            outcome["errors_after"] = after["errors"][:3]
        if after.get("notices"):
            outcome["notices_after"] = after["notices"][:3]
        if after.get("note"):
            outcome["note_after"] = after["note"][:200]
        steps[-1] = steps[-1] | outcome
        if resumed.get("evidence"):
            steps[-1] = steps[-1] | {"evidence": resumed["evidence"]}
        diagnostics = resumed["observation"].get("diagnostics")
        if diagnostics:
            steps[-1] = steps[-1] | {"diagnostics": diagnostics}
        return {"observation": resumed["observation"], "steps": steps}

    def check(state: SessionState) -> dict:
        steps = state["steps"]
        last = steps[-1]
        if last.get("safe_stop"):
            return {"status": "safe_stop"}
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


def _identity_value(label: str, input_type: str | None, run_id: str) -> str:
    """Test-identity value for a field, chosen from its label or input type."""
    text = f"{label} {input_type or ''}".lower()
    if "email" in text:
        return f"walkthru.tester+{run_id}@example.com"
    if "password" in text:
        return "Walk-thru-2026!"
    if "phone" in text or "tel" in text:
        return "5550100"
    if "name" in text:
        return "Test Walker"
    return "Hello, this is a Walkthru test message."


def _enforce(step: PersonaStep, state: SessionState) -> tuple[PersonaStep, bool]:
    """Code-level safety: replace unsafe or invalid choices instead of trusting the prompt.

    Returns (step, safe_stop). safe_stop means Walkthru ended the journey at a button on purpose.
    """
    elements = {e["id"]: e for e in state["observation"].get("elements", [])}
    if step.action not in ("click", "type"):
        return step, False
    el = elements.get(step.target_id)
    if el is None:
        thought = f"{step.thought} (element #{step.target_id} does not exist)"
        return PersonaStep(thought=thought, action="scroll", confusion=max(step.confusion, 2)), False
    label = el.get("text", "")
    if step.action == "type" and not (step.text or "").strip():
        # Models sometimes pick a field but forget the text; typing nothing would loop forever.
        return step.model_copy(update={"text": _identity_value(label, el.get("type"), state["run_id"])}), False
    button = step.action == "click" and el.get("tag") != "a"  # plain links only navigate
    if is_destructive(label) and (state.get("logged_in") or button):
        if state.get("logged_in"):
            return PersonaStep(thought=f"{step.thought} (blocked by safe mode: '{label}')", action="give_up", confusion=step.confusion), False
        thought = f"{step.thought} (Walkthru stopped at '{label}' by design: it never pays, deletes or cancels. The flow worked up to this point.)"
        return PersonaStep(thought=thought, action="done", confusion=step.confusion), True
    if is_sending(label) and button and any(s.get("sent") for s in state.get("steps", [])):
        thought = f"{step.thought} (Walkthru never sends twice in one run; a message was already sent.)"
        return PersonaStep(thought=thought, action="done", confusion=step.confusion), False
    if is_sending(label) and button and not state.get("verified"):
        thought = (
            f"{step.thought} (Walkthru stopped at '{label}' by design: it only sends real messages on a domain the owner "
            "has verified, after they confirm. Everything up to this button worked.)"
        )
        return PersonaStep(thought=thought, action="done", confusion=step.confusion), True
    return step, False
