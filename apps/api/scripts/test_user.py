"""Creates (or reuses) a local test account in Supabase and prints a session for it.

    .venv/Scripts/python scripts/test_user.py            # prints JSON {user_id, access_token, refresh_token, expires_at}

Uses the secret key (admin API) to create the user, then the publishable key to sign in with a password.
Dev only. The password is fixed and the account is throwaway.
"""

import json
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
URL = os.environ["SUPABASE_URL"]
PUB = os.environ["SUPABASE_PUBLISHABLE_KEY"]
SECRET = os.environ["SUPABASE_SECRET_KEY"]
EMAIL = os.environ.get("TEST_USER_EMAIL", "walkthru.tester@example.com")
PASSWORD = os.environ.get("TEST_USER_PASSWORD", "Walk-thru-2026-local!")


def main() -> None:
    r = httpx.post(
        f"{URL}/auth/v1/admin/users",
        headers={"apikey": SECRET, "Authorization": f"Bearer {SECRET}"},
        json={"email": EMAIL, "password": PASSWORD, "email_confirm": True},
        timeout=20,
    )
    if r.status_code not in (200, 201, 422):  # 422 = already exists
        sys.exit(f"create user failed: {r.status_code} {r.text[:200]}")
    r = httpx.post(
        f"{URL}/auth/v1/token?grant_type=password",
        headers={"apikey": PUB, "Content-Type": "application/json"},
        json={"email": EMAIL, "password": PASSWORD},
        timeout=20,
    )
    if r.status_code != 200:
        sys.exit(f"sign in failed: {r.status_code} {r.text[:200]}")
    s = r.json()
    print(json.dumps({"user_id": s["user"]["id"], "access_token": s["access_token"], "refresh_token": s["refresh_token"], "expires_at": s["expires_at"]}))


if __name__ == "__main__":
    main()
