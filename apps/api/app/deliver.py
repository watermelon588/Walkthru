"""Email delivery through Resend's REST API. No-op (returns False) when RESEND_API_KEY is unset."""

import html
import os

import httpx

FROM = os.environ.get("RESEND_FROM", "Walkthru <onboarding@resend.dev>")


def send_report(to: str, link: str, site: str, report: dict) -> bool:
    key = os.environ.get("RESEND_API_KEY")
    if not key:
        return False
    fixes = "".join(f"<li>{html.escape(f)}</li>" for f in report.get("top_fixes", []))
    body = (
        f"<p>Your Walkthru report for <strong>{html.escape(site)}</strong> is ready.</p>"
        f"<p>{html.escape(report.get('summary', ''))}</p>"
        f"<p><strong>Top fixes</strong></p><ol>{fixes}</ol>"
        f'<p><a href="{html.escape(link)}">Open the full report</a></p>'
    )
    r = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {key}"},
        json={"from": FROM, "to": [to], "subject": f"Walkthru report: {site}", "html": body},
        timeout=15,
    )
    return r.status_code in (200, 201)


def send_watch(to: str, site: str, link: str, diff: dict) -> bool:
    """Weekly watch: sent only when findings changed since the last check."""
    key = os.environ.get("RESEND_API_KEY")
    if not key:
        return False
    items = lambda titles: "".join(f"<li>{html.escape(t)}</li>" for t in titles) or "<li>None</li>"
    score = f"<p>Launch Ready score: <strong>{diff['score']}</strong> of 100.</p>" if diff.get("score") is not None else ""
    body = (
        f"<p>Walkthru rechecked <strong>{html.escape(site)}</strong> ({'after a deploy' if diff.get('reason') == 'deploy' else 'weekly check'}) and something changed.</p>"
        f"{score}<p><strong>New problems</strong></p><ul>{items(diff['new'])}</ul>"
        f"<p><strong>Fixed since last check</strong></p><ul>{items(diff['fixed'])}</ul>"
        f'<p><a href="{html.escape(link)}">Open the report</a></p>'
    )
    r = httpx.post("https://api.resend.com/emails", headers={"Authorization": f"Bearer {key}"},
                   json={"from": FROM, "to": [to], "subject": f"Walkthru watch: {site} changed", "html": body}, timeout=15)
    return r.status_code in (200, 201)


def send_access_request(to: str, email: str, plan: str, note: str, request_id: str) -> bool:
    """Tell the founder a plan request is waiting (FOUNDER_EMAIL). Approval stays in scripts/billing.py."""
    key = os.environ.get("RESEND_API_KEY")
    if not key:
        return False
    body = (
        f"<p><strong>{html.escape(email)}</strong> asked for <strong>{html.escape(plan)}</strong>.</p>"
        f"<p>What they will test: {html.escape(note) or 'not said'}</p>"
        f"<p>Approve (they then pay from Plan &amp; billing):<br><code>scripts/billing.py approve {html.escape(request_id)}</code>"
        f" (add <code>--founding</code> for the founding price)</p>"
        f"<p>Or decline: <code>scripts/billing.py reject {html.escape(request_id)}</code></p>"
    )
    r = httpx.post("https://api.resend.com/emails", headers={"Authorization": f"Bearer {key}"},
                   json={"from": FROM, "to": [to], "subject": f"Walkthru: {plan} request from {email}", "html": body}, timeout=15)
    return r.status_code in (200, 201)


ROLE_WORDS = {"admin": "an admin", "member": "a member", "viewer": "a viewer"}


def send_team_invite(to: str, team: str, inviter: str, role: str, link: str, expires) -> bool:
    """A workspace invitation (Plus teams). Every name is escaped; the link carries the code in its #fragment."""
    key = os.environ.get("RESEND_API_KEY")
    if not key:
        return False
    body = (
        f"<p><strong>{html.escape(inviter)}</strong> invited you to join <strong>{html.escape(team)}</strong> on Walkthru "
        f"as {ROLE_WORDS.get(role, 'a member')}.</p>"
        "<p>The workspace shares launch reports, the findings the team is fixing, and a chat about them.</p>"
        f'<p><a href="{html.escape(link)}">Accept the invitation</a></p>'
        f"<p>It works once, for {html.escape(to)}, until {expires:%d %B %Y}. If you did not expect it, ignore this email.</p>"
    )
    subject = " ".join(f"{inviter} invited you to {team} on Walkthru".split())[:150]
    r = httpx.post("https://api.resend.com/emails", headers={"Authorization": f"Bearer {key}"},
                   json={"from": FROM, "to": [to], "subject": subject, "html": body}, timeout=15)
    return r.status_code in (200, 201)
