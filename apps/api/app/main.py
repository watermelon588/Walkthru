import os
import uuid
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langgraph.types import Command
from pydantic import BaseModel, Field

from app import db
from app.agent import runtime
from app.agent.safety import MAX_STEPS
from app.agent.schema import Observation
from app.auth import require_user

app = FastAPI(title="Walkthru API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("WEB_URL", "http://localhost:5173")],
    allow_origin_regex=r"chrome-extension://.*",
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


class StartRun(BaseModel):
    site: str = Field(pattern=r"^https?://", max_length=2000)
    goal: str = Field(min_length=1, max_length=500)
    persona: str = Field(default="first_timer", max_length=40)
    tier: Literal["free", "paid"] = "free"
    logged_in: bool = False
    max_steps: int = Field(default=12, ge=1, le=MAX_STEPS)
    observation: Observation


class Observe(BaseModel):
    observation: Observation


def _cfg(run_id: str) -> dict:
    return {"configurable": {"thread_id": run_id}}


def _reply(run_id: str, tier: str, result: dict) -> dict:
    values = runtime.graph(tier).get_state(_cfg(run_id)).values
    running = "__interrupt__" in result
    status = "running" if running else values["status"]
    db.update_run(run_id, status, values.get("steps", []))
    if running:
        return {"run_id": run_id, "status": "running", "action": result["__interrupt__"][0].value}
    return {"run_id": run_id, "status": status, "steps": values["steps"]}


def _owned(run_id: str, user_id: str) -> dict:
    row = db.get_run(run_id)
    if row is None or row["user_id"] != user_id:
        raise HTTPException(404, "unknown run")
    return row


@app.post("/runs")
def start_run(body: StartRun, user_id: str = Depends(require_user)) -> dict:
    run_id = uuid.uuid4().hex
    db.insert_run(run_id, user_id, body.site, body.goal, body.persona, body.tier, body.logged_in)
    state = body.model_dump(exclude={"tier"}) | {"run_id": run_id, "steps": [], "status": "running"}
    result = runtime.graph(body.tier).invoke(state, _cfg(run_id))
    return _reply(run_id, body.tier, result)


@app.post("/runs/{run_id}/observe")
def observe(run_id: str, body: Observe, user_id: str = Depends(require_user)) -> dict:
    row = _owned(run_id, user_id)
    if row["status"] != "running":
        raise HTTPException(409, "run already finished")
    result = runtime.graph(row["tier"]).invoke(Command(resume=body.observation.model_dump()), _cfg(run_id))
    return _reply(run_id, row["tier"], result)


@app.get("/runs/{run_id}")
def get_run(run_id: str, user_id: str = Depends(require_user)) -> dict:
    row = _owned(run_id, user_id)
    return {"run_id": run_id, "status": row["status"], "steps": row["steps"]}
