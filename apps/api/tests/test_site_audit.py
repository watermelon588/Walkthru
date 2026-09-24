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
        if request.url.path in ("/sitemap.xml", "/llms.txt"):
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


def test_site_audit_asks_for_html_and_reports_when_none_is_served(monkeypatch):
    monkeypatch.setenv("ALLOW_LOCAL_SCANS", "1")
    accepts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        accepts.append(request.headers.get("accept", ""))
        if request.url.path in ("/robots.txt", "/sitemap.xml"):
            return httpx.Response(404, request=request)
        return httpx.Response(200, text="# Docs", headers={"content-type": "text/markdown"}, request=request)

    with httpx.Client(transport=httpx.MockTransport(handler), headers={"Accept": fetch.ACCEPT}) as client:
        result = site.audit("https://md.test/", client, verified=False, max_pages=2, time_limit=2)

    assert accepts[0].startswith("text/html")
    assert result.coverage.pages_scanned == 0
    assert any(f.title == "No HTML pages could be audited" and "text/markdown" in f.detail for f in result.seo)


def test_client_requests_html():
    with fetch.client() as c:
        assert c.headers["accept"].startswith("text/html")


def test_js_only_shell_is_reported_not_judged(monkeypatch):
    monkeypatch.setenv("ALLOW_LOCAL_SCANS", "1")
    shell = '<!doctype html><html lang="en"><head><title>Me</title></head><body><div id="root"></div><script type="module" src="/assets/index.js"></script></body></html>'

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path in ("/robots.txt", "/sitemap.xml"):
            return httpx.Response(404, request=request)
        return httpx.Response(200, text=shell, headers={"content-type": "text/html"}, request=request)

    assert fetch.is_js_shell(shell) and not fetch.is_js_shell("<p>Small but real page with a sentence.</p><script src='a.js'></script>")
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = site.audit("https://spa.test/", client, verified=False, max_pages=2, time_limit=2)
    # Reported once, by GEO: the SEO section only qualifies its page checks.
    assert any(f.title == "Homepage content only appears after JavaScript runs" for f in result.geo.findings)
    assert not any(f.title == "Homepage content only appears after JavaScript runs" for f in result.seo)
    assert result.geo.ai_words == 0


def test_js_shell_findings_say_they_describe_pre_javascript_html(monkeypatch):
    monkeypatch.setenv("ALLOW_LOCAL_SCANS", "1")
    shell = '<!doctype html><html lang="en"><head><title>A long enough page title</title></head><body><div id="root"></div><script type="module" src="/a.js"></script></body></html>'

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path in ("/robots.txt", "/sitemap.xml"):
            return httpx.Response(404, request=request)
        return httpx.Response(200, text=shell, headers={"content-type": "text/html"}, request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = site.audit("https://spa.test/", client, verified=False, max_pages=1, time_limit=2)
    h1 = next(f for f in result.seo if f.title == "No h1 heading")
    assert h1.detail.startswith("In the HTML sent before JavaScript runs:") and "screen readers" not in h1.detail


def _site(handler_pages, robots="User-agent: *\nDisallow: /\n"):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=robots, request=request)
        if request.url.path in handler_pages:
            return httpx.Response(200, text=handler_pages[request.url.path], headers={"content-type": "text/html"}, request=request)
        return httpx.Response(404, request=request)
    return httpx.Client(transport=httpx.MockTransport(handler))


SIGNUP_FORM = '<html><body><h1>Sign up</h1><form action="http://site.test/api/signup"><input name="email"></form></body></html>'


def test_pages_the_test_user_visited_are_audited_on_verified_sites(monkeypatch):
    monkeypatch.setenv("ALLOW_LOCAL_SCANS", "1")
    pages = {"/": "<html><body><h1>Home</h1></body></html>", "/signup.html": SIGNUP_FORM}
    with _site(pages) as c:
        verified = site.audit("https://site.test/", c, verified=True, visited=["https://site.test/signup.html", "https://elsewhere.test/x"])
    assert "https://site.test/signup.html" in verified.coverage.urls
    assert any(f.title == "Form submits over plain http" for f in verified.security)
    with _site(pages) as c:
        unverified = site.audit("https://site.test/", c, verified=False, visited=["https://site.test/signup.html"])
    assert "https://site.test/signup.html" not in unverified.coverage.urls  # robots.txt still wins for sites the user has not verified


def test_signup_link_only_in_the_footer_is_reported(monkeypatch):
    monkeypatch.setenv("ALLOW_LOCAL_SCANS", "1")
    hidden = '<html><body><header><a href="/login">Log in</a></header><main><h1>Hi</h1></main><footer><a href="/signup">Create account</a></footer></body></html>'
    visible = '<html><body><header><a href="/signup">Sign up</a></header><footer><a href="/signup">Create account</a></footer></body></html>'
    with _site({"/": hidden}, robots="") as c:
        found = site.audit("https://site.test/", c, verified=False)
    assert any(f.title == "Sign-up is hidden in the footer" and f.kind == "ux" for f in found.seo)
    with _site({"/": visible}, robots="") as c:
        fine = site.audit("https://site.test/", c, verified=False)
    assert not any("Sign-up is hidden" in f.title for f in fine.seo)


def _big_site(n: int) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path in ("/robots.txt", "/sitemap.xml", "/llms.txt"):
            return httpx.Response(404, request=request)
        i = 0 if path == "/" else int(path.strip("/p"))
        links = "".join(f'<a href="/p{j}">{j}</a>' for j in range(i + 1, min(i + 4, n)))
        html = f"<html lang='en'><head><title>Page number {i} of the site</title></head><body><h1>Page {i}</h1>{links}</body></html>"
        return httpx.Response(200, text=html, headers={"content-type": "text/html"}, request=request)
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_paid_reports_audit_50_pages_and_free_ones_10(monkeypatch):
    monkeypatch.setenv("ALLOW_LOCAL_SCANS", "1")
    with _big_site(60) as client:
        paid = site.audit("https://site.test/", client, verified=False, max_pages=site.PAID_MAX_PAGES, time_limit=site.PAID_TIME_LIMIT)
        free = site.audit("https://site.test/", client, verified=False)
    assert (paid.coverage.pages_scanned, paid.coverage.page_limit, paid.coverage.truncated) == (50, 50, True)
    assert (free.coverage.pages_scanned, free.coverage.page_limit) == (10, 10)


def test_report_picks_the_crawl_size_from_the_plan(monkeypatch):
    from app.agent import report

    seen = []
    monkeypatch.setattr(report.fetch, "assert_public", lambda url: None)
    monkeypatch.setattr(report.email, "check", lambda *a, **k: ([], None))
    monkeypatch.setattr(report.site, "audit", lambda *a, **k: seen.append((k["max_pages"], k["time_limit"])) or (_ for _ in ()).throw(RuntimeError("stop")))
    report.site_scan({"site": "https://site.test/", "paid": True})
    report.site_scan({"site": "https://site.test/", "paid": False})
    assert seen == [(50, 60.0), (10, 20.0)]


def test_report_schema_accepts_the_largest_paid_audit():
    from app.agent.schema import SiteAuditSummary

    most = site.PAID_MAX_PAGES + site.MAX_VISITED
    SiteAuditSummary(pages_scanned=most, page_limit=site.MAX_MAX_PAGES, duration_ms=60000, truncated=True,
                     urls=[f"https://site.test/p{i}" for i in range(most)])


def test_crawl_reports_broken_blocked_duplicate_and_orphan_pages(monkeypatch):
    """OpenSEO-style whole-crawl checks: nothing that failed is silently skipped."""
    monkeypatch.setenv("ALLOW_LOCAL_SCANS", "1")
    words = " ".join(["useful"] * 150)
    page = lambda title, body, links="": f"<html lang='en'><head><title>{title}</title><meta name='description' content='Short'></head><body><h1>{title}</h1><p>{body}</p>{links}</body></html>"
    routes = {
        "/": (200, page("Home page of the site", words, "<a href='/a'>A</a><a href='/b'>B</a><a href='/gone'>x</a><a href='/boom'>y</a><a href='/walled'>z</a><a href='/old'>o</a>")),
        "/a": (200, page("Same title for two", words + " a", "<a href='/'>home</a>")),
        "/b": (200, page("Same title for two", " ".join(["short"] * 30), "<a href='/'>home</a>")),
        "/gone": (404, "not here"), "/boom": (500, "error"), "/walled": (403, "denied"),
        "/final": (200, page("Final page after hops", words + " f", "<a href='/'>home</a>")),
        "/lonely": (200, page("Lonely", words)),
        "/sitemap.xml": (200, "<urlset><url><loc>https://site.test/lonely</loc></url></urlset>"),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/old":
            return httpx.Response(301, headers={"location": "/mid"}, request=request)
        if path == "/mid":
            return httpx.Response(301, headers={"location": "/final"}, request=request)
        status, body = routes.get(path, (404, ""))
        return httpx.Response(status, text=body, headers={"content-type": "text/html"}, request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = site.audit("https://site.test/", client, verified=False, max_pages=10, time_limit=5)
    titles = {f.title: f for f in result.seo}
    assert "https://site.test/gone (404), linked from https://site.test/" in titles["Broken internal link"].evidence
    assert "Server error on a linked page" in titles and "Crawler was blocked, so not checked" in titles
    assert "Duplicate title" in titles and "Thin content" in titles and "Meta description is too short" in titles
    assert "Redirect chain" in titles and titles["Orphan page"].evidence == "https://site.test/lonely"
