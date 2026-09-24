"""Goal planner: read what the owner typed for its intent and turn it into a short checklist, once per run.

The test user follows the checklist instead of the literal words, and code ends the run when the last
checkpoint is reached. A goal like "click next project" then stops after one click instead of circling.
"""

from app.agent.schema import GoalPlan

PLANNER_SYSTEM = (
    "You turn a website owner's test goal into a plan for an AI test user. Read the goal for its intent, not its literal words, "
    "and fix obvious typos. Write 1 to 4 checkpoints in order; the last one is the finish line. Each checkpoint happens once: "
    "never plan repetition ('keep clicking', 'visit every page'). Set url_contains only when you are sure what the URL will "
    "contain once the checkpoint is reached; otherwise null. Set feasible to false only when the goal asks to pay, delete, cancel, "
    "spam, attack or bypass security, or is about a different website, and say why in refusal. Anything else is feasible."
)


def fallback(goal: str) -> dict:
    return {"intent": goal, "checkpoints": [{"description": goal[:200], "url_contains": None}], "feasible": True, "refusal": None}


def plan(site: str, goal: str, observation: dict) -> dict:
    """One fast model call before the first step. A planner outage never blocks a test: the typed goal is used."""
    from app.agent import runtime
    from app.agent.persona import render_observation

    messages = [("system", PLANNER_SYSTEM), ("human", f"Site: {site}\nGoal as typed: {goal}\n\nStart page:\n{render_observation(observation)[:5000]}")]
    try:
        result, _ = runtime.call(GoalPlan, messages, fast=True)
    except Exception:  # noqa: BLE001 - fall back to the literal goal
        return fallback(goal)
    out = result.model_dump()
    return out if out["checkpoints"] or not out["feasible"] else fallback(goal)


def reached(checkpoint: dict, url: str, start_url: str) -> bool:
    """Deterministic check for a checkpoint with a URL marker. A marker the start page already matches proves nothing."""
    marker = (checkpoint.get("url_contains") or "").lower()
    return bool(marker) and marker in url.lower() and marker not in start_url.lower()
