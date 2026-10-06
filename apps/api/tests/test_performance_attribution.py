"""R-S18: offline PSI v5/Lighthouse response shapes, bounded evidence and honest fixes."""

import json

import httpx
import pytest

from app.agent import report
from app.scans import performance

URL = "https://site.test/product"


def payload():
    return {"analysisUTCTimestamp": "2026-10-06T08:00:01Z", "lighthouseResult": {
        "requestedUrl": URL, "finalUrl": URL, "fetchTime": "2026-10-06T08:00:00Z", "lighthouseVersion": "13.0.0",
        "runWarnings": ["The page may have loaded with cached resources."],
        "configSettings": {"formFactor": "mobile", "throttlingMethod": "simulate",
                           "throttling": {"rttMs": 150, "cpuSlowdownMultiplier": 4}}, "timing": {"total": 9100},
        "categories": {"performance": {"score": 0.42, "auditRefs": [{"id": "unused-javascript"}]}},
        "audits": {
            "largest-contentful-paint": {"title": "Largest Contentful Paint", "numericValue": 4800, "numericUnit": "millisecond", "score": 0.2},
            "cumulative-layout-shift": {"numericValue": 0.01},
            "unused-javascript": {"title": "Reduce unused JavaScript", "score": 0, "scoreDisplayMode": "metricSavings",
                                  "description": "Remove code that is not used on this page.", "metricSavings": {"LCP": 300, "FCP": 200},
                                  "details": {"type": "opportunity", "overallSavingsMs": 650, "overallSavingsBytes": 80000,
                                              "items": [{"url": "https://site.test/assets/app.js", "wastedBytes": 80000, "wastedMs": 650}]}},
            "largest-contentful-paint-element": {"title": "Largest contentful paint element", "score": None, "scoreDisplayMode": "informative",
                                                  "details": {"type": "table", "items": [{"node": {"type": "node", "selector": "main > img.hero", "snippet": '<img value="private">', "nodeLabel": "private text"}}]}},
        }}}


def run(monkeypatch, data, status=200):
    monkeypatch.setattr(performance, "get", lambda *a, **k: httpx.Response(status, json=data))
    with httpx.Client() as client:
        return performance._one(URL, client, "offline-key")


def test_lab_attribution_and_fix_survive_without_field_data(monkeypatch):
    findings, measured, row = run(monkeypatch, payload())
    assert measured and row["status"] == "lab_only" and row["field_status"] == "unavailable"
    assert row["lcp_ms"] is None and row["cls"] is None and row["inp_ms"] is None
    lab = row["lab"]
    assert lab["metrics"]["lcp_ms"] == 4800 and lab["metrics"]["cls"] == 0.01
    assert lab["requested_url"] == lab["final_url"] == URL and lab["version"] == "13.0.0"
    assert lab["measured_at"] == "2026-10-06T08:00:00Z" and lab["duration_ms"] == 9100
    assert lab["device"] == "mobile" and lab["throttling_method"] == "simulate"
    assert lab["throttling"] == {"rttMs": 150, "cpuSlowdownMultiplier": 4}
    assert lab["warnings"] == ["The page may have loaded with cached resources."]
    assert row["source"] == "pagespeed_insights" and row["request_duration_ms"] >= 0 and row["retrieved_at"]
    audits = {a["id"]: a for a in lab["audits"]}
    assert audits["unused-javascript"]["estimated_savings_ms"] == 650
    assert audits["unused-javascript"]["metric_savings_ms"] == {"LCP": 300, "FCP": 200}
    assert audits["largest-contentful-paint-element"]["resources"] == [{"selector": "main > img.hero"}]
    assert "private" not in json.dumps(row)
    assert "unused-javascript" in findings[0].fix and "https://site.test/assets/app.js" in findings[0].fix
    assert "Estimated opportunity savings" in findings[0].detail and "not measured gains" in findings[0].detail


def test_partial_field_and_lab_are_separate_and_origin_fallback_is_not_used(monkeypatch):
    data = payload()
    data["loadingExperience"] = {"id": URL, "metrics": {"LARGEST_CONTENTFUL_PAINT_MS": {"percentile": 3200}}}
    data["originLoadingExperience"] = {"metrics": {"INTERACTION_TO_NEXT_PAINT": {"percentile": 20}}}
    findings, measured, row = run(monkeypatch, data)
    assert measured and row["status"] == "field_data" and row["field_status"] == "partial"
    assert row["lcp_ms"] == 3200 and row["lab"]["metrics"]["lcp_ms"] == 4800
    assert row["inp_ms"] is None and row["cls"] is None
    field = findings[-1]
    assert "CrUX url-level 75th-percentile" in field.detail and "not proven causes" in field.detail


def test_origin_id_is_labelled_as_origin(monkeypatch):
    data = {"loadingExperience": {"id": "https://site.test/", "metrics": {"LARGEST_CONTENTFUL_PAINT_MS": {"percentile": 3000}}}}
    findings, measured, row = run(monkeypatch, data)
    assert measured and row["field_scope"] == "origin" and "origin-level" in findings[0].detail


@pytest.mark.parametrize("data", [None, [], {"lighthouseResult": []}, {"lighthouseResult": {"categories": []}},
                                      {"lighthouseResult": {"categories": {"performance": {"score": 2}}}},
                                      {"loadingExperience": {"metrics": {"LARGEST_CONTENTFUL_PAINT_MS": {"percentile": True}}}}])
def test_malformed_or_missing_data_is_unavailable(monkeypatch, data):
    findings, measured, row = run(monkeypatch, data)
    assert not measured and findings == [] and row["status"] == "unavailable" and row["lab_score"] is None


def test_runtime_error_invalidates_lab_but_not_real_field_data(monkeypatch):
    data = payload()
    data["lighthouseResult"]["runtimeError"] = {"code": "NO_FCP", "message": "No content rendered"}
    findings, measured, row = run(monkeypatch, data)
    assert not measured and findings == [] and row["lab"]["audits"] == []
    assert row["lab_score"] is None and row["lab"]["metrics"]["lcp_ms"] is None
    data["loadingExperience"] = {"metrics": {"LARGEST_CONTENTFUL_PAINT_MS": {"percentile": 3100}}}
    findings, measured, row = run(monkeypatch, data)
    assert measured and row["lab_score"] is None and len(findings) == 1


def test_bounded_modern_nested_audits_and_sensitive_values(monkeypatch):
    data = payload()
    lab = data["lighthouseResult"]
    lab["finalUrl"] = "https://user:password@site.test/product?token=secret#private"
    lab["categories"]["performance"]["auditRefs"] += [{"id": f"audit-{i}"} for i in range(30)]
    for i in range(30):
        lab["audits"][f"audit-{i}"] = {"title": "x" * 1000, "score": 0, "scoreDisplayMode": "metricSavings",
            "details": {"type": "checklist", "items": [{"value": {"type": "table", "items": [
                {"url": f"https://site.test/asset/{j}?secret=private", "node": {"selector": "img.hero", "snippet": "private"}} for j in range(100)]}}]}}
    _, _, row = run(monkeypatch, data)
    assert row["lab"]["final_url"] == URL
    assert len(row["lab"]["audits"]) == performance.MAX_AUDITS and row["lab"]["audits_omitted"] > 0
    assert all(len(a["resources"]) <= performance.MAX_RESOURCES for a in row["lab"]["audits"])
    assert any(a["resources_truncated"] for a in row["lab"]["audits"])
    assert "private" not in json.dumps(row) and "password" not in json.dumps(row)
    assert len(json.dumps(row)) < 20000


def test_numeric_invalids_are_not_zero_or_scores():
    for value in (True, -1, float("nan"), float("inf"), 10**1000, "1"):
        assert performance._number(value) is None
    assert performance._number(0) == 0


def test_partial_audit_error_does_not_become_a_measured_lab_metric(monkeypatch):
    data = payload()
    data["lighthouseResult"]["audits"]["largest-contentful-paint"] |= {"scoreDisplayMode": "error", "errorMessage": "No LCP found"}
    findings, measured, row = run(monkeypatch, data)
    assert measured and row["lab"]["metrics"]["lcp_ms"] is None
    assert "Lab LCP: unavailable" in findings[0].detail
    assert any(a["error"] == "No LCP found" for a in row["lab"]["audits"])


def test_failed_opportunity_cannot_support_a_specific_resource_fix(monkeypatch):
    data = payload()
    data["lighthouseResult"]["audits"]["unused-javascript"]["errorMessage"] = "Resource audit failed"
    findings, _, _ = run(monkeypatch, data)
    assert "No specific resource fix was measured" in findings[0].fix
    assert "Estimated opportunity savings" not in findings[0].detail


def test_no_audit_attribution_does_not_invent_compression_fix(monkeypatch):
    findings, _, _ = run(monkeypatch, {"lighthouseResult": {"categories": {"performance": {"score": 0.4}}}})
    assert "No specific resource fix was measured" in findings[0].fix
    assert "Compress images" not in findings[0].fix


def test_report_prompt_and_serialized_assessment_keep_measured_opportunity(monkeypatch):
    findings, _, row = run(monkeypatch, payload())
    state = {"site": URL, "status": "scan", "performance": [f.model_dump() for f in findings],
             "performance_measured": True, "site_audit": {"mobile_vitals": [row], "urls": [URL], "pages_scanned": 1}}
    inputs = report.synthesis_inputs(state)
    prompt = inputs["messages"][-1][1]
    assert "unused-javascript" in prompt and "app.js" in prompt
    assert '"lcp_ms": 4800' in prompt and "crux_p75" in prompt
    from app.agent.report_contract import build_assessment
    assessment = build_assessment(state, state["performance"], state["performance"], {"performance": "complete"})
    assert "unused-javascript" in assessment.issues[0].proposed_change


@pytest.mark.parametrize("style", ["full", "chat"])
def test_fix_prompt_keeps_measured_resource_instead_of_generic_image_recipe(monkeypatch, style):
    from app.agent import fix_prompt
    findings, _, _ = run(monkeypatch, payload())
    saved = {"version": 1, "findings": [f.model_dump() for f in findings], "stack": {"framework": "nextjs"}}
    run_row = {"site": URL, "kind": "scan", "created_at": "2026-10-06"}
    prompt = fix_prompt.build(run_row, saved, {}, style, "performance")
    assert "unused-javascript" in prompt and "https://site.test/assets/app.js" in prompt
    assert "hero.jpg" not in prompt and "hero.webp" not in prompt and "Compress images" not in prompt
