"""Bounded provider receipts, independent of report token totals and customer billing.

PROVIDER_USAGE=postgres opts into migration 0004's service-only RPCs. Default off
preserves local/free routing. A durable pending receipt precedes every dispatched
attempt; a crash or lost completion acknowledgement leaves uncertainty, never zero.
"""

import hashlib
import logging
import os
import re
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from app import db, observability

MAX_UNITS = 10**15
COUNTS = (
    "input_tokens", "output_tokens", "total_tokens", "cache_read_tokens", "cache_write_tokens",
    "cache_write_5m_tokens", "cache_write_1h_tokens", "cache_storage_token_seconds", "reasoning_tokens",
    "image_input_tokens", "image_output_tokens", "audio_input_tokens", "audio_output_tokens", "tool_input_tokens", "tool_requests",
)
MONEY = ("reported_cost_microunits", "reported_tool_cost_microusd")
PROVIDERS = {"groq", "gemini", "openrouter", "anthropic", "claude_vertex", "typesafe"}
STAGES = {"goal_plan", "persona_decision", "first_impression", "synthesis", "citation_web", "citation_memory", "scout", "other"}
_scope: ContextVar[dict | None] = ContextVar("provider_operation", default=None)
_stage: ContextVar[dict | None] = ContextVar("provider_stage", default=None)
_active: ContextVar[object | None] = ContextVar("provider_attempt", default=None)
log = logging.getLogger("walkthru.provider_usage")


def _dict(value):
    return value if isinstance(value, dict) else {}


def _count(value):
    return value if type(value) is int and 0 <= value <= MAX_UNITS else None


def _micro(value):
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        return None
    if isinstance(value, str) and len(value) > 64:
        return None
    try:
        number = Decimal(str(value))
        if not number.is_finite() or number < 0 or number > Decimal(MAX_UNITS) / 1_000_000:
            return None
        return int((number * 1_000_000).quantize(Decimal(1), rounding=ROUND_HALF_UP))
    except InvalidOperation:
        return None


def normalize(value, source="langchain") -> dict:
    """Read numeric allowlists only. Detail channels can overlap totals, not extra bills."""
    data = _dict(value)
    if source not in {"langchain", "gemini", "anthropic", "typesafe", "openai", "openrouter"}:
        raise ValueError("Unknown provider usage source")
    out = dict.fromkeys((*COUNTS, *MONEY)) | {"cost_currency": None, "input_semantics": "unknown", "output_semantics": "unknown", "usage_source": source}
    if source == "langchain":
        inp, output = _dict(data.get("input_token_details")), _dict(data.get("output_token_details"))
        fields = {"input_tokens": data.get("input_tokens"), "output_tokens": data.get("output_tokens"), "total_tokens": data.get("total_tokens"),
                  "cache_read_tokens": inp.get("cache_read"), "cache_write_tokens": inp.get("cache_creation"),
                  "cache_write_5m_tokens": inp.get("ephemeral_5m_input_tokens"), "cache_write_1h_tokens": inp.get("ephemeral_1h_input_tokens"),
                  "reasoning_tokens": output.get("reasoning"), "image_input_tokens": inp.get("image"), "image_output_tokens": output.get("image"),
                  "audio_input_tokens": inp.get("audio"), "audio_output_tokens": output.get("audio")}
        out["input_semantics"] = "inclusive"
        out["output_semantics"] = "inclusive"
    elif source == "gemini":
        fields = {"input_tokens": data.get("promptTokenCount"), "output_tokens": data.get("candidatesTokenCount"),
                  "total_tokens": data.get("totalTokenCount"), "cache_read_tokens": data.get("cachedContentTokenCount"),
                  "reasoning_tokens": data.get("thoughtsTokenCount"), "tool_input_tokens": data.get("toolUsePromptTokenCount")}
        # Gemini candidate output excludes thought tokens. Do not synthesize a total.
        for side, key in (("input", "promptTokensDetails"), ("output", "candidatesTokensDetails")):
            details = data.get(key)
            if isinstance(details, list):
                for modality in ("image", "audio"):
                    matches = [d.get("tokenCount") for d in details[:20] if isinstance(d, dict) and d.get("modality") == modality.upper()]
                    if matches and all(_count(n) is not None for n in matches):
                        fields[f"{modality}_{side}_tokens"] = sum(matches)
        out["input_semantics"] = "inclusive"
        out["output_semantics"] = "excludes_reasoning"
    elif source == "anthropic":
        cache = _dict(data.get("cache_creation"))
        fields = {"input_tokens": data.get("input_tokens"), "output_tokens": data.get("output_tokens"),
                  "cache_read_tokens": data.get("cache_read_input_tokens"), "cache_write_tokens": data.get("cache_creation_input_tokens"),
                  "cache_write_5m_tokens": cache.get("ephemeral_5m_input_tokens"), "cache_write_1h_tokens": cache.get("ephemeral_1h_input_tokens"),
                  "tool_requests": _dict(data.get("server_tool_use")).get("web_search_requests")}
        out["input_semantics"] = "excludes_cache"
        out["output_semantics"] = "inclusive"
    elif source == "typesafe":
        fields = {k: data.get(k) for k in ("input_tokens", "output_tokens", "total_tokens")}
    else:  # OpenAI-compatible native receipts, Groq and OpenRouter
        inp = _dict(data.get("prompt_tokens_details") or data.get("input_tokens_details"))
        output = _dict(data.get("completion_tokens_details") or data.get("output_tokens_details"))
        fields = {"input_tokens": data.get("prompt_tokens", data.get("input_tokens")), "output_tokens": data.get("completion_tokens", data.get("output_tokens")), "total_tokens": data.get("total_tokens"),
                  "cache_read_tokens": inp.get("cached_tokens"), "cache_write_tokens": inp.get("cache_write_tokens"),
                  "reasoning_tokens": output.get("reasoning_tokens"), "image_input_tokens": inp.get("image_tokens"), "image_output_tokens": output.get("image_tokens"),
                  "audio_input_tokens": inp.get("audio_tokens"), "audio_output_tokens": output.get("audio_tokens"),
                  "tool_requests": _dict(data.get("server_tool_use")).get("web_search_requests")}
        if source == "openrouter":
            out["reported_cost_microunits"] = _micro(data.get("cost"))
            if out["reported_cost_microunits"] is not None:
                out["cost_currency"] = "openrouter_credits"
            out["reported_tool_cost_microusd"] = _micro(_dict(data.get("cost_details")).get("server_tool_cost"))
        out["input_semantics"] = "inclusive"
        out["output_semantics"] = "inclusive"
    out.update({key: _count(value) for key, value in fields.items()})
    # Empty/invalid usage does not establish inclusive/exclusive accounting.
    if all(out[k] is None for k in COUNTS):
        out["input_semantics"] = "unknown"
        out["output_semantics"] = "unknown"
    return out


def estimate(provider: str, model: str, usage: dict) -> dict:
    """Versioned standard token list-price baseline, never an invoice/total charge.

    Integer micro-USD per million tokens; one final rounding. Reasoning/image/cache
    detail counts are not added again to inclusive input/output. Unpriced stays null.
    """
    rates = {"openai/gpt-oss-120b": (150_000, 600_000), "openai/gpt-oss-20b": (75_000, 300_000)}
    known = rates.get(model) if provider == "groq" else None
    value = None
    if known and usage.get("input_semantics") == "inclusive" and all(_count(usage.get(k)) is not None for k in ("input_tokens", "output_tokens")):
        numerator = usage["input_tokens"] * known[0] + usage["output_tokens"] * known[1]
        value = (numerator + 500_000) // 1_000_000
    return {"price_version": "groq-standard-2026-10-06" if known else None, "currency": "USD", "source_date": "2026-10-06" if known else None,
            "basis": "standard_tokens_no_cache_discount" if known else "unpriced", "token_estimate_microusd": value,
            "input_rate_microusd_per_million": known[0] if known else None, "output_rate_microusd_per_million": known[1] if known else None,
            "total_cost_microusd": None}


def _uuid(value):
    try:
        return str(uuid.UUID(str(value))) if value is not None else None
    except (ValueError, TypeError, AttributeError):
        return None


@contextmanager
def scope(**values):
    """Carry only server IDs, including across job leases. Never accept payload text."""
    previous = _scope.get() or {}
    ctx = previous | {k: _uuid(v) for k, v in values.items() if k in {"operation_id", "run_id", "user_id", "job_lease_id", "request_id"}}
    for key in ("job_id", "job_attempt"):
        if key in values:
            ctx[key] = _count(values[key]) if values[key] != 0 else None
    if not ctx.get("operation_id"):
        request = observability._context.get() or {}
        ctx["operation_id"] = _uuid(request.get("request_id")) or str(uuid.uuid4())
        ctx.setdefault("request_id", _uuid(request.get("request_id")))
        ctx.setdefault("user_id", _uuid(request.get("user_id")))
    token = _scope.set(ctx)
    try:
        yield
    finally:
        _scope.reset(token)


@contextmanager
def stage(name):
    if name not in STAGES:
        raise ValueError("Unknown provider stage")
    with scope():
        token = _stage.set({"stage": name, "stage_id": str(uuid.uuid4()), "attempt_number": 0})
        try:
            yield
        finally:
            _stage.reset(token)


class UsageUnavailable(RuntimeError):
    """The pre-dispatch receipt could not be confirmed. No provider call is allowed."""


class Attempt:
    def __init__(self):
        self.usage = normalize(None)
        self.provider_request_id_hash = None

    def capture(self, data, source="langchain", request_id=None):
        self.usage = normalize(data, source)
        if isinstance(request_id, str) and len(request_id) <= 256:
            self.provider_request_id_hash = hashlib.sha256(request_id.encode()).hexdigest()


def capture(data, source="langchain", request_id=None):
    current = _active.get()
    if current is not None:
        current.capture(data, source, request_id)


def capture_raw(raw):
    if raw is None:
        return
    # Native adapters capture before parsing; do not replace their richer receipts.
    current = _active.get()
    if current is not None and current.usage == normalize(None):
        metadata = _dict(getattr(raw, "response_metadata", None))
        if "token_usage" in metadata:
            # Groq's SDK otherwise fabricates missing output/total counts as zero.
            capture(metadata["token_usage"], "openai", getattr(raw, "id", None))
        elif "usage" in metadata:
            capture(metadata["usage"], "anthropic", metadata.get("id"))
        else:
            capture(getattr(raw, "usage_metadata", None), request_id=getattr(raw, "id", None))


def observe_gemini(llm):
    """Observe the existing synchronous SDK request before lossy LC normalization.

    Installed langchain-google-genai 4.4.0 calls this public SDK method once per
    invoke. No extra request or parsing/routing change. Fakes need no SDK client.
    """
    client = getattr(llm, "client", None)
    if client is not None:
        original = client.models.generate_content
        def generate_content(*args, **kwargs):
            response = original(*args, **kwargs)
            meta = response.usage_metadata
            capture(meta.model_dump(by_alias=True, exclude_none=True) if meta is not None else None, "gemini", response.response_id)
            return response
        client.models.generate_content = generate_content
    return llm


def initialize():
    """Only opt-in storage needs readiness. Off never contacts the database."""
    mode = os.environ.get("PROVIDER_USAGE", "off").strip().lower()
    if mode == "off":
        return
    if mode != "postgres":
        raise UsageUnavailable("PROVIDER_USAGE must be off or postgres")
    db._response("GET", "/rest/v1/provider_attempts", params={"select": "id", "limit": "0"})


def _failure(error):
    import httpx

    from app import providers
    if isinstance(error, providers.CircuitOpen):
        return "circuit_open"
    if isinstance(error, (TimeoutError, httpx.TimeoutException)):
        return "timeout"
    if isinstance(error, httpx.HTTPStatusError):
        return "http"
    if isinstance(error, httpx.TransportError):
        return "transport"
    if isinstance(error, (ValueError, KeyError, TypeError, StopIteration)):
        return "parse"
    if type(error).__name__ == "JevFallback":
        return "abstained"
    return "error" if isinstance(error, Exception) else "cancelled"


@contextmanager
def attempt(provider: str, model: str):
    """Wrap circuit admission so receipt writes never change provider health.

    Completion writes never trigger inference replay. If they fail, the durable
    pending receipt remains unknown for later reconciliation; no usage is fabricated.
    """
    mode = os.environ.get("PROVIDER_USAGE", "off").strip().lower()
    if mode not in {"off", "postgres"}:
        raise UsageUnavailable("PROVIDER_USAGE must be off or postgres")
    if provider not in PROVIDERS:
        raise ValueError("Unknown provider")
    model = model if isinstance(model, str) and re.fullmatch(r"[a-zA-Z0-9_./:@-]{1,128}", model) else "unknown"
    with scope():
        current = _stage.get()
        if current is None:
            with stage("other"), attempt(provider, model) as receipt:
                yield receipt
            return
        current["attempt_number"] += 1
        identity = {k: (_scope.get() or {}).get(k) for k in ("operation_id", "run_id", "user_id", "job_id", "job_attempt", "job_lease_id", "request_id")}
        identity |= {"stage_id": current["stage_id"], "stage": current["stage"], "attempt_number": current["attempt_number"], "provider": provider, "model": model}
        attempt_id = str(uuid.uuid4())
        if mode == "postgres":
            try:
                if db.begin_provider_attempt(attempt_id, identity) is not True:
                    raise UsageUnavailable("Provider receipt was not confirmed")
            except Exception as error:
                raise UsageUnavailable("Provider receipt storage unavailable") from error
        receipt = Attempt()
        token = _active.set(receipt)
        started = time.monotonic()
        state, error_kind = "succeeded", None
        try:
            yield receipt
        except BaseException as error:
            state, error_kind = "failed", _failure(error)
            if error_kind == "circuit_open":
                state = "skipped"
            raise
        finally:
            _active.reset(token)
            if mode == "postgres":
                result = {"state": state, "error_kind": error_kind, "duration_ms": min(MAX_UNITS, max(0, int((time.monotonic() - started) * 1000))),
                          "usage": receipt.usage, "estimate": estimate(provider, model, receipt.usage), "provider_request_id_hash": receipt.provider_request_id_hash}
                try:
                    if db.finish_provider_attempt(attempt_id, result) is not True:
                        raise UsageUnavailable("Provider completion was not confirmed")
                except Exception:  # noqa: BLE001 - a failed receipt write must never replay provider work
                    log.error("", extra={"event": "provider_usage_uncertain", "provider_attempt_id": attempt_id, "operation_id": identity["operation_id"]})
