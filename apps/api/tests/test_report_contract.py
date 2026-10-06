"""Versioned reports preserve legacy readers without promoting narration into facts."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.agent.report_contract import build_assessment, ensure_supported
from app.agent.schema import Report


def report(**changes):
    return {"summary": "Scoped report", "findings": [], "top_fixes": [], **changes}


def test_legacy_report_stays_readable_and_unknown_versions_fail():
    ensure_supported(report())
    assert Report.model_validate(report()).version == 1
    for version in (3, "2", True, None):
        with pytest.raises((ValueError, ValidationError), match="version"):
            ensure_supported(report(version=version))


def test_clean_declared_mission_records_matching_public_proof_without_defects():
    state = {"site": "https://example.test/", "goal": "Create account", "status": "done",
             "checkpoints": [{"description": "Create account", "text_contains": "Account created"}],
             "steps": [{"action": "click", "result_url": "https://example.test/welcome",
                        "checkpoint_evidence": {"checkpoint": 1, "step": 1, "url": "https://example.test/welcome",
                                                "signal": "public_text", "matched": "Account created"}}]}
    assessment = build_assessment(state, [], [], {"seo": "complete"}).model_dump()
    assert assessment["outcome"] == "completed"
    assert assessment["issues"] == []
    assert assessment["checkpoints"][0]["actual_result"] == "Account created"
    current = report(version=2, assessment=assessment)
    assert Report.model_validate(current).model_dump()["assessment"] == assessment


def test_missing_expected_result_and_controller_loss_are_unknown_not_site_failure():
    assessment = build_assessment({"site": "https://example.test/", "goal": "Create account", "status": "agent_lost",
                                   "checkpoints": [{"description": "Create account"}],
                                   "steps": [{"action": "give_up", "thought": "The site is broken", "code": "agent_lost"}]},
                                  [], [], {}).model_dump()
    assert assessment["outcome"] == "unconfirmed"
    assert assessment["checkpoints"][0]["expected_result"] is None
    assert assessment["checkpoints"][0]["actual_result"] is None
    assert assessment["evidence_index"] == []
    assert assessment["issues"] == []


def test_scanner_facts_and_proposals_are_separate_and_refs_are_validated():
    finding = {"kind": "seo", "severity": "low", "title": "Missing title", "detail": "No title element.",
               "fix": "Add a descriptive title.", "evidence": "<head> has no title", "rule": "seo.title.missing"}
    assessment = build_assessment({"site": "https://example.test/", "status": "scan"}, [finding], [finding],
                                  {"seo": "complete"}).model_dump()
    issue = assessment["issues"][0]
    assert issue["observed_facts"] == ["<head> has no title"]
    assert issue["proposed_change"] == finding["fix"]
    assert issue["expected_result"] is None and issue["cause_hypothesis"] is None
    assert issue["acceptance_test"]
    assessment["issues"][0]["evidence_refs"] = ["step:999"]
    with pytest.raises((ValueError, ValidationError), match="evidence"):
        ensure_supported(report(version=2, findings=[finding], assessment=assessment))


def test_unrelated_step_cannot_be_used_as_scanner_evidence():
    finding = {"kind": "seo", "severity": "low", "title": "Missing title", "detail": "No title.",
               "fix": "Add title.", "evidence": "No title", "rule": "seo.title.missing"}
    assessment = build_assessment({"site": "https://example.test/", "status": "scan",
                                   "steps": [{"action": "click", "result_url": "https://example.test/"}]},
                                  [finding], [finding], {}).model_dump()
    assessment["issues"][0]["evidence_refs"] = ["step:1"]
    with pytest.raises((ValueError, ValidationError), match="evidence"):
        ensure_supported(report(version=2, findings=[finding], assessment=assessment))


def test_shared_python_web_fixture_roundtrips_the_full_versioned_contract():
    path = Path(__file__).resolve().parents[2] / "web/tests/fixtures/report-v2.json"
    saved = json.loads(path.read_text(encoding="utf-8"))
    ensure_supported(saved)
    assert Report.model_validate(saved).model_dump() == saved


@pytest.mark.parametrize("field,value", [("observed_facts", ["Account created"]), ("actual_result", "Account created"),
                                         ("expected_result", "Account created")])
def test_unsupported_facts_results_and_expectations_are_rejected(field, value):
    path = Path(__file__).resolve().parents[2] / "web/tests/fixtures/report-v2.json"
    saved = json.loads(path.read_text(encoding="utf-8"))
    saved["assessment"]["issues"][0][field] = value
    with pytest.raises(ValueError, match="invalid evidence"):
        ensure_supported(saved)


def test_reproduction_and_new_evidence_never_contain_typed_values_or_model_thoughts():
    finding = {"kind": "ux", "severity": "high", "title": "Submit error", "detail": "The page reported an error.",
               "fix": "Inspect the recorded failure.", "evidence": "Step 2: Network error", "rule": "ux.submit_error"}
    steps = [{"action": "type", "text": "private-password", "thought": "invented cause", "target_label": "Password", "result_url": "https://example.test/"},
             {"action": "click", "target_label": "Submit", "result_url": "https://example.test/", "errors_after": ["Network error"]}]
    value = build_assessment({"status": "gave_up", "steps": steps}, [finding], [], {}).model_dump()
    text = json.dumps(value)
    assert "private-password" not in text and "invented cause" not in text
    assert value["issues"][0]["observed_facts"] == ["Step 2: Network error"]
    assert value["issues"][0]["reproduction_steps"] == ["Step 1: type Password", "Step 2: click Submit"]


def test_private_access_precedes_version_errors_and_owner_can_read_legacy(fake_db):
    from app.main import app
    from tests.conftest import USER

    run_id = "a" * 32
    row = {"id": run_id, "user_id": USER, "site": "https://example.test/", "status": "done", "steps": [], "report": report(version=99)}
    fake_db[run_id] = row
    client = TestClient(app)
    response = client.get(f"/runs/{run_id}")
    assert response.status_code == 409 and "Unsupported report version" in response.json()["detail"]
    row["user_id"] = "another-owner"
    assert client.get(f"/runs/{run_id}").status_code == 404
    row["user_id"] = USER
    row["report"] = report()
    assert client.get(f"/runs/{run_id}").json()["report"] == report()


def test_mcp_and_fix_prompt_keep_the_same_issue_ids_evidence_and_acceptance():
    from app import mcp_server
    from app.agent import fix_prompt

    saved = json.loads((Path(__file__).resolve().parents[2] / "web/tests/fixtures/report-v2.json").read_text(encoding="utf-8"))
    row = {"id": "a" * 32, "site": "https://example.test/", "kind": "scan", "status": "done", "report": saved}
    full = fix_prompt.build(row, saved, {})
    chat = fix_prompt.build(row, saved, {}, "chat")
    mcp = mcp_server._summary(row, full=True)
    issue = saved["assessment"]["issues"][0]
    for text in (full, chat, mcp):
        assert "Outcome: not_tested" in text
        assert issue["evidence_refs"][0] in text and issue["acceptance_test"] in text
    assert issue["id"] in full and issue["id"] in mcp


def test_mismatching_checkpoint_metadata_cannot_manufacture_completion():
    value = build_assessment({"status": "done", "checkpoints": [{"description": "Account", "text_contains": "Account created"}],
                              "steps": [{"action": "click", "result_url": "https://example.test/", "checkpoint_evidence":
                                         {"checkpoint": 1, "step": 1, "signal": "public_text", "matched": "Preferences saved"}}]}, [], [], {})
    assert value.outcome == "unconfirmed" and value.checkpoints[0].actual_result is None


def test_manual_only_fix_prompts_keep_evidence_and_acceptance(monkeypatch):
    from app.agent import fix_prompt

    saved = json.loads((Path(__file__).resolve().parents[2] / "web/tests/fixtures/report-v2.json").read_text(encoding="utf-8"))
    monkeypatch.setattr(fix_prompt, "recipe", lambda _: {"manual": "hosting", "manual_text": "Inspect the hosting setting."})
    row = {"id": "a" * 32, "site": "https://example.test/", "kind": "scan", "report": saved}
    issue = saved["assessment"]["issues"][0]
    for style in ("full", "chat"):
        text = fix_prompt.build(row, saved, {}, style)
        assert issue["evidence_refs"][0] in text and issue["acceptance_test"] in text
    assert issue["id"] in fix_prompt.build(row, saved, {})


def test_new_evidence_masks_url_values_credentials_fragments_and_public_pii():
    private_url = "https://viewer:password@example.test/login?token=private-value#private-fragment"
    assessment = build_assessment({"status": "done", "goal": private_url,
                                   "steps": [{"action": "click", "result_url": private_url,
                                              "errors_after": ["Contact person@example.test: " + private_url]}]}, [], [], {}).model_dump()
    text = json.dumps(assessment)
    for value in ("viewer:password", "private-value", "private-fragment", "person@example.test"):
        assert value not in text
    assert "example.test/login" in text


def test_clean_mission_prompts_and_mcp_retain_scope_without_fabricating_fixes():
    from app import mcp_server
    from app.agent import fix_prompt

    assessment = build_assessment({"status": "agent_lost", "goal": "Create account"}, [], [], {}).model_dump()
    saved = report(version=2, assessment=assessment)
    row = {"id": "a" * 32, "site": "https://example.test/", "kind": "test", "status": "agent_lost", "goal": "Create account", "report": saved}
    for text in (fix_prompt.build(row, saved, {}), fix_prompt.build(row, saved, {}, "chat"), mcp_server._summary(row, full=True)):
        assert "Outcome: unconfirmed" in text and "0 actions with recorded outcomes" in text
        assert "No declared checkpoint expectations" in text
    assert assessment["issues"] == []


def test_reproduction_reaches_the_last_referenced_problem():
    finding = {"kind": "ux", "severity": "high", "title": "Repeated failure", "detail": "Both attempts showed errors.",
               "fix": "Inspect the recorded failures.", "evidence": "Steps 1 and 2: Network error"}
    assessment = build_assessment({"status": "gave_up", "steps": [
        {"action": "click", "target_label": "Submit", "errors_after": ["Network error"]},
        {"action": "click", "target_label": "Retry", "errors_after": ["Network error"]},
    ]}, [finding], [], {})
    assert assessment.issues[0].evidence_refs == ["step:1", "step:2"]
    assert assessment.issues[0].reproduction_steps[-1] == "Step 2: click Retry"
