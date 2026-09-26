"""In-app notifications: a row per event for one user. The web app counts them per sidebar section and shows a toast
when Supabase Realtime delivers a new one. Sending never fails the action that caused it."""

import logging

from app import db

log = logging.getLogger("walkthru.notify")

SECTIONS = ("runs", "team", "compare", "watch", "billing")
PLAN_NAME = {"launch": "Launch Pack", "pro": "Pro", "plus": "Plus"}


def send(user_id: str | None, section: str, kind: str, title: str, body: str = "", link: str = "") -> None:
    if not user_id or section not in SECTIONS:
        return
    try:
        db.add_notification({"user_id": str(user_id), "section": section, "kind": kind, "title": title[:200], "body": body[:500],
                             "link": link if link.startswith("/") else ""})
    except Exception:  # a notification is a courtesy; the grant, payment or report already happened
        log.warning("notification %s for %s not stored", kind, user_id, exc_info=True)


# ---------- the events that matter, one place for their wording ----------


def pass_granted(user_id: str, plan: str, days: int, paid: bool = False) -> None:
    name = PLAN_NAME.get(plan, plan)
    title = f"Payment confirmed. {name} is active" if paid else f"Your {name} plan is active"
    send(user_id, "billing", "pass.granted", title, f"{days} days from today. Everything in {name} is unlocked.", "/app/billing")


def offer_ready(user_id: str, plan: str, price: str, expires: str) -> None:
    name = PLAN_NAME.get(plan, plan)
    send(user_id, "billing", "offer.ready", f"Your {name} offer is ready", f"Pay {price} from Plan & billing before {expires} UTC.", "/app/billing")


def request_declined(user_id: str) -> None:
    send(user_id, "billing", "request.declined", "Your plan request was not approved this time",
         "You can request again from Plan & billing, or reply to our email with questions.", "/app/billing")


def report_ready(user_id: str, run_id: str, site: str, goal: str) -> None:
    send(user_id, "runs", "report.ready", f"Report ready: {goal[:80]}", site[:200], f"/app/runs/{run_id}")


def watch_changed(user_id: str, run_id: str, site: str, new: int, fixed: int) -> None:
    send(user_id, "watch", "watch.changed", f"Something changed on {site[:120]}", f"{new} new, {fixed} fixed since the last check.", f"/app/runs/{run_id}")


def comparison_ready(user_id: str, run_id: str, site: str) -> None:
    send(user_id, "compare", "compare.ready", "Comparison ready", site[:200], f"/app/compare/{run_id}")
