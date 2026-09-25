"""Walkthru MCP server (Plus): Claude Code, Cursor and other agents scan, read reports and fix prompts from the editor.

Streamable HTTP at /mcp, stateless, authenticated by a personal API key (`Authorization: Bearer wt_...`). Every tool
runs under the same plan check, limits and grounding as the web API. ARCHITECTURE.md `mcp`.
"""

from __future__ import annotations

import contextvars
import hashlib
import json
import logging
import secrets
import threading
from datetime import UTC, datetime

from fastapi import HTTPException
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError  # its message reaches the agent; other errors are hidden
from mcp.server.transport_security import TransportSecuritySettings

from app import db, plans

KEY_PREFIX = "wt_"
MAX_KEYS = 5
SCANS_PER_DAY = 50  # per Plus user, on top of the web's own limits; MCP scans never use the free capacity

_user: contextvars.ContextVar[str] = contextvars.ContextVar("mcp_user")
log = logging.getLogger("walkthru.mcp")


def new_key() -> tuple[str, str]:
    """(key shown once, hash stored)."""
    key = KEY_PREFIX + secrets.token_urlsafe(32)
    return key, key_hash(key)


def key_hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def require_plus(user_id: str) -> None:
    if plans.current(user_id)["plan"].name != "plus":
        raise HTTPException(402, "The Walkthru MCP server is part of the Plus plan.")


# ---------- tools ----------

server = MCPServer(
    "Walkthru",
    instructions=(
        "Walkthru is the launch check for apps built with AI. Use scan_site for SEO, AI search readiness and passive "
        "security on a public site, get_report to read any of the user's reports, get_fix_prompt for a ready list of "
        "fixes to apply in this codebase, get_finding for everything about one finding, verify_finding to re-check just "
        "that finding after a fix, and rerun to repeat every check. Findings are grounded in evidence; never invent "
        "findings the report does not contain."
    ),
)


def _row(run_id: str) -> dict:
    row = db.get_run(run_id) if run_id.isalnum() and len(run_id) == 32 else None
    if row is None or str(row.get("user_id")) != _user.get():
        raise ToolError("No run with that id in your account. Use list_runs to see your runs.")
    return row


def _summary(row: dict, full: bool = False) -> str:
    from app.main import WEB_URL  # the web address links point to

    rep = row.get("report")
    link = f"{WEB_URL}/app/runs/{row['id']}"
    if not rep:
        return f"Run {row['id']} for {row['site']} is {row['status']} and has no report yet. Open {link} or try again in a minute."
    score = (rep.get("launch_ready") or {}).get("score")
    lines = [
        f"# Walkthru report for {row['site']}",
        f"Run {row['id']} ({'Instant Scan' if row.get('kind') == 'scan' else row.get('goal')}), {row.get('status')}. {link}",
        f"Launch Ready score: {score if score is not None else 'not measured'} of 100.",
        "",
        rep.get("summary", ""),
    ]
    if rep.get("top_fixes"):
        lines += ["", "## Fix these first", *[f"{i + 1}. {fix}" for i, fix in enumerate(rep["top_fixes"])]]
    findings = rep.get("findings") or []
    lines += ["", f"## Findings ({len(findings)})"]
    for f in findings:
        lines.append(f"- [{f['severity']}] {f['kind']}: {f['title']} (id: {finding_id(f)})" + (f"\n  Evidence: {f['evidence']}\n  Fix: {f['fix']}" if full else ""))
    if not full and findings:
        lines += ["", "Call get_report for evidence and fixes, or get_fix_prompt for a prompt to apply them."]
    if findings:
        lines += ["", "Pass a finding's id to get_finding for its full recipe, or to verify_finding after fixing it."]
    return "\n".join(lines)


def finding_id(finding: dict) -> str:
    """The id an agent passes back: the finding's stable rule id when the report has one, else its fingerprint."""
    from app.agent.compare import fingerprint

    return finding.get("rule") or fingerprint(finding)


def _find(row: dict, rule: str) -> dict:
    """The report finding a rule id, fingerprint or exact title names."""
    from app.agent.compare import fingerprint

    wanted = rule.strip().lower()
    for f in (row.get("report") or {}).get("findings", []):
        if wanted in {(f.get("rule") or "").lower(), fingerprint(f), f["title"].lower()} - {""}:
            return f
    raise ToolError(f"The report of run {row['id']} has no finding {rule!r}. Call get_report to see each finding's id.")


_verifies: dict[tuple[str, str], int] = {}  # (user, UTC day) -> verify_finding calls; ponytail: one API process, like the scan limit
_verifies_lock = threading.Lock()


def _within_daily_cap(user: str) -> None:
    """Scans, comparisons and finding checks share one daily cap per Plus user."""
    day = datetime.now(UTC).date().isoformat()
    if db.user_scans_today(user) + _verifies.get((user, day), 0) >= SCANS_PER_DAY:
        raise ToolError(f"You have run {SCANS_PER_DAY} MCP scans and checks today. The limit resets at midnight UTC.")


def _count_verify(user: str) -> None:
    day = datetime.now(UTC).date().isoformat()
    with _verifies_lock:
        for key in [k for k in _verifies if k[1] != day]:
            del _verifies[key]
        _verifies[(user, day)] = _verifies.get((user, day), 0) + 1


def _scan(site: str) -> dict:
    from app.main import run_scan

    user = _user.get()
    _within_daily_cap(user)
    try:
        run_id, _ = run_scan(site, user_id=user)
    except ValueError as e:  # not public, not responding: say so plainly
        raise ToolError(str(e)) from e
    return db.get_run(run_id)


@server.tool()
def scan_site(url: str) -> str:
    """Scan a public website: SEO across up to 10 pages, AI search readiness (GEO), passive security headers and a
    first impression. Takes about 20 seconds. Returns the report summary and findings."""
    return _summary(_scan(url))


@server.tool()
def get_report(run_id: str) -> str:
    """Read one of your Walkthru reports in full: summary, Launch Ready score, every finding with its evidence and fix."""
    return _summary(_row(run_id), full=True)


@server.tool()
def get_fix_prompt(run_id: str, style: str = "full") -> str:
    """A Markdown prompt listing every finding in the report with where it is, the required change and an acceptance
    check, ready for you to apply in this codebase. style: "full" or "chat" (shorter)."""
    from app.agent import compare, fix_prompt

    row = _row(run_id)
    if not row.get("report"):
        raise ToolError("The report is not ready yet. Try again in a minute.")
    ignored = db.ignored_fingerprints(_user.get(), compare.origin(row["site"]))
    return fix_prompt.build(row, row["report"], ignored, "chat" if style == "chat" else "full")


@server.tool()
def rerun(run_id: str) -> str:
    """Run the server-side checks again on the site of an earlier run, after you applied fixes. User journeys rerun
    from the Walkthru Chrome extension."""
    row = _row(run_id)
    fresh = _scan(row["site"])
    before = {(f["kind"], f["title"]) for f in (row.get("report") or {}).get("findings", [])}
    after = {(f["kind"], f["title"]) for f in (fresh.get("report") or {}).get("findings", [])}
    gone, new = sorted(before - after), sorted(after - before)
    note = [
        "",
        "## Compared with the earlier run",
        f"No longer reported ({len(gone)}): " + ("; ".join(t for _, t in gone) or "none"),
        f"New ({len(new)}): " + ("; ".join(t for _, t in new) or "none"),
    ]
    if row.get("kind") == "test":
        note.append("The earlier run was a journey; this rerun covers the server-side checks only. Rerun the journey in the extension.")
    return _summary(fresh) + "\n".join(note)


@server.tool()
def get_finding(run_id: str, rule: str) -> str:
    """Everything the report holds about one finding: why it matters, the evidence, every affected page, the change to
    make (with ready-made code when Walkthru has it) and how to confirm the fix. rule: the finding's id from get_report."""
    from app.agent import fix_prompt

    row = _row(run_id)
    f = _find(row, rule)
    rep = row["report"]
    pages = (rep.get("pages") or {}).get(finding_id(f)) or (rep.get("pages") or {}).get(_fingerprint(f)) or []
    lines = [
        f"# {f['title']}",
        f"id: {finding_id(f)}. {f['severity'].capitalize()} {f['kind']} finding on {row['site']} (run {row['id']}).",
        "",
        "## Why it matters",
        fix_prompt._mask(f["detail"]),
        "",
        "## Where",
        *([f"- {u}" for u in pages] or [f"`{fix_prompt._mask(f.get('evidence') or row['site'])}`"]),
        "",
        "## Change",
        fix_prompt._mask(f["fix"]),
    ]
    code = fix_prompt._fix_for(f, {x["id"]: x for x in (rep.get("geo") or {}).get("fixes", [])})
    if code:
        lines += ["", f"Ready-made fix for `{code['file']}` ({code['note']}):", "", "```", code["code"].rstrip(), "```"]
    lines += ["", "## Done when",
              ("Rerun the journey in the Walkthru Chrome extension: journey findings need a real browser."
               if f["kind"] == "ux" else f'verify_finding("{row["id"]}", "{finding_id(f)}") answers fixed.')]
    return "\n".join(lines)


@server.tool()
def verify_finding(run_id: str, rule: str) -> str:
    """After fixing one finding, re-run only the check behind it on the pages it affected and answer fixed or still
    broken. Faster than rerun. Counts toward the same daily limit as scans. rule: the finding's id from get_report."""
    from app.main import _verified

    row = _row(run_id)
    f = _find(row, rule)
    if f["kind"] == "ux":
        raise ToolError("This finding comes from a user journey. Rerun the journey from the Walkthru Chrome extension to check it.")
    user = _user.get()
    _within_daily_cap(user)
    _count_verify(user)
    pages = (row["report"].get("pages") or {}).get(_fingerprint(f)) or []
    try:
        result = recheck(row["site"], f, pages, verified=_verified(row["site"], user))
    except ValueError as e:
        raise ToolError(str(e)) from e
    return result


def _fingerprint(finding: dict) -> str:
    from app.agent.compare import fingerprint

    return fingerprint(finding)


def recheck(site: str, finding: dict, pages: list[str], *, verified: bool) -> str:
    """Run the scanner family that produced `finding` again, on its pages, and say whether it is still there."""
    from app.agent.compare import _same
    from app.scans import accessibility, fetch, performance, security, takeover, tls
    from app.scans import site as site_audit

    fetch.assert_public(site)
    targets = pages[:10] or [site]
    found: list[dict] = []
    checked: list[str] = []
    with fetch.client() as c:
        kind = finding["kind"]
        if kind == "security":
            for url in targets:
                resp = fetch.get(c, url)
                if resp is None:
                    continue
                checked.append(url)
                found += [x.model_dump() | {"page": url} for x in security.check_headers(resp) + security.check_content(resp.text, str(resp.url))]
            root = fetch.get(c, site)
            if root is not None:
                root_url = str(root.url)
                verified = verified and fetch.same_site(site, root_url)  # the owner verified this host, not a redirect target
                site_wide = security.check_transport(site, root, c) + security.check_cors(root_url, c) + tls.check(root_url) + tls.check_caa(root_url, c)
                if verified:
                    site_wide += security.check_exposed(fetch.origin(root_url), c) + security.check_bundles(root.text, root_url, c)
                    site_wide += takeover.check([(root_url, root.text)], root_url, c)
                found += [x.model_dump() | {"page": root_url} for x in site_wide]
                checked.append(root_url)
        elif kind in ("seo", "geo"):
            audit = site_audit.audit(site, c, verified=verified, visited=targets, max_pages=site_audit.DEFAULT_MAX_PAGES, time_limit=site_audit.DEFAULT_TIME_LIMIT)
            checked = audit.coverage.urls
            by_title = {(k, t): urls for k, t, urls in audit.pages}
            for x in audit.seo + (audit.geo.findings if audit.geo else []):
                found += [x.model_dump() | {"page": u} for u in by_title.get((x.kind, x.title), [None])]
        elif kind == "accessibility":
            for url in targets:
                resp = fetch.get(c, url)
                if resp is not None:
                    checked.append(url)
                    found += [x.model_dump() | {"page": url} for x in accessibility.scan(resp.text, str(resp.url))]
        elif kind == "performance":
            measured, ok, _ = performance.scan_pages(targets, c, limit=len(targets))
            if not ok:
                return f"Could not measure speed right now (PageSpeed unavailable), so {finding['title']!r} was not re-checked. Try again later."
            checked = targets
            found = [x.model_dump() | {"page": None} for x in measured]
        else:
            raise ValueError(f"Walkthru cannot re-check {kind} findings on their own. Use rerun.")
    if not checked:
        return f"{site} did not respond, so {finding['title']!r} was not re-checked. Try again when the site is up."
    still = [x for x in found if _same(finding, x)]
    if still:
        where = sorted({x["page"] for x in still if x.get("page")})
        return "\n".join([f"Still broken: {finding['title']}", *(f"- {u}" for u in where), "", f"Evidence now: {still[0].get('evidence') or '-'}",
                          f"Change: {still[0]['fix']}"])
    if pages and not set(pages) & set(checked):
        return f"Not re-checked: none of the pages that had {finding['title']!r} were reached this time ({', '.join(pages[:3])}). Use rerun for a full check."
    new = [x for x in found if x["kind"] == finding["kind"] and x["severity"] == "high"][:3]
    lines = [f"Fixed: {finding['title']} is no longer reported on {len(checked)} checked page{'s' if len(checked) != 1 else ''}."]
    if new:
        lines += ["", "High-severity issues this check reports now (they may be new or already known):", *(f"- {x['title']}" for x in new)]
    return "\n".join(lines)


@server.tool()
def list_runs(site: str = "", limit: int = 10) -> str:
    """Your most recent Walkthru runs and scans, newest first, optionally only for one site (any part of the address)."""
    # ponytail: reads every run of the user (the export query); add a limited query if accounts grow past a few hundred runs
    rows = [r for r in reversed(db.runs_for_user(_user.get())) if site.lower() in r["site"].lower()][: max(1, min(limit, 50))]
    if not rows:
        return "No runs yet" + (f" for {site}." if site else ".") + " Use scan_site to start."
    out = []
    for r in rows:
        score = ((r.get("report") or {}).get("launch_ready") or {}).get("score")
        out.append(f"- {r['id']} {r['created_at'][:16]} {r['site']} {'scan' if r.get('kind') == 'scan' else repr(r.get('goal'))} "
                   f"{r.get('status')}, score {score if score is not None else '-'}")
    return "\n".join(out)


def build_transport() -> None:
    """Create the session manager (it exists only once the HTTP app is built). A manager runs once per process, so
    tests that start the app again call this for a fresh one. Stateless JSON suits one request per tool call."""
    server.streamable_http_app(
        stateless_http=True,
        json_response=True,
        # Rebinding protection guards unauthenticated local servers; here every request must carry a valid key.
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )


build_transport()


async def _reply(send, status: int, message: str) -> None:
    body = json.dumps({"detail": message}).encode()
    await send({"type": "http.response.start", "status": status, "headers": [(b"content-type", b"application/json")]})
    await send({"type": "http.response.body", "body": body})


class Endpoint:
    """ASGI endpoint for /mcp: checks the API key and the Plus plan, then hands the request to the MCP session manager."""

    async def __call__(self, scope, receive, send) -> None:
        import anyio

        header = dict(scope.get("headers") or []).get(b"authorization", b"").decode()
        key = header.removeprefix("Bearer ").strip()
        if not key.startswith(KEY_PREFIX):
            return await _reply(send, 401, "Send your Walkthru API key as 'Authorization: Bearer wt_...'. Create one in Settings.")
        owner = await anyio.to_thread.run_sync(db.api_key_owner, key_hash(key))
        if owner is None:
            return await _reply(send, 401, "That API key is not valid or was revoked. Create a new one in Settings.")
        user = str(owner["user_id"])
        try:
            await anyio.to_thread.run_sync(require_plus, user)
        except HTTPException as e:
            return await _reply(send, e.status_code, e.detail)
        try:
            await anyio.to_thread.run_sync(db.touch_api_key, owner["id"])
        except Exception:
            log.warning("could not record API key use", exc_info=True)
        token = _user.set(user)
        try:
            await server.session_manager.handle_request(scope, receive, send)
        finally:
            _user.reset(token)
