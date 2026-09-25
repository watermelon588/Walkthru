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
        "fixes to apply in this codebase, and rerun after fixing to see what changed. Findings are grounded in evidence; "
        "never invent findings the report does not contain."
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
        lines.append(f"- [{f['severity']}] {f['kind']}: {f['title']}" + (f"\n  Evidence: {f['evidence']}\n  Fix: {f['fix']}" if full else ""))
    if not full and findings:
        lines += ["", "Call get_report for evidence and fixes, or get_fix_prompt for a prompt to apply them."]
    return "\n".join(lines)


def _scan(site: str) -> dict:
    from app.main import run_scan

    user = _user.get()
    if db.user_scans_today(user) >= SCANS_PER_DAY:
        raise ToolError(f"You have run {SCANS_PER_DAY} MCP scans today. The limit resets at midnight UTC.")
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


# The session manager only exists once the HTTP app is built; stateless JSON suits one request per tool call.
server.streamable_http_app(
    stateless_http=True,
    json_response=True,
    # Rebinding protection guards unauthenticated local servers; here every request must carry a valid key.
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


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
