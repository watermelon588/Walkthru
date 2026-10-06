"""Offline receipts: supplied usage, fallbacks, lost acknowledgements and privacy."""

import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import httpx
import pytest
from langchain_core.runnables import RunnableLambda

from app import citations, db, idempotency, jobs, main, providers, scout
from app import provider_usage as usage
from app.agent import runtime
from app.agent.schema import GoalPlan


@pytest.fixture
def receipts(monkeypatch):
    rows = {}
    def begin(identifier, identity):
        rows[identifier] = {"identity": identity, "result": None}
        return True
    def finish(identifier, result):
        assert rows[identifier]["result"] is None
        rows[identifier]["result"] = result
        return True
    monkeypatch.setenv("PROVIDER_USAGE", "postgres")
    monkeypatch.setattr(db, "begin_provider_attempt", begin)
    monkeypatch.setattr(db, "finish_provider_attempt", finish)
    return rows


def test_native_openrouter_channels_and_decimal_currency_are_separate():
    out = usage.normalize({"prompt_tokens": 100, "completion_tokens": 60, "total_tokens": 160,
                           "prompt_tokens_details": {"cached_tokens": 80, "cache_write_tokens": 20, "image_tokens": 10},
                           "completion_tokens_details": {"reasoning_tokens": 50, "image_tokens": 2},
                           "server_tool_use": {"web_search_requests": 1}, "cost": "0.0000005",
                           "cost_details": {"server_tool_cost": "0.0000015"}, "private_text": "never save"}, "openrouter")
    assert (out["input_tokens"], out["cache_read_tokens"], out["cache_write_tokens"], out["reasoning_tokens"]) == (100, 80, 20, 50)
    assert (out["image_input_tokens"], out["image_output_tokens"], out["tool_requests"]) == (10, 2, 1)
    assert out["reported_cost_microunits"] == 1 and out["reported_tool_cost_microusd"] == 2
    assert out["cost_currency"] == "openrouter_credits"
    assert "private_text" not in out and out["cache_storage_token_seconds"] is None


def test_anthropic_native_cache_and_langchain_inclusive_totals_are_not_added_twice():
    native = usage.normalize({"input_tokens": 20, "output_tokens": 4, "cache_read_input_tokens": 100,
                              "cache_creation_input_tokens": 30, "cache_creation": {"ephemeral_5m_input_tokens": 10, "ephemeral_1h_input_tokens": 20}}, "anthropic")
    lc = usage.normalize({"input_tokens": 150, "output_tokens": 4, "total_tokens": 154,
                          "input_token_details": {"cache_read": 100, "cache_creation": 30}})
    assert native["input_semantics"] == "excludes_cache" and native["input_tokens"] == 20
    assert native["cache_write_1h_tokens"] == 20 and native["total_tokens"] is None
    assert lc["input_semantics"] == "inclusive" and lc["input_tokens"] == 150


def test_gemini_thinking_and_modalities_are_retained_without_fabricating_totals():
    out = usage.normalize({"promptTokenCount": 12, "candidatesTokenCount": 3, "thoughtsTokenCount": 9, "cachedContentTokenCount": 0,
                           "promptTokensDetails": [{"modality": "IMAGE", "tokenCount": 4}, {"modality": "TEXT", "tokenCount": 8}]}, "gemini")
    assert out["reasoning_tokens"] == 9 and out["image_input_tokens"] == 4
    assert out["cache_read_tokens"] == 0 and out["total_tokens"] is None
    assert out["output_semantics"] == "excludes_reasoning"


@pytest.mark.parametrize("invalid", [True, -1, 1.2, "14", float("nan"), float("inf"), 10**16, {}, []])
def test_invalid_counts_stay_unknown(invalid):
    assert usage.normalize({"input_tokens": invalid})["input_tokens"] is None


@pytest.mark.parametrize("invalid", [True, "NaN", "Infinity", "-1", "private", 1e200, "1" * 65])
def test_invalid_money_stays_unknown(invalid):
    out = usage.normalize({"cost": invalid}, "openrouter")
    assert out["reported_cost_microunits"] is None and out["cost_currency"] is None


def test_versioned_integer_estimate_is_partial_and_does_not_charge_detail_channels():
    packet = usage.normalize({"input_tokens": 10, "output_tokens": 10, "input_token_details": {"cache_read": 10}, "output_token_details": {"reasoning": 10}})
    quote = usage.estimate("groq", "openai/gpt-oss-120b", packet)
    assert quote["token_estimate_microusd"] == 8  # 7.5 micro-USD, one half-up rounding
    assert quote["total_cost_microusd"] is None and quote["price_version"] == "groq-standard-2026-10-06"
    assert quote["basis"] == "standard_tokens_no_cache_discount" and quote["currency"] == "USD"
    assert usage.estimate("groq", "unknown", packet)["token_estimate_microusd"] is None
    assert usage.estimate("groq", "openai/gpt-oss-120b", usage.normalize(None))["token_estimate_microusd"] is None


def test_runtime_fallback_retains_parse_failure_usage_and_stage_identity(monkeypatch, receipts):
    raw = SimpleNamespace(usage_metadata={"input_tokens": 100, "output_tokens": 30, "total_tokens": 130}, content="private answer")
    bad = runtime.guarded("groq", RunnableLambda(lambda _: {"raw": raw, "parsed": None, "parsing_error": "private"}), model_name="openai/gpt-oss-120b")
    good = runtime.guarded("gemini", RunnableLambda(lambda _: {"raw": SimpleNamespace(usage_metadata=None), "parsed": "answer"}), model_name="gemini-3.1-flash-lite")
    monkeypatch.setattr(runtime, "structured", lambda *a: bad.with_fallbacks([good]))
    operation, run_id = str(uuid.uuid4()), str(uuid.uuid4())
    with usage.scope(operation_id=operation, run_id=run_id, payload="private", user_id="email@example.com"):
        assert runtime.call(GoalPlan, [("human", "password: private")]) == ("answer", 0)
    rows = list(receipts.values())
    assert len(rows) == 2
    assert rows[0]["identity"]["stage_id"] == rows[1]["identity"]["stage_id"]
    assert [r["identity"]["attempt_number"] for r in rows] == [1, 2]
    assert all(r["identity"]["operation_id"] == operation and r["identity"]["run_id"] == run_id for r in rows)
    assert rows[0]["result"]["error_kind"] == "parse" and rows[0]["result"]["usage"]["total_tokens"] == 130
    assert rows[1]["result"]["usage"]["input_tokens"] is None
    assert "private" not in json.dumps(rows) and "email@example.com" not in json.dumps(rows)


def test_pre_dispatch_storage_failure_blocks_entire_fallback_chain(monkeypatch, receipts):
    calls = []
    monkeypatch.setattr(db, "begin_provider_attempt", lambda *a: False)
    model = RunnableLambda(lambda _: calls.append("dispatch"))
    chain = runtime.guarded("groq", model).with_fallbacks([runtime.guarded("gemini", model)])
    with pytest.raises(usage.UsageUnavailable):
        chain.invoke([])
    assert calls == [] and providers._states == {}


def test_failed_completion_acknowledgement_preserves_pending_without_inference_replay(monkeypatch, receipts, caplog):
    def lost(*args):
        raise db.DatabaseUnavailable("secret-token")
    monkeypatch.setattr(db, "finish_provider_attempt", lost)
    calls = []
    model = runtime.guarded("groq", RunnableLambda(lambda _: calls.append("dispatch") or "answer"))
    assert model.invoke([]) == "answer"
    assert calls == ["dispatch"] and next(iter(receipts.values()))["result"] is None
    assert any(getattr(r, "event", None) == "provider_usage_uncertain" for r in caplog.records)
    assert "secret-token" not in caplog.text


def test_timeout_unknown_usage_and_open_circuit_skips_have_distinct_states(receipts):
    def timeout(_):
        raise httpx.ReadTimeout("private url and payload")
    model = runtime.guarded("groq", RunnableLambda(timeout))
    for _ in range(3):
        with pytest.raises(httpx.ReadTimeout):
            model.invoke([])
    with pytest.raises(providers.CircuitOpen):
        model.invoke([])
    results = [r["result"] for r in receipts.values()]
    assert [r["error_kind"] for r in results] == ["timeout"] * 3 + ["circuit_open"]
    assert results[-1]["state"] == "skipped"
    assert all(r["usage"]["total_tokens"] is None for r in results)


def test_native_receipt_survives_custom_adapter_parsing_error(monkeypatch, receipts):
    monkeypatch.setenv("OPENROUTER_API_KEY", "private-key")
    response = {"id": "private-provider-id", "usage": {"prompt_tokens": 10, "completion_tokens": 4, "cost": "0.000003"},
                "choices": [{"message": {"tool_calls": [{"function": {"arguments": "invalid private text"}}]}}]}
    monkeypatch.setattr(httpx, "post", lambda *a, **k: httpx.Response(200, json=response, request=httpx.Request("POST", "https://fixture.test")))
    with pytest.raises(ValueError):
        runtime.guarded("openrouter", runtime.openrouter(GoalPlan, "test:free"), model_name="test:free").invoke([])
    result = next(iter(receipts.values()))["result"]
    assert result["usage"]["reported_cost_microunits"] == 3 and result["usage"]["input_tokens"] == 10
    assert len(result["provider_request_id_hash"]) == 64 and "private" not in json.dumps(receipts)


def test_sibling_stages_job_retries_and_threads_do_not_share_attempt_ids(receipts):
    operation = str(uuid.uuid4())
    def work(retry):
        with usage.scope(operation_id=operation, job_id=7, job_attempt=retry):
            for name in ("first_impression", "synthesis"):
                with usage.stage(name), usage.attempt("groq", "openai/gpt-oss-20b"):
                    usage.capture({"input_tokens": retry, "output_tokens": 1})
    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(work, [1, 2]))
    identities = [r["identity"] for r in receipts.values()]
    assert len(identities) == 4 and len({r["stage_id"] for r in identities}) == 4
    assert {r["job_attempt"] for r in identities} == {1, 2}
    assert all(r["attempt_number"] == 1 for r in identities)
    assert usage._scope.get() is None and usage._stage.get() is None and usage._active.get() is None


def test_off_is_default_and_invalid_configuration_never_dispatches(monkeypatch):
    monkeypatch.delenv("PROVIDER_USAGE", raising=False)
    monkeypatch.setattr(db, "begin_provider_attempt", lambda *a: pytest.fail("off must not write"))
    with usage.attempt("groq", "test"):
        pass
    monkeypatch.setenv("PROVIDER_USAGE", "typo")
    with pytest.raises(usage.UsageUnavailable), usage.attempt("groq", "test"):
        pytest.fail("invalid mode must not dispatch")


def test_installed_gemini_sdk_receipt_precedes_lossy_langchain_normalization(monkeypatch, receipts):
    from google.genai.types import GenerateContentResponse
    from langchain_google_genai import ChatGoogleGenerativeAI

    response = GenerateContentResponse.model_validate({"responseId": "offline-provider-receipt", "modelVersion": "gemini-3.1-flash-lite",
        "candidates": [{"content": {"parts": [{"text": "answer"}], "role": "model"}, "finishReason": "STOP"}],
        "usageMetadata": {"promptTokenCount": 10, "thoughtsTokenCount": 5, "toolUsePromptTokenCount": 2,
                          "promptTokensDetails": [{"modality": "IMAGE", "tokenCount": 4}]}})
    llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", api_key="offline-unused-key", max_retries=0)
    called = []
    def fake(**kwargs):
        called.append("once")
        return response
    monkeypatch.setattr(llm.client.models, "generate_content", fake)
    usage.observe_gemini(llm)
    try:
        runtime.guarded("gemini", llm, model_name="gemini-3.1-flash-lite").invoke([("human", "private")])
    finally:
        llm.client.close()
    packet = next(iter(receipts.values()))["result"]["usage"]
    assert called == ["once"] and packet["usage_source"] == "gemini"
    assert packet["output_tokens"] is None and packet["total_tokens"] is None
    assert packet["reasoning_tokens"] == 5 and packet["tool_input_tokens"] == 2 and packet["image_input_tokens"] == 4


@pytest.mark.parametrize("native", [{}, {"prompt_tokens": 10}])
def test_native_groq_missing_usage_overrides_sdk_synthesized_zero(native, receipts):
    raw = SimpleNamespace(usage_metadata={"input_tokens": 10, "output_tokens": 0, "total_tokens": 10}, response_metadata={"token_usage": native})
    runtime.guarded("groq", RunnableLambda(lambda _: {"raw": raw, "parsed": "answer"})).invoke([])
    packet = next(iter(receipts.values()))["result"]["usage"]
    assert packet["input_tokens"] == native.get("prompt_tokens")
    assert packet["output_tokens"] is None and packet["total_tokens"] is None


def test_jev_abstention_retains_usage_before_llm_fallback(receipts):
    from tests.test_typesafe import client_with, response, state

    primary = client_with(response(operation_confidence=0.1))
    fallback = runtime.guarded("groq", RunnableLambda(lambda _: {"parsed": "fallback"}))
    model = runtime.HybridPersonaModel(primary, fallback)
    with usage.stage("persona_decision"):
        assert model.decide(state(), []).step == "fallback"
    rows = list(receipts.values())
    assert rows[0]["result"]["error_kind"] == "abstained" and rows[0]["result"]["usage"]["input_tokens"] == 900
    assert rows[0]["identity"]["stage_id"] == rows[1]["identity"]["stage_id"]
    assert [r["identity"]["attempt_number"] for r in rows] == [1, 2]


def test_scout_fallback_counts_and_citation_tool_receipts(monkeypatch, receipts):
    monkeypatch.setattr(scout, "key", lambda: "unused-private-key")
    monkeypatch.setattr(scout, "MODELS", ["gemini-a", "gemini-b"])
    calls = []
    def post(url, **kwargs):
        calls.append(url)
        if len(calls) == 1:
            raise httpx.ReadTimeout("private-prompt")
        if "generateContent" in url:
            body = {"candidates": [{"content": {"parts": [{"text": "answer"}]}}], "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 2}}
        else:
            body = {"choices": [{"message": {"content": "answer"}}], "usage": {"prompt_tokens": 7, "completion_tokens": 3, "server_tool_use": {"web_search_requests": 1}}}
        return httpx.Response(200, json=body, request=httpx.Request("POST", url))
    monkeypatch.setattr(httpx, "post", post)
    monkeypatch.setenv("GROQ_API_KEY", "unused-private-key")
    assert scout.ask("private-question", "private-data") == "answer"
    assert citations.ask_web("private-question")["answer"] == "answer"
    rows = list(receipts.values())
    assert len(rows) == 3 and rows[0]["identity"]["stage_id"] == rows[1]["identity"]["stage_id"]
    assert rows[0]["result"]["error_kind"] == "timeout"
    assert rows[1]["result"]["usage"]["input_tokens"] == 5 and rows[2]["result"]["usage"]["tool_requests"] == 1
    assert rows[2]["identity"]["stage"] == "citation_web" and "private" not in json.dumps(rows)


def test_job_retry_context_and_saved_report_guard_do_not_dispatch_again(monkeypatch, receipts):
    identifier, run_id, lease = 7, str(uuid.uuid4()), str(uuid.uuid4())
    job = {"id": identifier, "kind": "finish_run", "payload": {"run_id": run_id, "values": {}}, "attempts": 2, "max_attempts": 3, "lease": lease}
    monkeypatch.setattr(db, "claim_job", lambda *a: job)
    monkeypatch.setattr(db, "finish_job", lambda *a: None)
    monkeypatch.setattr(db, "get_run", lambda *a: {"report": {"summary": "already saved"}})
    assert jobs.run_one() and receipts == {}
    def handle(*args):
        with usage.stage("synthesis"), usage.attempt("groq", "openai/gpt-oss-120b"):
            pass
    monkeypatch.setattr(jobs, "handle", handle)
    assert jobs.run_one()
    meta = next(iter(receipts.values()))["identity"]
    assert meta["job_id"] == identifier and meta["operation_id"] == str(uuid.uuid5(uuid.NAMESPACE_URL, "walkthru:job:7"))
    assert meta["job_attempt"] == 2 and meta["run_id"] == run_id and meta["job_lease_id"] == lease


def test_request_key_correlates_once_and_replay_does_not_record_new_attempt(monkeypatch, receipts):
    from starlette.requests import Request

    key, run_id, user_id = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    request = Request({"type": "http", "headers": [(b"idempotency-key", key.encode())]})
    monkeypatch.setattr(db, "claim_run_request", lambda *a: {"state": "claimed", "run_id": run_id})
    monkeypatch.setattr(db, "finish_run_request", lambda *a: True)
    def perform(resource):
        with usage.stage("goal_plan"), usage.attempt("groq", "test"):
            return {"run_id": resource}
    idempotency.run(request, user_id, "start", {}, perform)
    monkeypatch.setattr(db, "claim_run_request", lambda *a: {"state": "replay", "response": {"run_id": run_id}, "status": 200})
    idempotency.run(request, user_id, "start", {}, perform)
    meta = next(iter(receipts.values()))["identity"]
    assert len(receipts) == 1 and meta["operation_id"] == key and meta["user_id"] == user_id and meta["run_id"] == run_id


def test_startup_only_checks_explicitly_enabled_storage(monkeypatch):
    checks = []
    monkeypatch.setattr(db, "_response", lambda *a, **k: checks.append(a))
    monkeypatch.setenv("PROVIDER_USAGE", "off")
    usage.initialize()
    assert checks == []
    monkeypatch.setenv("PROVIDER_USAGE", "postgres")
    usage.initialize()
    assert checks == [("GET", "/rest/v1/provider_attempts")]


def test_parallel_comparison_children_keep_job_context_and_their_own_run_ids(monkeypatch, receipts):
    operation, root, user_id = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    def scan(url, **kwargs):
        run_id = str(uuid.uuid4())
        with usage.scope(run_id=run_id, user_id=kwargs["user_id"]), usage.stage("synthesis"), usage.attempt("groq", "test"):
            return run_id, {"site": url, "report": {"findings": []}}
    monkeypatch.setattr(main, "run_scan", scan)
    monkeypatch.setattr(db, "set_report", lambda *a, **k: None)
    monkeypatch.setattr(main.notify, "comparison_ready", lambda *a: None)
    with usage.scope(operation_id=operation, job_id=7, job_attempt=2, run_id=root):
        main._compare(root, user_id, ["https://one.test", "https://two.test"])
    rows = [r["identity"] for r in receipts.values()]
    assert len(rows) == 2 and len({r["run_id"] for r in rows}) == 2
    assert all(r["operation_id"] == operation and r["job_id"] == 7 and r["user_id"] == user_id for r in rows)
