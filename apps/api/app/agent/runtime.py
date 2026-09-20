"""Process-wide models, checkpointer and compiled graph. Env-driven, no config classes.

`call(schema, messages)` is the one door to the LLM for everything except the persona loop:
it returns the parsed object plus the tokens used, so every run can log its cost.
"""

import os
from functools import lru_cache
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


def free_pool(schema: type[BaseModel]):
    """Groq first (fast, free), Gemini when Groq is rate-limited or down. include_raw keeps usage metadata."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_groq import ChatGroq

    # reasoning_effort=low and a hard timeout: gpt-oss once spent 63k reasoning tokens and 2 minutes on one step.
    # On timeout or error the call falls through to Gemini instead of hanging the run.
    groq = ChatGroq(model=GROQ_MODEL, temperature=0, max_tokens=2048, reasoning_effort="low", timeout=45, max_retries=1)
    gemini = ChatGoogleGenerativeAI(model=GEMINI_MODEL, temperature=0, timeout=45, max_retries=1)
    return groq.with_structured_output(schema, method="json_schema", strict=True, include_raw=True).with_fallbacks(
        [gemini.with_structured_output(schema, include_raw=True)]
    )


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
def structured(schema: type[BaseModel]):
    return free_pool(schema)


def call(schema: type[BaseModel], messages: list) -> tuple[Any, int]:
    """One LLM call returning (parsed schema instance, tokens used)."""
    return unwrap(structured(schema).invoke(messages))


def make_checkpointer():
    url = os.environ.get("DATABASE_URL")
    if not url:
        return MemorySaver()  # in-memory in dev, Postgres when DATABASE_URL is set
    from langgraph.checkpoint.postgres import PostgresSaver
    from psycopg import Connection
    from psycopg.rows import dict_row

    conn = Connection.connect(url, autocommit=True, prepare_threshold=0, row_factory=dict_row)
    saver = PostgresSaver(conn)
    saver.setup()
    return saver


@lru_cache(maxsize=1)
def checkpointer():
    return make_checkpointer()


@lru_cache(maxsize=2)
def graph(tier: str):
    return build_graph(make_model(tier), checkpointer())
