# Controller candidates, disabled (R-S11)

Implemented locally 2026-10-07. Code:

- `apps/api/app/agent/candidates.py` (adapters and opt-in gate);
- `CandidateController`, `_haiku_only` and `model_label` in `app/agent/runtime.py`;
- `"glm"` in `provider_usage.PROVIDERS`;
- tests in `tests/test_candidates.py`.

Plan: [live decision quality plan](live-decision-quality-plan.md), phase 2.

Nothing here is switched on. No live provider request was made, no key was added and no price or plan changed.

## What a candidate is

A stronger model that decides **persona steps only** (the controller). The goal planner, first impression and report writer keep their existing routes. A paid-plan run uses the candidate when one is opted in. Free plans never do.

| | Claude Sonnet 5.5 | GLM 5.3 |
|---|---|---|
| Route | Google Cloud `AnthropicVertex`, model `claude-sonnet-5-5` (`SONNET_MODEL` to override) | `POST https://api.z.ai/api/paas/v4/chat/completions`, model `glm-5.3`, plain httpx |
| Credentials | `CLAUDE_VERTEX_PROJECT` (+ optional `CLAUDE_VERTEX_REGION`, default `global`) | `ZAI_API_KEY` |
| Output | Native structured output: `output_config.format` json_schema with `additionalProperties: false`. Bounds move into descriptions and Pydantic enforces them. | `response_format: json_object` (JSON mode has no schema), schema in the prompt, Pydantic validation |
| Reasoning | Adaptive thinking (default, no `thinking` field), `output_config.effort` = `CANDIDATE_EFFORT` (default `medium`, allowed `low`/`medium`/`high`) | `thinking.type=enabled` (cannot be disabled), `reasoning_effort` = `CANDIDATE_EFFORT` (default `low`, allowed `low`/`high`/`max`) |
| Not sent | `temperature`, `top_p`, `top_k`, forced `tool_choice`, thinking budgets (each 400s on Sonnet 5.5) | `temperature`, tools |
| Refusal | `stop_reason: refusal` raises `Refused` | `finish_reason: sensitive` raises `Refused` |
| Truncation and other stops | `max_tokens`, `model_context_window_exceeded` and the rest raise `Unusable` | `length`, `network_error` and the rest raise `Unusable` |
| Images | Supported by the provider. Not sent: no authenticated image handoff exists yet (plan phase 3). | Text only. Image content is refused before any request. |
| Receipts (R-S7) | `claude_vertex`, Anthropic usage shape | `glm`, OpenAI usage shape. Storage migration 0004 does not accept `glm`, so with `PROVIDER_USAGE=postgres` a GLM attempt fails closed before any request. |

`max_tokens` is 4096 for both. Thinking counts toward it and is billed as output. A refused, truncated or out-of-schema answer is never parsed into a step.

Sources, checked 2026-10-07:

- [Sonnet 5.5 migration guide](https://platform.claude.com/docs/en/models/sonnet-5-5/migration-guide);
- [structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs);
- [GLM 5.3](https://docs.z.ai/guides/llm/glm-5.3);
- [Z.AI chat completion](https://docs.z.ai/api-reference/llm/chat-completion);
- the installed `anthropic==1.6.0` `Messages.create` signature: `output_config`, `thinking` and `cache_control` are present, `temperature` is not.

## Opt-in gate

`CONTROLLER_CANDIDATE=sonnet|glm` (unset by default) turns a candidate on. `candidates.active()` raises at startup, before any run, unless all of these hold:

- the name is known;
- its credentials are set;
- `CANDIDATE_EFFORT` is valid for it;
- `RESERVATIONS=postgres`;
- `RUN_MAX_COST_MICROUSD_LAUNCH`, `_PRO` and `_PLUS` are each above 0.

A half-configured opt-in therefore never runs free models under a paid label, and never spends without a reserved maximum. Unset means exactly the previous behaviour.

## Provenance and fallback

`CandidateController.decide` records on every step who answered:

- the candidate: `{"provider": "sonnet", "model": "claude-sonnet-5-5"}`;
- the free fallback: `{"provider": "llm", "fallback_from": "sonnet", "fallback_reason": "Refused: ..."}`.

On any candidate failure, that step is answered by the free pool, and the step record says so. A fallback is never counted as a candidate decision. No paid model sits behind a candidate. With `PERSONA_DECISION_MODEL=jev`, Jev stays first and the candidate is its fallback, with both reasons kept.

`model_label` (report and quote `model_route`) names both routes. Example: "Claude Sonnet 5.5 for test decisions (free models as backup); planning and the report: Claude Haiku 4.5, with free models as backup". Sonnet uses the same Vertex project as the existing Haiku route, so setting it also turns on Haiku for planning and the report; the label says so. A quote issued before a candidate is switched on becomes stale (R-S10), so customers see the change before it applies.

## Legacy Haiku fixes found on the way

- The direct Haiku-on-Vertex adapter (`runtime.claude`) passed `temperature=0`, which `anthropic==1.6.0` rejects with a TypeError. It had only ever been tested as a stub. It now sends `extra_body={"temperature": 0}`, verified through the real SDK with a mock transport. `ChatAnthropic` (langchain-anthropic 1.7.2) already handles this itself.
- `CLAUDE_MODEL` and `PAID_MODEL` now refuse any name that is not Claude Haiku 4.5. Their forced-tool, temperature-0 requests are invalid on Sonnet 5.5, so a name-only swap fails at startup and points here.

## Verification

`tests/test_candidates.py`, 21 passed, offline. The real SDK or httpx serializes each request; mock transports answer it. The tests cover:

- off by default with free defaults unchanged;
- five half-configured opt-ins refused, at startup too;
- candidates drive paid decisions only, while the planner and writer keep their routes;
- truthful labels for both candidates;
- documented Sonnet and GLM request bodies;
- refusal, truncation, context and out-of-bounds or invalid answers never parsed;
- receipts captured;
- GLM text only;
- GLM receipts fail closed before any request;
- per-step provenance, including through Jev;
- the legacy Haiku adapter against the installed SDK, and its name-swap refusal.

Affected suites (runtime, persona, goal, provider usage and receipts, providers, Jev, quotes): 145 passed. Ruff is clean.

## What R-S12 needs (not authorized here)

- **Founder approval** for a capped paid comparison. The plan proposes a $10 maximum: eight tasks, two repeats, Sonnet and GLM, stopping early at the cap. Optional Grok would be a separate decision.
- **A Google Cloud project with Claude Sonnet 5.5 partner-model access.** Trial credits do not cover partner models. Also needed: a Z.AI metered API key (a coding plan does not fund API use).
- **Ledger and caps.** Apply migrations 0005/0006, set `RESERVATIONS=postgres` and set per-run maximums above 0 for an evaluation account.
- **A proposed migration for GLM receipts.** It must let `begin_provider_attempt` accept `glm`; until then GLM can only run with `PROVIDER_USAGE=off`. Sonnet and GLM token prices also need a new estimate price version. Receipts record them as unpriced today.
- **One paid smoke request per route**, before benchmarking. It confirms account availability and the exact response blocks, especially Sonnet `stop_details` and GLM usage fields.

## Not built

- An image handoff to Sonnet (plan phase 3).
- Prompt caching (`cache_control`): it needs the stable/dynamic prompt split from phase 5.
- Per-stage paid planner or writer candidates.
- Grok.
