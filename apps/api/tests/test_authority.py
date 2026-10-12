"""R-S17a: the authority plan covers twelve link tactics from the audited pages' own copy. Nothing is invented,
exchanges are never a shortcut, backlinks stay distinct from GEO readiness and AI citations, and web, prompt and MCP
read the same plan. No fetch, model call or outreach."""

import pytest

from app import mcp_server
from app.agent import fix_prompt
from app.agent.report_chapters import chapters
from app.agent.schema import Report
from app.scans import authority, opportunities
from tests.conftest import USER
from tests.test_opportunities import BASE, PAGES, page

GUIDE = (f"{BASE}/guide", page("Invoicing guide", "How to invoice.", ["How to invoice clients"], ["Set your rates", "Write the invoice", "Chase late payment"],
                               "A step by step guide to invoicing clients as a freelancer."), [])
IDS = ["lost_links", "unlinked_mentions", "free_tool", "listicle_outreach", "competitor_links", "broken_link_building",
       "outdated_guides", "statistics_page", "reporter_outreach", "infographics", "article_to_video", "link_exchanges"]


@pytest.fixture
def plan():
    return authority.build(opportunities.build([*PAGES, GUIDE]))


def test_twelve_tactics_each_with_a_state_and_no_link_data(plan):
    assert [t["id"] for t in plan["tactics"]] == IDS
    assert plan["mode"] == "prelaunch_advisory" and plan["link_data"] == "none"
    assert authority.counts(plan) == {"advisory": 3, "prerequisite_missing": 8, "not_applicable": 0, "not_recommended": 1}
    assert authority.build(None) is None and authority.build({"pages": []}) is None  # legacy reports get no plan


def test_tactics_needing_outside_evidence_invent_nothing(plan):
    missing = [t for t in plan["tactics"] if t["state"] == "prerequisite_missing"]
    for t in missing:
        assert t["target"] is None and t["source"] is None and t["brief"] is None and t["missing"]
    by_id = {t["id"]: t for t in plan["tactics"]}
    assert "last seen" in by_id["lost_links"]["missing"][0]  # no history means loss is unverified
    assert "AI answer that mentions you is not such a page" in by_id["unlinked_mentions"]["reader_benefit"]
    assert "never supplies or estimates" in by_id["statistics_page"]["reader_benefit"]


def test_advisory_briefs_build_only_on_audited_pages_and_their_own_words(plan):
    audited = {p for p, _, _ in [*PAGES, GUIDE]}
    for t in (t for t in plan["tactics"] if t["state"] == "advisory"):
        assert t["target"] in audited and t["source"] == {"kind": "audited_page", "url": t["target"], "observed": "audited in this report"}
        assert t["prerequisites"] and t["missing"] and t["effort"] and "No rank change is promised" in t["measurement"]
    by_id = {t["id"]: t for t in plan["tactics"]}
    assert by_id["free_tool"]["target"] == f"{BASE}/" and '"Invoices for freelancers"' in by_id["free_tool"]["brief"]
    assert by_id["infographics"]["target"] == f"{BASE}/guide"
    assert '"Set your rates"; "Write the invoice"; "Chase late payment"' in by_id["article_to_video"]["brief"]


def test_without_material_the_tactic_is_not_applicable():
    thin = authority.build(opportunities.build(PAGES))  # no page has three sections
    by_id = {t["id"]: t for t in thin["tactics"]}
    assert by_id["infographics"]["state"] == by_id["article_to_video"]["state"] == "not_applicable"
    topicless = authority.build(opportunities.build([(f"{BASE}/", page(None, None, [], [], "Hello."), [])]))
    assert {t["id"]: t for t in topicless["tactics"]}["free_tool"]["state"] == "not_applicable"


def test_exchanges_are_never_a_shortcut_and_paid_links_are_qualified(plan):
    exchange = plan["tactics"][-1]
    assert exchange["state"] == "not_recommended" and 'rel="sponsored"' in exchange["policy"] and "three-way" in exchange["policy"]
    assert plan["policy_source"].startswith("https://developers.google.com/search/docs/essentials/spam-policies")
    assert all(t["state"] != "advisory" for t in plan["tactics"] if t["id"] == "link_exchanges")


def test_backlinks_geo_and_citations_stay_distinct(plan):
    assert set(plan["separate"]) == {"geo_readiness", "ai_citations", "backlinks"}
    assert "not a citation" in plan["separate"]["ai_citations"] and "not zero visibility" in plan["separate"]["ai_citations"]
    assert any("do not guarantee an AI citation" in r for r in plan["rules"])
    assert any("sends email, posts, registers profiles or places links" in r for r in plan["rules"])


def report_with_plan(plan, advice):
    return Report(summary="s", findings=[], top_fixes=[], opportunities=advice, authority=plan).model_dump()


def test_chapter_is_advisory_only_with_a_plan(plan):
    advice = opportunities.build([*PAGES, GUIDE])
    chapter = {c["key"]: c for c in chapters(report_with_plan(plan, advice))}["authority"]
    assert chapter["status"] == "advisory_links" and chapter["label"] == "Advisory, no link data"
    assert chapter["summary"].startswith("3 tactics with a brief from your own pages, 8 needing an input")
    legacy = {c["key"]: c for c in chapters({"summary": "s", "findings": [], "top_fixes": []})}["authority"]
    assert legacy["status"] == "not_measured"


def test_prompt_is_an_owner_plan_never_a_send_or_publish_task(plan):
    advice = opportunities.build([*PAGES, GUIDE])
    run = {"id": "r", "site": BASE, "kind": "scan", "created_at": "2026-10-07"}
    brief = fix_prompt.build(run, report_with_plan(plan, advice), {}, "full", "authority")
    assert brief.startswith(f"# Authority plan for {BASE}") and "Do not send email or messages" in brief and "Batch" not in brief
    assert "\n".join(authority.lines(plan)) in brief
    with pytest.raises(fix_prompt.EmptyChapter):
        fix_prompt.build(run, {"findings": [], "top_fixes": []}, {}, "full", "authority")


def test_mcp_authority_section_returns_the_same_plan(plan, fake_db, monkeypatch):
    advice = opportunities.build([*PAGES, GUIDE])
    run_id = "f" * 32
    fake_db[run_id] = {"id": run_id, "user_id": USER, "site": BASE, "kind": "scan", "status": "done", "goal": "Instant Scan",
                       "public": False, "report": report_with_plan(plan, advice)}
    monkeypatch.setattr(mcp_server.db, "ignored_fingerprints", lambda user, origin: {})
    token = mcp_server._user.set(USER)
    try:
        text = mcp_server.get_report(run_id, section="authority")
    finally:
        mcp_server._user.reset(token)
    assert "Status: Advisory, no link data." in text and "\n".join(authority.lines(plan)) in text
