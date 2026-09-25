"""Agent fix prompt (paid plans): one Markdown prompt for Cursor, Claude Code, Codex, Lovable or Bolt that fixes
every finding in a report. Built in code from the stored report, with no model call, so it can only contain what
the report found. Ignored findings are left out, and secret values are masked (SPEC.md "Agent fix prompt")."""

import re

from app.agent.compare import fingerprint, is_ignored, legacy_fingerprint

ORDER = ("security", "ux", "geo", "seo", "accessibility", "performance")
SEVERITY = {"high": 0, "medium": 1, "low": 2}
CHAT_LIMIT = 4000  # chat boxes in Lovable and Bolt; Estimate, confirm against their current limits
SECRET = re.compile(r"\b(sk_live_|sk_test_|rk_live_|AKIA|ghp_|github_pat_|xox[abp]-|AIza)[A-Za-z0-9_\-]{6,}|\b[A-Za-z0-9_\-]{40,}\b")
RULES = [
    "Change only what each issue needs. Keep existing behavior, copy and styling.",
    "Ask before adding a new dependency.",
    "Never paste secrets, API keys or passwords into code. If an issue is about a leaked key, rotate it and load it from environment variables.",
    "If something cannot be fixed in code (hosting, DNS, CDN or email provider settings), list it at the end as a manual step.",
]


def _mask(text: str) -> str:
    return SECRET.sub(lambda m: (m.group(1) or m.group(0)[:4]) + "[hidden]", text or "")


def _ordered(findings: list[dict], ignored: dict) -> list[dict]:
    kept = [f for f in findings if not is_ignored(f, ignored)]
    return sorted(kept, key=lambda f: (ORDER.index(f["kind"]) if f["kind"] in ORDER else len(ORDER), SEVERITY.get(f["severity"], 3)))


def build(run: dict, report: dict, ignored: dict, style: str = "full") -> str:
    findings = _ordered(report.get("findings", []), ignored)
    fixes = {f["id"]: f for f in (report.get("geo") or {}).get("fixes", [])}
    tested = "an Instant Scan of the homepage" if run.get("kind") == "scan" else f'a test of "{run.get("goal")}"'
    if style == "chat":
        return _chat(run, findings, tested)

    lines = [
        f"# Fix the issues Walkthru found on {run['site']}",
        "",
        (f"You are working in the codebase of {run['site']}. Walkthru ran {tested} on {run.get('created_at', '')[:10]}. "
         f"Fix the {len(findings)} issues below in order, most important first."),
        "",
        "## Rules",
        *[f"- {rule}" for rule in RULES],
        "",
    ]
    for i, f in enumerate(findings, start=1):
        lines += [
            f"## {i}. {f['title']}",
            f"**{f['severity'].capitalize()} {f['kind']} issue.** {_mask(f['detail'])}",
            "",
            *_where(f, report.get("pages", {})),
            f"Change: {_mask(f['fix'])}",
            f'Done when: a Walkthru rerun no longer reports "{f["title"]}".',
            "",
        ]
        code = _fix_for(f, fixes)
        if code:
            lines += [f"Ready-made fix for `{code['file']}` ({code['note']}):", "", "```", code["code"].rstrip(), "```", ""]
    lines += [
        "## Verify",
        "Run the same Walkthru test again. These should show as fixed:",
        *[f"- {f['title']}" for f in findings],
        "",
    ]
    return "\n".join(lines)


def _where(finding: dict, pages: dict) -> list[str]:
    """Every affected page when the report knows them (the evidence line shows at most 3)."""
    urls = pages.get(fingerprint(finding), pages.get(legacy_fingerprint(finding), []))
    if len(urls) > 1:
        return [f"Where ({len(urls)} pages, fix every one):", *[f"- {u}" for u in urls], ""]
    return [f"Where: `{_mask(finding['evidence'])}`"] if finding.get("evidence") else []


def _fix_for(finding: dict, fixes: dict) -> dict | None:
    """The GEO fix pack entry that solves this finding, if any."""
    title = finding["title"].lower()
    for key, words in (("render", "javascript runs"), ("robots", "robots.txt blocks"), ("schema", "structured data"),
                       ("name", "states its name"), ("llms", "llms.txt")):
        if key in fixes and words in title:
            return fixes[key]
    return None


def _chat(run: dict, findings: list[dict], tested: str) -> str:
    head = f"Fix these issues Walkthru found on {run['site']} ({tested}). Keep existing behavior, ask before adding dependencies, never paste secrets.\n"
    out, used = [head], len(head)
    for i, f in enumerate(findings, start=1):
        line = f"{i}. {f['title']}: {_mask(f['fix'])}\n"
        tail = f"...and {len(findings) - i + 1} more: download the full prompt from the Walkthru report.\n"
        if used + len(line) + len(tail) > CHAT_LIMIT:
            out.append(tail)
            break
        out.append(line)
        used += len(line)
    return "".join(out)
