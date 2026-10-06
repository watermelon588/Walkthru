"""Report chapters (R-S5a): one navigable dossier shared by the web report, CSV, fix prompts and MCP.

Built in code from the saved report, with no model call and no schema change, so legacy reports get chapters too.
Each finding has exactly one primary chapter (from its kind) and may cross-link to chapters a shared cause also
affects. Chapters without data say so; nothing is filled in. Keep in step with apps/web/src/lib/reportChapters.ts:
both are checked against web/tests/fixtures/report-chapters.json.
"""

from app.agent.compare import is_ignored
from app.agent.report_contract import finding_ids

CHAPTERS = (
    ("journey", "Journey and UX"),
    ("accessibility", "Accessibility"),
    ("performance", "Performance"),
    ("seo", "SEO foundations"),
    ("keywords", "Keywords and content"),
    ("authority", "Authority and backlinks"),
    ("geo", "GEO readiness"),
    ("citations", "AI citations"),
    ("security", "Security and email hygiene"),
    ("evidence", "Evidence and coverage"),
)
TITLE = dict(CHAPTERS)
ORDER = {key: n for n, (key, _) in enumerate(CHAPTERS)}
BY_KIND = {"ux": "journey", "accessibility": "accessibility", "performance": "performance", "seo": "seo", "geo": "geo", "security": "security"}
SEVERITY = {"high": 0, "medium": 1, "low": 2}
STATUS_LABEL = {"issues": None, "clear": "No issue observed in scope", "unconfirmed": "Outcome unconfirmed", "not_measured": "Not measured",
                "not_tested": "Not tested", "separate": "Measured separately", "reference": "Reference",
                "advisory": "Advisory, no search data"}


def chapter_of(finding: dict) -> str:
    return BY_KIND.get(finding.get("kind"), "evidence")


def also_affects(finding: dict) -> list[str]:
    """Other chapters one shared cause also affects. Rule ids only: legacy findings without a rule get no cross-link."""
    rule = finding.get("rule") or ""
    if rule.startswith("geo.") and "javascript" in rule:
        return ["seo"]  # content that needs JavaScript: AI crawlers and search previews read the same empty HTML
    if rule == "seo.image.alt_missing":
        return ["accessibility"]
    if rule == "a11y.image.alt_missing":
        return ["seo"]
    return []


def _measured(report: dict, kind: str) -> bool:
    state = (report.get("checks") or {}).get(kind)
    if state:
        return state == "complete"
    # Reports before per-check states: SEO and security always ran; GEO ran when its block is present.
    return kind in {"seo", "security"} or (kind == "geo" and bool(report.get("geo")))


def _count(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def chapters(report: dict, kind: str = "scan", status: str = "done", ignored: dict | set | None = None) -> list[dict]:
    """Every chapter in order: number, key, title, status, label, plain-language summary and its issue ids.
    `kind`/`status` are the run's; `ignored` findings stay listed but do not count as open issues."""
    findings = report.get("findings") or []
    ids = finding_ids(findings)
    assessment = report.get("assessment") or None
    ignored = ignored or {}
    out = []
    for number, (key, title) in enumerate(CHAPTERS, start=1):
        mine = [(fid, f) for fid, f in zip(ids, findings, strict=True) if chapter_of(f) == key]
        open_ = [f for _, f in mine if not is_ignored(f, ignored)]
        high = sum(f["severity"] == "high" for f in open_)
        state, summary = _status(key, title, report, kind, status, assessment, open_, high)
        out.append({"number": number, "key": key, "title": title, "status": state,
                    "label": STATUS_LABEL[state] or _count(len(open_), "open issue"), "summary": summary,
                    "issue_ids": [fid for fid, _ in mine],
                    "cross_links": sorted({fid for fid, f in zip(ids, findings, strict=True) if key in also_affects(f)})})
    return out


def _status(key, title, report, kind, status, assessment, open_, high):
    if key == "keywords" and (report.get("opportunities") or {}).get("pages"):
        mapped = report["opportunities"]
        return "advisory", (f"{_count(len(mapped['pages']), 'page')} mapped from the site's own copy. Intents are hypotheses to confirm; "
                            "no search volume, difficulty, rank or traffic data was used.")
    if key == "keywords":
        return "not_measured", "Not part of this report. Walkthru has no search demand data for this site, so it gives no keyword direction here."
    if key == "authority":
        return "not_measured", "Not part of this report. Backlinks and earned-link opportunities were not measured, and none are invented."
    if key == "citations":
        return "separate", "AI answers are sampled separately, each with its own date, engine and sources. This report does not include them."
    if key == "evidence":
        if assessment:
            return "reference", (f"What was tested and what was not: {_count(len(assessment['evidence_index']), 'evidence record')}, "
                                 f"{_count(len(assessment['coverage']['audited_urls']), 'audited page')} and {_count(len(assessment['limitations']), 'stated limitation')}.")
        return "reference", "Saved before detailed evidence records. Each finding shows its own evidence."
    if open_:
        return "issues", f"{_count(len(open_), 'open issue')}, {high} high priority. Each lists its evidence, the change and how to check it."
    if key == "journey":
        if kind != "test":
            return "not_tested", "No journey ran. This report checks public pages only."
        assertion = next(iter((assessment or {}).get("assertions", [])), None)
        if assertion:
            if assertion["status"] != "passed":
                return "unconfirmed", f"Declared filtered count: {assertion['status']}. UI checkpoint completion is shown separately; inspect the count evidence above."
            return "clear", "The declared synthetic filtered count passed within its dataset, time and tolerance scope. Backend behavior remains unverified."
        if assessment and assessment["outcome"] == "completed":
            return "clear", "The test user reached every declared checkpoint and recorded no journey issue."
        if not assessment and status == "done":  # legacy reports had no declared checkpoints
            return "clear", "The run reached its goal and recorded no journey issue."
        return "unconfirmed", "No journey issue was recorded, but the requested outcome was not confirmed. See the scope above."
    if not _measured(report, key):
        reason = (report.get("check_reasons") or {}).get(key)
        return "not_measured", reason or "This check did not run for this report."
    return "clear", f"Checked within this report's scope and nothing to fix was found. That is not proof of perfect {title.lower()}."


def next_actions(report: dict, ignored: dict | set | None = None, limit: int = 3) -> list[dict]:
    """The first actions to take: open findings by severity, then chapter order, then report order."""
    findings = report.get("findings") or []
    ranked = sorted(((SEVERITY.get(f["severity"], 3), ORDER[chapter_of(f)], i, fid, f)
                     for i, (fid, f) in enumerate(zip(finding_ids(findings), findings, strict=True)) if not is_ignored(f, ignored or {})),
                    key=lambda row: row[:3])
    return [{"id": fid, "chapter": chapter_of(f), "severity": f["severity"], "title": f["title"], "fix": f["fix"]} for *_, fid, f in ranked[:limit]]


def resolve(key: str) -> str:
    """A chapter key from user input, or ValueError naming the valid keys."""
    key = (key or "").strip().lower()
    if key not in TITLE:
        raise ValueError(f"Unknown chapter {key!r}. Use one of: {', '.join(TITLE)}.")
    return key
