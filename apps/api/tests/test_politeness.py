"""SD-2.3: Walkthru never hammers a site. At most fetch.PER_HOST requests in flight to one host from a process, and at
most main.TARGET_SCANS scans of one host an hour across all users (the shared counter, app/limits.py)."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi import HTTPException

from app import main, mcp_server
from app.scans import fetch


@pytest.fixture
def slow_site(monkeypatch):
    """A local site that takes 0.3 s per page and records the most requests it ever had in flight at once."""
    monkeypatch.setenv("ALLOW_LOCAL_SCANS", "1")
    state = {"now": 0, "most": 0, "served": 0}
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            with lock:
                state["now"] += 1
                state["most"] = max(state["most"], state["now"])
            time.sleep(0.3)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"x" * 1000)
            with lock:
                state["now"] -= 1
                state["served"] += 1

        def log_message(self, *a):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setattr(fetch, "_slots", {})
    yield f"http://127.0.0.1:{server.server_address[1]}/", state
    server.shutdown()


def test_many_scans_of_one_site_at_once_reach_it_two_at_a_time(slow_site):
    url, state = slow_site

    def one(i):
        with fetch.client(timeout=10) as c:  # separate clients, like separate users' scans
            return c.get(f"{url}?page={i}").status_code

    with ThreadPoolExecutor(8) as pool:
        codes = list(pool.map(one, range(8)))
    assert codes == [200] * 8 and state["served"] == 8
    assert state["most"] == fetch.PER_HOST  # never more than two in flight


def test_a_streamed_response_keeps_its_slot_until_it_is_closed(slow_site):
    url, _ = slow_site
    with (fetch.client(timeout=0.5) as c, c.stream("GET", url), c.stream("GET", url),
          pytest.raises(fetch.httpx.PoolTimeout, match="too many requests to this site")):
        c.get(url)  # both slots are held by the open streams
    with fetch.client(timeout=5) as c:
        assert c.get(url).status_code == 200  # closing them gave the slots back


def test_failed_connections_give_their_slot_back(monkeypatch):
    monkeypatch.setenv("ALLOW_LOCAL_SCANS", "1")
    monkeypatch.setattr(fetch, "_slots", {})
    with fetch.client(timeout=0.5) as c:
        for _ in range(fetch.PER_HOST + 2):
            with pytest.raises(fetch.httpx.TransportError):  # refused on Linux, a timeout on Windows
                c.get("http://127.0.0.1:9/")  # nothing listens on the discard port
    slot = fetch._slot("127.0.0.1")
    assert all(slot.acquire(timeout=0.1) for _ in range(fetch.PER_HOST))  # every slot is free again


def test_one_site_is_scanned_at_most_so_often_an_hour_by_everyone(monkeypatch, rate_limits):
    monkeypatch.setattr(main, "TARGET_SCANS", 2)
    monkeypatch.setattr(main.fetch, "assert_public", lambda url: None)
    monkeypatch.setattr(main.fetch, "get", lambda c, url, **k: None)  # the site does not answer; the scan still counts
    for _ in range(2):
        with pytest.raises(ValueError, match="did not respond"):
            main.run_scan("busy.example")
    with pytest.raises(HTTPException) as refused:
        main.run_scan("https://BUSY.example/pricing", user_id="someone-else")  # another user, another page, same host
    assert refused.value.status_code == 429 and "scanned many times" in refused.value.detail
    assert rate_limits["target:busy.example"] == 3
    with pytest.raises(ValueError):
        main.run_scan("quiet.example")  # other sites are not affected


def test_agents_and_comparisons_hear_why(monkeypatch, rate_limits):
    monkeypatch.setattr(main, "TARGET_SCANS", 0)
    token = mcp_server._user.set("u1")
    monkeypatch.setattr(mcp_server.db, "user_scans_today", lambda user: 0)
    try:
        with pytest.raises(mcp_server.ToolError, match="scanned many times"):
            mcp_server._scan("busy.example")
    finally:
        mcp_server._user.reset(token)
    sites = []
    monkeypatch.setattr(main.db, "set_report", lambda run_id, rep, status=None: sites.extend(rep["compare"]))
    monkeypatch.setattr(main.notify, "comparison_ready", lambda *a: None)
    main._compare("r1", "u1", ["https://busy.example", "https://rival.example"])
    assert all("scanned many times" in s["error"] for s in sites)
