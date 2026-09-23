"""Model runtime configuration tests."""

import sys
from types import SimpleNamespace
from typing import ClassVar

import pytest
from psycopg import OperationalError

from app.agent import runtime
from app.agent.schema import PersonaStep
from app.agent.typesafe import JevFallback


class FakeRunnable:
    def with_fallbacks(self, fallbacks):
        return self


class FakeChatModel:
    calls: ClassVar[list[tuple[object, dict[str, object]]]] = []

    def __init__(self, **kwargs):
        pass

    def with_structured_output(self, schema, **kwargs):
        self.calls.append((schema, kwargs))
        return FakeRunnable()


def test_free_pool_uses_constrained_json_schema_for_groq(monkeypatch):
    FakeChatModel.calls = []
    monkeypatch.setitem(sys.modules, "langchain_groq", SimpleNamespace(ChatGroq=FakeChatModel))
    monkeypatch.setitem(sys.modules, "langchain_google_genai", SimpleNamespace(ChatGoogleGenerativeAI=FakeChatModel))

    runtime.free_pool(PersonaStep)

    groq_schema, groq_options = FakeChatModel.calls[0]
    assert groq_schema is PersonaStep
    assert groq_options == {"method": "json_schema", "strict": True, "include_raw": True}


class Tagged:
    def __init__(self, tag):
        self.tag = tag

    def with_structured_output(self, schema, **kwargs):
        return self

    def with_fallbacks(self, rest):
        return [self.tag, *(r.tag for r in rest)]


@pytest.mark.parametrize(("writer", "order"), [
    (True, ["groq-a", "or-x", "groq-b", "gem"]),  # report text: careful OpenRouter writer right after the first Groq model
    (False, ["groq-a", "groq-b", "gem"]),  # persona steps: fast models only
])
def test_free_pool_orders_models_for_writer_and_persona(monkeypatch, writer, order):
    monkeypatch.setitem(sys.modules, "langchain_groq", SimpleNamespace(ChatGroq=lambda model, **kw: Tagged(model)))
    monkeypatch.setitem(sys.modules, "langchain_google_genai", SimpleNamespace(ChatGoogleGenerativeAI=lambda model, **kw: Tagged(model)))
    monkeypatch.setattr(runtime, "GROQ_MODELS", ["groq-a", "groq-b"])
    monkeypatch.setattr(runtime, "GEMINI_MODELS", ["gem"])
    monkeypatch.setattr(runtime, "OPENROUTER_MODELS", ["or-x"])
    monkeypatch.setattr(runtime, "openrouter", lambda schema, name: Tagged(name))
    monkeypatch.setenv("OPENROUTER_API_KEY", "test")

    assert runtime.free_pool(PersonaStep, writer=writer) == order


def test_free_pool_skips_openrouter_without_a_key(monkeypatch):
    monkeypatch.setitem(sys.modules, "langchain_groq", SimpleNamespace(ChatGroq=lambda model, **kw: Tagged(model)))
    monkeypatch.setitem(sys.modules, "langchain_google_genai", SimpleNamespace(ChatGoogleGenerativeAI=lambda model, **kw: Tagged(model)))
    monkeypatch.setattr(runtime, "GROQ_MODELS", ["groq-a"])
    monkeypatch.setattr(runtime, "GEMINI_MODELS", ["gem"])
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    assert runtime.free_pool(PersonaStep, writer=True) == ["groq-a", "gem"]


class FakeFallback:
    def invoke(self, messages):
        return PersonaStep(thought="fallback", action="scroll", confusion=1)


class FailingJev:
    def decide(self, state):
        raise JevFallback("low confidence")


def test_hybrid_model_falls_back_to_llm_and_records_reason():
    model = runtime.HybridPersonaModel(FailingJev(), FakeFallback())

    decision = model.decide({}, [("human", "page")])

    assert decision.step.action == "scroll"
    assert decision.tokens == 0
    assert decision.metadata == {"provider": "llm", "fallback_reason": "low confidence"}


def test_make_model_keeps_llm_default(monkeypatch):
    fallback = object()
    monkeypatch.delenv("PERSONA_DECISION_MODEL", raising=False)
    monkeypatch.setattr(runtime, "free_pool", lambda schema: fallback)

    assert runtime.make_model("free") is fallback


def test_make_model_enables_jev_only_with_explicit_flag_and_key(monkeypatch):
    fallback = object()
    sentinel_jev = object()
    monkeypatch.setenv("PERSONA_DECISION_MODEL", "jev")
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-secret")
    monkeypatch.setattr(runtime, "free_pool", lambda schema: fallback)
    monkeypatch.setattr(runtime, "JevDecisionClient", lambda api_key, **kwargs: sentinel_jev)

    model = runtime.make_model("free")

    assert isinstance(model, runtime.HybridPersonaModel)
    assert model.primary is sentinel_jev
    assert model.fallback is fallback


def test_make_model_rejects_jev_without_key(monkeypatch):
    monkeypatch.setenv("PERSONA_DECISION_MODEL", "jev")
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setattr(runtime, "free_pool", lambda schema: object())

    with pytest.raises(RuntimeError, match="TYPESAFE_API_KEY"):
        runtime.make_model("free")


def test_graph_call_retries_one_interrupted_database_connection(monkeypatch):
    class FlakyGraph:
        calls = 0

        def invoke(self, value, config):
            self.calls += 1
            if self.calls == 1:
                raise OperationalError("connection closed")
            return {"ok": True}

    graph = FlakyGraph()
    monkeypatch.setattr(runtime, "graph", lambda tier: graph)

    assert runtime.invoke("free", {}, {"configurable": {"thread_id": "r1"}}) == {"ok": True}
    assert graph.calls == 2
