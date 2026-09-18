"""Supabase session check. Asks Supabase Auth to validate the bearer token; no JWT library needed."""

import os
import time

import httpx
from fastapi import HTTPException, Request

TTL = 300  # seconds a validated token is trusted before re-checking
_cache: dict[str, tuple[str, float]] = {}


def require_user(request: Request) -> str:
    """FastAPI dependency. Returns the Supabase user id or raises 401."""
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(401, "sign in required")
    token = auth[7:].strip()
    hit = _cache.get(token)
    if hit and hit[1] > time.time():
        return hit[0]
    r = httpx.get(
        f"{os.environ['SUPABASE_URL']}/auth/v1/user",
        headers={"apikey": os.environ["SUPABASE_PUBLISHABLE_KEY"], "Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if r.status_code != 200:
        raise HTTPException(401, "invalid or expired session")
    uid = r.json()["id"]
    if len(_cache) > 1000:  # ponytail: tokens rotate hourly, so dropping expired entries is enough
        for k in [k for k, v in _cache.items() if v[1] <= time.time()]:
            del _cache[k]
    _cache[token] = (uid, time.time() + TTL)
    return uid
