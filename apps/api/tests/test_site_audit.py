"""Bounded multi-page launch audit behavior and SSRF regressions."""

import socket

import httpx

from app.scans import fetch, site


def test_site_audit_respects_robots_origin_cap_and_aggregates(monkeypatch):
    monkeypatch.setenv("ALLOW_LOCAL_SCANS", "1")
    requested: list[str] = []

    pages = {
        "/": """<html lang="en"><head><title>Useful home page title</title></head><body>
            <h1>Home</h1><a href="/about">About</a><a href="/private">Private</a>
            <a href="https://elsewhere.test/out">Elsewhere</a></body></html>""",
        "/about": """<html lang="en"><head><title>Useful about page title</title></head><body>
            <h1>About</h1><a href="/contact#team">Contact</a></body></html>""",
        "/contact": """<html lang="en"><head><title>Useful contact page title</title></head><body><h1>Contact</h1></body></html>""",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: WalkthruBot\nDisallow: /private\n", request=request)
        if request.url.path == "/sitemap.xml":
            return httpx.Response(404, request=request)
        if request.url.path in pages:
            return httpx.Response(200, text=pages[request.url.path], headers={"content-type": "text/html"}, request=request)
        raise AssertionError(f"unexpected request: {request.url}")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = site.audit("https://site.test/", client, verified=False, max_pages=2, time_limit=2)

    assert result.coverage.pages_scanned == 2
    assert result.coverage.page_limit == 2
    assert result.coverage.truncated is True
    assert result.coverage.urls == ["https://site.test/", "https://site.test/about"]
    assert not any("/private" in url for url in requested)
    assert not any("elsewhere.test" in url for url in requested)
    assert not any(p in url for url in requested for p in ("/.env", "/.git", "/.DS_Store", "wp-config")), "unverified audit must not probe exposed files"

    missing_description = next(finding for finding in result.seo if finding.title == "Missing meta description")
    assert "2 audited pages" in missing_description.detail
    assert missing_description.evidence and "https://site.test/about" in missing_description.evidence
    assert sum(finding.title == "Missing meta description" for finding in result.seo) == 1


def test_guarded_fetch_rejects_redirect_to_private_address(monkeypatch):
    monkeypatch.delenv("ALLOW_LOCAL_SCANS", raising=False)
    requested: list[str] = []

    def addresses(host: str, *_args, **_kwargs):
        address = "93.184.216.34" if host == "public.test" else "169.254.169.254"
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 0))]

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return httpx.Response(302, headers={"location": "http://169.254.169.254/latest/meta-data"}, request=request)

    monkeypatch.setattr(fetch.socket, "getaddrinfo", addresses)
    with httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False) as client:
        response = fetch.get(client, "https://public.test/")

    assert response is None
    assert requested == ["https://public.test/"]
