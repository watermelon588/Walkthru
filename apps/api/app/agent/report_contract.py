"""Additive report v2: code owns evidence and coverage; legacy fields remain readable."""

import re
from datetime import datetime

from app.agent.compare import fingerprint
from app.agent.schema import FilterCountAssertion, ReportAssessment


class ReportContractError(ValueError):
    """A stored report cannot be interpreted safely by this reader."""


def ensure_supported(report: dict | None) -> None:
    if report is None:
        return
    version = report.get("version", 1)
    if type(version) is not int or version not in (1, 2):
        raise ReportContractError("Unsupported report version. Update Walkthru to read this report.")
    if version == 1 and report.get("assessment") is not None:
        raise ReportContractError("Report version does not match its assessment")
    if version == 2:
        try:
            assessment = ReportAssessment.model_validate(report.get("assessment"))
        except ValueError as error:
            raise ReportContractError("Report version 2 contains invalid evidence or coverage.") from error
        if sorted(i.finding_index for i in assessment.issues) != list(range(len(report.get("findings", [])))):
            raise ReportContractError("Report version 2 assessment does not cover its findings")


def finding_ids(findings: list[dict]) -> list[str]:
    seen = {}
    ids = []
    for finding in findings:
        base = finding.get("rule") or fingerprint(finding)
        seen[base] = seen.get(base, 0) + 1
        ids.append(base if seen[base] == 1 else f"{base}#{seen[base]}")
    return ids


def issue_for(report: dict, finding: dict) -> dict | None:
    findings = report.get("findings", [])
    index = next((i for i, f in enumerate(findings) if f is finding), None)
    if index is None:
        index = next((i for i, f in enumerate(findings) if f == finding), None)
    return next((i for i in (report.get("assessment") or {}).get("issues", []) if i["finding_index"] == index), None)


def scope_lines(report: dict) -> list[str]:
    assessment = report.get("assessment")
    if not assessment:
        return []
    coverage = assessment["coverage"]
    lines = ["## Scope and outcome", (f"Outcome: {assessment['outcome']}. {coverage['confirmed_checkpoints']} of {coverage['declared_checkpoints']} declared checkpoints confirmed; "
            f"{coverage['actions_with_outcomes']} actions with recorded outcomes."), *[f"Limitation: {s}" for s in assessment["limitations"]]]
    for assertion in assessment.get("assertions", []):
        context = assertion["expected"]
        lines.append(f"Assertion {assertion['id']}: {assertion['status']}. State reached: {assertion['state_reached']}. Path: {context['path']}; filter: {context['filter_value']}; count label: {context['count_label']}; maximum age: {context['max_age_seconds']} seconds. Expected count: {context['expected_count']}; observed: {assertion['observed_count']}; tolerance: {context['tolerance']} records. Dataset: {context['dataset_id']} at {context['dataset_at']}; evaluated: {assertion['evaluated_at']}. {assertion['reason']} Evidence: {', '.join(assertion['evidence_refs']) or 'unavailable'}")
    return lines + [""]


def issue_lines(issue: dict) -> list[str]:
    return [f"Finding id: {issue['id']}", f"Observed facts: {'; '.join(issue['observed_facts'])}",
            f"Expected result: {issue['expected_result'] or 'Unknown, not declared'}", f"Actual result: {issue['actual_result']}",
            f"Interpretation: {issue['interpretation']}", f"Cause hypothesis: {issue['cause_hypothesis'] or 'Not established'}",
            f"Proposed change: {issue['proposed_change']}", f"Evidence references: {', '.join(issue['evidence_refs'])}",
            *[f"Recorded reproduction: {s}" for s in issue["reproduction_steps"]], f"Acceptance test: {issue['acceptance_test']}", ""]


def build_assessment(state: dict, findings: list[dict], code_findings: list[dict], checks: dict) -> ReportAssessment:
    from app.agent.report import _prompt_text, plain, problem_steps

    def public(value, limit=1000):
        return plain(_prompt_text(str(value or ""), limit))[:limit]

    steps = state.get("steps", [])
    problems = problem_steps(steps, state.get("status"))
    evidence, by_step = [], {}
    for number, step in enumerate(steps, 1):
        if step.get("interrupted") or step.get("action") in {"done", "give_up"} or step.get("code") in {"agent_lost", "safe_stop", "visitor_mode_limit"}:
            continue
        errors = step.get("errors_after", [])
        recorded = bool(step.get("result_url") or errors or step.get("notices_after") or step.get("no_change"))
        if not recorded:
            continue
        fact = "; ".join(errors) if errors else "No visible snapshot change recorded." if step.get("no_change") else "Browser action has a recorded public outcome."
        entry = {"id": f"step:{number}", "source": "step", "step": number, "url": public(step.get("result_url") or step.get("url"), 2000),
                 "observed": public(f"Step {number}: {fact}")}
        evidence.append(entry)
        by_step[number] = entry
    checkpoints = []
    proofs = [(n, p) for n, s in enumerate(steps, 1) for p in ([s["checkpoint_evidence"]] if s.get("checkpoint_evidence") else []) + s.get("additional_checkpoint_evidence", [])]
    for number, checkpoint in enumerate(state.get("checkpoints", [])[:4], 1):
        expected_marker = checkpoint.get("text_contains") or checkpoint.get("url_contains")
        proof = next((p for n, p in proofs if n in by_step and p.get("step") == n and p.get("checkpoint") == number and
                      p.get("signal") in {"navigation", "public_text"} and expected_marker and
                      " ".join(str(p.get("matched", "")).casefold().split()) == " ".join(expected_marker.casefold().split())), None)
        refs = []
        actual = None
        if proof:
            actual = public(proof["matched"])
            ref = f"milestone:{number}"
            evidence.append({"id": ref, "source": "milestone", "step": proof.get("step"), "url": public(proof.get("url"), 2000), "observed": actual})
            refs = [ref]
        checkpoints.append({"description": public(checkpoint.get("description"), 200),
                            "expected_result": public(expected_marker, 300) or None,
                            "actual_result": actual, "status": "passed" if proof else "unconfirmed", "evidence_refs": refs})
    issues = []
    ids = finding_ids(findings)
    for index, finding in enumerate(findings):
        cited = {int(n) for n in re.findall(r"\d+", " ".join(re.findall(r"steps?\s*[\d,\s and]+", finding.get("evidence") or "", re.IGNORECASE)))}
        refs = [by_step[n] for n in sorted(cited & problems) if n in by_step][:10] if finding["kind"] == "ux" else []
        source = "browser_observation"
        if not refs:
            if finding in code_findings:
                entry = {"id": f"scanner:{index}", "source": "scanner", "finding_index": index,
                         "observed": public(finding.get("evidence") or f"The {finding['kind']} check reported rule {finding.get('rule') or ids[index]}.")}
                source = "scanner"
            elif not steps and state.get("first_impression"):
                entry = {"id": f"impression:{index}", "source": "first_impression",
                         "observed": public("Recorded first-impression interpretation: " + str(state["first_impression"].get("what", "")))}
                source = "subjective"
            else:
                raise ValueError("Finding has no permitted report evidence")
            evidence.append(entry)
            refs = [entry]
        facts = [r["observed"] for r in refs]
        last_step = max((r.get("step", 0) for r in refs), default=0)
        reproduction = [public(f"Step {n}: {steps[n - 1].get('action')} {steps[n - 1].get('target_label', '')}", 300)
                        for n in sorted(by_step) if n <= last_step][-20:]
        if source == "scanner":
            reproduction = [public(f"Repeat the same {finding['kind']} check ({finding.get('rule') or ids[index]}) on the recorded page/scope.", 300)]
        elif source == "subjective":
            reproduction = ["Read the same recorded start-page text; this is a subjective first impression, not a verified functional defect."]
        expected = checkpoints[-1]["expected_result"] if checkpoints and source == "browser_observation" else None
        acceptance = ("Repeat the recorded browser flow and inspect the declared expected result: " + expected
                      if expected else "Repeat the recorded check within the same scope; inspect the original evidence and confirm this observation is resolved. Functional expectations remain unknown unless the owner declares them.")
        issues.append({"id": ids[index], "finding_index": index, "observation_type": source, "observed_facts": facts,
                       "expected_result": expected, "actual_result": "; ".join(facts)[:4000], "interpretation": public(finding["detail"], 600),
                       "cause_hypothesis": None, "proposed_change": public(finding["fix"], 400), "reproduction_steps": reproduction,
                       "acceptance_test": public(acceptance), "evidence_refs": [r["id"] for r in refs]})
    status = state.get("status", "scan")
    completed = bool(checkpoints) and all(c["status"] == "passed" for c in checkpoints)
    outcome = "completed" if completed and status == "done" else "not_tested" if status == "scan" else "blocked" if status in {"captcha", "bot_wall", "safe_stop"} or any(s.get("code") == "site_block" for s in steps) else "unconfirmed"
    audit = state.get("site_audit") or {}
    limitations = ["Public UI evidence does not verify backend persistence, email delivery, authorization or complete application behavior."]
    if not checkpoints and status != "scan":
        limitations.append("No declared checkpoint expectations were retained; journey completion remains unconfirmed.")
    if any(c["expected_result"] is None for c in checkpoints):
        limitations.append("Missing expected results are unknown; no business rule was inferred.")
    if any(i["observation_type"] == "subjective" for i in issues):
        limitations.append("First-impression findings are subjective interpretations, not observed functional failures.")
    if len(by_step) > 20:
        limitations.append("Reproduction lists retain at most 20 recent recorded actions; omitted or unconfirmed actions were not inferred.")
    if audit.get("truncated"):
        limitations.append("The page/time limit truncated the crawl; unaudited pages remain untested.")
    limitations.extend(public(x, 300) for x in state.get("notes", [])[:10])
    assertion_results = []
    if state.get("assertion"):
        from app.agent.assertions import finish

        retained = state.get("assertion_outcome")
        if retained and retained["evidence"].get("step") not in by_step:
            retained = None
        boundary = "site_block" if any(s.get("code") == "site_block" for s in steps) else status
        result = finish(FilterCountAssertion.model_validate(state["assertion"]), retained, boundary)
        if retained:
            record = retained["evidence"]
            # Generic phone-number masking also matches fractional ISO seconds. Keep only the
            # validated structured timestamp after masking all other public evidence text.
            facts = re.sub(r"Dataset time: [^;]+;", "", record["observed"])
            facts = public(facts)
            if result.get("observed_dataset_at"):
                facts += f" Dataset time: {datetime.fromisoformat(result['observed_dataset_at']).isoformat()};"
            evidence.append(record | {"url": public(record.get("url"), 2000), "observed": facts})
        assertion_results.append(result)
        limitations.append("This count assertion checks the declared synthetic filter state only; it does not verify backend persistence, authorization or broader task completion.")
    return ReportAssessment.model_validate({"objective": public(state.get("goal"), 2000), "outcome": outcome, "stop_reason": status,
                                           "coverage": {"checks": checks, "actions_with_outcomes": len(by_step), "declared_checkpoints": len(checkpoints),
                                                        "confirmed_checkpoints": sum(c["status"] == "passed" for c in checkpoints),
                                                        "audited_urls": [public(u, 2000) for u in audit.get("urls", [])[:55]], "crawl_truncated": bool(audit.get("truncated"))},
                                           "limitations": limitations, "checkpoints": checkpoints, "issues": issues, "evidence_index": evidence, "assertions": assertion_results})
