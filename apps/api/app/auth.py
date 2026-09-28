"""Supabase session check. Asks Supabase Auth to validate the bearer token; no JWT library needed.

A validated token is trusted for up to TTL seconds, never past its own expiry. The cache is keyed by the token's
SHA-256, so raw tokens are not kept in the cache. The per-process LRU holds at most MAX_CACHED entries.
Cache hits do not extend the validation window: sign-out/revocation may take up to five minutes to be noticed
by this cache (or less when the token expires). `forget` clears local entries on account deletion.
"""

import base64
import hashlib
import json
import os
import time
from collections import OrderedDict
from threading import Lock

import httpx
from fastapi import HTTPException, Request

from app import limits
from app.observability import bind_user

TTL = 300  # seconds a validated token is trusted before re-checking
MAX_CACHED = 2000
_cache: OrderedDict[str, tuple[dict, float]] = OrderedDict()
_cache_lock = Lock()  # FastAPI runs synchronous dependencies in multiple threads; never hold this over HTTP.


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
    with _cache_lock:
        hit = _cache.get(key)
        if hit and hit[1] > now:
            _cache.move_to_end(key)
        elif hit:
            _cache.pop(key)
    if hit and hit[1] > now:
        bind_user(request.scope, hit[0]["id"])
        limits.for_user(request, hit[0]["id"])
        return hit[0]
    limits.apply("auth", limits.address(request))  # each check reaches Supabase: a spray of made-up tokens stops here
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
    with _cache_lock:
        for k in [k for k, v in _cache.items() if v[1] <= now]:
            del _cache[k]
        if until > now:
            _cache[key] = (user, until)
            _cache.move_to_end(key)
        while len(_cache) > MAX_CACHED:
            _cache.popitem(last=False)
    bind_user(request.scope, user["id"])
    limits.for_user(request, user["id"])  # every signed-in route has a limit (app/limits.py, SD-2.1)
    return user


def forget(user_id: str) -> None:
    """Drop every cached session of a user (account deleted), so their tokens are checked again at once."""
    with _cache_lock:
        for key in [k for k, (u, _) in _cache.items() if u["id"] == user_id]:
            _cache.pop(key, None)
