"""Launch Ready score: one number from the areas a report actually measured (ARCHITECTURE.md `share-loop`).

Plain code over the stored report, never a model. Ignored findings still count, so the public badge cannot be
gamed by ignoring problems; they only stop repeating in lists.
"""

from app.agent.report_contract import ReportContractError, ensure_supported
from app.agent.schema import ReportAssessment

WEIGHTS = {"ux": 30, "security": 20, "geo": 20, "seo": 15, "speed": 15}
PENALTY = {"high": 25, "medium": 10, "low": 3}


def _journey(report: dict, status: str) -> tuple[bool, list[dict], int]:
    """Only a matching, supported assessment can establish completion or observed journey defects.

    Legacy stop labels contain no completion proof. Keep their static measurements, but do not infer a journey
    outcome. An interrupted run may still retain a genuine earlier browser-observed UX issue.
    """
    if status == "scan" or report.get("version") != 2:
        return False, [], 0
    try:
        ensure_supported(report)
    except ReportContractError:
        return False, [], 0
    assessment = ReportAssessment.model_validate(report["assessment"])
    if assessment.stop_reason != status:
        return False, [], 0
    findings = report.get("findings") or []
    observed = [findings[i.finding_index] for i in assessment.issues
                if i.observation_type == "browser_observation" and findings[i.finding_index]["kind"] == "ux"]
    records = {e.id: e for e in assessment.evidence_index}
    completed = assessment.outcome == "completed" and status == "done"
    if completed:
        for checkpoint in assessment.checkpoints:
            milestone = records[checkpoint.evidence_refs[0]]
            step = records.get(f"step:{milestone.step}")
            matches = " ".join(milestone.observed.casefold().split()) == " ".join(checkpoint.expected_result.casefold().split())
            if not matches or not step or step.source != "step" or not milestone.url or step.url != milestone.url:
                completed = False
                break
    return completed, observed, assessment.coverage.actions_with_outcomes


def _penalised(findings: list[dict], kinds: set[str], base: int = 100) -> int:
    return max(0, base - sum(PENALTY.get(f.get("severity"), 0) for f in findings if f.get("kind") in kinds))


def launch_ready(report: dict, status: str) -> dict:
    """{"score": 0-100 or None, "areas": {area: 0-100 or None}}. None means not measured."""
    findings, checks = report.get("findings") or [], report.get("checks") or {}
    completed, observed, _ = _journey(report, status)
    done = lambda *names: any(checks.get(n) == "complete" for n in names)
    geo = report.get("geo") or {}
    areas = {
        "ux": _penalised(observed, {"ux"}, 100 if completed else 50) if completed or observed else None,
        "security": _penalised(findings, {"security"}) if done("security") else None,
        "geo": geo.get("score") if done("geo") and geo.get("score") is not None else None,
        "seo": _penalised(findings, {"seo"}) if done("seo") else None,
        "speed": _penalised(findings, {"performance", "accessibility"}) if done("performance", "accessibility") else None,
    }
    measured = {k: v for k, v in areas.items() if v is not None}
    total = sum(WEIGHTS[k] for k in measured)
    return {"score": round(sum(WEIGHTS[k] * v for k, v in measured.items()) / total) if total else None, "areas": areas}


# Agent readiness (P1.7): can an AI agent (a browsing assistant, Operator-style tools, a WebMCP client) use the site?
AGENT_NAME_RULES = {"label", "button-name", "link-name", "input-button-name", "aria-input-field-name", "select-name", "aria-command-name",
                    "aria-toggle-field-name", "aria-tooltip-name", "summary-name"}


def _name_problems(report: dict, steps: list[dict]) -> int:
    rules = {i.get("rule") for s in steps for i in ((s.get("diagnostics") or {}).get("accessibility") or {}).get("issues") or []}
    found = {f.get("rule") for f in report.get("findings") or []}
    return len(rules & AGENT_NAME_RULES) + len({"a11y.control.name_missing", "a11y.axe.label", "a11y.axe.button_name", "a11y.axe.link_name"} & found)


def agent_ready(report: dict, status: str, steps: list[dict] | None = None, previous: dict | None = None) -> dict:
    """{"score": 0-100 or None, "parts": [...]} from evidence the report already holds; never a model.

    Parts: the journey reached its goal (25), no CAPTCHA in the way (15), fields and buttons with names an agent can read
    (25), homepage forms fully labelled, with a bonus for WebMCP-declared tools (15), a WebSite SearchAction (10), and the
    same journey working again on a rerun (10). A part with no evidence is left out, not scored as zero."""
    steps = steps or []
    checks = report.get("checks") or {}
    signals = (report.get("geo") or {}).get("agent") or {}
    completed, observed, actions = _journey(report, status)
    parts: list[dict] = []

    def part(pid: str, label: str, earned: float, most: int, note: str) -> None:
        parts.append({"id": pid, "label": label, "earned": round(earned), "max": most, "note": note})

    if completed:
        part("goal", "The test user reached the goal", 25, 25, "The declared UI checkpoints have matching recorded evidence; backend behavior is not verified.")
    elif observed:
        part("goal", "The test user reached the goal", 0, 25, "Completion is unconfirmed; the recorded journey contains an observed site UX issue.")

    if status in {"captcha", "bot_wall"}:
        part("captcha", "No CAPTCHA before the value", 0, 15, "A human check or bot wall stopped the journey; Walkthru does not bypass it.")
    elif completed:
        part("captcha", "No CAPTCHA before the value", 15, 15, "No CAPTCHA stopped the confirmed UI journey.")
    elif "captcha" in signals:
        part("captcha", "No CAPTCHA before the value", 0 if signals.get("captcha") else 15, 15,
             "A CAPTCHA widget loads on the homepage." if signals.get("captcha") else "No CAPTCHA widget on the homepage.")

    if checks.get("accessibility") == "complete" or any(s.get("diagnostics") for s in steps):
        problems = _name_problems(report, steps)
        part("names", "Buttons, links and fields have names", max(0, 25 - 8 * problems), 25,
             "Every control checked has an accessible name." if not problems else f"{problems} kind{'s' if problems > 1 else ''} of unnamed control found; agents read these names to act.")

    if signals.get("fields"):
        ratio = signals.get("named_fields", 0) / signals["fields"]
        webmcp = bool(signals.get("webmcp"))
        part("forms", "Labelled forms (WebMCP-style)", 12 * ratio + (3 if webmcp else 0), 15,
             f"{signals.get('named_fields', 0)} of {signals['fields']} homepage fields are labelled" + ("; forms declare WebMCP tools." if webmcp else "; no WebMCP tool declarations yet."))

    if checks.get("geo") == "complete" and signals:
        part("search", "Site search declared (SearchAction)", 10 if signals.get("search_action") else 0, 10,
             "The homepage declares a WebSite SearchAction." if signals.get("search_action") else "No WebSite SearchAction in the structured data.")

    if previous is not None and completed:
        prior_completed, _, before = _journey(previous.get("report") or {}, previous.get("status", ""))
        if prior_completed:
            stable = abs(before - actions) <= max(2, round(0.3 * max(before, actions)))
            part("stable", "Works the same on a rerun", 10 if stable else 3, 10,
                 f"Both runs confirmed their UI checkpoints; the last recorded {before} actions, this one {actions}.")

    total = sum(p["max"] for p in parts)
    return {"score": round(100 * sum(p["earned"] for p in parts) / total) if total else None, "parts": parts}


def band(value: int | None) -> str:
    if value is None:
        return "Not measured"
    return "Launch ready" if value >= 85 else "Almost ready" if value >= 60 else "Needs work"


def badge_svg(value: int | None) -> str:
    """A 20px status badge for the owner's footer or README. Hex values mirror DESIGN.md tokens (ink, accent, muted,
    danger) because the SVG renders on other people's sites, outside our CSS. Verdana keeps widths predictable there."""
    label, text = "Walkthru", f"Launch Ready {value}" if value is not None else "Launch Ready ?"
    colour = "#63636b" if value is None else "#4d7274" if value >= 85 else "#63636b" if value >= 60 else "#a33b3b"
    left, right = 10 + round(len(label) * 6.6), 10 + round(len(text) * 6.6)
    width = left + right
    title = f"Walkthru Launch Ready score: {value if value is not None else 'not measured'} of 100. {band(value)}."
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="20" role="img" aria-label="{title}">'
        f"<title>{title}</title>"
        f'<clipPath id="r"><rect width="{width}" height="20" rx="10"/></clipPath>'
        f'<g clip-path="url(#r)"><rect width="{left}" height="20" fill="#1b1b1f"/><rect x="{left}" width="{right}" height="20" fill="{colour}"/></g>'
        f'<g fill="#f4f4f5" font-family="Verdana,DejaVu Sans,sans-serif" font-size="11" text-anchor="middle">'
        f'<text x="{left / 2}" y="14" textLength="{left - 12}">{label}</text>'
        f'<text x="{left + right / 2}" y="14" textLength="{right - 12}">{text}</text></g></svg>'
    )
