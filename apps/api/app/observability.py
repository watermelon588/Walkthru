"""Request correlation and allowlisted JSON logs. Never serialize log arguments or exception text."""

import json
import logging
import re
import time
import uuid
from collections import deque
from contextvars import ContextVar
from datetime import UTC, datetime
from pathlib import Path

from starlette.datastructures import MutableHeaders

_context: ContextVar[dict | None] = ContextVar("request_log_context", default=None)
_EVENTS = {"request_finished", "request_failed", "server_error", "database_unavailable", "checkpoint_ready", "checkpoint_unavailable"}


def request_context(scope: dict) -> dict:
    ctx = scope.get("state", {}).get("request_log_context", {})
    if ctx:
        ctx["route"] = getattr(scope.get("route"), "path", "[unmatched]")
    return ctx


def bind_user(scope: dict, user_id: str) -> None:
    # Only an authenticated UUID, never an email, bearer token or unverified JWT claim.
    try:
        user_id = str(uuid.UUID(str(user_id)))
    except ValueError:
        return
    request_context(scope)["user_id"] = user_id


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        ctx = getattr(record, "request_context", None)
        if ctx is None:
            ctx = _context.get() or {}
        # Preserve the emission-time context for buffered handlers after the request has ended.
        record.request_context = dict(ctx)
        event = getattr(record, "event", "log")
        row = {"at": datetime.fromtimestamp(record.created, UTC).isoformat(), "level": record.levelname, "logger": record.name,
               "event": event if event in _EVENTS else "log", "request_id": ctx.get("request_id"),
               "user_id": ctx.get("user_id"), "route": ctx.get("route"), "method": ctx.get("method"),
               "status": ctx.get("status"), "duration_ms": ctx.get("duration_ms"),
               "source": f"{Path(record.pathname).name}:{record.lineno}", "function": record.funcName}
        if record.exc_info and record.exc_info[0]:
            row["error_type"] = record.exc_info[0].__name__
            frames: deque = deque(maxlen=30)
            tb = record.exc_info[2]
            while tb:
                frames.append({"file": Path(tb.tb_frame.f_code.co_filename).name, "line": tb.tb_lineno,
                               "function": tb.tb_frame.f_code.co_name})
                tb = tb.tb_next
            row["frames"] = list(frames)
        # No message, args, body, URL, headers, exception string, locals, or arbitrary extra fields.
        return json.dumps(row, ensure_ascii=True, separators=(",", ":"))


class SafeStreamHandler(logging.StreamHandler):
    def handleError(self, record: logging.LogRecord) -> None:
        # logging's default diagnostic prints the original args (possibly secrets) if stderr closes.
        # A failed log sink must never fall back to dumping the unsanitized record.
        pass


def configure_logging() -> None:
    handler = SafeStreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.WARNING)
    logging.getLogger("walkthru").setLevel(logging.INFO)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers = []
        logger.propagate = True
    # The request summary replaces uvicorn's raw URL/query access log.
    logging.getLogger("uvicorn.access").disabled = True


class RequestLog:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        ctx = {"request_id": uuid.uuid4().hex, "user_id": None, "method": scope["method"], "route": "[unmatched]"}
        scope.setdefault("state", {})["request_log_context"] = ctx
        token = _context.set(ctx)
        started, status, failed = time.perf_counter(), 500, False

        async def send_response(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                MutableHeaders(scope=message)["X-Request-Id"] = ctx["request_id"]
            await send(message)

        try:
            await self.app(scope, receive, send_response)
        except Exception:
            failed = True
            raise
        finally:
            route = scope.get("route")
            ctx.update(route=getattr(route, "path", "[unmatched]"), status=status,
                       duration_ms=round((time.perf_counter() - started) * 1000, 2))
            logging.getLogger("walkthru.requests").log(logging.ERROR if failed or status >= 500 else logging.INFO,
                "", extra={"event": "request_failed" if failed else "request_finished"})
            _context.reset(token)


def support_headers(scope: dict) -> dict:
    value = request_context(scope).get("request_id", "")
    return {"X-Request-Id": value} if re.fullmatch(r"[a-f0-9]{32}", value) else {}
