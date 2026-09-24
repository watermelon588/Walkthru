"""Process-wide models, checkpointer and compiled graph. Env-driven, no config classes.

`call(schema, messages)` is the one door to the LLM for everything except the persona loop:
it returns the parsed object plus the tokens used, so every run can log its cost.
"""

import atexit
import os
from functools import lru_cache
from types import SimpleNamespace
from typing import Any

from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel

from app.agent.persona import build_graph
from app.agent.schema import PersonaStep
from app.agent.typesafe import DEFAULT_MODEL as DEFAULT_JEV_MODEL
from app.agent.typesafe import JevDecision, JevDecisionClient, JevFallback

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
PAID_MODEL = os.environ.get("PAID_MODEL", "claude-haiku-4-5")  # T9 eval decides haiku vs sonnet-5


class HybridPersonaModel:
    """Use Jev for bounded choices and the existing LLM whenever Jev abstains."""

    def __init__(self, primary: JevDecisionClient, fallback: Any):
        self.primary = primary
        self.fallback = fallback

    def decide(self, state: dict, messages: list) -> JevDecision:
        try:
            return self.primary.decide(state)
        except JevFallback as error:
            step, tokens = unwrap(self.fallback.invoke(messages))
            return JevDecision(
                step=step,
                tokens=tokens,
                metadata={"provider": "llm", "fallback_reason": str(error)},
            )


def _models(env: str, first: str | None, default: str) -> list[str]:
    names = [m.strip() for m in os.environ.get(env, default).split(",") if m.strip()]
    return list(dict.fromkeys(([first] if first else []) + names))


# Several free models, each with its own rate budget (Groq free tier: 8k tokens/min per model).
GROQ_MODELS = _models("GROQ_MODELS", os.environ.get("GROQ_MODEL"), "openai/gpt-oss-120b,openai/gpt-oss-20b,qwen/qwen3.8-27b")
GEMINI_MODELS = _models("GEMINI_MODELS", None, "gemini-3.5-flash,gemini-3.1-flash-lite")
# Slow (median about 60 s) but the most careful free report writer we measured; see docs/decisions.md.
OPENROUTER_MODELS = _models("OPENROUTER_MODELS", None, "nvidia/nemotron-3-ultra-550b-a55b:free")


def openrouter(schema: type[BaseModel], model: str, timeout: float = 90):
    """One OpenRouter model as a runnable, over plain httpx. A forced tool call returns the schema's JSON."""
    import httpx
    from langchain_core.runnables import RunnableLambda

    tool = {"type": "function", "function": {"name": "answer", "description": "Return the answer.", "parameters": schema.model_json_schema()}}

    def run(messages: list) -> dict:
        body = {
            "model": model, "temperature": 0, "tools": [tool], "tool_choice": {"type": "function", "function": {"name": "answer"}},
            "messages": [{"role": "user" if role == "human" else role, "content": text} for role, text in messages],
        }
        headers = {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}
        r = httpx.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=body, timeout=httpx.Timeout(timeout, connect=5.0))
        r.raise_for_status()
        data = r.json()
        if not data.get("choices"):  # free providers sometimes answer 200 with only an error body
            raise RuntimeError(f"OpenRouter {model}: {str(data.get('error'))[:200]}")
        args = data["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"]
        raw = SimpleNamespace(usage_metadata={"total_tokens": (data.get("usage") or {}).get("total_tokens", 0)})
        return {"raw": raw, "parsed": schema.model_validate_json(args), "parsing_error": None}

    return RunnableLambda(run, name=f"openrouter:{model}")


def free_pool(schema: type[BaseModel], writer: bool = False):
    """Try each free model in order and move on instantly when one is rate-limited, overloaded or slow.

    max_retries=0 everywhere: a 429 or 503 falls through to the next model in milliseconds instead of
    sleeping on retry-after. reasoning_effort=low keeps gpt-oss from long reasoning spirals.
    writer=True (report text, one call per run): truth beats speed, so the careful OpenRouter writer comes
    right after the first Groq model (which the persona steps have usually rate-limited by report time).
    Persona steps stay on the fast models only.
    """
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_groq import ChatGroq

    groq = []
    for name in GROQ_MODELS:
        gpt_oss = name.startswith("openai/gpt-oss")
        llm = ChatGroq(model=name, temperature=0, max_tokens=2048, timeout=8, max_retries=0, **({"reasoning_effort": "low"} if gpt_oss else {}))
        groq.append(llm.with_structured_output(schema, include_raw=True, **({"method": "json_schema", "strict": True} if gpt_oss else {})))
    gemini = [ChatGoogleGenerativeAI(model=name, temperature=0, timeout=20, max_retries=0).with_structured_output(schema, include_raw=True) for name in GEMINI_MODELS]
    slow = [openrouter(schema, name) for name in OPENROUTER_MODELS] if writer and os.environ.get("OPENROUTER_API_KEY") else []
    chain = groq[:1] + slow + groq[1:] + gemini
    return chain[0].with_fallbacks(chain[1:])


def make_model(tier: str):
    fallback = _llm_model(tier)
    if os.environ.get("PERSONA_DECISION_MODEL", "llm").lower() != "jev":
        return fallback
    api_key = os.environ.get("TYPESAFE_API_KEY")
    if not api_key:
        raise RuntimeError("TYPESAFE_API_KEY is required when PERSONA_DECISION_MODEL=jev")
    client = JevDecisionClient(
        api_key,
        model=os.environ.get("TYPESAFE_MODEL", DEFAULT_JEV_MODEL),
        confidence_min=float(os.environ.get("TYPESAFE_CONFIDENCE_MIN", "0.5")),
    )
    return HybridPersonaModel(client, fallback)


def _llm_model(tier: str):
    if tier == "paid" and os.environ.get("ANTHROPIC_API_KEY"):
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=PAID_MODEL, max_tokens=1024, temperature=0).with_structured_output(PersonaStep, include_raw=True)
    return free_pool(PersonaStep)  # ponytail: paid tier rides the free pool until an Anthropic key exists


def tokens_of(raw: Any) -> int:
    meta = getattr(raw, "usage_metadata", None) or {}
    return int(meta.get("total_tokens") or 0)


def unwrap(result: Any) -> tuple[Any, int]:
    """Structured output with include_raw is {"raw", "parsed", "parsing_error"}; fakes return the object directly."""
    if isinstance(result, dict) and "parsed" in result:
        if result.get("parsed") is None:
            raise ValueError(f"model returned no structured output: {result.get('parsing_error')}")
        return result["parsed"], tokens_of(result.get("raw"))
    return result, 0


@lru_cache(maxsize=8)
def structured(schema: type[BaseModel], fast: bool = False):
    return free_pool(schema, writer=not fast)  # report text waits for the careful writer; fast calls do not


def call(schema: type[BaseModel], messages: list, fast: bool = False) -> tuple[Any, int]:
    """One LLM call returning (parsed schema instance, tokens used). fast=True skips the slow report writer
    (used before a run starts, where the owner is waiting)."""
    return unwrap(structured(schema, fast).invoke(messages))


def make_checkpointer():
    """In-memory by default: zero network per agent step. Set CHECKPOINTER=postgres on a server that sits
    next to the database (production) so runs survive restarts and the API can scale out."""
    url = os.environ.get("DATABASE_URL")
    if os.environ.get("CHECKPOINTER", "memory") != "postgres" or not url:
        return MemorySaver()
    from langgraph.checkpoint.postgres import PostgresSaver
    from psycopg.rows import dict_row
    from psycopg_pool import ConnectionPool

    connections = ConnectionPool(
        url,
        min_size=0,
        max_size=4,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        check=ConnectionPool.check_connection,
        max_lifetime=300,
        max_idle=60,
        reconnect_timeout=10,
        open=True,
    )
    atexit.register(connections.close)
    saver = PostgresSaver(connections)
    saver.setup()
    return saver


@lru_cache(maxsize=1)
def checkpointer():
    return make_checkpointer()


@lru_cache(maxsize=2)
def graph(tier: str):
    return build_graph(make_model(tier), checkpointer())


def invoke(tier: str, value: Any, config: dict) -> dict:
    """Retry one interrupted database-backed graph call on a fresh pooled connection."""
    from psycopg import OperationalError

    for attempt in range(2):
        try:
            return graph(tier).invoke(value, config)
        except OperationalError:
            if attempt:
                raise
    raise AssertionError("unreachable")


def get_state(tier: str, config: dict):
    """Read graph state with the same single reconnect allowance as writes."""
    from psycopg import OperationalError

    for attempt in range(2):
        try:
            return graph(tier).get_state(config)
        except OperationalError:
            if attempt:
                raise
    raise AssertionError("unreachable")
