"""Founder tool for paid access (payment.md): review requests, approve exact offers, check Dodo products.

There is no admin page on the public site or API: approvals run here or in the local admin panel (`python -m admin`),
on the founder's machine, with the Supabase secret key from apps/api/.env. Every change is written to admin_audit_log.

    .venv/Scripts/python scripts/billing.py list                          # pending requests and open offers
    .venv/Scripts/python scripts/billing.py approve REQUEST_ID            # offer the requested plan at list price
    .venv/Scripts/python scripts/billing.py approve REQUEST_ID --founding # founding price (first 50 customers)
    .venv/Scripts/python scripts/billing.py approve REQUEST_ID --runs 20  # fewer runs than the plan allows
    .venv/Scripts/python scripts/billing.py reject REQUEST_ID
    .venv/Scripts/python scripts/billing.py offer EMAIL pro --founding     # offer without a request
    .venv/Scripts/python scripts/billing.py cancel OFFER_ID               # withdraw an unpaid offer
    .venv/Scripts/python scripts/billing.py products                      # check every Dodo product against PRICES
    .venv/Scripts/python scripts/billing.py show EMAIL                    # requests, offers and plan for one account

For free testing of paid plans without Dodo, use scripts/grant_plan.py instead.
"""

import argparse
import getpass
import os
import sys
from datetime import UTC, datetime, timedelta

from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app import billing, db, notify, plans
from scripts.grant_plan import user_id_for

ACTOR = os.environ.get("WALKTHRU_ADMIN") or getpass.getuser()


def dollars(cents: int) -> str:
    return f"${cents / 100:.2f}"


def make_offer(user_id: str, plan: str, founding: bool, runs: int | None, request_id: str | None) -> dict:
    terms = billing.offer_terms(plan, founding, runs)
    if founding and db.paid_founding_offers() >= billing.FOUNDING_SEATS:
        sys.exit(f"all {billing.FOUNDING_SEATS} founding seats are taken; offer the list price")
    billing.check_product(terms)  # refuse to send a checkout whose Dodo product charges something else
    expires = datetime.now(UTC) + timedelta(hours=billing.CHECKOUT_HOURS)
    offer = db.create_offer(terms | {"user_id": user_id, "request_id": request_id, "checkout_expires_at": expires.isoformat(), "approved_by": ACTOR})
    notify.offer_ready(user_id, plan, dollars(offer["price_cents"]), expires.strftime("%b %d, %H:%M"))
    db.audit(ACTOR, "offer.create", offer["id"], {k: offer[k] for k in ("user_id", "plan", "founding", "price_cents", "runs", "days", "request_id")})
    print(f"offer {offer['id']}: {plan}{' (founding)' if founding else ''} {dollars(offer['price_cents'])}, {offer['runs']} runs, "
          f"{offer['days']} days. The user pays from {os.environ.get('WEB_URL', 'http://localhost:5173')}/app/billing before {expires:%Y-%m-%d %H:%M} UTC.")
    return offer


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    sub.add_parser("products")
    a = sub.add_parser("approve")
    a.add_argument("request_id")
    a.add_argument("--founding", action="store_true")
    a.add_argument("--runs", type=int)
    a.add_argument("--plan", choices=["launch", "pro", "plus"], help="offer a different plan than requested")
    r = sub.add_parser("reject")
    r.add_argument("request_id")
    r.add_argument("--reason", default="")
    o = sub.add_parser("offer")
    o.add_argument("email")
    o.add_argument("plan", choices=["launch", "pro", "plus"])
    o.add_argument("--founding", action="store_true")
    o.add_argument("--runs", type=int)
    c = sub.add_parser("cancel")
    c.add_argument("offer_id")
    s = sub.add_parser("show")
    s.add_argument("email")
    args = ap.parse_args()

    try:
        if args.cmd == "list":
            for req in db.pending_access_requests():
                who = db.user_email(req["user_id"]) or f"user {req['user_id']}"
                print(f"request {req['id']}  {req['plan']:<6}  {who}  {req['created_at'][:16]}  {req['note']!r}")
            for off in db.open_offers():
                print(f"offer   {off['id']}  {off['plan']:<6}  {dollars(off['price_cents'])}  user {off['user_id']}  until {off['checkout_expires_at'][:16]}")
        elif args.cmd == "products":
            for plan, founding in billing.PRICES:
                name = billing.product_env(plan, founding)
                try:
                    billing.check_product(billing.offer_terms(plan, founding))
                    print(f"ok       {name}")
                except (billing.NotConfigured, ValueError) as e:
                    print(f"PROBLEM  {name}: {e}")
        elif args.cmd == "approve":
            req = db.get_access_request(args.request_id)
            if not req or req["status"] != "pending":
                sys.exit("no pending request with that id")
            offer = make_offer(req["user_id"], args.plan or req["plan"], args.founding, args.runs, req["id"])
            if not db.decide_access_request(req["id"], "approved"):
                db.mark_offer(offer["id"], "approved", {"status": "cancelled"})
                sys.exit("the request changed while approving; the offer was cancelled")
            db.audit(ACTOR, "request.approve", req["id"], {"offer_id": offer["id"]})
        elif args.cmd == "reject":
            req = db.get_access_request(args.request_id)
            if not req or not db.decide_access_request(args.request_id, "rejected"):
                sys.exit("no pending request with that id")
            notify.request_declined(req["user_id"])
            db.audit(ACTOR, "request.reject", args.request_id, {"reason": args.reason})
            print("rejected")
        elif args.cmd == "offer":
            make_offer(user_id_for(args.email), args.plan, args.founding, args.runs, None)
        elif args.cmd == "cancel":
            if not db.mark_offer(args.offer_id, "approved", {"status": "cancelled"}):
                sys.exit("no unpaid offer with that id (paid offers are refunded in the Dodo dashboard)")
            db.audit(ACTOR, "offer.cancel", args.offer_id, {})
            print("cancelled")
        elif args.cmd == "show":
            user_id = user_id_for(args.email)
            for req in db.access_requests_for_user(user_id):
                print(f"request {req['id']}  {req['plan']:<6}  {req['status']:<8}  {req['created_at'][:16]}")
            for off in db.offers_for_user(user_id):
                print(f"offer   {off['id']}  {off['plan']:<6}  {off['status']:<9}  {dollars(off['price_cents'])}  payment {off.get('payment_id') or '-'}")
            print(plans.summary(plans.current(user_id)))
    except (billing.NotConfigured, ValueError) as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
