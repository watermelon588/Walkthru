"""Headless Chromium over the DevTools Protocol, for cloud runs and the eval driver.

One throwaway profile per browser, killed and deleted on exit. A reader thread delivers command replies and
hands protocol events to `on_event`, so a handler (the network guard) can answer while the caller is waiting.
"""

import contextlib
import itertools
import json
import logging
import os
import queue
import shutil
import signal
import subprocess
import tempfile
import threading
import time
import urllib.request
from collections.abc import Callable, Iterator
from contextlib import contextmanager

from websockets.exceptions import ConnectionClosed
from websockets.sync.client import connect

log = logging.getLogger("walkthru.runner")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
INJECT = os.environ.get("INJECT_JS") or os.path.join(ROOT, "apps", "extension", ".output", "chrome-mv3", "inject.js")
# The page script expects chrome.runtime.onMessage; a plain page has none, so the listener is kept on window.
FAKE_CHROME = "window.chrome = window.chrome || {}; window.chrome.runtime = { onMessage: { addListener(fn) { window.__wtListener = fn } } };"
FLAGS = (
    "--headless=new", "--no-first-run", "--no-default-browser-check", "--disable-extensions", "--disable-sync",
    "--disable-background-networking", "--disable-component-update", "--disable-default-apps", "--mute-audio",
    "--disable-dev-shm-usage", "--disk-cache-size=33554432", "--window-size=1280,900", "--remote-debugging-port=0",
    # Memory: measured 2026-11-12 on a WebGL-heavy site, these cut the browser's private memory by about 60 percent.
    # ponytail: one renderer and no site isolation is fine for one throwaway page; revisit if a run ever opens tabs.
    "--disable-gpu", "--renderer-process-limit=1", "--js-flags=--max-old-space-size=256",
    "--disable-features=IsolateOrigins,site-per-process,Translate,MediaRouter,OptimizationHints",
)


def chrome_path() -> str | None:
    candidates = (
        os.environ.get("CHROME_PATH") or "",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        shutil.which("chrome-headless-shell") or "", shutil.which("google-chrome") or "", shutil.which("chromium") or "",
    )
    return next((p for p in candidates if p and os.path.exists(p)), None)


class Tab:
    """Minimal DevTools client for one page."""

    def __init__(self, ws_url: str, inject: str = INJECT):
        self.ws = connect(ws_url, max_size=50_000_000, open_timeout=10)
        self.inject = inject
        self.ids = itertools.count(1)
        self.waiting: dict[int, queue.Queue] = {}
        self.on_event: Callable[[str, dict], None] | None = None
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self) -> None:
        try:
            for raw in self.ws:
                msg = json.loads(raw)
                if "id" in msg:
                    box = self.waiting.pop(msg["id"], None)
                    if box:
                        box.put(msg)
                elif self.on_event:
                    try:
                        self.on_event(msg.get("method", ""), msg.get("params", {}))
                    except Exception:
                        log.exception("browser event handler failed")
        except ConnectionClosed:
            pass
        for box in list(self.waiting.values()):  # the browser went away: wake every caller
            box.put({"error": {"message": "browser closed"}})

    def post(self, method: str, **params) -> int:
        """Send without waiting. Safe from the event handler, which runs on the reader thread."""
        msg_id = next(self.ids)
        self.ws.send(json.dumps({"id": msg_id, "method": method, "params": params}))
        return msg_id

    def send(self, method: str, **params):
        msg_id = next(self.ids)
        box = self.waiting[msg_id] = queue.Queue(1)
        self.ws.send(json.dumps({"id": msg_id, "method": method, "params": params}))
        try:
            msg = box.get(timeout=60)
        except queue.Empty:
            self.waiting.pop(msg_id, None)
            raise RuntimeError(f"{method}: no reply from the browser") from None
        if "error" in msg:
            raise RuntimeError(f"{method}: {msg['error']}")
        return msg.get("result", {})

    def js(self, expression: str):
        r = self.send("Runtime.evaluate", expression=expression, awaitPromise=True, returnByValue=True, timeout=45_000)
        if "exceptionDetails" in r:
            raise RuntimeError(r["exceptionDetails"].get("exception", {}).get("description", r["exceptionDetails"]))
        return r["result"].get("value")

    def wait_loaded(self, limit: float = 5) -> None:
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
            with open(self.inject, encoding="utf-8") as f:
                self.js(f.read())
        return self.js(f"new Promise(resolve => window.__wtListener({json.dumps(msg)}, {{}}, resolve))")

    def screenshot(self, quality: int = 60) -> str:
        """Base64 JPEG of the viewport."""
        return self.send("Page.captureScreenshot", format="jpeg", quality=quality)["data"]


def read(tab: Tab, limit: float) -> dict:
    """Snapshot the page once it has stopped changing. A loaded document is not a rendered one: many sites draw
    their content, or swap in a theme, a moment after load, and a test user who reads too early sees an empty page
    and gives up. Waits until two snapshots in a row agree on the address and the number of controls and, for the
    first read, until there is at least one control. Gives up waiting after `limit` seconds and returns what is there."""
    end, last = time.monotonic() + limit, None
    while True:
        obs = tab.message({"type": "snapshot"})
        shape = (obs.get("url"), len(obs.get("elements") or []), len(obs.get("text") or "") // 200)
        if (shape == last and shape[1] > 0) or time.monotonic() >= end:
            return obs
        last = shape
        time.sleep(0.6)


def _kill(proc: subprocess.Popen) -> None:
    """Chrome is a tree of processes (renderers, GPU, network). Kill all of them, never leave one behind."""
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True, timeout=15, check=False)
        else:
            os.killpg(proc.pid, signal.SIGKILL)
    except (OSError, subprocess.SubprocessError):
        proc.kill()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass


@contextmanager
def browser(extra_flags: tuple[str, ...] = ()) -> Iterator[Tab]:
    """A fresh headless browser with one blank page. The process and its profile are gone when the block ends."""
    chrome = chrome_path()
    if not chrome:
        raise RuntimeError("No Chrome found. Set CHROME_PATH.")
    profile = tempfile.mkdtemp(prefix="walkthru-run-")
    proc = subprocess.Popen([chrome, *FLAGS, *extra_flags, f"--user-data-dir={profile}", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=os.name != "nt")
    try:
        port_file, ws_url = os.path.join(profile, "DevToolsActivePort"), None
        for _ in range(60):  # Chrome writes the port it picked here once it is listening
            if os.path.exists(port_file):
                with open(port_file, encoding="utf-8") as f:
                    port = f.readline().strip()
                with contextlib.suppress(Exception):  # still starting
                    pages = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=2))
                    ws_url = next(p["webSocketDebuggerUrl"] for p in pages if p["type"] == "page")
                    break
            time.sleep(0.25)
        if not ws_url:
            raise RuntimeError("Chrome did not start")
        tab = Tab(ws_url)
        tab.pid, tab.profile = proc.pid, profile
        tab.send("Page.enable")
        try:
            yield tab
        finally:
            with contextlib.suppress(Exception):
                tab.ws.close()
    finally:
        _kill(proc)
        shutil.rmtree(profile, ignore_errors=True)
