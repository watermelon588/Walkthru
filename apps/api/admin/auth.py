"""Founder admin login: scrypt password, TOTP second factor, short server-side sessions, lockout. Stdlib only.

The password is never stored, only `scrypt:n:r:p:salt:hash` in ADMIN_PASSWORD_HASH. The TOTP secret (RFC 6238, what
Google Authenticator and 1Password use) is in ADMIN_TOTP_SECRET. Both are written by `python -m admin setup`.
"""

import base64
import hashlib
import hmac
import os
import secrets
import struct
import threading
import time
from dataclasses import dataclass, field

N, R, P = 2**15, 8, 1  # scrypt cost: about 0.1 s and 32 MB per attempt
IDLE_SECONDS = 15 * 60  # a session ends after 15 minutes without a request
MAX_SECONDS = 8 * 3600  # and after 8 hours in any case
MAX_FAILURES, LOCK_SECONDS = 5, 15 * 60  # 5 wrong logins lock the panel for 15 minutes


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=N, r=R, p=P, maxmem=64 * 1024 * 1024, dklen=32)
    b64 = lambda b: base64.urlsafe_b64encode(b).decode().rstrip("=")
    return f"scrypt:{N}:{R}:{P}:{b64(salt)}:{b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = stored.split(":")
        unb64 = lambda s: base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
        got = hashlib.scrypt(password.encode(), salt=unb64(salt), n=int(n), r=int(r), p=int(p), maxmem=64 * 1024 * 1024, dklen=32)
        return scheme == "scrypt" and hmac.compare_digest(got, unb64(digest))
    except (ValueError, TypeError):
        return False


def new_totp_secret() -> str:
    return base64.b32encode(os.urandom(20)).decode()


def totp(secret: str, counter: int, digits: int = 6) -> str:
    key = base64.b32decode(secret.upper() + "=" * (-len(secret) % 8))
    mac = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = mac[-1] & 0x0F
    value = struct.unpack(">I", mac[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(value % 10**digits).zfill(digits)


def totp_counter(secret: str, code: str, now: float | None = None) -> int | None:
    """The 30-second step the code belongs to (this one, or one step either side for clock drift), else None."""
    code = "".join(code.split())
    if not (code.isdigit() and len(code) == 6):
        return None
    current = int((time.time() if now is None else now) // 30)
    for counter in (current - 1, current, current + 1):
        if hmac.compare_digest(totp(secret, counter), code):
            return counter
    return None


@dataclass
class Session:
    csrf: str
    since: str = ""  # the previous sign-in, for "new since last time"
    created: float = field(default_factory=time.time)
    last: float = field(default_factory=time.time)


class Guard:
    """Sessions, lockout and TOTP replay protection. In memory: a restart signs the founder out, which is fine."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: dict[str, Session] = {}
        self._failures: list[float] = []
        self._locked_until = 0.0
        self._last_counter = -1

    def locked(self) -> bool:
        return time.time() < self._locked_until

    def login(self, password: str, code: str, password_hash: str, totp_secret: str) -> str | None:
        """A new session token, or None. Always runs scrypt, so a wrong password and a wrong code take the same time."""
        with self._lock:
            if self.locked():
                return None
        password_ok = verify_password(password, password_hash)
        counter = totp_counter(totp_secret, code)
        with self._lock:
            if password_ok and counter is not None and counter > self._last_counter:  # a code works once
                self._last_counter = counter
                self._failures.clear()
                token = secrets.token_urlsafe(32)
                self._sessions = {token: Session(csrf=secrets.token_urlsafe(32))}  # one session at a time
                return token
            now = time.time()
            self._failures = [t for t in self._failures if now - t < LOCK_SECONDS] + [now]
            if len(self._failures) >= MAX_FAILURES:
                self._locked_until = now + LOCK_SECONDS
                self._failures.clear()
            return None

    def session(self, token: str | None) -> Session | None:
        if not token:
            return None
        with self._lock:
            s = self._sessions.get(token)
            now = time.time()
            if s is None or now - s.last > IDLE_SECONDS or now - s.created > MAX_SECONDS:
                self._sessions.pop(token, None)
                return None
            s.last = now
            return s

    def logout(self, token: str | None) -> None:
        with self._lock:
            self._sessions.pop(token or "", None)
