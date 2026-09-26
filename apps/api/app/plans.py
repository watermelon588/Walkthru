"""Plan limits (SPEC.md "Plans"). The server decides the plan; the client never says which tier it is.

Free usage counts per calendar month (UTC). A paid pass counts the runs made since it started,
up to its `runs_granted`, until it expires. Local development servers never count as a site.
"""

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit

from fastapi import HTTPException

from app import db
from app.agent.report import is_local_site

PERSONAS = ("first_timer", "phone_user", "buyer", "skeptic")


@dataclass(frozen=True)
class Plan:
    name: str
    runs: int  # test runs per month (free) or per pass
    max_steps: int
    logged_in: bool
    personas: tuple[str, ...]
    sites: int  # distinct sites tested per month or pass


PLANS = {
    "free": Plan("free", 3, 12, False, ("first_timer",), 1),
    "launch": Plan("launch", 20, 30, True, PERSONAS, 1),
    "pro": Plan("pro", 40, 30, True, PERSONAS, 2),
    "plus": Plan("plus", 150, 30, True, PERSONAS, 5),
}
# About 80% of the free model budget: 3 Groq models x 1,000 requests a day / ~27 calls per run (ROADMAP weak point 12).
FREE_RUNS_PER_DAY = int(os.environ.get("FREE_RUNS_PER_DAY", "90"))
# Instant Scans use the same free models (2 report calls each): 200 scans is 400 calls, which with the runs' share
# stays inside the 3,000 Groq requests a day.
FREE_SCANS_PER_DAY = int(os.environ.get("FREE_SCANS_PER_DAY", "200"))


def _site(url: str) -> str | None:
    if is_local_site(url):
        return None
    host = (urlsplit(url).hostname or "").lower()
    return host.removeprefix("www.") or None


def current(user_id: str) -> dict:
    """The caller's plan, its counting window and what they used in it."""
    now = datetime.now(UTC)
    grant = db.active_entitlement(user_id, now.isoformat())
    if grant:
        plan, since, until, allowed = PLANS[grant["plan"]], grant["starts_at"], grant["expires_at"], grant["runs_granted"]
    else:
        month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        plan, since, until, allowed = PLANS["free"], month.isoformat(), (month + timedelta(days=32)).replace(day=1).isoformat(), PLANS["free"].runs
    runs = db.test_runs_since(user_id, since)
    return {"plan": plan, "since": since, "until": until, "allowed": allowed, "used": len(runs), "sites": {s for r in runs if (s := _site(r["site"]))}}


def check_start(state: dict, *, site: str, persona: str, logged_in: bool) -> None:
    """Raise a plain-language HTTP error when this run is outside the plan."""
    plan = state["plan"]
    if logged_in and not plan.logged_in:
        raise HTTPException(403, "Testing logged-in pages needs a paid plan. Free runs test public pages.")
    if persona not in plan.personas:
        raise HTTPException(403, "The free plan includes the first-time visitor. The other test users need a paid plan.")
    if state["used"] >= state["allowed"]:
        window = "this month" if plan.name == "free" else "this pass"
        raise HTTPException(402, f"You have used all {state['allowed']} test runs {window}. Instant Scans stay free.")
    key = _site(site)
    if key and key not in state["sites"] and len(state["sites"]) >= plan.sites:
        raise HTTPException(403, f"Your plan covers {plan.sites} site{'s' if plan.sites > 1 else ''} at a time ({', '.join(sorted(state['sites']))}).")
    if plan.name == "free" and db.free_runs_today() >= FREE_RUNS_PER_DAY:
        raise HTTPException(429, "Free test capacity is used up for today. Try again tomorrow; Instant Scans still work.")


def summary(state: dict) -> dict:
    """What the side panel and dashboard show: `GET /me/plan`."""
    plan = state["plan"]
    return {
        "plan": plan.name,
        "runs_allowed": state["allowed"],
        "runs_left": max(0, state["allowed"] - state["used"]),
        "expires_at": state["until"],
        "max_steps": plan.max_steps,
        "logged_in": plan.logged_in,
        "personas": list(plan.personas),
        "sites": plan.sites,
        "sites_used": sorted(state["sites"]),
    }
