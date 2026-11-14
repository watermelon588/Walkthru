"""Executive prose cannot expand measured findings into unsupported business claims."""

import httpx
import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import MemorySaver

from app import main
from app.agent import goal, report, runtime
from app.agent.persona import build_graph
from app.agent.schema import Finding, PersonaStep, Synthesis
from app.agent.typesafe import JevDecision
from app.scans import email, geo, seo, tls
from tests.test_geo import SHELL


@pytest.mark.parametrize("status", ["scan", "done", "gave_up", "stopped"])
def test_writer_summary_and_fixes_cannot_invent_impact_even_when_finding_is_grounded(monkeypatch, status):
    finding = Finding(kind="seo", severity="medium", title="Missing description", detail="No description was found.",
                      fix="Add a description.", evidence="https://fixture.test/", rule="seo.description.missing")
    monkeypatch.setattr(runtime, "call", lambda *a, **k: (Synthesis(summary="You lost 80% of revenue. Google banned the site.",
        ux_findings=[], top_fixes=["Buy ads to recover $50000 revenue."]), 13))
    state = {"site": "https://fixture.test/", "status": status, "seo": [finding.model_dump()],
             "steps": [{"action": "click", "thought": "Open", "result_url": "https://fixture.test/", "errors_after": ["Network error"]}],
             "site_audit": {"pages_scanned": 1, "page_limit": 1, "truncated": False, "urls": ["https://fixture.test/"], "duration_ms": 1, "robots_respected": True}}
    result = report.synthesize(state)["synthesis"]
    assert all(term not in result["summary"] for term in ("80%", "revenue", "banned"))
    assert result["top_fixes"] == [finding.fix]
    assert "1 page(s)" in result["summary"]
    assert "All declared journey checkpoints" not in result["summary"]  # provider/status alone is insufficient


def test_static_findings_do_not_claim_actual_search_preview_or_assistant_outcomes():
    findings = seo.check_html('<html><body><img src="a.png"></body></html>', "https://fixture.test/") + seo.check_robots(None)
    text = " ".join(f.detail for f in findings)
    assert "invisible to" not in text and "will show no preview" not in text and "cannot find your sitemap" not in text
    result = geo.audit("https://fixture.test/", [("https://fixture.test/", SHELL)], "User-agent: OAI-SearchBot\nDisallow: /", None, (403, "", {}), full=False)
    text = " ".join(f.detail for f in result.findings)
    assert "see an empty page" not in text and "cannot quote" not in text
    assert "not established" in text and "not a verified crawler request" in text


@pytest.mark.parametrize("status", [2, 5])
def test_dns_failure_is_unknown_not_absent_records(status):
    with httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json={"Status": status}))) as client:
        findings, note = email.check("https://fixture.test/", client, full=True)
        assert findings == [] and "failed" in note
        assert tls.check_caa("https://fixture.test/", client) == []


@pytest.mark.parametrize("body", [{}, [], {"Status": False}, {"Status": "0"}, {"Status": 0, "Answer": None},
                                  {"Status": 0, "Answer": ["bad"]}, {"Status": 0, "Answer": [{"type": 16, "data": None}]}])
def test_malformed_dns_payload_does_not_establish_absence(body):
    with httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=body))) as client:
        findings, note = email.check("https://fixture.test/", client, full=True)
        assert findings == [] and "failed" in note
        assert tls.check_caa("https://fixture.test/", client) == []


def test_absent_dns_records_do_not_claim_failed_delivery_or_successful_attack():
    with httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json={"Status": 0}))) as client:
        findings, _ = email.check("https://fixture.test/", client, full=True)
        findings += tls.check_caa("https://fixture.test/", client)
    text = " ".join(f.detail for f in findings)
    assert "cannot receive email" not in text and "anyone can send email" not in text and "can produce a valid certificate" not in text
    assert "delivery were not tested" in text and "does not demonstrate certificate misissuance" in text


def test_run_token_total_includes_planner_and_decision_once(monkeypatch):
    class Decision:
        def decide(self, state, messages):
            return JevDecision(PersonaStep(action="click", target_id=1, thought="Open", confusion=0), 17, {})
    monkeypatch.setattr(goal, "plan", lambda *a, **k: {"intent": "Open work", "feasible": True, "planner_tokens": 11,
        "checkpoints": [{"description": "Open work", "kind": "navigation", "url_contains": "/work"}]})
    graph = build_graph(Decision(), MemorySaver())
    monkeypatch.setattr(runtime, "graph", lambda tier: graph)
    client = TestClient(main.app)
    response = client.post("/runs", json={"site": "https://fixture.test/", "goal": "Open work",
        "observation": {"url": "https://fixture.test/", "title": "Fixture", "text": "Work", "elements": [{"id": 1, "tag": "a", "text": "Work"}]}})
    assert response.status_code == 200, response.text
    run_id = response.json()["run_id"]
    state = graph.get_state({"configurable": {"thread_id": run_id}}).values
    assert state["tokens"] == 28
