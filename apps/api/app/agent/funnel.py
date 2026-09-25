"""Signup funnel numbers (V18, todo P0.2): plain counts over a run's stored steps, never a model. Paid runs only."""

from __future__ import annotations

from datetime import datetime


def _at(step: dict) -> datetime | None:
    raw = (step.get("evidence") or {}).get("captured_at")
    try:
        return datetime.fromisoformat(str(raw)) if raw else None  # Python 3.11+ reads a trailing Z
    except ValueError:
        return None


def metrics(steps: list[dict], status: str) -> dict:
    """Steps to the goal, fields typed, distinct errors seen, safe stops, and the first useful screen: the first step
    that completed a checkpoint of the goal plan. Seconds come from screenshot times, so they are None without them."""
    useful = next((i for i, s in enumerate(steps) if (s.get("progress") or 0) > 0), None)
    start = next((t for s in steps if (t := _at(s))), None)
    reached = _at(steps[useful]) if useful is not None else None
    return {
        "steps_to_goal": len(steps) if status == "done" else None,
        "fields_typed": sum(s.get("action") == "type" for s in steps),
        "errors_seen": len({e for s in steps for e in s.get("errors_after") or []}),
        "safe_stops": sum(bool(s.get("safe_stop")) for s in steps),
        "first_useful_step": useful + 1 if useful is not None else None,
        "seconds_to_first_useful": round((reached - start).total_seconds()) if start and reached and reached >= start else None,
    }
