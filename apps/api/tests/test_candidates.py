"""R-S11: stronger controller candidates stay off by default, send the documented request shapes through the installed
SDKs (mock transports, no live request), classify refusal/truncation/parse failures, leave receipts and fall back
visibly. The legacy Haiku adapter is checked against the real SDK too."""

import json

import anthropic
import httpx
import httpx2
import pytest

from app import db, provider_usage
from app.agent import candidates, runtime
from app.agent.schema import PersonaStep

STEP = {"thought": "Sign up looks clear.", "action": "click", "target_id": 3, "confusion": 0}
STEP_JSON = json.dumps(STEP)
MESSAGES = [("system", "You are a first-time visitor."), ("human", "Current page: ...")]
REAL_VERTEX = anthropic.AnthropicVertex


@pytest.fixture
def opted_in(monkeypatch):
    monkeypatch.setenv("RESERVATIONS", "postgres")
    for plan in ("LAUNCH", "PRO", "PLUS"):
        monkeypatch.setenv(f"RUN_MAX_COST_MICROUSD_{plan}", "120000")
    monkeypatch.setenv("CLAUDE_VERTEX_PROJECT", "walkthru-test")
    monkeypatch.setenv("ZAI_API_KEY", "test-key")
    monkeypatch.delenv("CANDIDATE_EFFORT", raising=False)


def vertex(monkeypatch, reply: dict) -> list:
    """The real AnthropicVertex client serializes the request; a mock transport answers it."""
    sent = []

    def handler(request):
        sent.append((str(request.url), json.loads(request.content)))
        return httpx2.Response(200, json=reply)

    client = httpx2.Client(transport=httpx2.MockTransport(handler))
    monkeypatch.setattr(anthropic, "AnthropicVertex", lambda **kw: REAL_VERTEX(**kw, access_token="test", http_client=client))
    return sent


def message(stop="end_turn", text=STEP_JSON) -> dict:
    return {"id": "msg_1", "type": "message", "role": "assistant", "model": "claude-sonnet-5-5", "stop_reason": stop, "stop_sequence": None,
            "content": [{"type": "thinking", "thinking": "", "signature": "sig"}, {"type": "text", "text": text}],
            "usage": {"input_tokens": 900, "output_tokens": 120, "cache_read_input_tokens": 0}}


def zai(monkeypatch, reply: dict) -> list:
    sent = []

    def post(url, headers, json, timeout):
        sent.append((url, headers, json))
        return httpx.Response(200, json=reply, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", post)
    return sent


def completion(finish="stop", content=STEP_JSON) -> dict:
    return {"id": "glm_1", "choices": [{"finish_reason": finish, "message": {"content": content, "reasoning_content": "..."}}],
            "usage": {"prompt_tokens": 800, "completion_tokens": 90, "total_tokens": 890, "prompt_tokens_details": {"cached_tokens": 0}}}


def test_candidates_are_off_by_default_and_free_defaults_are_unchanged(monkeypatch):
    monkeypatch.delenv("CONTROLLER_CANDIDATE", raising=False)
    monkeypatch.delenv("CLAUDE_VERTEX_PROJECT", raising=False)
    monkeypatch.setattr(runtime, "free_pool", lambda schema, **kw: "free pool")
    assert candidates.active() is None
    assert runtime._llm_model("paid") == "free pool" and runtime._llm_model("free") == "free pool"
    assert runtime.model_label(True) == "Free models (gpt-oss-120b and backups)"


@pytest.mark.parametrize(("env", "missing"), [({"CONTROLLER_CANDIDATE": "opus"}, "must be sonnet or glm"),
                                              ({"CONTROLLER_CANDIDATE": "glm", "ZAI_API_KEY": ""}, "needs ZAI_API_KEY"),
                                              ({"CONTROLLER_CANDIDATE": "sonnet", "RESERVATIONS": "off"}, "RESERVATIONS=postgres"),
                                              ({"CONTROLLER_CANDIDATE": "sonnet", "RUN_MAX_COST_MICROUSD_PRO": "0"}, "above 0 for every paid plan"),
                                              ({"CONTROLLER_CANDIDATE": "glm", "CANDIDATE_EFFORT": "medium"}, "low, high, max")])
def test_a_half_configured_opt_in_refuses_to_start(monkeypatch, opted_in, env, missing):
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    with pytest.raises(RuntimeError, match=missing):
        candidates.active()
    with pytest.raises(RuntimeError, match=missing):
        runtime._llm_model("paid")  # startup builds the paid graph, so it fails before any run


def test_opted_in_candidate_drives_paid_decisions_only(monkeypatch, opted_in):
    monkeypatch.setenv("CONTROLLER_CANDIDATE", "sonnet")
    monkeypatch.setattr(runtime, "free_pool", lambda schema, **kw: "free pool")
    controller = runtime._llm_model("paid")
    assert isinstance(controller, runtime.CandidateController) and controller.name == "sonnet" and controller.fallback == "free pool"
    assert runtime._llm_model("free") == "free pool"
    assert runtime.structured.__wrapped__(PersonaStep) == "free pool"  # planner and report writer keep their routes
    # Sonnet shares the Vertex project, so the existing Haiku route writes the plan and report; the label says so.
    assert runtime.model_label(True) == "Claude Sonnet 5.5 for test decisions (free models as backup); planning and the report: Claude Haiku 4.5, with free models as backup"
    monkeypatch.setenv("CONTROLLER_CANDIDATE", "glm")
    monkeypatch.delenv("CLAUDE_VERTEX_PROJECT")
    assert runtime.model_label(True) == "GLM 5.3 for test decisions (free models as backup); planning and the report: Free models (gpt-oss-120b and backups)"
    assert runtime.model_label(False) == "Free models (gpt-oss-120b and backups)"


def test_sonnet_sends_the_documented_request(monkeypatch, opted_in):
    sent = vertex(monkeypatch, message())
    with provider_usage.attempt("claude_vertex", "claude-sonnet-5-5") as receipt:
        step, tokens = runtime.unwrap(candidates.sonnet(PersonaStep).invoke(MESSAGES))
    assert step == PersonaStep.model_validate(STEP) and tokens == 1020
    assert receipt.usage["input_tokens"] == 900 and receipt.usage["output_tokens"] == 120  # R-S7 receipt
    url, body = sent[0]
    assert "claude-sonnet-5-5" in url and "walkthru-test" in url
    assert body["system"] == "You are a first-time visitor." and body["messages"] == [{"role": "user", "content": "Current page: ..."}]
    for rejected in ("temperature", "top_p", "top_k", "tool_choice", "tools", "thinking"):  # 400s on Sonnet 5.5; thinking stays adaptive
        assert rejected not in body
    assert body["output_config"]["effort"] == "medium" and body["output_config"]["format"]["type"] == "json_schema"
    schema = json.dumps(body["output_config"]["format"]["schema"])
    assert '"additionalProperties": false' in schema and '"minimum"' not in schema and '"maximum"' not in schema


@pytest.mark.parametrize(("stop", "text", "error"), [("refusal", "I can't help with that.", candidates.Refused),
                                                     ("max_tokens", '{"thought": "Sign', candidates.Unusable),
                                                     ("model_context_window_exceeded", "", candidates.Unusable),
                                                     ("end_turn", json.dumps(STEP | {"confusion": 9}), ValueError)])
def test_sonnet_never_parses_refused_truncated_or_out_of_bounds_answers(monkeypatch, opted_in, stop, text, error):
    vertex(monkeypatch, message(stop, text))
    with pytest.raises(error):
        candidates.sonnet(PersonaStep).invoke(MESSAGES)


def test_glm_sends_the_documented_request(monkeypatch, opted_in):
    sent = zai(monkeypatch, completion())
    with provider_usage.attempt("glm", "glm-5.3") as receipt:
        step, tokens = runtime.unwrap(candidates.glm(PersonaStep).invoke(MESSAGES))
    assert step == PersonaStep.model_validate(STEP) and tokens == 890 and receipt.usage["input_tokens"] == 800
    url, headers, body = sent[0]
    assert url == "https://api.z.ai/api/paas/v4/chat/completions" and headers["Authorization"] == "Bearer test-key"
    assert body["model"] == "glm-5.3" and body["thinking"] == {"type": "enabled"} and body["reasoning_effort"] == "low"
    assert body["response_format"] == {"type": "json_object"} and "temperature" not in body and "tools" not in body
    assert body["messages"][0]["role"] == "system" and "JSON Schema" in body["messages"][0]["content"]


@pytest.mark.parametrize(("finish", "content", "error"), [("sensitive", "", candidates.Refused), ("length", '{"thought"', candidates.Unusable),
                                                          ("network_error", "", candidates.Unusable), ("stop", "not json", ValueError)])
def test_glm_never_parses_refused_truncated_or_invalid_answers(monkeypatch, opted_in, finish, content, error):
    zai(monkeypatch, completion(finish, content))
    with pytest.raises(error):
        candidates.glm(PersonaStep).invoke(MESSAGES)


def test_glm_receives_text_only(monkeypatch, opted_in):
    sent = zai(monkeypatch, completion())
    with pytest.raises(candidates.Unusable, match="text only"):
        candidates.glm(PersonaStep).invoke([("human", [{"type": "image_url", "image_url": {"url": "data:image/png;base64,AA"}}])])
    assert sent == []


def test_glm_receipts_fail_closed_until_storage_accepts_the_provider(monkeypatch, opted_in):
    sent = zai(monkeypatch, completion())
    monkeypatch.setenv("PROVIDER_USAGE", "postgres")
    monkeypatch.setattr(db, "begin_provider_attempt", lambda attempt_id, identity: (_ for _ in ()).throw(RuntimeError("Invalid provider")))
    with pytest.raises(provider_usage.UsageUnavailable):
        runtime.guarded("glm", candidates.glm(PersonaStep), model_name="glm-5.3").invoke(MESSAGES)
    assert sent == []  # no receipt, no request


class Answers:
    def __init__(self, result):
        self.result = result

    def invoke(self, messages):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def test_each_step_records_who_answered_and_fallbacks_are_visible():
    step = PersonaStep.model_validate(STEP)
    ok = runtime.CandidateController("sonnet", Answers(step), Answers(None)).decide({}, MESSAGES)
    assert ok.step == step and ok.metadata == {"provider": "sonnet", "model": candidates.SONNET_MODEL}
    fell = runtime.CandidateController("glm", Answers(candidates.Refused("GLM declined (sensitive)")), Answers(step)).decide({}, MESSAGES)
    assert fell.step == step and fell.metadata == {"provider": "llm", "fallback_from": "glm", "fallback_reason": "Refused: GLM declined (sensitive)"}
    hybrid = runtime.HybridPersonaModel(type("Abstains", (), {"decide": lambda self, state: (_ for _ in ()).throw(runtime.JevFallback("low confidence"))})(),
                                        runtime.CandidateController("sonnet", Answers(step), Answers(None)))
    assert hybrid.decide({}, MESSAGES).metadata == {"provider": "sonnet", "model": candidates.SONNET_MODEL, "jev_fallback_reason": "low confidence"}


def test_legacy_haiku_adapter_works_with_the_installed_sdk_and_refuses_name_swaps(monkeypatch):
    monkeypatch.setenv("CLAUDE_VERTEX_PROJECT", "walkthru-test")
    reply = message() | {"stop_reason": "tool_use", "content": [{"type": "tool_use", "id": "t", "name": "answer", "input": STEP}]}
    sent = vertex(monkeypatch, reply)
    step, _ = runtime.unwrap(runtime.claude(PersonaStep).invoke(MESSAGES))
    assert step == PersonaStep.model_validate(STEP)
    body = sent[0][1]
    assert body["temperature"] == 0 and body["tool_choice"] == {"type": "tool", "name": "answer"}  # valid for Haiku 4.5 only
    monkeypatch.setattr(runtime, "CLAUDE_MODEL", "claude-sonnet-5-5")
    with pytest.raises(RuntimeError, match="CONTROLLER_CANDIDATE"):
        runtime.claude(PersonaStep)
    monkeypatch.setattr(runtime, "PAID_MODEL", "claude-sonnet-5-5")
    monkeypatch.delenv("CLAUDE_VERTEX_PROJECT")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    with pytest.raises(RuntimeError, match="not Claude Haiku 4.5"):
        runtime._llm_model("paid")
