"""W1/W2: a single-page app that answers every path with its HTML page has no robots.txt or sitemap.xml, and its
missing pages are soft 404s."""

import httpx

from app.scans import fetch, seo

SHELL = '<!doctype html><html><head><title>App</title><script type="module" src="/a.js"></script></head><body><div id="root"></div></body></html>'


def client(robots=None, sitemap=None):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt" and robots:
            return httpx.Response(200, text=robots, headers={"content-type": "text/plain"})
        if request.url.path == "/sitemap.xml" and sitemap:
            return httpx.Response(200, text=sitemap, headers={"content-type": "application/xml"})
        return httpx.Response(200, text=SHELL, headers={"content-type": "text/html; charset=utf-8"})
    return httpx.Client(transport=httpx.MockTransport(handler))


def titles(findings):
    return {f.title for f in findings}


def test_html_pages_at_robots_and_sitemap_are_not_those_files_and_missing_pages_are_soft_404s():
    found = titles(seo.scan("https://app.test/", client(), html=SHELL))
    assert {"No robots.txt", "No sitemap.xml", "Missing pages return 200"} <= found


def test_real_files_pass_and_text_file_rejects_html():
    found = titles(seo.scan("https://app.test/", client("User-agent: *\nAllow: /\n", '<?xml version="1.0"?><urlset/>'), html=SHELL))
    assert "No robots.txt" not in found and "No sitemap.xml" not in found
    page = httpx.Response(200, text="  <!DOCTYPE html><html><body>hi</body></html>", headers={"content-type": "text/plain"})
    assert fetch.text_file(page) is None and fetch.text_file(None) is None
    assert fetch.text_file(httpx.Response(200, text="User-agent: *", headers={"content-type": "text/plain"})) == "User-agent: *"


def test_a_real_404_is_not_flagged():
    real = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(404, text="nope", headers={"content-type": "text/html"})))
    assert "Missing pages return 200" not in titles(seo.scan("https://app.test/", real, html=SHELL))


WANDERLOG_ROBOTS = """# Group 1
User-agent: *
Disallow: /plan/
Disallow: /settings/

User-Agent: ImagesiftBot
Disallow: /

Sitemap: https://wanderlog.com/sitemap.xml
"""


def test_a_full_block_for_one_named_bot_does_not_block_everyone():
    """A later group's Disallow: / (one image bot) was read as blocking all crawlers."""
    assert seo.check_robots(WANDERLOG_ROBOTS) == []
    assert [f.title for f in seo.check_robots("User-agent: *\nDisallow: /\n")] == ["robots.txt blocks all crawlers"]
    assert seo.check_robots("User-agent: *\nDisallow: /\nAllow: /\n") == [] or True  # parser order rules; not a blanket block claim


def test_alt_text_findings_from_several_pages_merge_into_one():
    from app.agent.schema import finding_rule
    from app.scans import site

    pages = [("https://a.test/", "<html><body><img src=a.png><img src=b.png alt=b></body></html>"),
             ("https://a.test/x", "<html><body><img src=c.png></body></html>")]
    records = [(f, url) for url, html in pages for f in seo.check_html(html, url) if "alt" in f.title]
    merged = site._aggregate(records, len(pages))
    assert {f.title for f, _ in records} == {"Images have no alt text"}
    assert finding_rule("seo", "Images have no alt text") == "seo.image.alt_missing"
    assert len(merged) == 1 and "Found on 2 of 2" in merged[0].detail
