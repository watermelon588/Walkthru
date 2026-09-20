"""TypeSafe Jev browser-decision contract."""

import httpx
import pytest

from app.agent.schema import PersonaStep
from app.agent.typesafe import JevDecisionClient, JevFallback, build_request


def state(*, history=None, elements=None, text="Create your account"):
    return {
        "run_id": "run-123",
        "goal": "Create a free account",
        "persona": "first_timer",
        "logged_in": False,
        "steps": history or [],
        "observation": {
            "url": "https://fixture.test/signup",
            "title": "Create account",
            "elements": elements
            or [
                {"id": 1, "tag": "a", "text": "Home"},
                {"id": 2, "tag": "input", "type": "email", "text": "Email"},
                {"id": 3, "tag": "input", "type": "password", "text": "Password"},
                {"id": 4, "tag": "button", "type": "submit", "text": "Create account"},
            ],
            "text": text,
            "errors": [],
        },
    }


def response(*, operation="click", operation_confidence=0.95, click="e4", click_confidence=0.91, type_target="none", type_confidence=0.9, goal=0.04, confusion=0.2):
    return {
        "model": "jev-1.13.0",
        "answers": {
            "operation": {
                "type": "choice",
                "choice": operation,
                "confidence": operation_confidence,
                "probabilities": {operation: 1.0},
            },
            "click_target": {
                "type": "choice",
                "choice": click,
                "confidence": click_confidence,
                "probabilities": {click: 1.0},
            },
            "type_target": {
                "type": "choice",
                "choice": type_target,
                "confidence": type_confidence,
                "probabilities": {type_target: 1.0},
            },
            "goal_achieved": {"type": "noul", "noul": goal},
            "confusion": {
                "type": "score",
                "score": confusion,
                "confidence": 0.9,
                "legend": {"0": "clear", "1": "hesitant", "2": "confused", "3": "stuck"},
                "probabilities": {"0": 1.0},
            },
        },
        "usage": {"input_tokens": 900, "output_tokens": 20},
    }


def client_with(body):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer secret-key"
        return httpx.Response(200, json=body)

    return JevDecisionClient("secret-key", client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_build_request_uses_structured_state_and_compatible_targets():
    payload = build_request(
        state(
            history=[
                {
                    "action": "type",
                    "target_id": 2,
                    "text": "walkthru.tester@example.com",
                    "thought": "I entered the email",
                    "url": "https://fixture.test/signup",
                }
            ]
        )
    )

    assert payload["model"] == "jev-1.13.0"
    assert set(payload["questions"]) == {"operation", "click_target", "type_target", "goal_achieved", "confusion"}
    assert set(payload["questions"]["click_target"]["criteria"]) == {"none", "e1", "e4"}
    assert set(payload["questions"]["type_target"]["criteria"]) == {"none", "e2", "e3"}
    assert payload["state"]["history"] == [
        {"action": "type", "target_id": 2, "url": "https://fixture.test/signup"}
    ]
    assert "walkthru.tester@example.com" not in str(payload)


def test_maps_high_confidence_click_to_persona_step():
    decision = client_with(response()).decide(state())

    assert decision.step == PersonaStep(
        thought="I will use Create account because it looks like the clearest next step.",
        action="click",
        target_id=4,
        confusion=0,
    )
    assert decision.tokens == 920
    assert decision.metadata == {
        "provider": "jev",
        "decision_model": "jev-1.13.0",
        "decision_confidence": 0.91,
        "goal_probability": 0.04,
    }


@pytest.mark.parametrize(
    ("field_type", "label", "expected"),
    [
        ("email", "Email", "walkthru.tester+run-123@example.com"),
        ("password", "Password", "Walk-thru-2026!"),
        ("text", "Full name", "Test Walker"),
    ],
)
def test_known_identity_fields_do_not_need_generation(field_type, label, expected):
    current = state(elements=[{"id": 7, "tag": "input", "type": field_type, "text": label}])
    body = response(operation="type", type_target="e7", confusion=0.6)

    decision = client_with(body).decide(current)

    assert decision.step.action == "type"
    assert decision.step.target_id == 7
    assert decision.step.text == expected
    assert decision.step.confusion == 1


def test_low_operation_confidence_requests_llm_fallback():
    body = response(operation_confidence=0.38)

    with pytest.raises(JevFallback, match="operation confidence"):
        client_with(body).decide(state())


def test_low_target_confidence_requests_llm_fallback():
    body = response(click_confidence=0.44)

    with pytest.raises(JevFallback, match="target confidence"):
        client_with(body).decide(state())


def test_open_ended_text_field_requests_llm_fallback():
    current = state(elements=[{"id": 8, "tag": "textarea", "text": "Tell us about your project"}])
    body = response(operation="type", type_target="e8")

    with pytest.raises(JevFallback, match="open-ended text"):
        client_with(body).decide(current)


def test_done_requires_goal_confirmation():
    body = response(operation="done", goal=0.4)

    with pytest.raises(JevFallback, match="goal probability"):
        client_with(body).decide(state())


def test_provider_failure_requests_llm_fallback():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(529, json={"detail": "overloaded"})

    client = JevDecisionClient("secret-key", client=httpx.Client(transport=httpx.MockTransport(handler)))

    with pytest.raises(JevFallback, match="provider error"):
        client.decide(state())


def test_malformed_target_requests_llm_fallback():
    body = response(operation="click", click="e4")
    del body["answers"]["click_target"]

    with pytest.raises(JevFallback, match="malformed target"):
        client_with(body).decide(state())
