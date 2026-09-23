import logging
import os
import time
import uuid
from typing import Literal
from urllib.parse import urlsplit

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langgraph.types import Command
from psycopg import OperationalError
from psycopg_pool import PoolTimeout
from pydantic import BaseModel, EmailStr, Field

from app import auth, db, deliver, retention
from app.agent import report, runtime
from app.agent.safety import MAX_STEPS
from app.agent.schema import Observation, StepEvidence
from app.auth import require_user
from app.scans import fetch, security

log = logging.getLogger("walkthru")
WEB_URL = os.environ.get("WEB_URL", "http://localhost:5173")
WEB_ORIGINS = {WEB_URL.rstrip("/")}
_web = urlsplit(WEB_URL)
if _web.hostname in {"localhost", "127.0.0.1"}:
    _port = f":{_web.port}" if _web.port else ""
    WEB_ORIGINS.update({f"{_web.scheme}://localhost{_port}", f"{_web.scheme}://127.0.0.1{_port}"})

app = FastAPI(title="Walkthru API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(WEB_ORIGINS),
    allow_origin_regex=r"chrome-extension://.*",
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


def _database_unavailable(request: Request, error: Exception) -> JSONResponse:
    log.warning("database temporarily unavailable: %s", error)
    return JSONResponse(status_code=503, content={"detail": "Walkthru could not reach its database just now. Please try again in a few seconds."})


if os.environ.get("WARMUP", "1") == "1":
    # Import model clients and build the agent graph in the background so the first run after a start is not slow.
    import threading

    threading.Thread(target=lambda: runtime.graph("free"), name="warmup", daemon=True).start()

if os.environ.get("RETENTION_JOB", "1") == "1" and os.environ.get("SUPABASE_SECRET_KEY"):
    retention.start_background()

app.add_exception_handler(OperationalError, _database_unavailable)
app.add_exception_handler(PoolTimeout, _database_unavailable)
app.add_exception_handler(db.DatabaseUnavailable, _database_unavailable)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# ---------- persona test runs (extension) ----------


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
    evidence: StepEvidence | None = None


def _cfg(run_id: str) -> dict:
    return {"configurable": {"thread_id": run_id}}


def _reply(run_id: str, tier: str, result: dict, background: BackgroundTasks) -> dict:
    values = runtime.get_state(tier, _cfg(run_id)).values
    running = "__interrupt__" in result
    status = "running" if running else values["status"]
    db.update_run(run_id, status, values.get("steps", []), values.get("tokens", 0))
    if running:
        return {"run_id": run_id, "status": "running", "action": result["__interrupt__"][0].value, "verified": bool(values.get("verified"))}
    background.add_task(finish_run, run_id, values)
    return {"run_id": run_id, "status": status, "steps": values["steps"]}


def _owned(run_id: str, user: dict) -> dict:
    row = db.get_run(run_id)
    if row is None or str(row["user_id"]) != user["id"]:
        raise HTTPException(404, "unknown run")
    return row


@app.post("/runs")
def start_run(body: StartRun, background: BackgroundTasks, user: dict = Depends(require_user)) -> dict:
    run_id = uuid.uuid4().hex
    db.insert_run(run_id, user["id"], body.site, body.goal, body.persona, body.tier, body.logged_in, email=user.get("email"))
    verified = _verified(body.site, user["id"])  # owner-verified domains may send real messages after confirmation
    state = body.model_dump(exclude={"tier"}, mode="json") | {"run_id": run_id, "steps": [], "status": "running", "tokens": 0, "first_text": body.observation.text[:6000], "verified": verified}
    result = runtime.invoke(body.tier, state, _cfg(run_id))
    return _reply(run_id, body.tier, result, background)


@app.post("/runs/{run_id}/observe")
def observe(run_id: str, body: Observe, background: BackgroundTasks, user: dict = Depends(require_user)) -> dict:
    row = _owned(run_id, user)
    if row["status"] != "running":
        raise HTTPException(409, "run already finished")
    if body.evidence and not body.evidence.screenshot_path.startswith(f"{run_id}/"):
        raise HTTPException(422, "evidence path does not belong to this run")
    if not runtime.get_state(row["tier"], _cfg(run_id)).next:
        # The live agent state is gone (API restarted with the in-memory checkpointer). Close the run
        # truthfully with its saved steps instead of failing; the extension shows "Ended early".
        return stop_run(run_id, background, StopRequest(reason="the Walkthru server restarted and lost the live test"), user=user)
    resume = {"observation": body.observation.model_dump(mode="json")}
    if body.evidence:
        resume["evidence"] = body.evidence.model_dump(mode="json")
    result = runtime.invoke(row["tier"], Command(resume=resume), _cfg(run_id))
    return _reply(run_id, row["tier"], result, background)


@app.get("/runs/{run_id}")
def get_run(run_id: str, user: dict = Depends(require_user)) -> dict:
    row = _owned(run_id, user)
    return {"run_id": run_id, "status": row["status"], "steps": row["steps"], "report": row.get("report")}


class StopRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=300)  # why the browser ended early, shown to the report


@app.post("/runs/{run_id}/stop")
def stop_run(run_id: str, background: BackgroundTasks, body: StopRequest | None = None, user: dict = Depends(require_user)) -> dict:
    """End an interrupted browser session and generate a truthful partial report."""
    row = _owned(run_id, user)
    if row["status"] == "stopped":
        return {
            "run_id": run_id,
            "status": "stopped",
            "steps": row["steps"],
            "report_status": "ready" if row.get("report") else "generating",
        }
    if row["status"] != "running":
        raise HTTPException(409, "run already finished")

    steps = [dict(step) for step in row.get("steps", [])]
    if steps and steps[-1].get("action") not in {"done", "give_up"}:
        steps[-1] = steps[-1] | {"interrupted": True}
    if steps and body and body.reason:
        steps[-1] = steps[-1] | {"note_after": body.reason}
    tokens = row.get("tokens", 0)
    first_text = ""
    try:
        first_text = runtime.get_state(row["tier"], _cfg(run_id)).values.get("first_text", "")
    except Exception:  # noqa: BLE001 - old or missing checkpoints still produce a partial report
        log.info("checkpoint unavailable while stopping run %s", run_id)

    if not db.mark_run_stopped(run_id, steps, tokens):
        refreshed = _owned(run_id, user)
        if refreshed["status"] != "stopped":
            raise HTTPException(409, "run already finished")
        return {
            "run_id": run_id,
            "status": "stopped",
            "steps": refreshed["steps"],
            "report_status": "ready" if refreshed.get("report") else "generating",
        }

    values = {"status": "stopped", "steps": steps, "tokens": tokens, "first_text": first_text}
    background.add_task(finish_run, run_id, values)
    return {"run_id": run_id, "status": "stopped", "steps": steps, "report_status": "generating"}


def finish_run(run_id: str, values: dict) -> None:
    """After the persona session ends: scans + first impression + synthesis, saved as the report, then email."""
    row = db.get_run(run_id)
    if row is None:
        return
    try:
        verified = bool(row["user_id"]) and _verified(row["site"], str(row["user_id"]))
        rep = report.run_report(
            row["site"],
            values.get("first_text", ""),
            goal=row["goal"],
            persona=row["persona"],
            status=values.get("status", row["status"]),
            steps=values.get("steps", []),
            verified=verified,
            final_controls=[f"{e.get('tag')}: {e.get('text')}" for e in (values.get("observation") or {}).get("elements", []) if e.get("text")][:40],
        )
        rep.tokens += values.get("tokens", 0)
        db.set_report(run_id, rep.model_dump())
        if row.get("email"):
            deliver.send_report(row["email"], f"{WEB_URL}/app/runs/{run_id}", row["site"], rep.model_dump())
    except Exception:
        log.exception("report failed for run %s", run_id)


def _verified(site: str, user_id: str) -> bool:
    try:
        fetch.assert_public(site)
        with fetch.client(timeout=5) as c:
            return security.verify_domain(site, security.verification_token(user_id), c)
    except Exception:  # noqa: BLE001 - unverified is the safe default
        return False


# ---------- instant scan (no account) ----------


class ScanRequest(BaseModel):
    site: str = Field(pattern=r"^https?://", max_length=2000)
    email: EmailStr | None = None


_scan_hits: dict[str, list[float]] = {}  # ponytail: per-process rate limit; move to Postgres when there is more than one instance
SCAN_LIMIT, SCAN_WINDOW = 5, 3600


def _rate_limit(ip: str) -> None:
    if os.environ.get("ALLOW_LOCAL_SCANS") == "1" and ip in ("127.0.0.1", "::1"):
        return  # dev only: the founder testing from this machine; production never sets ALLOW_LOCAL_SCANS
    now = time.time()
    hits = [t for t in _scan_hits.get(ip, []) if now - t < SCAN_WINDOW]
    if len(hits) >= SCAN_LIMIT:
        raise HTTPException(429, "Too many scans from this address. Try again in an hour or sign in.")
    _scan_hits[ip] = hits + [now]


@app.post("/scans")
def instant_scan(body: ScanRequest, request: Request) -> dict:
    """Free homepage scan: first impression, SEO basics, security headers. Public report, no login."""
    _rate_limit(request.client.host if request.client else "?")
    try:
        fetch.assert_public(body.site)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    with fetch.client() as c:
        resp = fetch.get(c, body.site)
    if resp is None or resp.status_code >= 400:
        raise HTTPException(422, "That site did not respond. Check the address and try again.")
    run_id = uuid.uuid4().hex
    db.insert_run(run_id, None, str(resp.url), "Instant Scan", "stranger", "free", False, kind="scan", email=body.email, public=True)
    rep = report.run_report(str(resp.url), fetch.page_text(resp.text))
    db.set_report(run_id, rep.model_dump(), status="done")
    if body.email:
        deliver.send_report(body.email, f"{WEB_URL}/r/{run_id}", str(resp.url), rep.model_dump())
    return {"run_id": run_id, "url": f"{WEB_URL}/r/{run_id}", "report": rep.model_dump()}


# ---------- sharing, email, verification ----------


@app.post("/runs/{run_id}/share")
def share_run(run_id: str, user: dict = Depends(require_user)) -> dict:
    _owned(run_id, user)
    db.set_public(run_id, True)
    return {"url": f"{WEB_URL}/r/{run_id}"}


@app.post("/runs/{run_id}/email")
def email_run(run_id: str, user: dict = Depends(require_user)) -> dict:
    row = _owned(run_id, user)
    to = row.get("email") or user.get("email")
    if not row.get("report") or not to:
        raise HTTPException(409, "report not ready")
    sent = deliver.send_report(to, f"{WEB_URL}/app/runs/{run_id}", row["site"], row["report"])
    # Keep the destination in the response when delivery is not configured so
    # the web app can offer a truthful, ready-to-send mail-client fallback.
    return {"sent": sent, "to": to}


@app.delete("/runs/{run_id}")
def delete_run(run_id: str, user: dict = Depends(require_user)) -> dict:
    """Owner deletes one run: screenshots, checkpoint, report and row."""
    _owned(run_id, user)
    retention.delete_runs([run_id])
    return {"deleted": run_id}


@app.get("/account/export")
def export_account(user: dict = Depends(require_user)) -> dict:
    """Everything stored about the signed-in user's runs, as one JSON document."""
    return {
        "user": {"id": user["id"], "email": user.get("email")},
        "evidence_retention_days": retention.RETENTION_DAYS,
        "note": "Screenshots are listed by storage path; open them from the report while they are retained.",
        "runs": db.runs_for_user(user["id"]),
    }


class DeleteAccount(BaseModel):
    confirm: str = Field(max_length=320)


@app.post("/account/delete")
def delete_account(body: DeleteAccount, user: dict = Depends(require_user)) -> dict:
    """Permanent. The caller must type their account email to confirm."""
    if not user.get("email") or body.confirm.strip().lower() != user["email"].lower():
        raise HTTPException(422, "Type your account email exactly to confirm deletion.")
    retention.delete_account(user["id"])
    for token in [t for t, (u, _) in auth._cache.items() if u["id"] == user["id"]]:
        auth._cache.pop(token, None)
    return {"deleted": True}


@app.get("/verification")
def verification(user: dict = Depends(require_user)) -> dict:
    """Token the site owner publishes to unlock the full security scan (exposed files, secrets in bundles)."""
    token = security.verification_token(user["id"])
    return {"token": token, "meta": f'<meta name="walkthru-verification" content="{token}">', "file": "/.well-known/walkthru.txt"}
