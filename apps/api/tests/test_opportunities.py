"""R-S17 advisory mode: keyword/content direction from the site's own pages, with no demand numbers or invented claims;
recalibrated length/heading advice; the same map in the report, the Keywords chapter prompt and MCP."""

import json
import re

import pytest

from app import mcp_server
from app.agent import fix_prompt
from app.agent.report_chapters import chapters
from app.agent.schema import finding_rule
from app.scans import opportunities, seo, seo_guidance
from tests.conftest import USER

BASE = "https://shop.test"


def page(title=None, desc=None, h1=(), h2=(), body="", robots=None, links=()):
    head = (f"<title>{title}</title>" if title else "") + (f'<meta name="description" content="{desc}">' if desc else "") \
        + (f'<meta name="robots" content="{robots}">' if robots else "")
    heads = "".join(f"<h1>{h}</h1>" for h in h1) + "".join(f"<h2>{h}</h2>" for h in h2)
    anchors = "".join(f'<a href="{href}">link</a>' for href in links)
    return f"<html><head>{head}</head><body>{heads}<p>{body}</p>{anchors}<script>var secret = 'not copy'</script></body></html>"


PAGES = [
    (f"{BASE}/", page("Quickinvoice: invoices for freelancers", "Send invoices in two minutes.", ["Invoices for freelancers"],
                      ["How it works", "Pricing"], "Quickinvoice sends invoices and reminders for freelancers.", links=[f"{BASE}/features"]),
     [f"{BASE}/features"]),
    (f"{BASE}/pricing", page(None, None, ["Simple invoice pricing"], [], "Plans start free. Paid plans add reminders and team seats for agencies."), []),
    (f"{BASE}/features", page("Quickinvoice: invoices for freelancers", "Features.", ["Invoice reminders"], ["Automatic reminders"],
                              "Automatic invoice reminders for overdue freelancers clients."), []),
    (f"{BASE}/also-features", page("Reminders", "More.", ["Invoice reminders"], [], "Invoice reminders again."), []),
    (f"{BASE}/thanks", page("Thanks", "Thanks.", ["Thanks"], [], "Thanks for signing up.", robots="noindex"), []),
]


@pytest.fixture
def advice():
    return opportunities.build(PAGES)


def keys(value):
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in keys(v)}
    if isinstance(value, list):
        return {k for v in value for k in keys(v)}
    return set()


def test_mode_is_explicit_and_no_demand_numbers_exist(advice):
    assert advice["mode"] == "prelaunch_advisory" and advice["demand_data"] == "none"
    assert not keys(advice) & {"volume", "search_volume", "difficulty", "rank", "position", "traffic", "ctr", "clicks", "impressions"}
    assert "No search volume" in advice["basis"] and "Search Console" in advice["measurement"]


def test_proposals_only_reuse_the_pages_own_words(advice):
    pricing = next(p for p in advice["pages"] if p["url"].endswith("/pricing"))
    assert pricing["proposed"]["title"] == "Simple invoice pricing"  # its own h1, verbatim
    assert pricing["proposed"]["description"] == "Plans start free."  # its first sentence, verbatim
    source = " ".join(html for _, html, _ in PAGES).lower()
    for entry in advice["pages"]:
        for text in (entry["proposed"]["title"], entry["proposed"]["description"], *entry["proposed"]["outline"]):
            if text:
                assert set(re.findall(r"[a-z]+", text.lower())) <= set(re.findall(r"[a-z]+", source)), text
    assert "secret" not in json.dumps(advice)  # script text is never read as copy


def test_gaps_priority_links_overlaps_and_noindex(advice):
    urls = [p["url"] for p in advice["pages"]]
    assert urls[0] == f"{BASE}/pricing"  # no title, no description, no sections, nothing links to it
    pricing = advice["pages"][0]
    assert pricing["internal_links"]["inbound_from"] == [] and pricing["internal_links"]["suggested_from"][0] == f"{BASE}/"
    home = next(p for p in advice["pages"] if p["url"] == f"{BASE}/")
    assert home["primary_intent"] == {"text": "Invoices for freelancers", "source": "h1"}
    features = next(p for p in advice["pages"] if p["url"] == f"{BASE}/features")
    assert features["internal_links"]["inbound_from"] == [f"{BASE}/"]
    assert any("shared with 1 other" in g for g in features["gaps"])  # duplicate title with the homepage
    assert features["proposed"]["title"] == "Invoice reminders | Quickinvoice: invoices for freelancers"
    assert advice["overlaps"] == [{"intent": "Invoice reminders", "pages": [f"{BASE}/features", f"{BASE}/also-features"],
                                   "note": advice["overlaps"][0]["note"]}]
    assert "before treating this as competition" in advice["overlaps"][0]["note"]
    assert advice["excluded_noindex"] == [f"{BASE}/thanks"] and f"{BASE}/thanks" not in urls


def test_a_page_with_no_readable_topic_gets_no_invented_intent():
    advice = opportunities.build([(f"{BASE}/", page(body="Short."), [])])
    entry = advice["pages"][0]
    assert entry["primary_intent"] is None and entry["proposed"]["title"] is None
    assert entry["next_action"].startswith("Add a title and one main heading")


def test_length_and_heading_checks_are_advisory_with_registered_sources():
    long_page = page("x" * 80, "y" * 200, ["One", "Two"], [], "body")
    found = {f.title: f for f in seo.check_html(long_page, BASE)}
    for title in ("Page title is too long", "Meta description is too long", "More than one h1 heading"):
        f = found[title]
        assert f.severity == "low" and "Advisory" in f.detail and "60" not in f.fix and "160" not in f.fix
        assert seo_guidance.RULES[finding_rule("seo", title)][0] == "advisory"
    bare = {f.title: f for f in seo.check_html(page(), BASE)}
    assert bare["Missing page title"].severity == "high" and bare["Missing meta description"].severity == "medium"
    assert bare["No h1 heading"].severity == "low"
    emitted = {finding_rule("seo", t) for t in [*found, *bare] if finding_rule("seo", t) in seo_guidance.RULES}
    assert len(emitted) == 6 and all(seo_guidance.RULES[r][1].startswith("https://developers.google.com/") for r in seo_guidance.RULES)


def test_fix_prompt_cites_guidance_and_recipes_drop_strict_limits():
    finding = {"kind": "seo", "severity": "low", "title": "Page title is too long", "detail": "d", "fix": "f", "evidence": "e"}
    run = {"id": "r", "site": BASE, "kind": "scan", "created_at": "2026-10-06"}
    text = fix_prompt.build(run, {"findings": [finding], "top_fixes": []}, {})
    assert "Guidance (advisory, reviewed 2026-10-06)" in text and "title-link" in text
    recipes = json.dumps(fix_prompt._recipes())
    assert "120 to 160" not in recipes and "30 to 60" not in recipes and "Keep one <h1> per page" not in recipes


def report_with_map(advice):
    return {"summary": "s", "top_fixes": [], "findings": [], "opportunities": advice}


def test_keywords_chapter_becomes_advisory_only_with_a_map(advice):
    chapter = {c["key"]: c for c in chapters(report_with_map(advice))}["keywords"]
    assert chapter["status"] == "advisory" and chapter["label"] == "Advisory, no search data"
    assert chapter["summary"].startswith("4 pages mapped")
    assert {c["key"]: c for c in chapters({"findings": []})}["keywords"]["status"] == "not_measured"


def test_keywords_prompt_is_a_content_brief_separate_from_repairs(advice):
    run = {"id": "r", "site": BASE, "kind": "scan", "created_at": "2026-10-06"}
    brief = fix_prompt.build(run, report_with_map(advice), {}, "full", "keywords")
    assert brief.startswith(f"# Content brief for {BASE}") and "Do not add product claims" in brief
    assert 'Proposed title: "Simple invoice pricing"' in brief and "no search demand data" in brief
    assert "Batch" not in brief  # not a technical repair plan
    with pytest.raises(fix_prompt.EmptyChapter):
        fix_prompt.build(run, {"findings": [], "top_fixes": []}, {}, "full", "keywords")


def test_mcp_keywords_section_returns_the_same_map(advice, fake_db, monkeypatch):
    run_id = "e" * 32
    fake_db[run_id] = {"id": run_id, "user_id": USER, "site": BASE, "kind": "scan", "status": "done", "goal": "Instant Scan",
                       "public": False, "report": report_with_map(advice)}
    monkeypatch.setattr(mcp_server.db, "ignored_fingerprints", lambda user, origin: {})
    token = mcp_server._user.set(USER)
    try:
        text = mcp_server.get_report(run_id, section="keywords")
    finally:
        mcp_server._user.reset(token)
    assert "Status: Advisory, no search data." in text
    assert "\n".join(opportunities.lines(advice)) in text


def test_a_real_crawl_carries_the_map_and_skips_private_pages(monkeypatch):
    from app.scans import site
    from tests.test_site_audit import _site

    monkeypatch.setenv("ALLOW_LOCAL_SCANS", "1")
    pages = {"/": '<html lang="en"><head><title>Acme home</title></head><body><h1>Plan trips together</h1><a href="/guide">Guide</a></body></html>',
             "/guide": '<html lang="en"><body><h1>Trip planning guide</h1><p>Plan a shared trip with friends in five steps.</p></body></html>'}
    result = site.audit("http://site.test/", _site(pages, robots="User-agent: *\nAllow: /\n"), verified=False)
    assert result.opportunities["mode"] == "prelaunch_advisory"
    mapped = {p["url"]: p for p in result.opportunities["pages"]}
    assert set(mapped) == {"http://site.test/", "http://site.test/guide"}
    assert mapped["http://site.test/guide"]["proposed"] == {
        "title": "Trip planning guide", "description": "Plan a shared trip with friends in five steps.",
        "outline": ["Trip planning guide"], "basis": mapped["http://site.test/guide"]["proposed"]["basis"]}
