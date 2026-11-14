"""Deterministic control context and bounded, public execution explanations."""

import json

from app.agent import goal
from app.agent.schema import HarnessEvent


def append_event(state: dict, node: str, reason: str, *, next_step: bool = False, **fields) -> list[dict]:
    log = list(state.get("harness_worklog", []))
    if len(log) >= 256:
        return log
    entry = HarnessEvent(sequence=len(log) + 1, step=max(1, len(state.get("steps", [])) + int(next_step)),
                         node=node, reason=reason, progress=state.get("plan_done", 0), **fields)
    return log + [entry.model_dump(exclude_none=True)]


def context(state: dict) -> dict:
    index = state.get("plan_done", 0)
    checkpoints = (state.get("plan") or {}).get("checkpoints", [])
    current = checkpoints[index] if index < len(checkpoints) else None
    previous = next((e for e in reversed(state.get("harness_worklog", [])) if e["node"] == "assess"), None)
    return {"checkpoint": index + 1 if current else None,
            "predicate_problem": goal.checkpoint_problem(current, state["observation"]) if current else None,
            "last_proof_result": previous["reason"] if previous else None,
            "contract_version": (state.get("plan") or {}).get("contract_version", 1),
            "facts": {"confirmed_checkpoints": index, "document_id": state["observation"].get("document_id")},
            "hypothesis": {"kind": current.get("kind"), "url_contains": current.get("url_contains"),
                           "section_key": current.get("section_key")} if current else None,
            "discovery_attempts": state.get("contract_attempts", {}).get(str(index), 0),
            "stop_reason": state.get("contract_stop_reason"),
            "executable_target_ids": [e["id"] for e in state["observation"].get("elements", [])
                                      if e.get("in_view") is not False and not e.get("occluded")],
            "recoveries_used": sum(e["node"] == "recover" for e in state.get("harness_worklog", []))}


def action_signature(step: dict) -> str:
    """Do not let irrelevant model fields hide repeated clicks; IDs remain page-scoped."""
    fields = ["action", "url"]
    if step["action"] in {"click", "type"}:
        fields += ["target_id", "target_label"]
        if step["action"] == "type":
            fields += ["text"]
    elif step["action"] == "scroll":
        fields += ["scroll_pct", "scroll_container_id", "scroll_direction", "scroll_position"]
    elif step["action"] == "wait":
        fields += ["wait_condition"]
    values = {k: step.get(k) for k in fields}
    if step["action"] == "scroll":
        values["scroll_container_id"] = step.get("scroll_container_id") or 0
        values["scroll_direction"] = step.get("scroll_direction") or "down"
    return json.dumps(values, sort_keys=True)


def can_refresh(state: dict, target_id: int) -> bool:
    obs = state["observation"]
    recoveries = [e for e in state.get("harness_worklog", []) if e["node"] == "recover"]
    return (obs.get("navigation_version") == 3 and bool(obs.get("revision")) and len(state.get("harness_worklog", [])) < 254 and len(recoveries) < 2
            and not any(e.get("target_id") == target_id and (not obs.get("document_id") or not e.get("document_id") or
                        e["document_id"] == obs["document_id"]) for e in recoveries))
