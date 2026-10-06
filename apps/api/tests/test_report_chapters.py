"""Report chapters (R-S5a): one primary chapter per finding, honest empty chapters, and the same ids, order and
summaries in the web report (checked through the shared fixture), fix prompts and MCP."""

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import db, mcp_server
from app.agent import fix_prompt
from app.agent.report_chapters import CHAPTERS, chapters, next_actions, resolve
from app.main import app
from tests.conftest import USER

FIXTURES = Path(__file__).resolve().parents[2] / "web/tests/fixtures"
RUN_ID = "c" * 32


def f(kind, severity, title, rule=None, evidence="https://site.test/"):
    return {"kind": kind, "severity": severity, "title": title, "detail": f"{title}.", "fix": f"Fix {title.lower()}.", "evidence": evidence,
            **({"rule": rule} if rule else {})}


# A long legacy journey report across most chapters: shared causes, a repeated rule, a legacy row without a rule id.
LONG = {"summary": "Signup stalled after the email step.", "top_fixes": ["Fix the submit error"], "verified": False, "tokens": 0,
        "checks": {"accessibility": "complete", "performance": "unavailable", "seo": "complete", "security": "complete", "geo": "complete"},
        "check_reasons": {"performance": "PageSpeed did not answer within the time limit."},
        "geo": {"score": 41, "band": "foundation", "categories": [], "ai_words": 12, "ai_view": "", "notes": []},
        "findings": [f("seo", "low", "3 of 9 images have no alt text", "seo.image.alt_missing"),
                     f("ux", "high", "Submit shows a network error", "ux.submit_network_error", "Step 4: Network error"),
                     f("geo", "high", "Homepage content only appears after JavaScript runs", "geo.homepage_content_only_appears_after_javascript_runs"),
                     f("security", "medium", 'Cookie "sid" lacks Secure', "sec.cookie.flags_missing"),
                     f("security", "medium", 'Cookie "csrf" lacks Secure', "sec.cookie.flags_missing"),
                     f("accessibility", "medium", "2 images are missing text alternatives", "a11y.image.alt_missing"),
                     f("security", "low", "No SPF record")]}
CLEAN = {"summary": "Nothing to fix in scope.", "top_fixes": [], "findings": [], "verified": True, "tokens": 0,
         "checks": {"accessibility": "complete", "performance": "complete", "seo": "complete", "security": "complete", "geo": "complete"},
         "geo": {"score": 88, "band": "excellent", "categories": [], "ai_words": 900, "ai_view": "", "notes": []}}
INTERRUPTED = {"summary": "The run stopped before any action.", "top_fixes": [], "findings": [], "verified": False, "tokens": 0}


# R-S17: a clean scan with an advisory keyword map, so the Keywords chapter status stays in step on web and API.
KEYWORDS = {**CLEAN, "opportunities": {"mode": "prelaunch_advisory", "demand_data": "none", "basis": "b", "measurement": "m", "pages_considered": 1,
            "excluded_noindex": [], "overlaps": [], "pages": [{"url": "https://site.test/", "primary_intent": {"text": "Plan trips", "source": "h1"},
            "supporting": [], "current": {"title": None, "description": None, "h1": ["Plan trips"]},
            "proposed": {"title": "Plan trips", "description": None, "outline": ["Plan trips"], "basis": "b"}, "gaps": ["No title element."],
            "internal_links": {"inbound_from": [], "suggested_from": []}, "next_action": "n", "effort": "low"}]}}


def cases() -> list[dict]:
    v2 = json.loads((FIXTURES / "report-v2.json").read_text(encoding="utf-8"))
    asserted = json.loads((FIXTURES / "report-assertion.json").read_text(encoding="utf-8"))
    return [{"name": name, "kind": kind, "status": status, "report": rep, "chapters": chapters(rep, kind, status), "next_actions": next_actions(rep)}
            for name, kind, status, rep in (("v2-scan", "scan", "done", v2), ("long-legacy-journey", "test", "gave_up", LONG),
                                            ("clean-scan", "scan", "done", CLEAN), ("interrupted-journey", "test", "agent_lost", INTERRUPTED),
                                            ("assertion-failed", "test", "done", asserted), ("keyword-advisory", "scan", "done", KEYWORDS))]


def test_shared_fixture_matches_the_api_so_web_and_mcp_agree():
    path = FIXTURES / "report-chapters.json"
    current = {"cases": cases()}
    if os.environ.get("WALKTHRU_WRITE_FIXTURES") == "1":  # regenerate after a deliberate contract change
        path.write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    assert json.loads(path.read_text(encoding="utf-8")) == current


def test_every_finding_has_exactly_one_primary_chapter_and_shared_causes_cross_link():
    result = {c["key"]: c for c in chapters(LONG, "test", "gave_up")}
    listed = [i for c in result.values() for i in c["issue_ids"]]
    assert len(listed) == len(LONG["findings"]) == len(set(listed))  # once each, stable ids, the repeat gets #2
    assert result["security"]["issue_ids"] == ["sec.cookie.flags_missing", "sec.cookie.flags_missing#2", "security:no spf record"]
    assert result["seo"]["cross_links"] == ["a11y.image.alt_missing", "geo.homepage_content_only_appears_after_javascript_runs"]
    assert result["accessibility"]["cross_links"] == ["seo.image.alt_missing"]
    assert result["geo"]["issue_ids"] == ["geo.homepage_content_only_appears_after_javascript_runs"]  # not a second GEO defect


def test_missing_data_stays_unmeasured_never_a_green_pass():
    result = {c["key"]: c for c in chapters(LONG, "test", "gave_up")}
    assert result["performance"]["status"] == "not_measured" and "PageSpeed" in result["performance"]["summary"]
    assert result["keywords"]["status"] == result["authority"]["status"] == "not_measured"
    assert result["citations"]["status"] == "separate"
    legacy = {c["key"]: c for c in chapters({"findings": []}, "scan", "done")}
    assert legacy["accessibility"]["status"] == legacy["geo"]["status"] == "not_measured"  # pre-2026-09-24 reports
    assert legacy["seo"]["status"] == "clear" and "not proof" in legacy["seo"]["summary"]
    stopped = {c["key"]: c for c in chapters(INTERRUPTED, "test", "agent_lost")}
    assert stopped["journey"]["status"] == "unconfirmed"  # an early stop is neither a pass nor a site defect
    assert {c["key"]: c for c in chapters(CLEAN, "scan", "done")}["journey"]["status"] == "not_tested"
    legacy_done = {c["key"]: c for c in chapters(INTERRUPTED, "test", "done")}["journey"]
    assert legacy_done["status"] == "clear" and "declared checkpoint" not in legacy_done["summary"]  # never claimed for legacy runs


def test_next_actions_lead_with_high_severity_and_skip_ignored_findings():
    ids = [a["id"] for a in next_actions(LONG)]
    assert ids == ["ux.submit_network_error", "geo.homepage_content_only_appears_after_javascript_runs", "a11y.image.alt_missing"]
    ignored = {"ux:ux.submit_network_error": "known, fixing next sprint"}
    assert "ux.submit_network_error" not in [a["id"] for a in next_actions(LONG, ignored)]
    after = {c["key"]: c for c in chapters(LONG, "test", "gave_up", ignored)}["journey"]
    assert after["status"] == "unconfirmed" and after["issue_ids"] == ["ux.submit_network_error"]  # still listed, not open


def test_unknown_chapter_names_the_valid_keys():
    assert resolve(" SEO ") == "seo"
    with pytest.raises(ValueError, match="journey, accessibility"):
        resolve("backlinks")
    assert len(CHAPTERS) == 10


def test_section_prompt_holds_only_that_chapter_and_says_so():
    run = {"id": "r1", "site": "https://site.test/", "goal": "Sign up", "kind": "test", "created_at": "2026-10-06T00:00:00+00:00"}
    text = fix_prompt.build(run, LONG, {}, "full", "security")
    assert "## Chapter: Security and email hygiene" in text and 'Cookie "sid"' in text and 'Cookie "csrf"' in text
    assert "Submit shows a network error" not in text and "alt text" not in text
    chat = fix_prompt.build(run, LONG, {}, "chat", "seo")
    assert "Chapter: SEO foundations" in chat and "3 of 9 images" in chat and "Cookie" not in chat
    assert fix_prompt.build(run, LONG, {}, "full") == fix_prompt.build(run, LONG, {}, "full", None)  # whole plan unchanged
    with pytest.raises(fix_prompt.EmptyChapter, match="Performance"):
        fix_prompt.build(run, LONG, {}, "full", "performance")


def _owned(fake_db, passes):
    fake_db[RUN_ID] = {"id": RUN_ID, "user_id": USER, "site": "https://site.test/", "goal": "Sign up", "kind": "test", "status": "gave_up",
                       "steps": [], "public": False, "created_at": "2026-10-06T00:00:00+00:00", "report": LONG}
    passes.append({"user_id": USER, "plan": "pro", "starts_at": "2000-01-01T00:00:00+00:00", "expires_at": "2999-01-01T00:00:00+00:00", "runs_granted": 40})


def test_fix_prompt_route_takes_a_chapter_and_rejects_unknown_or_empty_ones(fake_db, passes):
    _owned(fake_db, passes)
    c = TestClient(app)
    r = c.get(f"/runs/{RUN_ID}/fix-prompt", params={"section": "geo", "download": 1})
    assert r.status_code == 200 and "Chapter: GEO readiness" in r.text and "walkthru-fixes-geo.md" in r.headers["content-disposition"]
    assert c.get(f"/runs/{RUN_ID}/fix-prompt", params={"section": "backlinks"}).status_code == 422
    assert c.get(f"/runs/{RUN_ID}/fix-prompt", params={"section": "keywords"}).status_code == 409


@pytest.fixture
def owner(monkeypatch, fake_db, passes):
    _owned(fake_db, passes)
    monkeypatch.setattr(db, "ignored_fingerprints", lambda user, origin: {})
    token = mcp_server._user.set(USER)
    yield
    mcp_server._user.reset(token)


def test_mcp_report_leads_with_next_actions_and_the_chapter_index(owner):
    text = mcp_server.get_report(RUN_ID)
    assert text.index("## Next actions") < text.index("## Chapters") < text.index("## Findings")
    assert "1. [high] Submit shows a network error" in text and "(id: ux.submit_network_error, chapter: journey)" in text
    assert "05 Keywords and content (keywords): Not measured." in text
    assert "Issues: sec.cookie.flags_missing, sec.cookie.flags_missing#2, security:no spf record." in text


def test_mcp_section_reads_one_chapter_in_bounded_pages(owner, monkeypatch):
    monkeypatch.setattr(mcp_server, "CHAPTER_PAGE", 2)
    first = mcp_server.get_report(RUN_ID, section="security")
    assert first.startswith("# 09 Security and email hygiene") and "next cursor: 2" in first and "SPF" not in first
    rest = mcp_server.get_report(RUN_ID, section="security", cursor="2")
    assert "No SPF record" in rest and "next cursor" not in rest and 'Cookie "sid"' not in rest
    seo = mcp_server.get_report(RUN_ID, section="seo")
    assert "Also affects chapters: accessibility" in seo and "geo.homepage_content_only_appears_after_javascript_runs" in seo
    with pytest.raises(mcp_server.ToolError, match="Unknown chapter"):
        mcp_server.get_report(RUN_ID, section="backlinks")
    with pytest.raises(mcp_server.ToolError, match="cursor"):
        mcp_server.get_report(RUN_ID, section="seo", cursor="x")


def test_mcp_section_fix_prompt_matches_the_web_route(owner, fake_db):
    text = mcp_server.get_fix_prompt(RUN_ID, section="security")
    run = fake_db[RUN_ID]
    assert text == fix_prompt.build(run, LONG, {}, "full", "security")
    with pytest.raises(mcp_server.ToolError, match="no open findings"):
        mcp_server.get_fix_prompt(RUN_ID, section="citations")


def test_mcp_chapters_stay_owner_scoped(owner):
    token = mcp_server._user.set("someone-else")
    try:
        with pytest.raises(mcp_server.ToolError, match="No run with that id"):
            mcp_server.get_report(RUN_ID, section="seo")
    finally:
        mcp_server._user.reset(token)
