"""Model runtime configuration tests."""

import sys
from types import SimpleNamespace
from typing import ClassVar

from app.agent import runtime
from app.agent.schema import PersonaStep


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
