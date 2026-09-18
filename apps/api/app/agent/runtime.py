"""Process-wide model, checkpointer and compiled graph. Env-driven, no config classes."""

import os
from functools import lru_cache

from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver

from app.agent.persona import build_graph
from app.agent.schema import PersonaStep

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
PAID_MODEL = os.environ.get("PAID_MODEL", "claude-haiku-4-5")  # T9 eval decides haiku vs sonnet-5


def free_pool():
    """Groq first (fast, free), Gemini when Groq is rate-limited or down."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_groq import ChatGroq

    groq = ChatGroq(model=GROQ_MODEL, temperature=0, max_tokens=1024).with_structured_output(PersonaStep)
    gemini = ChatGoogleGenerativeAI(model=GEMINI_MODEL, temperature=0).with_structured_output(PersonaStep)
    return groq.with_fallbacks([gemini])


def make_model(tier: str):
    if tier == "paid" and os.environ.get("ANTHROPIC_API_KEY"):
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=PAID_MODEL, max_tokens=1024, temperature=0).with_structured_output(PersonaStep)
    return free_pool()  # ponytail: paid tier rides the free pool until an Anthropic key exists


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
