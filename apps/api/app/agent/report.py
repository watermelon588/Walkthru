"""Report graph: first impression and deterministic launch checks run in parallel, then synthesize.

Used for both a finished persona run (steps present) and an Instant Scan (no steps).
Only first_impression and synthesize call the LLM; the scans are plain code.
"""

from __future__ import annotations

import operator
import re
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agent import compare, score
from app.agent.schema import Finding, FirstImpression, LaunchReady, Report, Synthesis
from app.scans import accessibility, email, fetch, performance, security, seo, site


class ReportState(TypedDict, total=False):
    site: str
    goal: str
    persona: str
    status: str  # persona outcome, or "scan"
    intent: str  # the goal as the planner understood it
    steps: list[dict]
    page_text: str  # visible homepage text (from the first observation, or fetched)
    verified: bool
    first_impression: dict
    seo: list[dict]
    security: list[dict]
    accessibility: list[dict]
    performance: list[dict]
    accessibility_measured: bool
    performance_measured: bool
    seo_measured: bool
    security_measured: bool
    site_audit: dict
    geo: list[dict]
    geo_summary: dict
    finding_pages: dict  # finding fingerprint -> every affected page (code only, never the model)
    paid: bool  # paid plans get GEO scored on every audited page, free on the homepage
    production_like: bool
    final_controls: list[str]  # labels of the buttons, links and fields on the page where the journey ended
    synthesis: dict
    tokens: Annotated[int, operator.add]
    notes: Annotated[list[str], operator.add]  # non-fatal problems, e.g. a scan that could not fetch


def first_impression(state: ReportState) -> dict:
    from app.agent import runtime

    text = state.get("page_text", "")
    if len(text.strip()) < fetch.MIN_TEXT:
        # Nothing readable (usually a JavaScript-only page seen without a browser). Asking a model here
        # only produces invented detail, so the report says what it could not judge instead.
        return {"first_impression": {}, "notes": ["first impression skipped: no readable page text"]}
    messages = [
        ("system", "You are a stranger landing on a website for the first time. You have five seconds and you only see the page text below, not its design. Answer plainly, in the second person about the site owner ('your site'). Only mention things present in the text; never describe visuals, layout, colours or typography."),
        ("human", f"Homepage text of {state['site']}:\n\n{state.get('page_text', '')[:5000]}"),
    ]
    fi, used = runtime.call(FirstImpression, messages, paid=state.get("paid", False))
    return {"first_impression": fi.model_dump(), "tokens": used}


def _scan(state: ReportState, which: str) -> dict:
    try:
        fetch.assert_public(state["site"])
        with fetch.client() as c:
            if which == "performance":
                findings, measured = performance.scan(state["site"], c)
                return {which: [f.model_dump() for f in findings], "performance_measured": measured}
            resp = fetch.get(c, state["site"])
            if resp is None:
                return {which: [], f"{which}_measured": False, "notes": [f"{which} scan: site did not respond"]}
            if which == "seo":
                findings = seo.scan(str(resp.url), c, html=resp.text)
            elif which == "security":
                findings = security.scan(state["site"], c, state.get("verified", False), resp=resp)
            elif which == "accessibility":
                if fetch.is_js_shell(resp.text):
                    # An empty shell always "passes"; only the extension's real-browser audit can measure it.
                    return {which: [], f"{which}_measured": False, "notes": ["accessibility: page is rendered by JavaScript"]}
                findings = accessibility.scan(resp.text, str(resp.url))
        return {which: [f.model_dump() for f in findings], f"{which}_measured": True}
    except Exception as e:  # noqa: BLE001 - a failed scan must not sink the report
        return {which: [], f"{which}_measured": False, "notes": [f"{which} scan failed: {e}"]}


def seo_scan(state: ReportState) -> dict:
    return _scan(state, "seo")


def security_scan(state: ReportState) -> dict:
    return _scan(state, "security")


def accessibility_scan(state: ReportState) -> dict:
    return _scan(state, "accessibility")


def performance_scan(state: ReportState) -> dict:
    return _scan(state, "performance")


def site_scan(state: ReportState) -> dict:
    """Crawl once, then feed both SEO and passive-security report branches."""
    try:
        fetch.assert_public(state["site"])
        with fetch.client() as c:
            visited = [u for s in state.get("steps", []) for u in (s.get("url"), s.get("result_url")) if u]
            paid = state.get("paid", False)
            result = site.audit(state["site"], c, verified=state.get("verified", False), geo_full=paid, visited=visited,
                                max_pages=site.PAID_MAX_PAGES if paid else site.DEFAULT_MAX_PAGES,
                                time_limit=site.PAID_TIME_LIMIT if paid else site.DEFAULT_TIME_LIMIT)
            mail, mail_note = email.check(state["site"], c, full=state.get("paid", False))
        return {
            "seo": [finding.model_dump() for finding in result.seo],
            "geo": [finding.model_dump() for finding in result.geo.findings] if result.geo else [],
            "geo_summary": result.geo.summary() if result.geo else {},
            "finding_pages": {compare.fingerprint({"kind": kind, "title": title}): urls for kind, title, urls in result.pages},
            "security": [finding.model_dump() for finding in result.security + mail],
            "notes": [mail_note] if mail_note else [],
            "seo_measured": result.coverage.pages_scanned > 0,
            "security_measured": result.coverage.pages_scanned > 0,
            "production_like": result.production_like,
            "site_audit": {
                "pages_scanned": result.coverage.pages_scanned,
                "page_limit": result.coverage.page_limit,
                "duration_ms": result.coverage.duration_ms,
                "truncated": result.coverage.truncated,
                "urls": result.coverage.urls,
                "robots_respected": True,
            },
        }
    except Exception as error:  # noqa: BLE001 - a failed audit must not sink the report
        return {
            "seo": [],
            "security": [],
            "seo_measured": False,
            "security_measured": False,
            "notes": [f"site audit failed: {error}"],
        }


def render_steps(steps: list[dict]) -> str:
    """Each step with where it started, where it ended and what the page showed afterwards."""
    lines = []
    for i, s in enumerate(steps):
        target = f" #{s['target_id']}" if s.get("target_id") is not None else ""
        line = f"{i + 1}. [{s['action']}{target}] confusion {s.get('confusion', 0)}/3 at {s.get('url', '?')}: {s['thought']}"
        if s.get("interrupted"):
            line += " (interrupted before confirmation)"
        if s.get("result_url"):
            moved = s["result_url"] != s.get("url")
            line += f" -> ended on {s['result_url']}{' (navigation worked)' if moved else ''}"
        if s.get("errors_after"):
            line += f"; page then showed: {' | '.join(s['errors_after'])}"
        if s.get("notices_after"):
            line += f"; page then confirmed: {' | '.join(s['notices_after'])}"
        if s.get("note_after"):
            line += f"; executor: {s['note_after']}"
        if s.get("safe_stop"):
            line += " [Walkthru stopped here on purpose; not a site problem]"
        lines.append(line)
    return "\n".join(lines)


def browser_findings(steps: list[dict]) -> tuple[list[Finding], bool, bool]:
    """Turn real-browser diagnostics into bounded, step-specific report findings."""
    findings: list[Finding] = []
    rules: dict[str, dict] = {}  # one finding per failing rule, listing every element and step it hit
    accessibility_measured = False
    performance_measured = False
    worst: dict[str, tuple[float, int, str]] = {}
    rank = {"low": 0, "medium": 1, "high": 2}

    for index, step in enumerate(steps, start=1):
        diagnostics = step.get("diagnostics") or {}
        accessibility = diagnostics.get("accessibility") or {}
        if accessibility.get("status") == "complete":
            accessibility_measured = True
        for issue in accessibility.get("issues", []):
            rule = issue.get("rule", "browser-audit")
            severity = issue.get("severity") if issue.get("severity") in rank else "medium"
            entry = rules.setdefault(rule, {"message": issue.get("message"), "severity": severity, "targets": [], "steps": [], "url": step.get("url", "?")})
            if rank[severity] > rank[entry["severity"]]:
                entry["severity"] = severity
            if issue.get("target") and issue["target"] not in entry["targets"]:
                entry["targets"].append(issue["target"])
            if index not in entry["steps"]:
                entry["steps"].append(index)

        vitals = diagnostics.get("web_vitals") or {}
        for metric in ("lcp_ms", "cls", "inp_ms"):
            value = vitals.get(metric)
            if value is None:
                continue
            performance_measured = True
            if metric not in worst or value > worst[metric][0]:
                worst[metric] = (float(value), index, step.get("url", "?"))

    for rule, e in rules.items():
        targets = e["targets"] or ["the affected element"]
        shown = ", ".join(targets[:3]) + (f" +{len(targets) - 3} more" if len(targets) > 3 else "")
        findings.append(
            Finding(
                kind="accessibility",
                severity=e["severity"],
                title=(e["message"] or f"Accessibility rule {rule} failed")[:120],
                detail=f"The real-browser audit found the {rule} rule failing on {len(targets)} element{'s' if len(targets) != 1 else ''}: {shown}."[:600],
                fix=f"Fix each listed element so it passes the {rule} rule, then rerun this journey.",
                evidence=f"step {', '.join(map(str, e['steps'][:5]))}: {e['url']}"[:300],
            )
        )

    performance_rules = {
        "lcp_ms": (2500, 4000, "Largest Contentful Paint is slow", "Reduce render-blocking work and optimize the largest above-the-fold element."),
        "cls": (0.1, 0.25, "Layout shifts exceed the Core Web Vitals target", "Reserve space for images, embeds and dynamic content before they load."),
        "inp_ms": (200, 500, "Interaction latency is high", "Break up long main-thread tasks and shorten the slow interaction handler."),
    }
    labels = {"lcp_ms": "LCP", "cls": "CLS", "inp_ms": "INP"}
    for metric, (value, index, url) in worst.items():
        good, poor, title, fix = performance_rules[metric]
        if value <= good:
            continue
        severity = "high" if value > poor else "medium"
        shown = f"{round(value):.0f} ms" if metric != "cls" else f"{value:.3f}"
        findings.append(
            Finding(
                kind="performance",
                severity=severity,
                title=title,
                detail=f"The browser observed {labels[metric]} at {shown}; the good threshold is {good} {'ms' if metric != 'cls' else ''}.".strip(),
                fix=fix,
                evidence=f"step {index}: {url}"[:300],
            )
        )

    return findings, accessibility_measured, performance_measured


def _words(text: str) -> set[str]:
    return {w[:5] for w in re.findall(r"[a-z]+", text.lower()) if len(w) > 3}  # crude stem: "framed" ~ "frame"


NOT_A_SITE_PROBLEM = ("working contact method", "not sent:", "safe mode", "never sends twice", "owner declined", "owner pressed stop")


def problem_steps(steps: list[dict], status: str | None = None) -> set[int]:
    """1-based numbers of steps where something observably went wrong. UX findings must cite one of these."""
    out = set()
    for i, s in enumerate(steps, start=1):
        note = (s.get("note_after") or "").lower()
        if s.get("safe_stop"):
            continue
        walkthru_note = any(k in note for k in NOT_A_SITE_PROBLEM)
        # An interruption is only evidence when the browser run broke, not when the owner pressed Stop.
        # no_change: a click that visibly did nothing (a silent submit, a dead button) is evidence too.
        if (s.get("confusion", 0) >= 2 or s.get("errors_after") or s.get("no_change") or (s.get("interrupted") and not walkthru_note) or s.get("action") == "give_up"
                or (note and not walkthru_note)):
            out.add(i)
    if status in ("stuck", "budget"):
        out |= set(range(max(1, len(steps) - 2), len(steps) + 1))
    return out


def grounded_ux(ux: list[Finding], code: list[Finding], steps: list[dict], status: str | None = None) -> list[Finding]:
    """Keep only UX findings the journey supports: they must cite a step where something went wrong
    and must not restate a scan finding. A journey where every step worked yields no UX findings."""
    problems = problem_steps(steps, status)
    kept = []
    for f in ux:
        if steps:
            cited = {int(n) for n in re.findall(r"\d+", " ".join(re.findall(r"steps?\s*[\d,\s and]+", f.evidence or "", re.IGNORECASE)))}
            if not cited & problems:
                continue
        words = _words(f.title)
        if any(words and len(words & _words(c.title)) / len(words | _words(c.title)) >= 0.5 for c in code):
            continue
        if "safe mode" in f"{f.title} {f.detail}".lower():
            continue
        kept.append(f)
    return kept


is_local_site = fetch.is_local_site  # moved to app/scans/fetch.py so scans can use it too


SYNTHESIS_SYSTEM = (
    "You write short, concrete website reports for busy developers. Plain words, no jargon, no em dashes, no praise padding. "
    "Every fix is one actionable sentence. The summary and fixes may only use facts given below: the scan findings, the journey steps and "
    "their outcomes, and the first impression. Never add claims about content, links, testimonials or features you were not shown."
)
LOCAL_NOTE = (
    "This is a local development server. Do not mention HTTPS, security headers, cookies or page speed; "
    "those are judged on the deployed site."
)
# Only these security checks mean something on a dev server (they describe the code, not the host).
CODE_LEVEL_SECURITY = ("is publicly readable", "in a JavaScript bundle")


# Error text a journey can show that comes from the auth provider's mailer, not from the site's own code.
MAILER_LIMITS = (
    ("email rate limit exceeded", "Supabase's built-in email service",
     "Set up your own SMTP provider (for example Resend, Postmark or Amazon SES) in Supabase Auth settings. The built-in mailer is for testing and sends only a few emails an hour."),
)


def mailer_findings(steps: list[dict]) -> list[Finding]:
    """A signup that failed on the auth provider's email sending limit, with the exact fix."""
    for i, s in enumerate(steps, start=1):
        for error in s.get("errors_after") or []:
            for pattern, who, fix in MAILER_LIMITS:
                if pattern in error.lower():
                    return [Finding(kind="ux", severity="high", title="Signup emails hit your auth provider's sending limit",
                                    detail=f"The page showed \"{error}\". That message comes from {who}, which sends only a few emails an hour, so real visitors cannot sign up or get their confirmation email.",
                                    fix=fix, evidence=f"Step {i}: page then showed: {error}"[:300])]
    return []


def synthesis_inputs(state: ReportState) -> dict:
    """Everything the report writer is given, built from graph state. Shared by synthesize and model evals."""
    journey_findings, browser_accessibility, browser_performance = browser_findings(state.get("steps", []))
    code_findings = journey_findings + mailer_findings(state.get("steps", [])) + [
        Finding.model_validate(f)
        for f in state.get("accessibility", []) + state.get("performance", []) + state.get("seo", []) + state.get("geo", []) + state.get("security", [])
    ]
    local = is_local_site(state["site"]) and not state.get("production_like")
    if local:
        code_findings = [
            f for f in code_findings
            if f.kind != "performance" and (f.kind != "security" or any(k in f.title for k in CODE_LEVEL_SECURITY))
        ]
    steps = state.get("steps", [])
    fi = state.get("first_impression") or {}
    context = [
        *([LOCAL_NOTE] if local else []),
        f"Site: {state['site']}",
        (f"First impression: {fi.get('what', '?')} For: {fi.get('who', '?')} Clarity {fi.get('clarity', '?')}/3. Trust: {', '.join(fi.get('trust', []))}"
         if fi else "First impression: not available, the page had no readable text without JavaScript. Do not guess what the site looks like or contains."),
        "Scan findings (already in the report, do not repeat them as UX findings):\n" + "\n".join(f"- [{f.kind}/{f.severity}] {f.title}" for f in code_findings),
    ]
    audit = state.get("site_audit")
    if audit:
        context.append(f"Site audit coverage: {audit.get('pages_scanned', 0)} pages scanned, limit {audit.get('page_limit', 0)}, truncated: {audit.get('truncated', False)}.")
    if any(f.title == "Homepage content only appears after JavaScript runs" for f in code_findings):
        context.append("Context: the homepage is rendered by JavaScript. Google and screen readers do run JavaScript and see the content; "
                       "link previews (WhatsApp, LinkedIn, Slack), most AI crawlers and simpler search crawlers see an empty page. Do not overstate the impact.")
    if steps:
        outcome = {
            "safe_stop": "stopped by Walkthru at the send button (by design)",
            "looping": "stopped by Walkthru because the test user started going in circles. That is Walkthru's own limit, not a site problem; never report the repeated visits as a site problem",
        }.get(state.get("status", ""), state.get("status"))
        intent = f" Understood as: {state['intent']}." if state.get("intent") else ""
        context.append(f"Test user: {state.get('persona')}. Goal: {state.get('goal')}.{intent} Outcome: {outcome}.\nSteps:\n{render_steps(steps)}")
        context.append("Steps marked as stopped on purpose, or mentioning safe mode, were Walkthru's own choice. They are not site problems; never report them as findings.")
        if state.get("final_controls"):
            context.append("Controls visible on the page where the journey ended: " + "; ".join(state["final_controls"]) +
                           ". Never claim a button, link or option is missing if it appears in this list, even if the test user said so.")
        problems = sorted(problem_steps(steps, state.get("status")))
        context.append(f"Steps where something went wrong: {', '.join(map(str, problems))}. Only these may support UX findings." if problems
                       else "No step went wrong: every action worked. Write no UX findings and do not describe UX problems in the summary.")
        context.append("Judge each step by its outcome: 'ended on' shows where it led and 'page then showed' is the exact error text the user saw. "
                       "Only call something broken or missing when an outcome proves it, and quote that outcome as evidence. "
                       "A step that ended on a new page worked. A field typed and then shown as filled worked.")
        task = "Write UX findings for where the test user hesitated, looped, hit errors or gave up; cite the step number as evidence. Then a summary and the top fixes across everything."
    else:
        context.append("No test user run; this is an Instant Scan of the homepage only.")
        task = "No UX findings from steps (leave ux_findings empty unless the first impression reveals a clarity problem). Write the summary and the top fixes across the first impression and scan findings."
    messages = [
        ("system", SYNTHESIS_SYSTEM),
        ("human", "\n\n".join(context) + "\n\n" + task),
    ]
    return {"messages": messages, "code_findings": code_findings, "local": local, "steps": steps, "fi": fi,
            "browser_accessibility": browser_accessibility, "browser_performance": browser_performance}


def plain(text: str) -> str:
    """House style for model-written text: no em or en dashes (models add them even when told not to)."""
    text = re.sub(r"(?<=\d)\u2013(?=\d)", "-", text)
    return re.sub(r"\s*[\u2014\u2013]\s*", ", ", text)


def synthesize(state: ReportState) -> dict:
    from app.agent import runtime

    inputs = synthesis_inputs(state)
    code_findings, local, steps, fi = inputs["code_findings"], inputs["local"], inputs["steps"], inputs["fi"]
    browser_accessibility, browser_performance = inputs["browser_accessibility"], inputs["browser_performance"]
    syn, used = runtime.call(Synthesis, inputs["messages"], paid=state.get("paid", False))
    written = [f.model_copy(update={"kind": "ux", "title": plain(f.title), "detail": plain(f.detail), "fix": plain(f.fix)})
               for f in grounded_ux(syn.ux_findings, code_findings, steps, state.get("status"))]
    findings = written + code_findings
    order = {"high": 0, "medium": 1, "low": 2}
    findings.sort(key=lambda f: order[f.severity])
    report = Report(
        summary=plain(syn.summary),
        first_impression=FirstImpression.model_validate({k: plain(v) if isinstance(v, str) else [plain(t) for t in v] if isinstance(v, list) else v for k, v in fi.items()}) if fi else None,
        findings=findings,
        top_fixes=[plain(t) for t in syn.top_fixes[:5]],
        verified=state.get("verified", False),
        tokens=state.get("tokens", 0) + used,
        checks={
            "accessibility": "complete" if state.get("accessibility_measured", False) or browser_accessibility else "unavailable",
            "performance": "unavailable" if local else "complete" if state.get("performance_measured", False) or browser_performance else "unavailable",
            "seo": "complete" if state.get("seo_measured", False) else "unavailable",
            "security": "unavailable" if local else "complete" if state.get("security_measured", False) else "unavailable",
            "geo": "complete" if state.get("geo_summary") else "unavailable",
        },
        site_audit=state.get("site_audit"),
        geo=state.get("geo_summary") or None,
        model=runtime.model_label(state.get("paid", False)),
        pages=state.get("finding_pages") or {},
    )
    report.launch_ready = LaunchReady.model_validate(score.launch_ready(report.model_dump(), state.get("status", "scan")))
    return {"synthesis": report.model_dump(), "tokens": used}


def build_graph():
    g = StateGraph(ReportState)
    g.add_node("first_impression", first_impression)
    g.add_node("site_scan", site_scan)
    g.add_node("accessibility_scan", accessibility_scan)
    g.add_node("performance_scan", performance_scan)
    g.add_node("synthesize", synthesize)
    for n in ("first_impression", "accessibility_scan", "performance_scan", "site_scan"):
        g.add_edge(START, n)
        g.add_edge(n, "synthesize")
    g.add_edge("synthesize", END)
    return g.compile()


_graph = None


def run_report(site: str, page_text: str, *, goal: str = "", persona: str = "", status: str = "scan", steps: list[dict] | None = None, verified: bool = False, final_controls: list[str] | None = None, paid: bool = False, intent: str = "") -> Report:
    global _graph
    _graph = _graph or build_graph()
    out = _graph.invoke({"site": site, "page_text": page_text, "goal": goal, "persona": persona, "status": status, "steps": steps or [], "verified": verified, "final_controls": final_controls or [], "paid": paid, "intent": intent, "tokens": 0, "notes": []})
    report = Report.model_validate(out["synthesis"])
    report.tokens = out["tokens"]
    return report
