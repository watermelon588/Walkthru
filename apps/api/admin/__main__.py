"""Founder admin panel. Run from apps/api:

    .venv/Scripts/python -m admin setup   # once: choose the password, add the code to your authenticator app
    .venv/Scripts/python -m admin         # then open http://127.0.0.1:8020

It listens on this computer only (127.0.0.1) and is never deployed with the public API.
"""

import getpass
import os
import re
import sys
from urllib.parse import quote

from dotenv import load_dotenv

ENV = os.path.join(os.path.dirname(__file__), "..", ".env")
MIN_PASSWORD = 14


def _write_env(values: dict[str, str]) -> None:
    """Replace or append KEY='value' lines in apps/api/.env (single quotes: no $ or # surprises)."""
    text = ""
    if os.path.exists(ENV):
        with open(ENV, encoding="utf-8") as f:
            text = f.read()
    for key, value in values.items():
        line = f"{key}='{value}'"
        text, n = re.subn(rf"(?m)^{key}=.*$", lambda _m, line=line: line, text)
        if not n:
            text = text.rstrip("\n") + f"\n{line}\n"
    with open(ENV, "w", encoding="utf-8") as f:
        f.write(text)


def setup() -> None:
    from admin.auth import hash_password, new_totp_secret

    load_dotenv(ENV)
    email = (os.environ.get("ADMIN_EMAIL") or os.environ.get("FOUNDER_EMAIL") or input("Your admin email: ")).strip().lower()
    while True:
        password = getpass.getpass(f"New admin password ({MIN_PASSWORD}+ characters, not used anywhere else): ")
        if len(password) < MIN_PASSWORD:
            print(f"Too short. Use at least {MIN_PASSWORD} characters; a few random words work well.")
        elif getpass.getpass("Type it again: ") != password:
            print("They did not match.")
        else:
            break
    secret = new_totp_secret()
    _write_env({"ADMIN_EMAIL": email, "ADMIN_PASSWORD_HASH": hash_password(password), "ADMIN_TOTP_SECRET": secret})
    print("\nSaved to apps/api/.env: the password's hash (never the password) and the authenticator secret.")
    print("Add this to Google Authenticator, 1Password or Authy with 'Enter a setup key':")
    print(f"  Account: Walkthru admin\n  Key:     {secret}\n  Type:    time based")
    print(f"  or as a link: otpauth://totp/{quote('Walkthru admin:' + email)}?secret={secret}&issuer={quote('Walkthru admin')}")
    print("\nThen start the panel with: .venv/Scripts/python -m admin")


def run() -> None:
    load_dotenv(ENV)
    missing = [k for k in ("ADMIN_PASSWORD_HASH", "ADMIN_TOTP_SECRET", "SUPABASE_URL", "SUPABASE_SECRET_KEY") if not os.environ.get(k)]
    if missing:
        sys.exit(f"Missing {', '.join(missing)} in apps/api/.env. Run: .venv/Scripts/python -m admin setup")
    import uvicorn

    from admin.app import PORT, app

    print(f"Walkthru admin on http://127.0.0.1:{PORT} (this computer only). Ctrl+C to stop.")
    uvicorn.run(app, host="127.0.0.1", port=PORT, proxy_headers=False, server_header=False, log_level="warning")


if __name__ == "__main__":
    setup() if sys.argv[1:] == ["setup"] else run() if not sys.argv[1:] else sys.exit(__doc__)
