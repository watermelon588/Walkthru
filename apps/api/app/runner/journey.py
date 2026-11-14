"""One test user's journey in the server's browser: the same loop as the extension's side panel
(apps/extension/entrypoints/sidepanel/run.ts), calling the same run logic as the API routes.

Differences from the extension, all on the safe side: the page is never signed in, nobody is there to approve a
real send so none is ever made, and every step is captured so the web app can replay it.
"""

import base64
import logging
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import HTTPException

from app import db, main, provider_usage
from app.agent.schema import StepEvidence
from app.runner import cdp, guard
from app.scans import fetch

log = logging.getLogger("walkthru.runner")
MAX_SECONDS = 4 * 60  # the extension's limit (MAX_MINUTES in run.ts)
SETTLE_S = 1.2
NO_SEND = "not sent: live runs never send real messages. Use the Walkthru extension to approve a send."
VERBS = {"click": "Clicked", "type": "Typed in", "wait": "Waited", "back": "Went back", "done": "Finished", "give_up": "Gave up"}


def label(step: dict, observation: dict) -> str:
    """A short name for the action, from the page's own (already masked) control text. Never model text."""
    if step["action"] == "scroll":
        return f"Scrolled {step.get('scroll_direction') or 'down'}"
    verb = VERBS.get(step["action"], "Acted")
    if step["action"] in ("click", "type"):
        name = next((e.get("text", "") for e in observation.get("elements", []) if e.get("id") == step.get("target_id")), "")
        name = " ".join(name.split())[:60]
        return f'{verb} "{name}"' if name else verb
    return verb


def _frame(tab: cdp.Tab, path: str) -> list[dict]:
    """Capture the viewport with form values hidden, and store it. Returns the visible error boxes (R-S19)."""
    regions = (tab.message({"type": "evidence_capture", "active": True}) or {}).get("regions") or []
    try:
        db.upload_evidence(path, base64.b64decode(tab.screenshot()))
    finally:
        tab.message({"type": "evidence_capture", "active": False})
    return regions


_read = cdp.read  # kept under this name for the loop below and its tests


BUSY = ("429", "rate limit", "overloaded", "503", "timed out", "timeout")


def _decide(observe: Callable[[], dict], deadline: float) -> dict:
    """Ask for the next step, waiting out a busy model. The free models allow a few thousand tokens a minute each, and
    a headless browser steps faster than a person's tab, so the whole chain can be busy for some seconds. The
    extension retries the same request in that case; so does this. The pending action is untouched by a failed
    call, so asking again cannot repeat a click."""
    for attempt in range(4):
        try:
            return observe()
        except HTTPException as e:
            if e.status_code not in (502, 503, 504) or attempt == 3 or time.monotonic() + 20 > deadline:
                raise
        except Exception as e:
            if not any(sign in str(e).lower() for sign in BUSY) or attempt == 3 or time.monotonic() + 20 > deadline:
                raise
        log.info("model busy, waiting before asking again (attempt %s)", attempt + 1)
        time.sleep(20)
    raise RuntimeError("unreachable")


def _last_frame(tab: cdp.Tab, run_id: str) -> None:
    """A run that ends on a step with no frame (the test user gave up or finished without acting) still shows where
    it was: capture that view and attach it to the final step. Best effort."""
    try:
        saved = db.get_run(run_id)
        steps = [dict(step) for step in (saved or {}).get("steps") or []]
        if not steps or steps[-1].get("evidence"):
            return
        path = f"{run_id}/step-{len(steps):02d}.jpg"
        regions = _frame(tab, path)
        width, height = tab.js("[innerWidth, innerHeight]")
        steps[-1]["evidence"] = StepEvidence(screenshot_path=path, captured_at=datetime.now(UTC), result_url=tab.js("location.href"), width=width,
                                             height=height, regions=regions, label="Stopped here" if steps[-1].get("action") == "give_up" else "Finished here",
                                             ).model_dump(mode="json", exclude_defaults=True)
        db.update_run(run_id, saved["status"], steps, saved.get("tokens", 0))
    except Exception:
        log.warning("final frame failed for %s", run_id, exc_info=True)


def run(row: dict, hold: Callable[[dict | None], bool]) -> tuple[str, str | None]:
    """Walk one claimed `cloud_runs` row to its end. `hold` extends the lease and reports whether the row is still
    ours. Returns the row's final status and, when it did not finish, a plain reason."""
    user = {"id": str(row["user_id"])}
    site = row["site"]
    try:
        fetch.assert_public(site)
    except ValueError as e:
        return "blocked", f"Walkthru cannot open this address: {e}."
    run_id = uuid.uuid4().hex
    deadline = time.monotonic() + MAX_SECONDS
    started = False

    def stop(reason: str) -> None:
        if started:
            with provider_usage.scope(run_id=run_id, user_id=user["id"]):
                main._stop_run(run_id, main.StopRequest(reason=reason[:300]), user)

    try:
        with cdp.browser() as tab:
            rules = guard.install(tab)
            tab.send("Page.navigate", url=site)
            tab.wait_loaded(15)
            if rules.blocked:
                return "blocked", f"Walkthru cannot open this address: {rules.blocked}."
            landed = tab.js("location.href")
            home = fetch.origin(landed if fetch.same_site(landed, site) else site)  # example.com may answer as www.example.com
            tab.message({"type": "agent_visibility", "visible": False})  # no one is watching this tab; keep frames clean
            obs = _read(tab, 10)
            grouped = len(db.cloud_runs_in_group(str(row["group_id"]), user["id"])) > 1
            body = main.StartRun(site=site, goal=row["goal"], persona=row["persona"], logged_in=False, max_steps=row["max_steps"],
                                 observation=obs, group_id=row["group_id"] if grouped else None)
            with provider_usage.scope(run_id=run_id, user_id=user["id"]):
                reply = main._start_run(body, user, run_id)
            started = True
            try:  # what the test user saw first; the replay opens on it (web: lib/live.ts landingFrame)
                _frame(tab, f"{run_id}/step-00.jpg")
            except Exception:
                log.warning("landing frame failed for %s", run_id, exc_info=True)
            if not hold({"run_id": run_id}):
                stop("the owner stopped this live test")
                return "stopped", None
            verified, acted, index = bool(reply.get("verified")), set(), 0
            while reply["status"] == "running":
                if time.monotonic() > deadline:
                    stop("the 4-minute time limit ended the test")
                    return "finished", None
                step = reply["action"]
                if reply.get("action_id") in acted:
                    raise RuntimeError("Walkthru returned an earlier action; stopping so nothing is done twice")
                acted.add(reply.get("action_id"))
                index += 1
                paths = f"{run_id}/step-{index:02d}"
                name, note, result, pointer, aim = label(step, obs), None, None, None, None
                if step["action"] not in ("done", "give_up"):
                    opts = {"logged_in": False, "verified": verified, "deadline_ms": int((time.time() + deadline - time.monotonic()) * 1000)}
                    if step["action"] in ("click", "type"):
                        ready = tab.message({"type": "act", "step": step, "opts": opts | {"prepare": True}}) or {}
                        note = ready.get("note")
                        if not note and step["action"] == "click" and verified:
                            probe = tab.message({"type": "act", "step": step, "opts": opts | {"dryRun": True}}) or {}
                            note = NO_SEND if probe.get("confirm") == "send" else None
                        if not note and ready.get("point"):
                            try:
                                _frame(tab, f"{paths}-aim.jpg")
                                pointer, aim = ready["point"], f"{paths}-aim.jpg"
                            except Exception:
                                log.warning("aim frame failed for %s", paths, exc_info=True)
                    if note is None:
                        result = tab.message({"type": "act", "operation_id": str(uuid.uuid4()), "step": step, "opts": opts | {"confirmed": False}}) or {}
                        note = result.get("note")
                    if step["action"] not in ("wait", "scroll"):
                        time.sleep(SETTLE_S)
                        tab.wait_loaded()
                if rules.blocked:
                    stop(f"the page tried to open an address Walkthru does not load ({rules.blocked}), so the test stopped there")
                    return "blocked", f"The site sent the test user to an address Walkthru does not load: {rules.blocked}."
                url = tab.js("location.href")
                if fetch.origin(url) != home:
                    stop(f"the last click led away from the site, to {url}")
                    return "finished", None
                obs = _read(tab, 5 if step["action"] in ("click", "back") else 1.5)
                if result and result.get("executor_result"):
                    obs["executor_result"] = result["executor_result"]
                if note:
                    obs["note"] = note if note.startswith("stale target:") else f"{obs['note']}; {note}" if obs.get("note") else note
                evidence = None
                try:
                    regions = _frame(tab, f"{paths}.jpg")
                    width, height = tab.js("[innerWidth, innerHeight]")
                    evidence = StepEvidence(screenshot_path=f"{paths}.jpg", captured_at=datetime.now(UTC), result_url=obs["url"], width=width,
                                            height=height, note=note[:300] if note else None, regions=regions, aim_path=aim, pointer=pointer, label=name)
                except Exception:
                    log.warning("step frame failed for %s", paths, exc_info=True)
                if not hold(None):
                    stop("the owner stopped this live test")
                    return "stopped", None
                answer = main.Observe(observation=obs, evidence=evidence, action_id=reply.get("action_id"))
                with provider_usage.scope(run_id=run_id, user_id=user["id"]):
                    reply = _decide(lambda answer=answer: main._observe(run_id, answer, user), deadline)
            _last_frame(tab, run_id)
            return "finished", None
    except HTTPException as e:  # the same refusals the extension would get: plan limits, blocked sites, unsafe goals
        if started:
            stop(f"the live test could not continue: {e.detail}")
        return ("blocked" if e.status_code in (403, 422) else "failed"), str(e.detail)[:300]
    except Exception as e:
        log.exception("live run %s failed", row["id"])
        try:
            stop(f"the test browser failed: {e}")
        except Exception:
            log.exception("could not close run %s", run_id)
        busy = any(sign in str(e).lower() for sign in BUSY)
        return "failed", ("Walkthru's free AI models were busy and the test user could not continue. Nothing is wrong with your site. Try again in a minute."
                          if busy else "The test browser stopped unexpectedly. Start the test again.")
