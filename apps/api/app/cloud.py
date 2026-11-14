"""In-app live runs: start, watch and stop test users that walk a site in the server's browser.

These routes only queue and report. The browser belongs to the runner service (app/runner), which runs each
journey through the same run logic as the extension, so plan limits, site policy and safety rules are decided
there, in one place. A refusal at that point shows up on the test user's card as `blocked` with its reason.
Off unless CLOUD_RUNNER=on.
"""

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app import db, goal_ideas, limits, plans, plus
from app.agent.safety import MAX_STEPS
from app.auth import require_user
from app.scans import fetch

router = APIRouter()
MAX_PERSONAS = 3  # per test, and the most one account may have queued or running at once
STEP_KEYS = ("thought", "action", "confusion", "url", "result_url", "note_after", "code", "interrupted", "evidence")


def _enabled() -> None:
    if os.environ.get("CLOUD_RUNNER", "off") != "on":
        raise HTTPException(403, "Live runs are not switched on yet. Use the Walkthru extension to run a test.")


class StartCloudRun(BaseModel):
    model_config = {"extra": "forbid"}
    site: str = Field(pattern=r"^https?://", max_length=2000)
    goal: str = Field(min_length=1, max_length=500)
    personas: list[str] = Field(default=["first_timer"], min_length=1, max_length=MAX_PERSONAS)  # built-in keys or "custom:<id>"
    max_steps: int = Field(default=MAX_STEPS, ge=1, le=MAX_STEPS)


@router.get("/cloud-runs/goal-ideas")
def goal_ideas_for(site: str = Query(pattern=r"^https?://", max_length=2000), user: dict = Depends(require_user)) -> dict:
    """Goals this site's own links and buttons support, read from its served pages without a model (app/goal_ideas.py)."""
    limits.apply("costly", user["id"])
    try:
        fetch.assert_public(site)
    except ValueError:
        return {"ideas": []}
    return {"ideas": goal_ideas.suggest(site)}


@router.post("/cloud-runs")
def start(body: StartCloudRun, user: dict = Depends(require_user)) -> dict:
    _enabled()
    limits.apply("start_run", user["id"])  # router routes name their tighter rule here (as app/teams.py does)
    try:
        fetch.assert_public(body.site)
    except ValueError as e:
        raise HTTPException(422, f"Live runs test public websites. This address cannot be opened: {e}. "
                                 "For a local or private site, use the Walkthru extension.") from e
    personas = list(dict.fromkeys(body.personas))
    usage = plans.current(user["id"])
    plan = usage["plan"]
    if len(personas) > 1 and plan.name != "plus":
        raise HTTPException(403, "Several test users on one goal are part of the Plus plan.")
    for persona in personas:
        custom = persona.startswith(plus.CUSTOM_PREFIX)
        if custom and plan.name != "plus":
            raise HTTPException(403, "Custom test users are part of the Plus plan.")
        plans.check_start(usage, site=body.site, persona=plan.personas[0] if custom else persona, logged_in=False)
    if usage["allowed"] - usage["used"] < len(personas):
        raise HTTPException(402, f"This test needs {len(personas)} runs and you have {max(0, usage['allowed'] - usage['used'])} left.")
    if db.active_cloud_runs(user["id"]) + len(personas) > MAX_PERSONAS:
        raise HTTPException(429, f"You can have {MAX_PERSONAS} test users waiting or running at once. Wait for one to finish, or stop a test.")
    group_id = str(uuid.uuid4())
    rows = db.queue_cloud_runs([{"user_id": user["id"], "group_id": group_id, "site": body.site, "goal": body.goal, "persona": persona,
                                 "max_steps": min(body.max_steps, plan.max_steps)} for persona in personas])
    return {"group_id": group_id, "runs": [_card(row, user["id"]) for row in rows]}


def _card(row: dict, user_id: str) -> dict:
    """One test user's state for the live page. Frames are named by path; the page signs them with the owner's session."""
    card = {"id": row["id"], "persona": row["persona"], "status": row["status"], "error": row.get("error"), "run_id": row.get("run_id"),
            "created_at": row["created_at"], "updated_at": row["updated_at"], "steps": [], "report_ready": False}
    if row["status"] == "queued":
        card["ahead"] = db.cloud_runs_ahead(row["created_at"])
    run = db.get_run(row["run_id"]) if row.get("run_id") else None
    if run and str(run["user_id"]) == user_id:
        card |= {"run_status": run["status"], "report_ready": bool(run.get("report")), "persona": run.get("persona") or row["persona"],
                 "steps": [{k: step[k] for k in STEP_KEYS if k in step} for step in run.get("steps") or []]}
    return card


@router.get("/cloud-runs/{group_id}")
def watch(group_id: uuid.UUID, user: dict = Depends(require_user)) -> dict:
    rows = db.cloud_runs_in_group(str(group_id), user["id"])
    if not rows:
        raise HTTPException(404, "unknown live test")
    return {"group_id": str(group_id), "site": rows[0]["site"], "goal": rows[0]["goal"], "runs": [_card(row, user["id"]) for row in rows]}


@router.post("/cloud-runs/{group_id}/stop")
def stop(group_id: uuid.UUID, user: dict = Depends(require_user)) -> dict:
    """Queued test users end now. A running one is closed by its runner at its next step, with a partial report."""
    if not db.cloud_runs_in_group(str(group_id), user["id"]):
        raise HTTPException(404, "unknown live test")
    return {"stopped": len(db.stop_cloud_runs(str(group_id), user["id"]))}
