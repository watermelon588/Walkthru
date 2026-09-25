"""Crafted SEO depth traps, with the same bounded fetch path as a site audit."""

import time
from urllib.robotparser import RobotFileParser

import httpx

from app.scans import seo_depth, site

BASE = "https://site.test"


def page(path: str, body: str) -> tuple[str, httpx.Response]:
    url = BASE + path
    return url, httpx.Response(200, text=body, request=httpx.Request("GET", url), headers={"content-type": "text/html"})


def run(pages, handler=None, *, truncated=False):
    rules = RobotFileParser()
    rules.parse(["User-agent: *", "Allow: /"])
    transport = httpx.MockTransport(handler or (lambda request: httpx.Response(404)))
    with httpx.Client(transport=transport) as client:
        return seo_depth.audit(pages, BASE, client, rules, truncated=truncated, deadline=time.monotonic() + 5)


def titles(records):
    return {finding.title for finding, _ in records}


def test_required_rich_result_fields_only_for_types_that_have_them():
    html = """<html><head><script type="application/ld+json">{"@graph":[
    {"@type":"Product","name":"Widget"},
    {"@type":"SoftwareApplication","name":"App","offers":{"price":0}},
    {"@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1}]},
    {"@type":"Article","headline":"Guide"}]}</script></head><body></body></html>"""
    names = titles(run([page("/", html)]))
    assert "Product rich-result fields are incomplete" in names
    assert "SoftwareApplication rich-result fields are incomplete" in names
    assert "BreadcrumbList rich-result fields are incomplete" in names
    assert not any("Article" in name for name in names)


def test_hreflang_requires_absolute_valid_and_reciprocal_targets():
    en = page("/en", """<link rel="alternate" hreflang="en" href="https://site.test/en">
    <link rel="alternate" hreflang="fr" href="https://site.test/fr">
    <link rel="alternate" hreflang="bad_@@" href="/x">""")
    fr = page("/fr", '<link rel="alternate" hreflang="fr" href="https://site.test/fr">')
    names = titles(run([en, fr]))
    assert "Invalid hreflang annotation" in names
    assert "Hreflang return link is missing" in names
    assert "Hreflang omits its own page" not in names


def test_content_link_lazy_image_and_button_only_pagination():
    html = """<html><body><main><a href="/docs">Click here</a>
    <img src="/hero.jpg" alt="Hero" loading="lazy">
    <nav aria-label="Pagination"><button>Next</button></nav></main></body></html>"""
    names = titles(run([page("/", html)]))
    assert {"Generic internal link text", "Lazy images lack intrinsic dimensions", "Pagination has no crawlable next link"} <= names


def test_pagination_metadata_needs_visible_link_and_each_page_its_own_canonical():
    first = page("/articles", '<link rel="next" href="https://site.test/articles?page=2"><main><p>Part one</p></main>')
    second = page("/articles?page=2", '<link rel="canonical" href="https://site.test/articles"><main><p>Part two</p></main>')
    names = titles(run([first, second]))
    assert "Pagination next page lacks a crawlable link" in names
    assert "Paginated page canonicalizes elsewhere" in names


def test_image_head_size_and_format_are_bounded_and_same_origin(monkeypatch):
    monkeypatch.setattr(seo_depth.fetch, "assert_public", lambda url: None)
    seen = []

    def handle(request):
        seen.append((request.method, str(request.url)))
        return httpx.Response(200, headers={"content-length": "600000", "content-type": "image/jpeg"})

    records = run([page("/", '<main><img src="/large.jpg" width="1200" height="800"><img src="https://other.test/never.jpg"></main>')], handle)
    assert {"Large content image", "Large image uses an older format"} <= titles(records)
    assert seen == [("HEAD", "https://site.test/large.jpg")]


def test_canonical_to_audited_noindex_or_redirect_is_reported(monkeypatch):
    source = page("/article", '<link rel="canonical" href="https://site.test/target">')
    noindex = page("/target", '<meta name="robots" content="noindex">')
    monkeypatch.setattr(seo_depth.fetch, "assert_public", lambda url: None)  # independent of ALLOW_LOCAL_SCANS set by other tests
    serve_noindex = lambda request: httpx.Response(200, text='<meta name="robots" content="noindex">')
    assert "Canonical points at a noindex page" in titles(run([source, noindex], serve_noindex))

    def handle(request):
        if request.url.path == "/target":
            return httpx.Response(301, headers={"location": "/final"})
        return httpx.Response(200, text="<html>Final page</html>")

    assert "Canonical points at a redirect" in titles(run([source, page("/target", "<html></html>")], handle))
    arrived_via_other_url = page("/target", "<html>Target is direct</html>")
    arrived_via_other_url[1].extensions["walkthru_hops"] = 1
    assert "Canonical points at a redirect" not in titles(run([source, arrived_via_other_url], lambda request: httpx.Response(200, text="<html>Target is direct</html>")))


def test_one_inbound_link_only_when_crawl_is_complete():
    home = page("/", '<a href="/guide">Guide</a><a href="/about">About</a>' + "".join(f'<a href="/extra-{n}">Extra {n}</a>' for n in range(7)))
    guide = page("/guide", '<a href="/about">About</a>')
    about = page("/about", "<main>About us</main>")
    pages = [home, guide, about] + [page(f"/extra-{n}", "<main>Extra</main>") for n in range(7)]
    names = titles(run(pages))
    assert "Page has one internal link in" in names
    assert "Page has one internal link in" not in titles(run(pages, truncated=True))


def test_clean_fixture_avoids_new_findings():
    html = """<html lang="en"><head>
    <link rel="canonical" href="https://site.test/">
    <script type="application/ld+json">{"@type":"Article","headline":"Guide"}</script>
    </head><body><main><a href="/docs">Read the docs</a>
    <img src="/diagram.svg" width="300" height="200" alt="Diagram"></main></body></html>"""
    assert run([page("/", html)]) == []


def test_easy_fixture_has_no_depth_false_alarms():
    from pathlib import Path

    fixture = Path(__file__).resolve().parents[3] / "evals" / "fixtures" / "easy" / "index.html"
    html = fixture.read_text(encoding="utf-8")
    assert seo_depth._page(BASE + "/", html)[0] == []


def test_crawler_keeps_bounded_pagination_urls_but_drops_tracking_queries():
    root = BASE + "/articles"
    assert site._normal_url("?page=2&utm_source=mail", root, BASE) == root + "?page=2"
    assert site._normal_url("?page=100000", root, BASE) == root
    assert site._normal_url("?utm_source=mail", root, BASE) == root
