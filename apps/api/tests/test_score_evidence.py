"""Readiness describes retained browser proof, not a run's termination label."""

import pytest

from app.agent import score
from app.agent.report_contract import build_assessment, ensure_supported

SITE = "https://example.test/"
CHECKPOINTS = [{"description": "Create account", "text_contains": "Account created"}]
COMPLETED_STEPS = [{
    "action": "click", "target_label": "Create account", "result_url": SITE + "welcome",
    "checkpoint_evidence": {"checkpoint": 1, "step": 1, "url": SITE + "welcome",
                            "signal": "public_text", "matched": "Account created"},
}]
FAILED_STEPS = [{"action": "click", "target_label": "Create account", "result_url": SITE,
                 "errors_after": ["Account creation failed. Please try again."]}]
UX_FAILURE = {
    "kind": "ux", "severity": "high", "title": "Account creation reports an error",
    "detail": "The page reported an account creation error after submission.",
    "fix": "Inspect and resolve the recorded account creation error.",
    "evidence": "Step 1: Account creation failed. Please try again.", "rule": "ux.submit_error",
}


def assessed_report(status, *, steps=None, findings=None, checks=None, checkpoints=None, geo=None, code_findings=None):
    """Use the real report contract so fixtures cannot invent an outcome or issue proof."""
    findings, checks = findings or [], checks or {}
    assessment = build_assessment({
        "site": SITE, "goal": "Create account", "status": status,
        "steps": steps or [], "checkpoints": CHECKPOINTS if checkpoints is None else checkpoints,
    }, findings, code_findings or [], checks).model_dump()
    report = {"version": 2, "summary": "Scoped test", "findings": findings,
              "top_fixes": [], "checks": checks, "assessment": assessment}
    if geo is not None:
        report["geo"] = geo
    ensure_supported(report)
    return report


def parts(result):
    return {part["id"]: part for part in result["parts"]}


def test_checkpoint_proof_preserves_successful_journey_scores():
    report = assessed_report("done", steps=COMPLETED_STEPS)
    assert report["assessment"]["outcome"] == "completed"
    assert score.launch_ready(report, "done")["areas"]["ux"] == 100
    assert parts(score.agent_ready(report, "done", COMPLETED_STEPS))["goal"]["earned"] == 25


def test_safe_stop_does_not_turn_a_blocked_assessment_into_completion():
    report = assessed_report("safe_stop")
    assert report["assessment"]["outcome"] == "blocked"
    assert score.launch_ready(report, "safe_stop")["areas"]["ux"] is None
    result = parts(score.agent_ready(report, "safe_stop"))
    assert "goal" not in result or result["goal"]["earned"] < result["goal"]["max"]


@pytest.mark.parametrize("status", ["budget", "agent_lost", "looping", "stopped", "gave_up", "stuck"])
def test_unproven_stops_do_not_measure_a_site_failure(status):
    steps = [{"action": "give_up", "code": status, "thought": "The site must be broken."}]
    report = assessed_report(status, steps=steps)
    assert report["assessment"]["outcome"] == "unconfirmed"
    assert report["assessment"]["issues"] == []
    assert score.launch_ready(report, status)["areas"]["ux"] is None
    assert "goal" not in parts(score.agent_ready(report, status, steps))


@pytest.mark.parametrize("legacy", [False, True])
def test_done_without_checkpoint_proof_cannot_claim_success(legacy):
    report = ({"findings": [], "checks": {}} if legacy else
              assessed_report("done", steps=[{"action": "click", "result_url": SITE}]))
    assert score.launch_ready(report, "done")["areas"]["ux"] is None
    assert "goal" not in parts(score.agent_ready(report, "done"))


@pytest.mark.parametrize("status", ["budget", "agent_lost", "looping", "stopped", "safe_stop"])
def test_an_interruption_preserves_a_previously_observed_site_error(status):
    baseline = assessed_report("gave_up", steps=FAILED_STEPS, findings=[UX_FAILURE])
    steps = FAILED_STEPS + [{"action": "give_up", "code": status, "interrupted": True}]
    interrupted = assessed_report(status, steps=steps, findings=[UX_FAILURE])
    assert interrupted["assessment"]["issues"][0]["observation_type"] == "browser_observation"
    assert interrupted["assessment"]["issues"][0]["evidence_refs"] == ["step:1"]
    expected_ux = score.launch_ready(baseline, "gave_up")["areas"]["ux"]
    assert expected_ux is not None and expected_ux < 100
    assert score.launch_ready(interrupted, status)["areas"]["ux"] == expected_ux
    assert parts(score.agent_ready(interrupted, status, steps))["goal"]["earned"] == 0


@pytest.mark.parametrize("prior_status", ["done", "safe_stop"])
def test_unproven_prior_run_cannot_earn_full_rerun_stability(prior_status):
    report = assessed_report("done", steps=COMPLETED_STEPS)
    previous_steps = [{"action": "click", "result_url": SITE}]
    previous = {"status": prior_status, "steps": previous_steps,
                "report": assessed_report(prior_status, steps=previous_steps)}
    result = parts(score.agent_ready(report, "done", COMPLETED_STEPS, previous))
    assert "stable" not in result or result["stable"]["earned"] < result["stable"]["max"]


def test_proven_prior_and_current_runs_still_earn_full_rerun_stability():
    report = assessed_report("done", steps=COMPLETED_STEPS)
    previous = {"status": "done", "steps": COMPLETED_STEPS, "report": report}
    result = parts(score.agent_ready(report, "done", COMPLETED_STEPS, previous))
    assert result["stable"]["earned"] == result["stable"]["max"]


def test_static_measurements_survive_an_unconfirmed_journey():
    checks = {"seo": "complete", "security": "complete", "accessibility": "complete", "geo": "complete"}
    geo = {"score": 80, "agent": {"fields": 2, "named_fields": 2, "webmcp": True, "search_action": True}}
    report = assessed_report("budget", checks=checks, geo=geo)
    launch = score.launch_ready(report, "budget")
    assert launch["areas"] == {"ux": None, "security": 100, "geo": 80, "seo": 100, "speed": 100}
    assert launch["score"] == round((20 * 100 + 20 * 80 + 15 * 100 + 15 * 100) / 70)
    agent = parts(score.agent_ready(report, "budget"))
    assert {"names", "forms", "search"} <= agent.keys()
    assert agent["names"]["earned"] == 25
    assert agent["forms"]["earned"] == 15
    assert agent["search"]["earned"] == 10
    assert "goal" not in agent


@pytest.mark.parametrize("invalid", ["future_version", "missing_proof", "wrong_status", "uncovered_finding"])
def test_invalid_or_mismatched_assessments_cannot_supply_completion(invalid):
    report = assessed_report("done", steps=COMPLETED_STEPS)
    if invalid == "future_version":
        report["version"] = 3
    elif invalid == "missing_proof":
        report["assessment"]["evidence_index"] = []
    elif invalid == "wrong_status":
        report["assessment"]["stop_reason"] = "safe_stop"
    else:
        report["findings"] = [UX_FAILURE]
    assert score.launch_ready(report, "done")["areas"]["ux"] is None
    assert "goal" not in parts(score.agent_ready(report, "done"))


@pytest.mark.parametrize("missing", ["executed_step", "matching_url"])
def test_milestone_without_matching_executed_step_cannot_supply_completion(missing):
    report = assessed_report("done", steps=COMPLETED_STEPS)
    evidence = report["assessment"]["evidence_index"]
    if missing == "executed_step":
        report["assessment"]["evidence_index"] = [e for e in evidence if e["source"] != "step"]
        report["assessment"]["coverage"]["actions_with_outcomes"] = 0
    else:
        next(e for e in evidence if e["source"] == "milestone")["url"] = SITE + "other"
    ensure_supported(report)
    assert score.launch_ready(report, "done")["areas"]["ux"] is None
    assert "goal" not in parts(score.agent_ready(report, "done"))


def test_rerun_stability_uses_validated_action_counts():
    report = assessed_report("done", steps=COMPLETED_STEPS)
    report["assessment"]["coverage"]["actions_with_outcomes"] = "1"
    ensure_supported(report)
    previous = {"status": "done", "report": report}
    result = parts(score.agent_ready(report, "done", COMPLETED_STEPS, previous))
    assert result["stable"]["earned"] == result["stable"]["max"]


@pytest.mark.parametrize("observed, completed", [("Preferences saved", False), (" account  CREATED ", True)])
def test_completion_requires_the_declared_result_with_normalized_text(observed, completed):
    report = assessed_report("done", steps=COMPLETED_STEPS)
    report["assessment"]["checkpoints"][0]["actual_result"] = observed
    next(e for e in report["assessment"]["evidence_index"] if e["source"] == "milestone")["observed"] = observed
    ensure_supported(report)
    assert score.launch_ready(report, "done")["areas"]["ux"] == (100 if completed else None)
    assert ("goal" in parts(score.agent_ready(report, "done"))) == completed
