import uuid
from typing import Literal

from fastapi import FastAPI, HTTPException
from langgraph.types import Command
from pydantic import BaseModel, Field

from app.agent import runtime
from app.agent.safety import MAX_STEPS
from app.agent.schema import Observation

app = FastAPI(title="Walkthru API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


class StartRun(BaseModel):
    site: str
    goal: str
    persona: str = "first_timer"
    tier: Literal["free", "paid"] = "free"
    logged_in: bool = False
    max_steps: int = Field(default=12, ge=1, le=MAX_STEPS)
    observation: Observation


class Observe(BaseModel):
    observation: Observation


_tiers: dict[str, str] = {}  # ponytail: run_id -> tier in memory until the Supabase runs table (T10)


def _reply(run_id: str, result: dict) -> dict:
    if "__interrupt__" in result:
        return {"run_id": run_id, "status": "running", "action": result["__interrupt__"][0].value}
    return {"run_id": run_id, "status": result["status"], "steps": result["steps"]}


def _cfg(run_id: str) -> dict:
    return {"configurable": {"thread_id": run_id}}


@app.post("/runs")
def start_run(body: StartRun) -> dict:
    run_id = uuid.uuid4().hex
    _tiers[run_id] = body.tier
    state = body.model_dump(exclude={"tier"}) | {"run_id": run_id, "steps": [], "status": "running"}
    result = runtime.graph(body.tier).invoke(state, _cfg(run_id))
    return _reply(run_id, result)


@app.post("/runs/{run_id}/observe")
def observe(run_id: str, body: Observe) -> dict:
    tier = _tiers.get(run_id)
    if tier is None:
        raise HTTPException(404, "unknown run")
    g = runtime.graph(tier)
    if not g.get_state(_cfg(run_id)).next:
        raise HTTPException(409, "run already finished")
    result = g.invoke(Command(resume=body.observation.model_dump()), _cfg(run_id))
    return _reply(run_id, result)


@app.get("/runs/{run_id}")
def get_run(run_id: str) -> dict:
    tier = _tiers.get(run_id)
    if tier is None:
        raise HTTPException(404, "unknown run")
    values = runtime.graph(tier).get_state(_cfg(run_id)).values
    return {"run_id": run_id, "status": values.get("status"), "steps": values.get("steps", [])}
