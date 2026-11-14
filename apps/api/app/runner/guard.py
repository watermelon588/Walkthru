"""Network rules for the server's browser: it may only talk to public web addresses.

Every request the page makes (documents, scripts, images, fetch calls, redirects) is paused and checked before it
leaves. The same address rules as the scanners apply (app/scans/fetch.py). The address a reply actually came from
is checked again, which catches a name that changed its answer between our lookup and Chrome's.

ponytail: WebSocket handshakes are not paused by the Fetch domain, and the second check happens after the request
was sent. The VM's firewall should also drop private and metadata ranges for the runner user (deployment guide).
"""

import os
import threading
from urllib.parse import urlsplit

from app.runner.cdp import Tab
from app.scans import fetch

PASS = ("data:", "blob:", "about:")  # never leave the browser
BOT = f" WalkthruBot/1.0 (+{os.environ.get('WEB_URL', 'https://trywalkthru.com').rstrip('/')}/bot)"


class Guard:
    def __init__(self, tab: Tab):
        self.tab = tab
        self.blocked: str | None = None  # why the page itself was refused; a refused image or script only fails that request
        self.hosts: dict[tuple[str, int], str | None] = {}
        self.lock = threading.Lock()

    def refusal(self, url: str) -> str | None:
        """None when the request may go out, else the reason."""
        if url.startswith(PASS):
            return None
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            return "only http and https pages can be tested"
        key = (parts.hostname, parts.port or (443 if parts.scheme == "https" else 80))
        with self.lock:
            if key not in self.hosts:
                try:
                    fetch.public_addresses(*key)
                    self.hosts[key] = None
                except ValueError as e:
                    self.hosts[key] = str(e)
            return self.hosts[key]

    def on_event(self, method: str, params: dict) -> None:
        if method == "Fetch.requestPaused":
            reason = self.refusal(params["request"]["url"])
            if reason is None:
                self.tab.post("Fetch.continueRequest", requestId=params["requestId"])
                return
            if params.get("resourceType") == "Document" and not self.blocked:
                self.blocked = reason
            self.tab.post("Fetch.failRequest", requestId=params["requestId"], errorReason="BlockedByClient")
        elif method == "Network.responseReceived":
            address = params["response"].get("remoteIPAddress", "").strip("[]")
            if address and os.environ.get("ALLOW_LOCAL_SCANS") != "1" and not fetch.is_public_ip(address) and not self.blocked:
                self.blocked = "site resolves to a private address"


def install(tab: Tab) -> Guard:
    """Call before the first navigation. Also denies downloads and names Walkthru in the user agent."""
    guard = Guard(tab)
    tab.on_event = guard.on_event
    tab.send("Fetch.enable", patterns=[{"urlPattern": "*"}])
    tab.send("Network.enable")
    tab.send("Browser.setDownloadBehavior", behavior="deny")
    agent = tab.send("Browser.getVersion")["userAgent"].replace("HeadlessChrome", "Chrome")
    tab.send("Network.setUserAgentOverride", userAgent=agent + BOT)
    return guard
