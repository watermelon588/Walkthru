import sys
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace

import pytest

from app import providers


def fail(provider="groq"):
    with providers.guard(provider):
        raise RuntimeError("provider unavailable")


def trip(provider="groq"):
    for _ in range(3):
        with pytest.raises(RuntimeError, match="provider unavailable"):
            fail(provider)


def test_consecutive_failures_skip_only_the_failed_provider():
    trip()
    with pytest.raises(providers.CircuitOpen), providers.guard("groq"):
        pytest.fail("must not make a provider call")
    with providers.guard("gemini"):
        pass


def test_success_resets_consecutive_failure_count():
    for _ in range(2):
        with pytest.raises(RuntimeError):
            fail()
    with providers.guard("groq"):
        pass
    for _ in range(2):
        with pytest.raises(RuntimeError):
            fail()
    with providers.guard("groq"):
        pass


def test_only_one_recovery_probe_is_admitted_and_failure_reopens(monkeypatch):
    now = [100.0]
    monkeypatch.setattr(providers, "monotonic", lambda: now[0])
    trip()
    assert not providers.available("groq")
    now[0] += 60
    entered, release = Event(), Event()
    def probe():
        with providers.guard("groq"):
            entered.set()
            assert release.wait(5)
            raise RuntimeError("still down")
    with ThreadPoolExecutor(max_workers=1) as pool:
        result = pool.submit(probe)
        try:
            assert entered.wait(5)
            with pytest.raises(providers.CircuitOpen), providers.guard("groq"):
                pytest.fail("parallel recovery probe")
        finally:
            release.set()
        with pytest.raises(RuntimeError, match="still down"):
            result.result()
    assert not providers.available("groq")
    now[0] += 60
    with providers.guard("groq"):
        pass
    assert providers.available("groq")


def test_old_inflight_success_cannot_close_newer_open_circuit():
    entered, release = Event(), Event()
    def old_call():
        with providers.guard("groq"):
            entered.set()
            assert release.wait(5)
    with ThreadPoolExecutor(max_workers=1) as pool:
        result = pool.submit(old_call)
        try:
            assert entered.wait(5)
            trip()
        finally:
            release.set()
        result.result()
    assert not providers.available("groq")


def test_real_fallback_chain_shares_health_between_schema_instances(monkeypatch):
    from langchain_core.runnables import RunnableLambda

    from app.agent import runtime
    from app.agent.schema import PersonaStep

    calls = []
    class Model:
        def __init__(self, model, **kwargs):
            self.name = model
            assert kwargs["timeout"] > 0 and kwargs["max_retries"] == 0
        def with_structured_output(self, schema, **kwargs):
            def invoke(messages, config):
                calls.append((self.name, config.get("metadata", {}).get("trace")))
                if self.name == "groq":
                    raise RuntimeError("offline")
                return PersonaStep(thought="working fallback", action="scroll", confusion=0)
            return RunnableLambda(invoke)
    monkeypatch.setitem(sys.modules, "langchain_groq", SimpleNamespace(ChatGroq=Model))
    monkeypatch.setitem(sys.modules, "langchain_google_genai", SimpleNamespace(ChatGoogleGenerativeAI=Model))
    monkeypatch.setattr(runtime, "GROQ_MODELS", ["groq"])
    monkeypatch.setattr(runtime, "GEMINI_MODELS", ["gemini"])
    for _ in range(4):
        answer = runtime.free_pool(PersonaStep).invoke([], config={"metadata": {"trace": "kept"}})
        assert answer.action == "scroll"
    assert calls.count(("groq", "kept")) == 3
    assert calls.count(("gemini", "kept")) == 4

    # The real HTTP/graph journey also progresses while the failed provider is skipped.
    from fastapi.testclient import TestClient
    from langgraph.checkpoint.memory import MemorySaver

    from app import main
    from app.agent.persona import build_graph
    from tests.test_persona import page

    graph = build_graph(runtime.free_pool(PersonaStep), MemorySaver())
    monkeypatch.setattr(runtime, "graph", lambda tier: graph)
    client = TestClient(main.app)
    observation = page("https://fixture.test/", [])
    started = client.post("/runs", json={"site": "https://fixture.test", "goal": "read guide", "max_steps": 1, "observation": observation})
    assert started.status_code == 200 and started.json()["status"] == "running"
    ended = client.post(f"/runs/{started.json()['run_id']}/observe", json={"observation": observation})
    assert ended.status_code == 200 and ended.json()["status"] == "budget"
    assert sum(name == "groq" for name, _ in calls) == 3


def test_unparsed_structured_answer_uses_fallback():
    from langchain_core.runnables import RunnableLambda

    from app.agent import runtime

    broken = runtime.guarded("groq", RunnableLambda(lambda _: {"parsed": None, "parsing_error": "bad output"}))
    backup = runtime.guarded("gemini", RunnableLambda(lambda _: {"parsed": "usable"}))
    assert broken.with_fallbacks([backup]).invoke([])["parsed"] == "usable"
