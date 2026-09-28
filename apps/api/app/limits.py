"""Shared rate limits (SD-2.1, docs/system-design.md). Every route has one, counted in Postgres (migrations/0001_initial.sql
`hit_rate_limit`, one fixed window per key), so limits hold across restarts and API processes.

- Signed-in routes: counted per user inside auth.require_user, by the route's rule in ROUTES, else "account".
- Routes without sign-in: counted per client address by `by_address`, a dependency of the whole app.
- /mcp: per API key (mcp_server.Endpoint). Business limits (scans, invitations, pull requests, billing, feedback)
  call `hit` with their own key.

Fails open: when the database cannot be reached the request goes ahead, and then fails or succeeds on its own.
The client address is request.client, so production runs uvicorn with --proxy-headers behind its proxy (SD-6.6).
"""

import logging
import os

import httpx
from fastapi import HTTPException, Request

from app import db

log = logging.getLogger("walkthru.limits")

# name: (requests, seconds, message)
RULES: dict[str, tuple[int, int, str]] = {
    "public": (120, 60, "Too many requests from this address. Wait a minute and try again."),
    "account": (240, 60, "Too many requests. Wait a minute and try again."),
    "auth": (60, 60, "Too many sign-in checks from this address. Wait a minute and try again."),
    "start_run": (10, 60, "You started many tests in the last minute. Wait a moment and try again."),
    "observe": (60, 60, "This test is sending steps too fast. Wait a moment and try again."),
    "costly": (10, 60, "Too many requests of this kind. Wait a minute and try again."),
    "mcp": (60, 60, "Too many MCP calls with this key. Wait a minute and try again."),
}

# Routes that need a tighter rule than the default ("account" when signed in, "public" otherwise).
ROUTES: dict[tuple[str, str], str] = {
    ("POST", "/runs"): "start_run",
    ("POST", "/runs/{run_id}/observe"): "observe",  # per run, not per user
    **{route: "costly" for route in [
        ("POST", "/compare"), ("POST", "/watch"), ("POST", "/watch/{site_id}/check"), ("POST", "/watch/{site_id}/hook"),
        ("POST", "/me/api-keys"), ("DELETE", "/me/api-keys/{key_id}"), ("POST", "/citations"), ("POST", "/citations/{site_id}/check"),
        ("POST", "/runs/{run_id}/fix-pr"), ("POST", "/runs/{run_id}/email"), ("GET", "/verification"), ("GET", "/account/export"),
        ("POST", "/account/delete"), ("POST", "/me/test-users"), ("POST", "/me/branding"),
    ]},
}
EXEMPT = {("GET", "/health")}  # the uptime monitor and load balancer must never depend on the database


def hit(key: str, count: int, seconds: int, message: str) -> None:
    """Count one request against `key`; over `count` in the window raises 429 with Retry-After."""
    try:
        wait = db.hit_rate_limit(key, count, seconds)
    except (db.DatabaseUnavailable, httpx.HTTPError):
        log.warning("rate limit %s unavailable, allowing the request", key.split(":", 1)[0], exc_info=True)  # no ids in logs
        return
    if wait:
        raise HTTPException(429, message, headers={"Retry-After": str(wait)})


def apply(name: str, subject: str) -> None:
    count, seconds, message = RULES[name]
    hit(f"{name}:{subject}", count, seconds, message)


def _rule(request: Request) -> str | None:
    return ROUTES.get((request.method, getattr(request.scope.get("route"), "path", "")))


def address(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def local_dev(request: Request) -> bool:
    """The founder testing from this machine; production never sets ALLOW_LOCAL_SCANS."""
    return os.environ.get("ALLOW_LOCAL_SCANS") == "1" and address(request) in ("127.0.0.1", "::1")


def for_user(request: Request, user_id: str) -> None:
    """Called by auth.require_user once it knows who is asking."""
    name = _rule(request) or "account"
    apply(name, request.path_params.get("run_id", user_id) if name == "observe" else user_id)


_signed_in_routes: dict[int, bool] = {}  # by id(route): routes live as long as the app and are not hashable


def _signed_in(route) -> bool:
    """Whether a route depends on auth.require_user anywhere in its dependency tree (then it is counted per user)."""
    from app.auth import require_user

    if id(route) not in _signed_in_routes:
        todo, found = list(route.dependant.dependencies), False
        while todo and not found:
            dep = todo.pop()
            found = dep.call is require_user
            todo += dep.dependencies
        _signed_in_routes[id(route)] = found
    return _signed_in_routes[id(route)]


def by_address(request: Request) -> None:
    """App-wide dependency: routes without sign-in are counted per client address. Signed-in routes are skipped here,
    whatever headers the request carries, and counted per user in require_user instead."""
    route = request.scope.get("route")
    if route is None or (request.method, route.path) in EXEMPT or _signed_in(route) or local_dev(request):
        return
    apply(_rule(request) or "public", address(request))
