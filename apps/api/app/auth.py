"""Supabase session check. Asks Supabase Auth to validate the bearer token; no JWT library needed.

A validated token is trusted for up to TTL seconds, never past its own expiry. The cache is keyed by the token's
SHA-256, so raw tokens are not kept in memory, and it is bounded.
"""

import base64
import hashlib
import json
import os
import time

import httpx
from fastapi import HTTPException, Request

TTL = 300  # seconds a validated token is trusted before re-checking
MAX_CACHED = 2000
_cache: dict[str, tuple[dict, float]] = {}


def _expiry(token: str) -> float:
    """The token's own `exp` claim (Supabase already checked the signature), or 0 when it cannot be read."""
    try:
        payload = token.split(".")[1]
        return float(json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))["exp"])
    except (IndexError, ValueError, KeyError, TypeError):
        return 0.0


def _text(value: object, limit: int) -> str:
    """Profile text for display: printable, single-spaced, bounded."""
    if not isinstance(value, str):
        return ""
    return " ".join("".join(ch for ch in value if ch.isprintable()).split())[:limit]


def profile(data: dict) -> dict:
    """What the API needs from a Supabase user: id, email, whether the email is confirmed, a display name, avatar."""
    meta = data.get("user_metadata") or {}
    email = data.get("email") or None
    return {
        "id": data["id"],
        "email": email,
        "email_verified": bool(email and data.get("email_confirmed_at")),
        "name": _text(meta.get("full_name") or meta.get("name"), 80),
        "avatar": _text(meta.get("avatar_url") or meta.get("picture"), 500),
    }


def require_user(request: Request) -> dict:
    """FastAPI dependency. Returns `profile()` of the Supabase user or raises 401."""
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(401, "sign in required")
    token = auth[7:].strip()
    key = hashlib.sha256(token.encode()).hexdigest()
    now = time.time()
    hit = _cache.get(key)
    if hit and hit[1] > now:
        return hit[0]
    try:
        r = httpx.get(
            f"{os.environ['SUPABASE_URL']}/auth/v1/user",
            headers={"apikey": os.environ["SUPABASE_PUBLISHABLE_KEY"], "Authorization": f"Bearer {token}"},
            timeout=10,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(503, "authentication service temporarily unavailable") from exc
    if r.status_code != 200:
        raise HTTPException(401, "invalid or expired session")
    user = profile(r.json())
    until = min(now + TTL, _expiry(token) or now + TTL)
    if len(_cache) >= MAX_CACHED:
        for k in [k for k, v in _cache.items() if v[1] <= now]:
            del _cache[k]
        while len(_cache) >= MAX_CACHED:  # still full: drop the oldest entries (dicts keep insertion order)
            del _cache[next(iter(_cache))]
    if until > now:
        _cache[key] = (user, until)
    return user


def forget(user_id: str) -> None:
    """Drop every cached session of a user (account deleted), so their tokens are checked again at once."""
    for key in [k for k, (u, _) in _cache.items() if u["id"] == user_id]:
        _cache.pop(key, None)
