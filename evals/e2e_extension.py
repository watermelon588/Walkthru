"""DEV/EVAL ONLY: run a real persona test against any site without clicking the extension by hand.

Loads the BUILT extension page script (apps/extension/.output/chrome-mv3/inject.js) into headless Chrome,
then drives the same loop as the side panel: snapshot -> POST /runs -> act -> screenshot -> observe,
using the real API, model, Supabase Storage and a real signed-in test account. Only the side panel UI
itself is not exercised.

    apps/api/.venv/Scripts/python evals/e2e_extension.py https://your-site.vercel.app "Find the projects and a way to get in touch"

Needs the dev stack running (.\\dev) and apps/api/.env. Uses TEST_USER_EMAIL / TEST_USER_PASSWORD
(defaults to the local throwaway account created by apps/api/scripts/test_user.py).
"""

import base64
import itertools
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import UTC, datetime
from urllib.parse import urlsplit

import httpx
from dotenv import load_dotenv
from websockets.sync.client import connect

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT, "apps", "api", ".env"))
API = os.environ.get("WALKTHRU_API", "http://127.0.0.1:8010")
WEB = os.environ.get("WEB_URL", "http://localhost:5173")
SB, PUB = os.environ["SUPABASE_URL"], os.environ["SUPABASE_PUBLISHABLE_KEY"]
INJECT = os.path.join(ROOT, "apps", "extension", ".output", "chrome-mv3", "inject.js")
CHROME = next(
    (
        p
        for p in (
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            shutil.which("google-chrome") or "",
        )
        if p and os.path.exists(p)
    ),
    None,
)
MAX_SCREENSHOTS, SETTLE_S, PORT = 8, 1.2, 9333
FAKE_CHROME = "window.chrome = window.chrome || {}; window.chrome.runtime = { onMessage: { addListener(fn) { window.__wtListener = fn } } };"


class Tab:
    """Minimal Chrome DevTools Protocol client for one page."""

    def __init__(self, ws_url: str):
        self.ws = connect(ws_url, max_size=50_000_000, open_timeout=10)
        self.ids = itertools.count(1)

    def send(self, method: str, **params):
        msg_id = next(self.ids)
        self.ws.send(json.dumps({"id": msg_id, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv(timeout=60))
            if msg.get("id") == msg_id:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})

    def js(self, expression: str):
        r = self.send(
            "Runtime.evaluate",
            expression=expression,
            awaitPromise=True,
            returnByValue=True,
            timeout=45_000,
        )
        if "exceptionDetails" in r:
            raise RuntimeError(
                r["exceptionDetails"]
                .get("exception", {})
                .get("description", r["exceptionDetails"])
            )
        return r["result"].get("value")

    def wait_loaded(self, limit: float = 5):
        """Like the panel's settled(): the page must be fully loaded twice in a row (a navigation may just be starting)."""
        end, streak = time.time() + limit, 0
        while time.time() < end and streak < 2:
            try:
                ready = self.js("document.readyState === 'complete' && !!document.body")
            except RuntimeError:
                ready = False  # navigating: execution context not ready yet
            streak = streak + 1 if ready else 0
            time.sleep(0.25)

    def message(self, msg: dict):
        """Same as chrome.tabs.sendMessage to the injected script, re-injecting after full navigations."""
        if not self.js("!!window.__wtListener"):
            self.js(FAKE_CHROME)
            with open(INJECT, encoding="utf-8") as f:
                self.js(f.read())
        return self.js(
            f"new Promise(resolve => window.__wtListener({json.dumps(msg)}, {{}}, resolve))"
        )


def session() -> tuple[str, str]:
    email = os.environ.get("TEST_USER_EMAIL", "walkthru.tester@example.com")
    password = os.environ.get("TEST_USER_PASSWORD", "Walk-thru-2026-local!")
    r = httpx.post(
        f"{SB}/auth/v1/token?grant_type=password",
        headers={"apikey": PUB},
        json={"email": email, "password": password},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()["access_token"], email


def upload(token: str, path: str, jpeg: bytes) -> None:
    r = httpx.post(
        f"{SB}/storage/v1/object/run-evidence/{path}",
        headers={
            "apikey": PUB,
            "Authorization": f"Bearer {token}",
            "content-type": "image/jpeg",
        },
        content=jpeg,
        timeout=30,
    )
    r.raise_for_status()


def should_capture(
    step: dict, obs: dict, index: int, captured: int
) -> bool:  # mirrors lib/evidence.ts
    if captured >= MAX_SCREENSHOTS:
        return False
    if index == 0 or step["confusion"] >= 2 or obs.get("errors"):
        return True
    return step["action"] in ("click", "type", "back")


def main() -> int:
    site = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8101/"
    goal = sys.argv[2] if len(sys.argv) > 2 else "Sign up for an account"
    persona = os.environ.get("PERSONA", "first_timer")
    max_steps = int(os.environ.get("MAX_STEPS", "10"))
    if not CHROME or not os.path.exists(INJECT):
        print("Needs Chrome or Edge, and a built extension (run .\\dev once).")
        return 1
    token, email = session()
    api = httpx.Client(
        base_url=API, headers={"Authorization": f"Bearer {token}"}, timeout=90
    )
    profile = tempfile.mkdtemp(prefix="walkthru-e2e-")
    chrome = subprocess.Popen(
        [
            CHROME,
            "--headless=new",
            f"--remote-debugging-port={PORT}",
            f"--user-data-dir={profile}",
            "--window-size=1280,900",
            "--no-first-run",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    t0 = time.time()

    def clock() -> str:
        return f"{time.time() - t0:5.1f}s"

    try:
        for _ in range(40):
            try:
                pages = json.load(
                    urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json")
                )
                ws_url = next(
                    p["webSocketDebuggerUrl"] for p in pages if p["type"] == "page"
                )
                break
            except Exception:  # noqa: BLE001 - chrome still starting
                time.sleep(0.25)
        tab = Tab(ws_url)
        tab.send("Page.enable")
        tab.send("Page.navigate", url=site)
        tab.wait_loaded()
        origin = f"{urlsplit(site).scheme}://{urlsplit(site).netloc}"
        print(f"{clock()} signed in as {email}; testing {site} as {persona}: {goal}")

        t = time.time()
        obs = tab.message({"type": "snapshot"})
        timing = {"snapshot": time.time() - t}
        t = time.time()
        reply = api.post(
            "/runs",
            json={
                "site": site,
                "goal": goal,
                "persona": persona,
                "logged_in": False,
                "max_steps": max_steps,
                "observation": obs,
            },
        )
        reply.raise_for_status()
        reply = reply.json()
        timing["api"] = time.time() - t
        run_id, steps, captured = reply["run_id"], [], 0
        verified = bool(reply.get("verified"))
        auto_confirm = os.environ.get("AUTO_CONFIRM") == "1"  # stands in for the owner's confirm dialog
        sent_once = False
        print(f"{clock()} domain verified: {verified}; owner approves sends: {auto_confirm}")
        while reply["status"] == "running":
            step = reply["action"]
            steps.append(step)
            print(
                f"{clock()} step {len(steps)} {step['action']}{' #' + str(step['target_id']) if step.get('target_id') is not None else ''} (confusion {step['confusion']}) [snapshot {timing['snapshot']:.1f}s, api {timing['api']:.1f}s]: {step['thought'][:100]}"
            )
            note = None
            if step["action"] not in ("done", "give_up"):
                base = {"logged_in": False, "verified": verified}
                confirmed, note = False, None
                if step["action"] == "click" and verified:  # mirrors act() in sidepanel/run.ts
                    probe = tab.message({"type": "act", "step": step, "opts": base | {"dryRun": True}})
                    note = probe.get("note")
                    if not note and probe.get("confirm") == "send" and sent_once:
                        note = "a message was already sent in this run; Walkthru never sends twice"
                    elif not note and probe.get("confirm") == "send":
                        confirmed = sent_once = auto_confirm
                        note = None if confirmed else "the site owner declined this submit"
                        print(f"{clock()}   owner asked to approve a real send: {'approved' if confirmed else 'declined'}")
                if note is None:
                    result = tab.message({"type": "act", "step": step, "opts": base | {"confirmed": confirmed}})
                    note = result.get("note") if isinstance(result, dict) else None
                if note:
                    print(f"{clock()}   executor: {note}")
                time.sleep(SETTLE_S)
                tab.wait_loaded()
            url = tab.js("location.href")
            if not url.startswith(origin):
                print(f"{clock()} left the site ({url}); closing run")
                api.post(f"/runs/{run_id}/stop", json={"reason": f"the last click led away from the site, to {url}"}).raise_for_status()
                break
            t = time.time()
            obs = tab.message({"type": "snapshot"})
            timing["snapshot"] = time.time() - t
            if note:
                obs["note"] = f"{obs['note']}; {note}" if obs.get("note") else note
            body = {"observation": obs}
            index = len(steps) - 1
            if should_capture(step, obs, index, captured):
                shot = tab.send("Page.captureScreenshot", format="jpeg", quality=60)
                path = f"{run_id}/step-{index + 1:02d}.jpg"
                upload(token, path, base64.b64decode(shot["data"]))
                size = tab.js("[innerWidth, innerHeight]")
                body["evidence"] = {
                    "screenshot_path": path,
                    "captured_at": datetime.now(UTC).isoformat(),
                    "result_url": obs["url"],
                    "width": size[0],
                    "height": size[1],
                    "note": note,
                }
                captured += 1
            t = time.time()
            r = api.post(f"/runs/{run_id}/observe", json=body)
            r.raise_for_status()
            reply = r.json()
            timing["api"] = time.time() - t
        print(
            f"{clock()} run ended: {reply['status']} after {len(steps)} steps, {captured} screenshots"
        )

        for _ in range(60):  # report is written in the background
            row = api.get(f"/runs/{run_id}").json()
            if row.get("report"):
                rep = row["report"]
                print(
                    f"{clock()} report ready: {len(rep['findings'])} findings, {rep['tokens']} tokens"
                )
                print("  summary:", rep["summary"])
                for f in rep["findings"][:10]:
                    print(f"  - {f['severity']:6} {f['kind']:13} {f['title']}")
                print(f"  open: {WEB}/app/runs/{run_id}")
                return 0
            time.sleep(3)
        print("report not ready after 3 minutes")
        return 1
    finally:
        chrome.kill()
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
