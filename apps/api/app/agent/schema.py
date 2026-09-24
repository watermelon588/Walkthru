"""Wire contracts between the extension and the persona agent."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Action = Literal["click", "type", "scroll", "back", "done", "give_up"]


class Element(BaseModel):
    id: int
    tag: str  # a, button, input, select, textarea
    text: str = ""  # visible text or aria-label, already redacted client side
    type: str | None = None  # input type
    state: Literal["filled", "empty", "checked", "unchecked"] | None = None  # form fields only; never the value


class WebVitals(BaseModel):
    """Core Web Vitals observed in the real browser so far."""

    lcp_ms: int | None = Field(default=None, ge=0, le=600_000)
    cls: float | None = Field(default=None, ge=0, le=100)
    inp_ms: int | None = Field(default=None, ge=0, le=600_000)


class AccessibilityIssue(BaseModel):
    rule: str = Field(max_length=100)
    severity: Literal["high", "medium", "low"]
    message: str = Field(max_length=300)
    target: str | None = Field(default=None, max_length=300)


class AccessibilityAudit(BaseModel):
    status: Literal["complete", "unavailable"]
    total: int = Field(ge=0, le=500)
    issues: list[AccessibilityIssue] = Field(default_factory=list, max_length=12)


class BrowserDiagnostics(BaseModel):
    captured_at: datetime
    accessibility: AccessibilityAudit
    web_vitals: WebVitals = Field(default_factory=WebVitals)


class Observation(BaseModel):
    """One page snapshot from the content script. PII is masked before upload."""

    url: str
    title: str = ""
    elements: list[Element] = Field(default_factory=list)
    text: str = ""  # visible text, trimmed client side
    errors: list[str] = Field(default_factory=list)  # visible error messages
    notices: list[str] = Field(default_factory=list)  # visible confirmations, e.g. 'Message sent'
    note: str | None = None  # executor feedback: "element not found", "captcha", ...
    diagnostics: BrowserDiagnostics | None = None
    scroll_pct: int | None = Field(default=None, ge=0, le=100)  # how far down the page the viewport is
    at_end: bool | None = None  # the viewport reaches the bottom of the page


class StepEvidence(BaseModel):
    """Private visual proof captured after one browser action."""

    screenshot_path: str = Field(pattern=r"^[a-f0-9]{32}/step-\d{2}\.jpg$", max_length=80)
    captured_at: datetime
    result_url: str = Field(pattern=r"^https?://", max_length=2000)
    width: int = Field(ge=1, le=10000)
    height: int = Field(ge=1, le=10000)
    note: str | None = Field(default=None, max_length=300)


class PersonaStep(BaseModel):
    """What the test user thinks and does next. Exactly one action per step."""

    thought: str = Field(description="Think aloud, in character, one or two sentences.")
    action: Action
    target_id: int | None = Field(default=None, description="Element id for click/type.")
    text: str | None = Field(default=None, description="Text to type, for type only.")
    confusion: int = Field(ge=0, le=3, description="0 clear, 1 hesitant, 2 confused, 3 stuck")
    progress: int = Field(default=0, ge=0, le=4, description="How many checklist items are complete, counting what your previous actions achieved.")


class Checkpoint(BaseModel):
    description: str = Field(max_length=200, description="One observable milestone, in plain words.")
    url_contains: str | None = Field(default=None, max_length=100, description="Part of the URL that is only true once this checkpoint is reached, e.g. '/pricing'. Null unless you are sure.")


class GoalPlan(BaseModel):
    """The owner's goal as intent plus an ordered checklist (app/agent/goal.py)."""

    intent: str = Field(max_length=300, description="What the owner wants to learn about their site, in one sentence.")
    checkpoints: list[Checkpoint] = Field(max_length=4, description="1 to 4 milestones in order; the last one finishes the test.")
    feasible: bool = Field(description="False only if the goal asks to pay, delete, cancel, spam, attack or bypass security, or is about another website.")
    refusal: str | None = Field(default=None, max_length=300, description="Why the goal cannot run, when feasible is false.")


class Finding(BaseModel):
    """One problem in the report. Deterministic scans and the synthesis LLM both produce these."""

    kind: Literal["ux", "accessibility", "performance", "seo", "security", "geo"]
    severity: Literal["high", "medium", "low"]
    title: str = Field(max_length=120)
    detail: str = Field(max_length=600)
    fix: str = Field(max_length=400)
    evidence: str | None = Field(default=None, max_length=300, description="Step number, URL, header or snippet that shows it.")


class FirstImpression(BaseModel):
    """What a stranger takes from the homepage in five seconds."""

    what: str = Field(description="What this site does, in one plain sentence, as a stranger would put it.")
    who: str = Field(description="Who it seems to be for.")
    first_click: str = Field(description="What they would click first and why.")
    trust: list[str] = Field(description="Trust signals noticed, or notably missing.", max_length=5)
    clarity: int = Field(ge=0, le=3, description="0 = instantly clear, 3 = no idea what this is.")


class Synthesis(BaseModel):
    """The LLM's half of the report; code merges it with scan findings."""

    summary: str = Field(description="Three or four sentences: what happened, where it hurt, what to do first.")
    ux_findings: list[Finding] = Field(description="Problems the test user hit, each citing the step number.", max_length=8)
    top_fixes: list[str] = Field(description="Up to five fixes ranked by impact, across UX, SEO and security.", max_length=5)


class SiteAuditSummary(BaseModel):
    """Bounded crawl coverage included with new reports. Absent on legacy reports."""

    # Paid crawls reach 50 pages (site.PAID_MAX_PAGES), plus up to 5 pages the test user visited (site.MAX_VISITED).
    pages_scanned: int = Field(ge=0, le=55)
    page_limit: int = Field(ge=1, le=50)
    duration_ms: int = Field(ge=0)
    truncated: bool
    urls: list[str] = Field(default_factory=list, max_length=55)
    robots_respected: bool = True


class GeoCategory(BaseModel):
    id: str
    label: str
    earned: int = Field(ge=0)
    max: int = Field(ge=1)


class GeoSummary(BaseModel):
    """AI search readiness (app/scans/geo.py). Findings live in the report's findings list with kind "geo"."""

    score: int = Field(ge=0, le=100)
    band: Literal["critical", "foundation", "good", "excellent"]
    categories: list[GeoCategory]
    ai_words: int = Field(ge=0, description="Words of homepage text an AI crawler gets before JavaScript runs.")
    ai_view: str = Field(default="", description="The start of that text, as the crawler reads it.")
    notes: list[str] = Field(default_factory=list)
    fixes: list[dict] = Field(default_factory=list)  # GEO fix pack: id, title, file, code, note (one on free reports)
    fixes_total: int = 0


class ComparedFinding(BaseModel):
    kind: str
    severity: str
    title: str
    fingerprint: str
    pages_fixed: list[str] = Field(default_factory=list)  # pages where it is gone this run
    pages_new: list[str] = Field(default_factory=list)  # pages where it appeared this run
    pages_unchecked: list[str] = Field(default_factory=list)  # earlier pages this run did not audit


class Comparison(BaseModel):
    """Against the previous run of the same goal on the same site (app/agent/compare.py). Paid plans only."""

    previous_run_id: str
    previous_at: str
    fixed: list[ComparedFinding] = Field(default_factory=list)
    still_broken: list[ComparedFinding] = Field(default_factory=list)
    new: list[ComparedFinding] = Field(default_factory=list)
    not_rechecked: list[ComparedFinding] = Field(default_factory=list)  # gone only because its pages were not audited


class LaunchReady(BaseModel):
    score: int | None = Field(default=None, ge=0, le=100)  # None when no area was measured
    areas: dict[str, int | None] = Field(default_factory=dict)  # ux, security, geo, seo, speed; None = not measured


class Report(BaseModel):
    summary: str
    first_impression: FirstImpression | None = None
    findings: list[Finding]
    top_fixes: list[str]
    verified: bool = False
    tokens: int = 0
    checks: dict[str, Literal["complete", "unavailable"]] = Field(default_factory=dict)
    site_audit: SiteAuditSummary | None = None
    geo: GeoSummary | None = None
    comparison: Comparison | None = None
    model: str | None = None  # which models ran the test and wrote the report, shown on the report
    pages: dict[str, list[str]] = Field(default_factory=dict)  # finding fingerprint -> every affected page
    launch_ready: LaunchReady | None = None  # app/agent/score.py; absent on reports written before 2026-09-24
