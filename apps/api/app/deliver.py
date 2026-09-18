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
