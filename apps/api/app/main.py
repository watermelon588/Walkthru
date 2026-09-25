import logging
import os
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from itertools import pairwise
from typing import Literal
from urllib.parse import urlsplit

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, Response
from langgraph.types import Command
from psycopg import OperationalError
from psycopg_pool import PoolTimeout
from pydantic import BaseModel, EmailStr, Field
from starlette.routing import Route

from app import auth, db, deliver, mcp_server, plans, retention, watch
from app.agent import compare, fix_prompt, goal, report, runtime, score
from app.agent.safety import MAX_STEPS
from app.agent.schema import Observation, StepEvidence
from app.auth import require_user
from app.scans import fetch, security

logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s")  # libraries stay at WARNING
log = logging.getLogger("walkthru")
log.setLevel(logging.INFO)  # Walkthru's own INFO lines (step timings, retention) reach the console
_background = ThreadPoolExecutor(max_workers=8, thread_name_prefix="start-run")  # short side tasks of a request
WEB_URL = os.environ.get("WEB_URL", "http://localhost:5173")
WEB_ORIGINS = {WEB_URL.rstrip("/")}
_web = urlsplit(WEB_URL)
if _web.hostname in {"localhost", "127.0.0.1"}:
    _port = f":{_web.port}" if _web.port else ""
    WEB_ORIGINS.update({f"{_web.scheme}://localhost{_port}", f"{_web.scheme}://127.0.0.1{_port}"})



@asynccontextmanager
async def _lifespan(_app: FastAPI):
    async with mcp_server.server.session_manager.run():  # the MCP transport needs its task group running
        yield


app = FastAPI(title="Walkthru API", lifespan=_lifespan)
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
    # Import model clients and build both agent graphs and the goal planner's model chain in the background,
    # so the first run after a start does not pay for it (measured: about 5 s on the first paid run).
    import threading

    from app.agent.schema import GoalPlan

    def _warm() -> None:
        for tier in ("free", "paid"):
            runtime.graph(tier)
        for paid in (False, True):
            runtime.structured(GoalPlan, True, paid)  # the same cache key goal.plan's runtime.call uses

    threading.Thread(target=_warm, name="warmup", daemon=True).start()

if os.environ.get("RETENTION_JOB", "1") == "1" and os.environ.get("SUPABASE_SECRET_KEY"):
    retention.start_background()
    watch.start_background()  # same switch: background jobs off in tests and one-off scripts

app.add_exception_handler(OperationalError, _database_unavailable)
app.add_exception_handler(PoolTimeout, _database_unavailable)
app.add_exception_handler(db.DatabaseUnavailable, _database_unavailable)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# ---------- persona test runs (extension) ----------


class StartRun(BaseModel):
    # No tier field: the plan comes from the caller's entitlement (app/plans.py). Older clients that
    # still send `tier` are accepted and ignored.
    site: str = Field(pattern=r"^https?://", max_length=2000)
    goal: str = Field(min_length=1, max_length=500)
    persona: str = Field(default="first_timer", max_length=40)
    logged_in: bool = False
    max_steps: int = Field(default=MAX_STEPS, ge=1, le=MAX_STEPS)  # clamped to the plan
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


@app.get("/me/plan")
def my_plan(user: dict = Depends(require_user)) -> dict:
    return plans.summary(plans.current(user["id"]))


@app.post("/runs")
def start_run(body: StartRun, background: BackgroundTasks, user: dict = Depends(require_user)) -> dict:
    marks = [("start", time.monotonic())]
    # Domain verification is a passive fetch of the owner's site that needs nothing else, so it runs while the
    # plan check and the goal planner work instead of after them (measured: 4 to 6 s saved on the first step).
    verifying = _background.submit(_verified, body.site, user["id"])
    usage = plans.current(user["id"])
    plans.check_start(usage, site=body.site, persona=body.persona, logged_in=body.logged_in)
    marks.append(("plan_check", time.monotonic()))
    plan = usage["plan"]
    tier = "free" if plan.name == "free" else "paid"  # model routing only; limits come from `plan`
    # Read the goal for its intent before any step, and refuse unsafe goals without using a run.
    goal_plan = goal.plan(body.site, body.goal, body.observation.model_dump(mode="json"), paid=tier == "paid")
    marks.append(("goal_planner", time.monotonic()))
    if not goal_plan.get("feasible", True) and goal_plan.get("refusal"):
        raise HTTPException(422, f"Walkthru will not run this goal: {goal_plan['refusal']}")
    run_id = uuid.uuid4().hex
    db.insert_run(run_id, user["id"], body.site, body.goal, body.persona, tier, body.logged_in)
    marks.append(("insert_run", time.monotonic()))
    verified = verifying.result()  # owner-verified domains may send real messages after confirmation
    marks.append(("verify_domain_wait", time.monotonic()))
    state = body.model_dump(mode="json") | {"max_steps": min(body.max_steps, plan.max_steps), "run_id": run_id, "steps": [], "status": "running", "tokens": 0,
                                            "first_text": body.observation.text[:6000], "verified": verified, "plan": goal_plan, "plan_done": 0, "start_url": body.observation.url}
    result = runtime.invoke(tier, state, _cfg(run_id))
    marks.append(("first_step", time.monotonic()))
    reply = _reply(run_id, tier, result, background)
    marks.append(("save_step", time.monotonic()))
    log.info("start_run %s %s", run_id, " ".join(f"{name}={later - earlier:.1f}s" for (_, earlier), (name, later) in pairwise(marks)))
    # The side panel shows how Walkthru understood the goal.
    return reply | {"plan": {"intent": goal_plan["intent"], "checkpoints": [c["description"] for c in goal_plan["checkpoints"]]}}


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


class IgnoreFinding(BaseModel):
    fingerprint: str = Field(min_length=3, max_length=300)
    reason: str = Field(min_length=1, max_length=200)


@app.post("/runs/{run_id}/findings/ignore")
def ignore_finding(run_id: str, body: IgnoreFinding, user: dict = Depends(require_user)) -> dict:
    """Mark a finding as accepted ("won't fix") for this site. It stays in the score but leaves compare lists."""
    row = _owned(run_id, user)
    if plans.current(user["id"])["plan"].name == "free":
        raise HTTPException(402, "Ignoring findings is part of the paid plans.")
    db.set_ignored(user["id"], compare.origin(row["site"]), body.fingerprint, body.reason.strip())
    return {"ignored": body.fingerprint}


@app.delete("/runs/{run_id}/findings/ignore")
def unignore_finding(run_id: str, fingerprint: str, user: dict = Depends(require_user)) -> dict:
    row = _owned(run_id, user)
    db.clear_ignored(user["id"], compare.origin(row["site"]), fingerprint)
    return {"cleared": fingerprint}


@app.get("/runs/{run_id}/fix-prompt")
def get_fix_prompt(run_id: str, style: Literal["full", "chat"] = "full", download: bool = False, user: dict = Depends(require_user)) -> Response:
    """The agent fix prompt as Markdown (paid plans). Built on request, never stored in the report, so the free plan
    cannot read it through the report row."""
    row = _owned(run_id, user)
    if plans.current(user["id"])["plan"].name == "free":
        raise HTTPException(402, "The agent fix prompt is part of the paid plans.")
    if not row.get("report"):
        raise HTTPException(409, "The report is not ready yet.")
    try:
        ignored = db.ignored_fingerprints(user["id"], compare.origin(row["site"]))
    except (httpx.HTTPError, db.DatabaseUnavailable):
        ignored = {}
    text = fix_prompt.build(row, row["report"], ignored, style)
    headers = {"Content-Disposition": 'attachment; filename="walkthru-fixes.md"'} if download else {}
    return Response(text, media_type="text/markdown; charset=utf-8", headers=headers)


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
            paid=row.get("tier") == "paid",  # GEO on every audited page for paid plans (SPEC.md)
            intent=(values.get("plan") or {}).get("intent", ""),
        )
        rep.tokens += values.get("tokens", 0)
        try:
            rep.comparison = compare.attach(row, rep.model_dump())
        except Exception:  # a failed comparison must never lose the report
            log.warning("rerun comparison failed for run %s", run_id, exc_info=True)
        db.set_report(run_id, rep.model_dump())
        to = db.user_email(str(row["user_id"])) if row.get("user_id") and os.environ.get("RESEND_API_KEY") else None
        if to:
            deliver.send_report(to, f"{WEB_URL}/app/runs/{run_id}", row["site"], rep.model_dump())
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


_scan_hits: dict[str, list[float]] = {}  # ponytail: per-process; production runs one API process. The daily cap (plans.FREE_SCANS_PER_DAY) is in the database.
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
    if db.free_runs_today("scan") >= plans.FREE_SCANS_PER_DAY:
        raise HTTPException(429, "Free scan capacity is used up for today. Try again tomorrow.")
    try:
        run_id, rep = run_scan(body.site)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    if body.email:
        deliver.send_report(body.email, f"{WEB_URL}/r/{run_id}", rep["site"], rep["report"])
    return {"run_id": run_id, "url": f"{WEB_URL}/r/{run_id}", "report": rep["report"]}


def run_scan(site: str, *, user_id: str | None = None, kind: str = "scan") -> tuple[str, dict]:
    """One server-side scan, stored as a run. Anonymous Instant Scans are public; an owner's scan (MCP) is private.
    Raises ValueError with a message for the caller when the site cannot be scanned."""
    fetch.assert_public(site)
    with fetch.client() as c:
        resp = fetch.get(c, site)
    if resp is None or resp.status_code >= 400:
        raise ValueError("That site did not respond. Check the address and try again.")
    run_id = uuid.uuid4().hex
    # Owners' scans use the paid tier so they never count against the free daily capacity.
    db.insert_run(run_id, user_id, str(resp.url), "Instant Scan", "stranger", "paid" if user_id else "free", False, kind=kind, public=user_id is None)
    rep = report.run_report(str(resp.url), fetch.page_text(resp.text))
    db.set_report(run_id, rep.model_dump(), status="done")
    return run_id, {"site": str(resp.url), "report": rep.model_dump()}


# ---------- Walkthru MCP server and personal API keys (Plus) ----------

app.router.routes.append(Route("/mcp", mcp_server.Endpoint(), methods=["GET", "POST", "DELETE"]))


class NewApiKey(BaseModel):
    name: str = Field(min_length=1, max_length=60)


@app.get("/me/api-keys")
def list_api_keys(user: dict = Depends(require_user)) -> list[dict]:
    return db.api_keys_for_user(user["id"])


@app.post("/me/api-keys")
def create_api_key(body: NewApiKey, user: dict = Depends(require_user)) -> dict:
    """The key is returned once and only its hash is stored."""
    mcp_server.require_plus(user["id"])
    if len(db.api_keys_for_user(user["id"])) >= mcp_server.MAX_KEYS:
        raise HTTPException(409, f"You already have {mcp_server.MAX_KEYS} keys. Revoke one you no longer use.")
    key, hashed = mcp_server.new_key()
    return db.insert_api_key(user["id"], body.name.strip(), hashed) | {"key": key}


def _plan_name(user_id: str) -> str:
    return plans.current(user_id)["plan"].name


# ---------- weekly watch (Plus) and deploy hooks ----------


class WatchSite(BaseModel):
    site: str = Field(pattern=r"^https?://", max_length=2000)


@app.get("/watch")
def list_watched(user: dict = Depends(require_user)) -> dict:
    plan = plans.current(user["id"])["plan"]
    return {"sites": db.sites_for_user(user["id"]) if plan.name == "plus" else [], "plan": plan.name, "limit": plan.sites,
            "email": bool(os.environ.get("RESEND_API_KEY"))}


@app.post("/watch")
def add_watched(body: WatchSite, background: BackgroundTasks, user: dict = Depends(require_user)) -> dict:
    plan = plans.current(user["id"])["plan"]
    if plan.name != "plus":
        raise HTTPException(402, "Weekly watch is part of the Plus plan.")
    try:
        fetch.assert_public(body.site)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    site = compare.origin(body.site) + "/"
    current = db.sites_for_user(user["id"])
    if any(s["site"] == site for s in current):
        raise HTTPException(409, "You already watch that site.")
    if len(current) >= plan.sites:
        raise HTTPException(409, f"Your plan watches up to {plan.sites} sites. Remove one first.")
    row = db.add_site(user["id"], site)
    background.add_task(_watch_check, row, "added")  # the baseline every later check compares with
    return row


def _watch_check(site: dict, reason: str) -> None:
    try:
        watch.check(site, reason)
    except Exception:  # background work: the next weekly pass retries
        log.warning("watch check failed for %s", site.get("site"), exc_info=True)


@app.delete("/watch/{site_id}")
def remove_watched(site_id: str, user: dict = Depends(require_user)) -> dict:
    if not re.fullmatch(r"[0-9a-f-]{36}", site_id) or not db.remove_site(user["id"], site_id):
        raise HTTPException(404, "You do not watch that site.")
    return {"removed": site_id}


def _owned_site(site_id: str, user_id: str) -> dict:
    site = next((s for s in db.sites_for_user(user_id) if s["id"] == site_id), None)
    if site is None:
        raise HTTPException(404, "You do not watch that site.")
    return site


@app.post("/watch/{site_id}/check")
def check_watched_now(site_id: str, background: BackgroundTasks, user: dict = Depends(require_user)) -> dict:
    """Check now, for example right after a deploy. Shares the deploy hook's 10-minute limit."""
    if _plan_name(user["id"]) != "plus":
        raise HTTPException(402, "Weekly watch is part of the Plus plan.")
    site = _owned_site(site_id, user["id"])
    if not db.claim_hook(site_id, (datetime.now(UTC) - watch.HOOK_COOLDOWN).isoformat()):
        raise HTTPException(429, "This site was checked in the last 10 minutes. Try again shortly.")
    background.add_task(_watch_check, site, "manual")
    return {"queued": True}


@app.post("/watch/{site_id}/hook")
def create_deploy_hook(site_id: str, request: Request, user: dict = Depends(require_user)) -> dict:
    """A URL to POST after each deploy (a Netlify deploy notification, a CI step). Shown once; a new one replaces the old."""
    if _plan_name(user["id"]) != "plus":
        raise HTTPException(402, "Deploy hooks are part of the Plus plan.")
    _owned_site(site_id, user["id"])
    token, hashed = watch.new_hook()
    db.update_site(site_id, {"hook_hash": hashed})
    return {"url": f"{str(request.base_url).rstrip('/')}/hooks/deploy/{token}"}


@app.post("/hooks/deploy/{token}", status_code=202)
def deploy_hook(token: str, background: BackgroundTasks) -> dict:
    site = db.site_by_hook(watch.hook_hash(token)) if token.startswith("wh_") else None
    if site is None:
        raise HTTPException(404, "Unknown deploy hook.")
    if _plan_name(str(site["user_id"])) != "plus":
        raise HTTPException(402, "Deploy hooks are part of the Plus plan.")
    if not db.claim_hook(site["id"], (datetime.now(UTC) - watch.HOOK_COOLDOWN).isoformat()):
        raise HTTPException(429, "Checked in the last 10 minutes; this deploy is covered by that check.")
    background.add_task(_watch_check, site, "deploy")
    return {"queued": True}


# ---------- competitor side by side (paid plans) ----------

MAX_COMPETITORS = 3


class CompareRequest(BaseModel):
    site: str = Field(pattern=r"^https?://", max_length=2000)
    competitors: list[str] = Field(min_length=1, max_length=MAX_COMPETITORS)


@app.post("/compare")
def start_compare(body: CompareRequest, background: BackgroundTasks, user: dict = Depends(require_user)) -> dict:
    """Your site and up to three competitors through the same passive checks, side by side. Deep security checks
    never run on sites you have not verified, so competitors only get public checks."""
    if _plan_name(user["id"]) == "free":
        raise HTTPException(402, "Competitor comparison is part of the paid plans.")
    urls = list(dict.fromkeys([body.site, *body.competitors]))
    for url in urls:
        if not re.match(r"^https?://", url):
            raise HTTPException(422, f"Use a full address beginning with http:// or https://: {url}")
        try:
            fetch.assert_public(url)
        except ValueError as e:
            raise HTTPException(422, f"{url}: {e}") from e
    if db.user_scans_today(user["id"]) + len(urls) > mcp_server.SCANS_PER_DAY:
        raise HTTPException(429, f"That would pass your {mcp_server.SCANS_PER_DAY} scans for today. Try again tomorrow.")
    run_id = uuid.uuid4().hex
    db.insert_run(run_id, user["id"], body.site, f"Compared with {len(urls) - 1} competitor{'s' if len(urls) > 2 else ''}", "stranger", "paid", False, kind="compare")
    background.add_task(_compare, run_id, user["id"], urls)
    return {"run_id": run_id}


def _compare(run_id: str, user_id: str, urls: list[str]) -> None:
    def one(url: str) -> dict:
        try:
            part_id, fresh = run_scan(url, user_id=user_id, kind="compare_part")
        except Exception as e:  # noqa: BLE001 - one unreachable competitor must not sink the comparison
            return {"site": url, "error": str(e) if isinstance(e, ValueError) else "The scan failed."}
        rep = fresh["report"]
        counts = {s: sum(f["severity"] == s for f in rep["findings"]) for s in ("high", "medium", "low")}
        return {"site": fresh["site"], "run_id": part_id, "score": (rep.get("launch_ready") or {}).get("score"),
                "areas": (rep.get("launch_ready") or {}).get("areas", {}), "geo": (rep.get("geo") or {}).get("score"),
                "findings": counts, "pages": (rep.get("site_audit") or {}).get("pages_scanned"),
                "impression": (rep.get("first_impression") or {}).get("what")}

    with ThreadPoolExecutor(max_workers=len(urls)) as pool:
        sites = list(pool.map(one, urls))
    sites[0]["yours"] = True
    db.set_report(run_id, {"compare": sites}, status="done")


@app.delete("/me/api-keys/{key_id}")
def revoke_api_key(key_id: str, user: dict = Depends(require_user)) -> dict:
    if not re.fullmatch(r"[0-9a-f-]{36}", key_id) or not db.revoke_api_key(user["id"], key_id):
        raise HTTPException(404, "No active key with that id.")
    return {"revoked": key_id}


# ---------- sharing, email, verification ----------


@app.post("/runs/{run_id}/share")
def share_run(run_id: str, user: dict = Depends(require_user)) -> dict:
    _owned(run_id, user)
    db.set_public(run_id, True)
    return {"url": f"{WEB_URL}/r/{run_id}"}


# ---------- Launch Ready badge (public reports only; no login) ----------


def _badge_run(run_id: str) -> dict:
    """The embedded report, or the owner's newer public report of the same site, so a rerun updates the badge."""
    row = db.get_run(run_id) if re.fullmatch(r"[0-9a-f]{32}", run_id) else None
    if not row or not row.get("public") or not row.get("report"):
        raise HTTPException(404, "No public report with that id.")
    if row.get("user_id"):  # Instant Scans have no owner, so they always show themselves
        origin = fetch.origin(row["site"])
        same_site = [r for r in db.public_reports(str(row["user_id"])) if fetch.origin(r["site"]) == origin]
        row = max([row, *same_site], key=lambda r: r.get("created_at") or "")
    return row


@app.get("/badge/{run_id}.svg")
def badge(run_id: str) -> Response:
    row = _badge_run(run_id)
    stored = row["report"].get("launch_ready") or score.launch_ready(row["report"], "scan" if row.get("kind") == "scan" else row.get("status", ""))
    return Response(score.badge_svg(stored.get("score")), media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=3600"})


@app.get("/badge/{run_id}")
def badge_link(run_id: str) -> RedirectResponse:
    """Where a click on the badge goes: the latest public report for that site."""
    return RedirectResponse(f"{WEB_URL}/r/{_badge_run(run_id)['id']}", status_code=302)


@app.post("/runs/{run_id}/email")
def email_run(run_id: str, user: dict = Depends(require_user)) -> dict:
    row = _owned(run_id, user)
    to = user.get("email")
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
        "passes": db.entitlements_for_user(user["id"]),
        "ignored_findings": db.ignored_for_user(user["id"]),
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
