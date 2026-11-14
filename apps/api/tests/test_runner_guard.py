"""The server's browser may only reach public web addresses (docs/in-app-runner-plan.md, T3)."""

import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from app.runner import cdp, guard

PAGE = b"<title>local page</title><h1>hello</h1><img src='/pixel.png'>"


class _Tab:  # refusal() needs no browser
    pass


@pytest.fixture
def public_dns(monkeypatch):
    monkeypatch.delenv("ALLOW_LOCAL_SCANS", raising=False)
    answers = {"example.com": "93.184.216.34", "rebind.test": "10.0.0.5", "meta.test": "169.254.169.254"}

    def lookup(host, port, **_):
        if host in answers:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (answers[host], port))]
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (host, port))]  # literal addresses resolve to themselves

    monkeypatch.setattr(socket, "getaddrinfo", lookup)


@pytest.mark.parametrize("url", ["https://example.com/pricing", "data:text/html,hi", "blob:https://example.com/1", "about:blank"])
def test_public_and_in_browser_urls_pass(public_dns, url):
    assert guard.Guard(_Tab()).refusal(url) is None


@pytest.mark.parametrize("url", [
    "http://127.0.0.1:8010/health", "http://localhost/", "http://[::1]/", "http://10.0.0.5/admin", "http://192.168.1.1/",
    "http://169.254.169.254/latest/meta-data/", "http://[::ffff:127.0.0.1]/", "http://rebind.test/", "https://meta.test/",
    "file:///etc/passwd", "chrome://settings", "ftp://example.com/x", "javascript:alert(1)",
])
def test_private_addresses_and_other_schemes_are_refused(public_dns, url):
    assert guard.Guard(_Tab()).refusal(url)


def test_a_host_is_looked_up_once(public_dns, monkeypatch):
    calls = []
    real = socket.getaddrinfo
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: calls.append(a) or real(*a, **k))
    g = guard.Guard(_Tab())
    g.refusal("https://example.com/a")
    g.refusal("https://example.com/b")
    assert len(calls) == 1


@pytest.fixture
def local_site():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("content-type", "text/html")
            self.end_headers()
            self.wfile.write(PAGE)

        def log_message(self, *_):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}/"
    server.shutdown()


needs_chrome = pytest.mark.skipif(not cdp.chrome_path(), reason="no Chrome on this machine")


@needs_chrome
def test_the_browser_cannot_open_a_local_address(local_site, monkeypatch):
    monkeypatch.delenv("ALLOW_LOCAL_SCANS", raising=False)
    with cdp.browser() as tab:
        g = guard.install(tab)
        tab.send("Page.navigate", url=local_site)
        tab.wait_loaded(3)
        assert g.blocked == "site resolves to a private address"
        assert "hello" not in (tab.js("document.body ? document.body.innerText : ''") or "")


@needs_chrome
def test_fixtures_load_when_local_scans_are_allowed_and_the_bot_is_named(local_site, monkeypatch):
    monkeypatch.setenv("ALLOW_LOCAL_SCANS", "1")
    with cdp.browser() as tab:
        g = guard.install(tab)
        tab.send("Page.navigate", url=local_site)
        tab.wait_loaded(5)
        assert g.blocked is None
        assert tab.js("document.title") == "local page"
        assert "WalkthruBot/" in tab.js("navigator.userAgent") and "Headless" not in tab.js("navigator.userAgent")
