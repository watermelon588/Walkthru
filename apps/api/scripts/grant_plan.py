"""DEV and founder tool: give an account a paid pass, or end its passes. No payment involved.

    .venv/Scripts/python scripts/grant_plan.py EMAIL pro            # Pro for 30 days, 40 runs
    .venv/Scripts/python scripts/grant_plan.py EMAIL plus 7          # Plus for 7 days
    .venv/Scripts/python scripts/grant_plan.py EMAIL launch --source founder   # a concierge pass (payment.md)
    .venv/Scripts/python scripts/grant_plan.py EMAIL --revoke        # back to free now
    .venv/Scripts/python scripts/grant_plan.py EMAIL --show          # current plan, changes nothing

Test paid plans without spending money: grant a pass to the local test account (scripts/test_user.py).
"""

import argparse
import os
import sys

import httpx
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app import db, notify, plans


def user_id_for(email: str) -> str:
    secret = os.environ["SUPABASE_SECRET_KEY"]
    headers = {"apikey": secret, "Authorization": f"Bearer {secret}"}
    for page in range(1, 50):
        r = httpx.get(f"{os.environ['SUPABASE_URL']}/auth/v1/admin/users", params={"page": page, "per_page": 200}, headers=headers, timeout=20)
        r.raise_for_status()
        users = r.json().get("users", [])
        for u in users:
            if (u.get("email") or "").lower() == email.lower():
                return u["id"]
        if len(users) < 200:
            break
    sys.exit(f"no account with email {email}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("email")
    ap.add_argument("plan", nargs="?", choices=[p for p in plans.PLANS if p != "free"])
    ap.add_argument("days", nargs="?", type=int, default=30)
    ap.add_argument("--runs", type=int, help="runs in the pass (default: the plan's allowance)")
    ap.add_argument("--source", default="dev", choices=["dev", "founder", "promo"])
    ap.add_argument("--revoke", action="store_true", help="end every active pass now")
    ap.add_argument("--show", action="store_true", help="print the current plan and change nothing")
    args = ap.parse_args()

    user_id = user_id_for(args.email)
    if args.show:
        pass
    elif args.revoke:
        db.expire_entitlements(user_id)
    elif args.plan:
        db.grant_entitlement(user_id, args.plan, args.days, args.runs or plans.PLANS[args.plan].runs, args.source)
        notify.pass_granted(user_id, args.plan, args.days)
    else:
        ap.error("give a plan, --revoke or --show")
    print(plans.summary(plans.current(user_id)))


if __name__ == "__main__":
    main()
