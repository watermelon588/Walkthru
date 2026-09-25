"""SEO and security scans against the fixture sites: hard trips its traps, easy stays clean."""

import os
import sys

import httpx
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "evals"))
from serve import start

from app.scans import accessibility, fetch, performance, security, seo

EASY, HARD = "http://127.0.0.1:8121", "http://127.0.0.1:8122"


@pytest.fixture(scope="module", autouse=True)
def servers():
    os.environ["ALLOW_LOCAL_SCANS"] = "1"
    a, b = start("easy", 8121), start("hard", 8122)
    yield
    a.shutdown()
    b.shutdown()


def titles(findings):
    return {f.title for f in findings}


def test_seo_hard_site_trips_every_seo_trap():
    with fetch.client() as c:
        t = titles(seo.scan(HARD + "/", c))
    assert "Missing meta description" in t  # S1
    assert "More than one h1 heading" in t  # S2
    assert any("images have no alt text" in x for x in t)  # S3
    assert "No canonical link" in t  # S4
    assert "robots.txt blocks all crawlers" in t  # S5
    assert "No sitemap.xml" in t  # S6


def test_seo_easy_site_is_clean():
    with fetch.client() as c:
        t = titles(seo.scan(EASY + "/", c))
    assert not t & {"Missing meta description", "No h1 heading", "More than one h1 heading", "No canonical link", "robots.txt blocks all crawlers", "No sitemap.xml"}
    assert not any("alt text" in x for x in t)


def test_security_hard_site_unverified_vs_verified():
    with fetch.client() as c:
        basic = titles(security.scan(HARD + "/", c, verified=False))
        full = titles(security.scan(HARD + "/", c, verified=True))
    assert "Local development uses plain http" in basic  # local fixture is a dev note, not a production warning
    assert "No Content-Security-Policy" in basic and "Page can be framed" in basic  # X1 headers
    assert any(x.startswith('Cookie "session" is missing') for x in basic)  # X2
    assert "Server header reveals a version" in basic  # X6
    with fetch.client() as c:
        signup = c.get(HARD + "/signup.html").text
    assert "Local form submits over plain http" in titles(security.check_content(signup, HARD + "/signup.html"))  # X5, dev note
    assert not any("publicly readable" in x for x in basic)  # exposed files need verification
    assert "/.env is publicly readable" in full and "/.git/config is publicly readable" in full  # X3
    assert "Stripe live key in a JavaScript bundle" in full  # X4


def test_security_easy_site_headers_and_cookie_pass():
    with fetch.client() as c:
        t = titles(security.scan(EASY + "/", c, verified=True))
    assert not t & {"No Content-Security-Policy", "Page can be framed", "No X-Content-Type-Options", "Server header reveals a version", "Form submits over plain http"}
    assert not any("Cookie" in x or "publicly readable" in x or "JavaScript bundle" in x for x in t)


def test_verify_domain_meta_and_well_known():
    token = security.verification_token("user-1")
    assert token.startswith("wt-") and token != security.verification_token("user-2")

    def handler(req: httpx.Request):
        if req.url.path == "/.well-known/walkthru.txt":
            return httpx.Response(200, text=token + "\n")
        return httpx.Response(200, text="<html><head></head></html>")

    c = httpx.Client(transport=httpx.MockTransport(handler))
    assert security.verify_domain("https://site.test/", token, c)
    assert security.verify_domain("https://site.test/", token, c, html=f'<meta name="walkthru-verification" content="{token}">')
    assert not security.verify_domain("https://site.test/", "wt-other", c, html="<html></html>")


def test_ssrf_guard_blocks_private_hosts(monkeypatch):
    monkeypatch.delenv("ALLOW_LOCAL_SCANS", raising=False)
    with pytest.raises(ValueError):
        fetch.assert_public("http://127.0.0.1:8122/")
    with pytest.raises(ValueError):
        fetch.assert_public("http://169.254.169.254/latest/meta-data")


def test_page_text_strips_scripts():
    assert fetch.page_text("<body><h1>Hi</h1><script>var x=1</script><p>there</p></body>") == "Hi there"


def test_accessibility_scan_reports_static_html_failures():
    html = """<html><body><h1>Account</h1><h3>Details</h3><img src="hero.png"><input type="email"><button></button></body></html>"""
    found = titles(accessibility.scan(html, "https://site.test/account"))
    assert "Page language is not declared" in found
    assert "Heading levels are skipped" in found
    assert "Image is missing text alternative" in found
    assert "2 form controls have no accessible name" in found


def test_accessibility_easy_homepage_is_clean():
    with fetch.client() as c:
        response = c.get(EASY + "/")
    assert accessibility.scan(response.text, str(response.url)) == []


def test_performance_scan_is_explicitly_unavailable_without_key(monkeypatch):
    monkeypatch.delenv("PAGESPEED_API_KEY", raising=False)
    with fetch.client() as c:
        findings, measured = performance.scan("https://site.test", c)
    assert findings == [] and measured is False


def test_performance_scan_maps_pagespeed_evidence(monkeypatch):
    monkeypatch.setenv("PAGESPEED_API_KEY", "test-key")

    def handler(_: httpx.Request):
        return httpx.Response(200, json={"lighthouseResult": {"categories": {"performance": {"score": 0.42}}, "audits": {"largest-contentful-paint": {"displayValue": "4.8 s"}}}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as c:
        findings, measured = performance.scan("https://site.test", c)
    assert measured is True
    assert findings[0].kind == "performance"
    assert findings[0].title == "Mobile performance score 42/100"
    assert findings[0].evidence == "PageSpeed Insights, mobile: 42"
