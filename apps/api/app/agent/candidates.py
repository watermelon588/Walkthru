"""Stronger controller candidates (R-S11): Claude Sonnet 5.5 on Google Cloud and GLM 5.3. Off by default.

A candidate decides persona steps only (the controller). The goal planner and the report writer keep their
routes. It runs only when CONTROLLER_CANDIDATE names it, its credentials exist, the reservation ledger is
active and every paid plan reserves a per-run maximum above zero; anything less fails at startup instead of
running free under a paid label. Requests follow each provider's current documented API (checked 2026-10-07)
and the installed SDKs; no live request is made by the tests. Contract: docs/controller-candidates.md.
"""

import json
import os
from types import SimpleNamespace

from pydantic import BaseModel

from app import provider_usage, reservations

SONNET_MODEL = os.environ.get("SONNET_MODEL", "claude-sonnet-5-5")
GLM_MODEL = "glm-5.3"
GLM_URL = "https://api.z.ai/api/paas/v4/chat/completions"
MAX_TOKENS = 4096  # covers adaptive thinking plus one PersonaStep; thinking is billed as output
LABELS = {"sonnet": "Claude Sonnet 5.5", "glm": "GLM 5.3"}
MODELS = {"sonnet": SONNET_MODEL, "glm": GLM_MODEL}
PROVIDERS = {"sonnet": "claude_vertex", "glm": "glm"}  # provider_usage receipt names
CREDENTIALS = {"sonnet": ("CLAUDE_VERTEX_PROJECT",), "glm": ("ZAI_API_KEY",)}
EFFORTS = {"sonnet": ("medium", ("low", "medium", "high")), "glm": ("low", ("low", "high", "max"))}  # default, allowed
IMAGES = {"sonnet": True, "glm": False}  # provider support; no image handoff exists yet, so both receive text only


class Refused(RuntimeError):
    """The provider declined (Sonnet stop_reason refusal, GLM finish_reason sensitive). No schema guarantee."""


class Unusable(ValueError):
    """Truncated, cut off or not the schema: never parsed into a step."""


def active() -> str | None:
    """The opted-in candidate, or None. A half-configured opt-in raises rather than silently running something else."""
    name = os.environ.get("CONTROLLER_CANDIDATE", "").strip().lower()
    if not name:
        return None
    if name not in LABELS:
        raise RuntimeError("CONTROLLER_CANDIDATE must be sonnet or glm, or unset")
    missing = [key for key in CREDENTIALS[name] if not os.environ.get(key)]
    if missing:
        raise RuntimeError(f"CONTROLLER_CANDIDATE={name} needs {', '.join(missing)}")
    if not reservations.enabled() or any(reservations.max_cost(plan) <= 0 for plan in ("launch", "pro", "plus")):
        raise RuntimeError(f"CONTROLLER_CANDIDATE={name} needs RESERVATIONS=postgres and a per-run maximum above 0 for every paid plan")
    effort()
    return name


def effort(name: str | None = None) -> str:
    name = name or os.environ.get("CONTROLLER_CANDIDATE", "").strip().lower()
    default, allowed = EFFORTS[name]
    value = os.environ.get("CANDIDATE_EFFORT", default).strip().lower()
    if value not in allowed:
        raise RuntimeError(f"CANDIDATE_EFFORT for {name} must be one of {', '.join(allowed)}")
    return value


def strict_schema(schema: type[BaseModel]) -> dict:
    """Claude structured outputs need additionalProperties false and reject numeric/length bounds; the bounds move
    into the description and Pydantic still enforces them when the answer is parsed."""
    unsupported = ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "minLength", "maxLength", "multipleOf")

    def walk(node):
        if isinstance(node, dict):
            bounds = {k: node.pop(k) for k in unsupported if k in node}
            if bounds:
                node["description"] = (node.get("description", "") + f" Bounds: {json.dumps(bounds)}.").strip()
            if node.get("type") == "object":
                node["additionalProperties"] = False
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        return node

    return walk(schema.model_json_schema())


def turns(messages: list) -> tuple[str, list[dict]]:
    """(role, text) pairs to Anthropic's system string and alternating user/assistant turns."""
    system = "\n\n".join(text for role, text in messages if role == "system")
    chat: list[dict] = []
    for role, text in messages:
        if role == "system":
            continue
        role = "user" if role == "human" else "assistant"
        if chat and chat[-1]["role"] == role:  # the API wants turns to alternate
            chat[-1]["content"] += "\n\n" + text
        else:
            chat.append({"role": role, "content": text})
    return system, chat


def _text_only(messages: list) -> None:
    if any(not isinstance(text, str) for _, text in messages):
        raise Unusable("This candidate receives text only; no image handoff is implemented")


def sonnet(schema: type[BaseModel], timeout: float = 60):
    """Sonnet 5.5 on Google Cloud with native structured output. Per the migration guide: no sampling parameters,
    no forced tool choice, no thinking budget; adaptive thinking (the default) with an explicit effort."""
    from anthropic import AnthropicVertex
    from langchain_core.runnables import RunnableLambda

    client = AnthropicVertex(project_id=os.environ["CLAUDE_VERTEX_PROJECT"], region=os.environ.get("CLAUDE_VERTEX_REGION", "global"),
                             timeout=timeout, max_retries=0)
    output = {"effort": effort("sonnet"), "format": {"type": "json_schema", "schema": strict_schema(schema)}}

    def run(messages: list) -> dict:
        _text_only(messages)
        system, chat = turns(messages)
        msg = client.messages.create(model=SONNET_MODEL, max_tokens=MAX_TOKENS, system=system, messages=chat, output_config=output)
        provider_usage.capture(msg.usage.model_dump(), "anthropic", msg.id)
        if msg.stop_reason == "refusal":
            raise Refused(f"Sonnet declined ({getattr(msg, 'stop_details', None) or 'no category'})")
        if msg.stop_reason != "end_turn":
            raise Unusable(f"Sonnet stopped with {msg.stop_reason}")
        text = "".join(block.text for block in msg.content if block.type == "text")
        raw = SimpleNamespace(usage_metadata={"total_tokens": msg.usage.input_tokens + msg.usage.output_tokens})
        return {"raw": raw, "parsed": schema.model_validate_json(text), "parsing_error": None}

    return RunnableLambda(run, name=f"candidate:{SONNET_MODEL}")


def glm(schema: type[BaseModel], timeout: float = 60):
    """GLM 5.3 over the general metered API with plain httpx. Thinking cannot be turned off; JSON mode has no schema,
    so the schema goes in the prompt and Pydantic validates the answer."""
    import httpx
    from langchain_core.runnables import RunnableLambda

    instructions = "Reply with one JSON object only, matching this JSON Schema:\n" + json.dumps(schema.model_json_schema())

    def run(messages: list) -> dict:
        _text_only(messages)
        body = {"model": GLM_MODEL, "max_tokens": MAX_TOKENS, "thinking": {"type": "enabled"}, "reasoning_effort": effort("glm"),
                "response_format": {"type": "json_object"},
                "messages": [{"role": "system", "content": instructions}] + [{"role": "user" if role == "human" else role, "content": text} for role, text in messages]}
        r = httpx.post(GLM_URL, headers={"Authorization": f"Bearer {os.environ['ZAI_API_KEY']}"}, json=body, timeout=httpx.Timeout(timeout, connect=5.0))
        r.raise_for_status()
        data = r.json()
        provider_usage.capture(data.get("usage"), "openai", data.get("id"))
        choice = (data.get("choices") or [{}])[0]
        if choice.get("finish_reason") == "sensitive":
            raise Refused("GLM declined (sensitive)")
        if choice.get("finish_reason") != "stop":
            raise Unusable(f"GLM stopped with {choice.get('finish_reason')}")
        raw = SimpleNamespace(usage_metadata={"total_tokens": (data.get("usage") or {}).get("total_tokens")})
        return {"raw": raw, "parsed": schema.model_validate_json(choice["message"]["content"]), "parsing_error": None}

    return RunnableLambda(run, name=f"candidate:{GLM_MODEL}")


ADAPTERS = {"sonnet": sonnet, "glm": glm}
