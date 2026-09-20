"""Report graph: first impression and deterministic launch checks run in parallel, then synthesize.

Used for both a finished persona run (steps present) and an Instant Scan (no steps).
Only first_impression and synthesize call the LLM; the scans are plain code.
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agent.schema import Finding, FirstImpression, Report, Synthesis
from app.scans import accessibility, fetch, performance, security, seo


class ReportState(TypedDict, total=False):
    site: str
    goal: str
    persona: str
    status: str  # persona outcome, or "scan"
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
    synthesis: dict
    tokens: Annotated[int, operator.add]
    notes: Annotated[list[str], operator.add]  # non-fatal problems, e.g. a scan that could not fetch


def first_impression(state: ReportState) -> dict:
    from app.agent import runtime

    messages = [
        ("system", "You are a stranger landing on a website for the first time. You have five seconds. Answer plainly, in the second person about the site owner ('your site'). Do not invent features that are not on the page."),
        ("human", f"Homepage text of {state['site']}:\n\n{state.get('page_text', '')[:5000]}"),
    ]
    fi, used = runtime.call(FirstImpression, messages)
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


def render_steps(steps: list[dict]) -> str:
    return "\n".join(f"{i + 1}. [{s['action']}{' #' + str(s['target_id']) if s.get('target_id') is not None else ''}] confusion {s.get('confusion', 0)}/3 at {s.get('url', '?')}: {s['thought']}" for i, s in enumerate(steps))


def synthesize(state: ReportState) -> dict:
    from app.agent import runtime

    code_findings = [
        Finding.model_validate(f)
        for f in state.get("accessibility", []) + state.get("performance", []) + state.get("seo", []) + state.get("security", [])
    ]
    steps = state.get("steps", [])
    fi = state.get("first_impression") or {}
    context = [
        f"Site: {state['site']}",
        f"First impression: {fi.get('what', '?')} For: {fi.get('who', '?')} Clarity {fi.get('clarity', '?')}/3. Trust: {', '.join(fi.get('trust', []))}",
        "Scan findings (already in the report, do not repeat them as UX findings):\n" + "\n".join(f"- [{f.kind}/{f.severity}] {f.title}" for f in code_findings),
    ]
    if steps:
        context.append(f"Test user: {state.get('persona')}. Goal: {state.get('goal')}. Outcome: {state.get('status')}.\nSteps:\n{render_steps(steps)}")
        task = "Write UX findings for where the test user hesitated, looped, hit errors or gave up; cite the step number as evidence. Then a summary and the top fixes across everything."
    else:
        context.append("No test user run; this is an Instant Scan of the homepage only.")
        task = "No UX findings from steps (leave ux_findings empty unless the first impression reveals a clarity problem). Write the summary and the top fixes across the first impression and scan findings."
    messages = [
        ("system", "You write short, concrete website reports for busy developers. Plain words, no jargon, no em dashes, no praise padding. Every fix is one actionable sentence."),
        ("human", "\n\n".join(context) + "\n\n" + task),
    ]
    syn, used = runtime.call(Synthesis, messages)
    findings = [f.model_copy(update={"kind": "ux"}) for f in syn.ux_findings] + code_findings
    order = {"high": 0, "medium": 1, "low": 2}
    findings.sort(key=lambda f: order[f.severity])
    report = Report(
        summary=syn.summary,
        first_impression=FirstImpression.model_validate(fi) if fi else None,
        findings=findings,
        top_fixes=syn.top_fixes[:5],
        verified=state.get("verified", False),
        tokens=state.get("tokens", 0) + used,
        checks={
            "accessibility": "complete" if state.get("accessibility_measured", False) else "unavailable",
            "performance": "complete" if state.get("performance_measured", False) else "unavailable",
            "seo": "complete" if state.get("seo_measured", False) else "unavailable",
            "security": "complete" if state.get("security_measured", False) else "unavailable",
        },
    )
    return {"synthesis": report.model_dump(), "tokens": used}


def build_graph():
    g = StateGraph(ReportState)
    g.add_node("first_impression", first_impression)
    g.add_node("seo_scan", seo_scan)
    g.add_node("security_scan", security_scan)
    g.add_node("accessibility_scan", accessibility_scan)
    g.add_node("performance_scan", performance_scan)
    g.add_node("synthesize", synthesize)
    for n in ("first_impression", "accessibility_scan", "performance_scan", "seo_scan", "security_scan"):
        g.add_edge(START, n)
        g.add_edge(n, "synthesize")
    g.add_edge("synthesize", END)
    return g.compile()


_graph = None


def run_report(site: str, page_text: str, *, goal: str = "", persona: str = "", status: str = "scan", steps: list[dict] | None = None, verified: bool = False) -> Report:
    global _graph
    _graph = _graph or build_graph()
    out = _graph.invoke({"site": site, "page_text": page_text, "goal": goal, "persona": persona, "status": status, "steps": steps or [], "verified": verified, "tokens": 0, "notes": []})
    report = Report.model_validate(out["synthesis"])
    report.tokens = out["tokens"]
    return report
