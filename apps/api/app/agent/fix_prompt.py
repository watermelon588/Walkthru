"""Agent fix plan (paid plans, P1.3): one Markdown prompt for Cursor, Claude Code, Codex, Lovable or Bolt that fixes
every finding in a report, in batches that each end with "stop and verify".

Built in code from the stored report and the recipes in recipes.json, with no model call, so it can only contain what
the report found. Each finding gets why it matters, the change for the detected stack (vercel.json, netlify.toml,
next.config.js, public/_headers...), the risk and a local check. Things outside the code (DNS, hosting, email and
provider dashboards) are listed separately. Ignored findings are left out and secret values are masked.
"""

import json
import os
import re
from fnmatch import fnmatchcase
from functools import lru_cache
from urllib.parse import urlsplit

from app.agent.compare import fingerprint, is_ignored, legacy_fingerprint
from app.agent.schema import finding_rule
from app.scans import stack as stacks

BATCHES = (
    ("security", "Security"),
    ("backend", "Backend exposure"),
    ("ux", "Journey blockers"),
    ("geo", "AI search (GEO)"),
    ("seo", "Search (SEO)"),
    ("accessibility", "Accessibility"),
    ("performance", "Speed"),
)
SEVERITY = {"high": 0, "medium": 1, "low": 2}
CHAT_LIMIT = 4000  # one chat message in Lovable or Bolt
MANUAL = {"dns": "DNS", "hosting": "Hosting settings", "email": "Email provider", "provider": "Provider dashboard"}
SECRET = re.compile(r"\b(sk_live_|sk_test_|rk_live_|AKIA|ghp_|github_pat_|xox[abp]-|AIza)[A-Za-z0-9_\-]{6,}|\b[A-Za-z0-9_\-]{40,}\b")
RULES = [
    "Work through the batches in order. Finish every fix in a batch, then stop and run that batch's checks before starting the next.",
    "Change only what each issue needs. Keep existing behavior, copy and styling.",
    "Ask before adding a new dependency.",
    "Never paste secrets, API keys or passwords into code. If an issue is about a leaked key, rotate it and load it from environment variables.",
    "If the detected stack above is wrong, say so and use the matching file for the real stack.",
]


def _mask(text: str) -> str:
    return SECRET.sub(lambda m: (m.group(1) or m.group(0)[:4]) + "[hidden]", text or "")


@lru_cache(maxsize=1)
def _recipes() -> dict:
    with open(os.path.join(os.path.dirname(__file__), "recipes.json"), encoding="utf-8") as f:
        rules = json.load(f)["rules"]
    exact = {k: v for k, v in rules.items() if not any(c in k for c in "*?[")}
    patterns = sorted(((k, v) for k, v in rules.items() if k not in exact), key=lambda kv: -len(kv[0].replace("*", "")))
    return {"exact": exact, "patterns": patterns}


def rule_of(finding: dict) -> str:
    return (finding.get("rule") or "").strip() or finding_rule(finding["kind"], finding["title"])


def recipe(finding: dict) -> dict | None:
    """The recipe for a finding's rule: an exact id first, then the most specific matching pattern."""
    rule, book = rule_of(finding), _recipes()
    if rule in book["exact"]:
        return book["exact"][rule]
    return next((r for pattern, r in book["patterns"] if fnmatchcase(rule, pattern)), None)


def batch_of(finding: dict) -> str:
    rule = rule_of(finding)
    if rule.startswith(("sec.supabase", "sec.firebase", "sec.backend")):
        return "backend"
    return finding["kind"] if finding["kind"] in dict(BATCHES) else "performance"


# One header, the file it goes in for each host. Next.js apps set headers in next.config.js on any host.
def header_step(name: str, value: str, stack: dict | None) -> dict:
    stack = stack or {}
    if stack.get("framework") == "nextjs":
        return {"file": "next.config.js", "lang": "js", "note": "Merge into your existing config; keep any headers already there.",
                "snippet": (f"module.exports = {{\n  async headers() {{\n    return [{{ source: '/(.*)', headers: [\n"
                            f"      {{ key: '{name}', value: \"{value}\" }},\n    ] }}]\n  }},\n}}")}
    host = stack.get("hosting")
    if host == "vercel":
        return {"file": "vercel.json", "lang": "json", "note": "Merge into the headers array if the file already has one.",
                "snippet": json.dumps({"headers": [{"source": "/(.*)", "headers": [{"key": name, "value": value}]}]}, indent=2)}
    if host == "netlify":
        return {"file": "netlify.toml", "lang": "toml", "note": "Or the same lines in a _headers file in your publish folder.",
                "snippet": f'[[headers]]\n  for = "/*"\n  [headers.values]\n    {name} = "{value}"'}
    if host == "cloudflare":
        return {"file": "public/_headers", "lang": "text", "note": "Cloudflare Pages reads _headers from the build output folder.",
                "snippet": f"/*\n  {name}: {value}"}
    if host == "render":
        return {"file": "render.yaml", "lang": "yaml", "note": "Static sites on Render; a web service sets the header in its own code.",
                "snippet": f"services:\n  - type: web\n    name: your-site\n    headers:\n      - path: /*\n        name: {name}\n        value: \"{value}\""}
    if host == "github_pages":
        return {"file": "GitHub Pages cannot send custom headers", "lang": "text", "manual": True,
                "note": "Put Cloudflare (free) in front and add the header with a Transform Rule, or move to Netlify, Vercel or Cloudflare Pages.",
                "snippet": f"{name}: {value}"}
    return {"file": "your hosting or server config", "lang": "text", "note": "Use the one that matches where the site runs.",
            "snippet": f"# nginx\nadd_header {name} \"{value}\" always;\n\n# Express\napp.use((req, res, next) => {{ res.setHeader('{name}', \"{value}\"); next() }})\n\n# _headers file (Netlify, Cloudflare Pages)\n/*\n  {name}: {value}"}


def step(finding: dict, stack: dict | None) -> dict | None:
    """The change for this stack: {file, snippet, note, lang, label} or None when only a text change or manual step exists."""
    r = recipe(finding) or {}
    stack = stack or {}
    if r.get("header"):
        return header_step(r["header"]["name"], r["header"]["value"], stack) | {"label": stacks.label(stack)}
    steps = r.get("steps") or {}
    for key in (stack.get("framework"), stack.get("hosting"), stack.get("backend"), "*"):
        if key and key in steps:
            return {**steps[key], "lang": "text", "label": stacks.LABEL.get(key, "any stack")}
    return None


def _places(run: dict, report: dict) -> dict:
    parts = urlsplit(run.get("site") or "")
    evidence = " ".join(str(f.get("evidence") or "") for f in report.get("findings", []))
    supabase = re.search(r"https://[a-z0-9]+\.supabase\.co", evidence)
    return {"url": run.get("site") or "", "origin": f"{parts.scheme}://{parts.netloc}", "host": parts.hostname or "",
            "supabase_url": supabase.group(0) if supabase else "https://<project>.supabase.co"}


def _fill(text: str, places: dict) -> str:
    return re.sub(r"\{(url|origin|host|supabase_url)\}", lambda m: places[m.group(1)], text)


def plan(run: dict, report: dict, ignored: dict) -> dict:
    """Findings grouped into batches (each item: finding, recipe, step) and the manual steps. Used by both prompt styles,
    get_finding and the fix pull request."""
    stack = report.get("stack") or None
    kept = [f for f in report.get("findings", []) if not is_ignored(f, ignored)]
    batches: dict[str, list[dict]] = {key: [] for key, _ in BATCHES}
    manual: list[dict] = []
    for f in sorted(kept, key=lambda f: SEVERITY.get(f["severity"], 3)):
        r = recipe(f) or {}
        s = step(f, stack)
        item = {"finding": f, "recipe": r, "step": s, "batched": True}
        only_manual = bool(r.get("manual")) and not r.get("steps") and not r.get("change") and not r.get("header")
        if s and s.get("manual"):  # a header the host cannot send (GitHub Pages)
            only_manual = True
        item["batched"] = not only_manual
        if r.get("manual") and (r.get("manual_text") or only_manual):
            manual.append(item)
        if item["batched"]:
            batches[batch_of(f)].append(item)
    return {"stack": stack, "batches": [(key, title, batches[key]) for key, title in BATCHES if batches[key]], "manual": manual}


def finding_lines(item: dict, report: dict, places: dict, fixes: dict, *, heading: str) -> list[str]:
    """Why, where, the change for this stack, the risk and the local check, for one finding."""
    f, r, s = item["finding"], item["recipe"], item["step"]
    lines = [heading, f"**{f['severity'].capitalize()} {f['kind']} issue.** {_mask(f['detail'])}", ""]
    if r.get("why"):
        lines += [f"Why it matters: {r['why']}", ""]
    lines += _where(f, report.get("pages", {}))
    if s:
        lines += [f"Change for {s['label']}, in `{_fill(s['file'], places)}`:", "", f"```{s['lang'] if s['lang'] != 'text' else ''}",
                  _fill(s["snippet"], places).rstrip(), "```"]
        if s.get("note"):
            lines.append(s["note"])
        lines.append(f"What the report says to change: {_mask(f['fix'])}")
    else:
        lines.append(f"Change: {_mask(r.get('change') or f['fix'])}")
    code = _fix_for(f, fixes)
    if code:
        lines += ["", f"Ready-made fix for `{code['file']}` ({code['note']}):", "", "```", code["code"].rstrip(), "```"]
    if r.get("risk"):
        lines += ["", f"Risk: {r['risk']}"]
    lines += [f"Check locally: `{_fill(r['check'], places)}`" if r.get("check") else f'Check: a Walkthru rerun no longer reports "{f["title"]}".', ""]
    return lines


def build(run: dict, report: dict, ignored: dict, style: str = "full") -> str:
    p = plan(run, report, ignored)
    places = _places(run, report)
    fixes = {f["id"]: f for f in (report.get("geo") or {}).get("fixes", [])}
    tested = "an Instant Scan of the homepage" if run.get("kind") == "scan" else f'a test of "{run.get("goal")}"'
    if style == "chat":
        return _chat(run, p, places, tested)

    stack = p["stack"]
    how = "; ".join(f"{k}: {v}" for k, v in (stack or {}).get("evidence", {}).items())
    everything = [it["finding"] for _, _, b in p["batches"] for it in b] + [it["finding"] for it in p["manual"] if not it["batched"]]
    count = len(everything)
    lines = [
        f"# Fix plan for {run['site']}",
        "",
        (f"You are working in the codebase of {run['site']}. Walkthru ran {tested} on {run.get('created_at', '')[:10]} and found "
         f"{count} issues. Fix them batch by batch, most important first."),
        "",
        f"Detected stack: {stacks.label(stack)}" + (f" ({how})." if how else ". Walkthru could not tell, so each change is the generic one."),
        "",
        "## Rules",
        *[f"- {rule}" for rule in RULES],
        "",
    ]
    n = 0
    for b, (_, title, items) in enumerate(p["batches"], start=1):
        lines += [f"## Batch {b}: {title} ({len(items)} {'fix' if len(items) == 1 else 'fixes'})", ""]
        for i, item in enumerate(items, start=1):
            n += 1
            lines += finding_lines(item, report, places, fixes, heading=f"### {b}.{i} {item['finding']['title']}")
        checks = [_fill(it["recipe"]["check"], places) for it in items if it["recipe"].get("check")]
        lines += [f"**Stop and verify batch {b}.** Deploy a preview (or run the site locally) and run:",
                  *([f"- `{c}`" for c in dict.fromkeys(checks)] or ["- Walk through the affected pages by hand."]),
                  "Continue only when these pass and nothing else broke.", ""]
    if p["manual"]:
        lines += ["## Manual steps (outside the code)", "These cannot be done in the codebase; do them in the named dashboard.", ""]
        for item in p["manual"]:
            f, r = item["finding"], item["recipe"]
            where = MANUAL.get(r.get("manual"), "Hosting settings")
            text = r.get("manual_text") or (item["step"] or {}).get("note") or f["fix"]
            check = f" Check: `{_fill(r['check'], places)}`" if r.get("check") and not item["batched"] else ""
            lines.append(f"- **{where}: {f['title']}.** {_mask(text)}{check}")
        lines.append("")
    lines += ["## Verify", "Run the same Walkthru test again (or `verify_finding` from the Walkthru MCP server). These should show as fixed:",
              *[f"- {f['title']}" for f in everything], ""]
    return "\n".join(lines)


def _where(finding: dict, pages: dict) -> list[str]:
    """Every affected page when the report knows them (the evidence line shows at most 3)."""
    urls = pages.get(fingerprint(finding), pages.get(legacy_fingerprint(finding), []))
    if len(urls) > 1:
        return [f"Where ({len(urls)} pages, fix every one):", *[f"- {u}" for u in urls], ""]
    return [f"Where: `{_mask(finding['evidence'])}`", ""] if finding.get("evidence") else []


def _fix_for(finding: dict, fixes: dict) -> dict | None:
    """The GEO fix pack entry that solves this finding, if any."""
    title = finding["title"].lower()
    for key, words in (("render", "javascript runs"), ("robots", "robots.txt blocks"), ("schema", "structured data"),
                       ("name", "states its name"), ("llms", "llms.txt")):
        if key in fixes and words in title:
            return fixes[key]
    return None


def _chat(run: dict, p: dict, places: dict, tested: str) -> str:
    """Short parts for chat builders (Lovable, Bolt), each at most CHAT_LIMIT characters with its own header, in batch
    order. Every finding is included: long plans become more parts, never "and N more"."""
    lines: list[str] = []
    n = 0
    for b, (_, title, items) in enumerate(p["batches"], start=1):
        lines.append(f"Batch {b}, {title}:")
        for item in items:
            n += 1
            f, s = item["finding"], item["step"]
            where = f" In {_fill(s['file'], places)}." if s else ""
            check = f" Check: {_fill(item['recipe']['check'], places)}" if item["recipe"].get("check") else ""
            lines.append(_mask(f"{n}. {f['title']}: {item['recipe'].get('change') or f['fix']}{where}{check}")[:1500])
        lines.append(f"Stop here and check batch {b} works before going on.")
    if p["manual"]:
        lines.append("Do these yourself, outside the code:")
        lines += [_mask(f"- {MANUAL.get(it['recipe'].get('manual'), 'Hosting settings')}: {it['finding']['title']}. "
                        f"{it['recipe'].get('manual_text') or it['finding']['fix']}")[:1500] for it in p["manual"]]
    head = (f"Walkthru fix plan for {run['site']} ({tested}), part {{i}} of {{n}}. Stack: {stacks.label(p['stack'])}. "
            "Keep existing behavior, ask before adding dependencies, never paste secrets.\n")
    tail = "\nWhen this part works, paste the next part.\n"
    room = CHAT_LIMIT - len(head.format(i=99, n=99)) - len(tail)
    parts: list[list[str]] = [[]]
    for line in lines:
        if parts[-1] and sum(len(x) + 1 for x in parts[-1]) + len(line) + 1 > room:
            parts.append([])
        parts[-1].append(line)
    total = len(parts)
    return "\n\n".join(head.format(i=i, n=total) + "\n".join(part) + (tail if i < total else "\n")
                       for i, part in enumerate(parts, start=1)).strip() + "\n"


def chat_parts(text: str) -> list[str]:
    """Split a chat plan back into its parts (each starts with "Walkthru fix plan for")."""
    return [p.strip() for p in re.split(r"\n\n(?=Walkthru fix plan for )", text) if p.strip()]
