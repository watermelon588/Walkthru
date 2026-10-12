"""Run quotes (R-S10): what one test run may use, pinned before it starts and bound to the run when it is accepted.

A quote is a server-signed, stateless token: no table, no migration. It pins the account, the scope (site origin,
logged-in or public pages, which test users, the step and time caps), the plan window and run credits, the price
version and the per-run maximum provider cost (R-S8), the model route and an expiry. `POST /runs` with a quote
re-checks every pinned value against the request and the server's current terms; anything stale or different is
refused with 409 so the client asks again, never a silent change. Contract: docs/run-quotes.md.

A quote is terms, not a credit: the reservation (R-S8/R-S9) remains the only authority that admits work.
"""

import base64
import hashlib
import hmac
import json
import os
import time
from urllib.parse import urlsplit

from fastapi import HTTPException

from app import plans, reservations
from app.agent import runtime

VERSION = 1
TTL_SECONDS = 600
MAX_MINUTES = 4  # the extension's hard time limit for one test (apps/extension/lib/safety.ts MAX_MINUTES)
RULES = (
    "A test run stops at its step and time caps and writes a report from the evidence so far; it never continues past them.",
    "Nothing is topped up or charged automatically. Runs use credits from your plan or pass; no card is charged per run.",
    "The model route is fixed for this quote. Fallbacks inside that route are named in the report; a different, cheaper route is never substituted without a new quote.",
    "A run stopped early keeps its partial evidence. Start a new run to continue; credits returned by a refused or unstarted run are shown in your usage.",
)


def _key() -> bytes:
    secret = os.environ.get("QUOTE_SIGNING_KEY") or os.environ.get("SUPABASE_SECRET_KEY", "dev")
    return hmac.new(secret.encode(), b"walkthru-run-quote-v1", hashlib.sha256).digest()  # domain-separated


def _origin(site: str) -> str:
    parts = urlsplit(site)
    return f"{parts.scheme}://{(parts.hostname or '').lower()}" + (f":{parts.port}" if parts.port else "")


def terms(user_id: str, site: str, *, personas: list[str], logged_in: bool, max_steps: int, assertion: bool) -> dict:
    """The server's current terms for this request. Raises the same plain-language errors as starting would."""
    usage = plans.current(user_id)
    plan = usage["plan"]
    for persona in personas:
        plans.check_start(usage, site=site, persona=persona if not persona.startswith("custom:") else plan.personas[0], logged_in=logged_in)
    runs_left = max(0, usage["allowed"] - usage["used"])
    if len(personas) > runs_left:
        raise HTTPException(402, f"Each test user uses one run, and {runs_left} are left. Pick fewer test users.")
    cap = reservations.max_cost(plan.name)
    return {
        "v": VERSION, "user": user_id, "site": _origin(site), "logged_in": logged_in, "personas": personas,
        "max_steps": min(max_steps, plan.max_steps), "max_minutes": MAX_MINUTES, "assertion": assertion,
        "plan": plan.name, "window": [usage["since"], usage["until"]], "runs": len(personas), "runs_left_before": runs_left,
        "price_version": reservations.PRICE_VERSION, "max_cost_microusd_per_run": cap,
        "model_route": runtime.model_label(plan.name != "free"),
        "ledger": "active" if reservations.enabled() else "plan_count",
    }


def issue(t: dict) -> dict:
    """Sign the terms with an expiry. The token is what the client sends back on acceptance."""
    body = t | {"exp": int(time.time()) + TTL_SECONDS}
    raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    sig = hmac.new(_key(), raw, hashlib.sha256).hexdigest()
    return {"token": base64.urlsafe_b64encode(raw).decode() + "." + sig, "terms": body, "summary": describe(body), "rules": list(RULES)}


def _decode(token: str) -> dict:
    try:
        payload, sig = token.rsplit(".", 1)
        raw = base64.urlsafe_b64decode(payload.encode())
    except (ValueError, TypeError) as error:
        raise HTTPException(409, "This quote could not be read. Ask for a new quote and start again.") from error
    if not hmac.compare_digest(hmac.new(_key(), raw, hashlib.sha256).hexdigest(), sig):
        raise HTTPException(409, "This quote is not valid. Ask for a new quote and start again.")
    return json.loads(raw)


STALE = "The terms changed since this quote. Review the new quote and start again."


def accept(token: str, user_id: str, *, site: str, persona: str, logged_in: bool, max_steps: int, assertion: bool) -> dict:
    """Bind a run to its quote: signature, account, expiry, the request's scope and the server's current terms.
    Returns the pinned terms; the caller clamps the run to the quote's step cap. Raises 409 when stale or different."""
    quoted = _decode(token)
    if quoted.get("v") != VERSION or quoted.get("user") != user_id:
        raise HTTPException(409, "This quote belongs to a different account. Ask for a new quote.")
    if quoted.get("exp", 0) < time.time():
        raise HTTPException(409, "This quote has expired. Review the new quote and start again.")
    if quoted["site"] != _origin(site) or quoted["logged_in"] != logged_in or persona not in quoted["personas"] or quoted["assertion"] != assertion:
        raise HTTPException(409, "This run asks for more than its quote (site, pages or test user). Ask for a new quote.")
    now = terms(user_id, site, personas=[persona], logged_in=logged_in, max_steps=quoted["max_steps"], assertion=assertion)
    pinned = ("plan", "window", "price_version", "max_cost_microusd_per_run", "model_route", "max_minutes", "ledger")
    if any(now[k] != quoted[k] for k in pinned):
        raise HTTPException(409, STALE)
    return quoted


def _money(microusd: int) -> str:
    return "$0" if microusd == 0 else f"${microusd / 1_000_000:.6f}".rstrip("0").rstrip(".")


def describe(t: dict) -> str:
    """One plain-language paragraph, shared by the API, MCP and both clients."""
    who = f"{t['runs']} test users, one run each" if t["runs"] > 1 else "one test user, one run"
    pages = "signed-in pages in your own browser tab" if t["logged_in"] else "public pages"
    credits = f"{t['runs_left_before']} of your {t['plan']} runs left before this; {max(0, t['runs_left_before'] - t['runs'])} after."
    cost = (f"Walkthru reserves up to {_money(t['max_cost_microusd_per_run'])} of provider cost per run (price version {t['price_version']})."
            if t["ledger"] == "active" else "Usage is counted from your plan's run history.")
    return (f"{t['site']}: {who}, {pages}, up to {t['max_steps']} steps and {t['max_minutes']} minutes each. {credits} "
            f"Model route: {t['model_route']}. {cost} No card is charged per run. Quote valid for {TTL_SECONDS // 60} minutes.")


UNIT = {"run": ("test run", "test runs"), "scan": ("scan or finding check", "scans or finding checks"), "watch": ("watch check", "watch checks"),
        "citations": ("AI answer check", "AI answer checks"), "scout": ("Scout answer", "Scout answers"), "public_scan": ("Instant Scan", "Instant Scans")}


def explain(row: dict) -> dict:
    """One usage record in plain language: what happened to the credit and to the reserved provider cost."""
    one, many = UNIT.get(row.get("operation") or "run", ("unit", "units"))
    units = int(row.get("units") or 1)
    what = f"{units} {one if units == 1 else many}"
    outcome = row.get("outcome") or {}
    reserved = _money(int(row.get("max_cost_microusd") or 0))
    actual = row.get("actual_cost_microusd")
    if actual is not None:
        cost = f"Provider cost {_money(int(actual))}."
    elif reserved == "$0":
        cost = "No provider cost reserved."
    else:
        cost = f"Provider cost not measured yet; counted at the reserved maximum of {reserved}."
    state = row.get("state")
    if state == "released":
        text = f"Returned: the work never started, so {what} and the reserved {reserved} were released."
        cost = ""
    elif state == "refunded":
        text = f"Refunded by Walkthru ({(outcome.get('refund') or {}).get('reason', 'no reason recorded')}): {what} returned."
    elif state == "settled" and outcome.get("credit") == 1:
        text = f"Used {what} ({outcome.get('reason', 'completed')})."
    elif state == "settled":
        why = {"refused": "the goal was refused before the test started", "failed": "it failed after starting"}.get(outcome.get("reason"), "it did not complete")
        text = f"Not counted: {why}, so {what} returned."
    elif row.get("dispatched"):
        text = f"In progress or awaiting its result: {what} counted until it settles."
    else:
        text = f"Admitted, not started yet: {what} held."
    return {"operation": row.get("operation") or "run", "key": row.get("operation_key"), "state": state, "units": units,
            "created_at": row.get("created_at"), "price_version": row.get("price_version"), "text": text, "cost": cost}
