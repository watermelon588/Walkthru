# Provider attempt receipts (R-S7)

Implementation date: 2026-10-06. Records provider usage separately from legacy report token totals. This slice adds no billing, credit balance, reservation, model route, dependency, provider request or customer charge.

## Storage and activation

`PROVIDER_USAGE=off` is the default. It makes no receipt database requests. Existing model order, free defaults and configured paid-route gates are unchanged. This state does **not** claim that deployed calls have durable receipts.

`0004_provider_attempts.sql` and its reversible `.down.sql` are proposed numbered migrations. They were tested only against disposable local PostgreSQL. No configured or hosted database was inspected or migrated. The [session workflow](restructure-sessions.md#working-contract) explicitly excludes migration activation from a build session.

After separate migration/activation authorization, the operator applies the numbered migration through the existing runner and sets `PROVIDER_USAGE=postgres` on API **and standalone worker** processes. Restart both. API startup checks that service-only receipt storage is readable; every provider dispatch additionally requires a confirmed begin RPC. A missing schema or unavailable storage cannot silently fall through into unrecorded inference. Worker begin checks cover processes that do not run API startup. Do not enable the flag before applying the migration. Rolling it back deletes historical receipts, so disable recording and export/reconcile pending entries first.

The table is protected by RLS and revoked grants. `anon` and `authenticated` can neither read it nor execute its RPCs. `service_role` can read records and execute the two narrow write RPCs, but cannot directly insert, update or delete records. There is no browser/report/public/MCP receipt endpoint. Retention and account-erasure handling need an explicit policy before activation; the proposed table intentionally has no run/job foreign key, because planning may precede run creation and jobs are purged independently. It retains opaque owner UUIDs, never email addresses.

## Identity and lifecycle

| Field | Contract |
| --- | --- |
| Attempt ID | Fresh server UUID for each provider wrapper invocation; persisted before provider work. |
| Operation ID | Accepted request key for idempotent run operations; otherwise server request correlation UUID or fresh UUID. Jobs use deterministic UUIDv5 of `walkthru:job:<integer ID>`. Citation checks use their check UUID. |
| Stage ID/name | Fresh UUID for each logical model call. Names: goal plan, persona decision, first impression, synthesis, citation web/memory, Scout or other. All model fallbacks within that call share it. |
| Attempt number | Increasing within one stage, including failed/abstained/skipped candidates. A controller correction creates a new stage rather than overwriting its first attempt. |
| Run/user ID | Validated server UUIDs when available. The planner can refer to a run ID before its row exists. Child comparison scans retain their own run IDs. |
| Job fields | Actual positive integer job ID, claimed attempt number and UUID lease. The logical operation stays stable across leases/restarts; new dispatches retain distinct attempt/stage IDs. |
| Provider/model | Fixed provider allowlist plus bounded configured/requested model identifier. These identify the requested route, not proof of the upstream model/version an aggregator executed. |
| Provider request ID hash | SHA-256 of a bounded supplied provider ID, when available. It supports matching receipts, not fetching later provider stats. No unrestricted response identifier is stored. |

The begin RPC inserts `pending`. Repeating the same ID and exact identity returns the same acknowledgement, including after completion; conflicting identity returns false. This acknowledgement confirms a receipt write. It is **not** an inference idempotency/admission token.

Completion stores immutable `succeeded`, `failed` or `skipped`, integer duration, an allowlisted error category, usage and estimate. Identical completion replay returns true; missing IDs or conflicting terminal payloads return false. Receipt RPC transport retries reuse the exact ID/payload. They never repeat model work. Existing saved-report guards and request idempotency prevent their own application replays independently.

If the process dies after begin or the completion write cannot be confirmed, the receipt stays pending and its usage/cost remain unknown. Completion persistence failure emits `provider_usage_uncertain` with safe operation/attempt IDs and preserves the provider result. It does not trigger an inference fallback. No lease expiry deletes/releases pending receipts. A later application/job retry can make new attempts and must count both. This is evidence retention, not the uncertain-spend reconciliation or admission promised by R-S8/R-S9.

An open circuit creates `skipped/circuit_open`, with unknown usage and no provider request. Other categories are timeout, transport, HTTP, parse, abstained, error and cancelled. A failed request or timeout does not establish zero liability. Configured SDK retries remain zero; unsupported hidden provider-side retries cannot be observed here. Pre-call configuration failures may be recorded as failed without a request. A response returned by the provider can incur usage even if local parsing or Jev confidence checks reject it.

## Usage contract

Every channel is a nonnegative bounded integer or JSON null. Missing/invalid values are null; booleans, numeric strings, fractional token counts, negative counts, non-finite values and oversized values are not counts. No total is synthesized from incomplete channels.

Channels: input, output, supplied total, cache read/write, cache write at 5 minutes/1 hour, cache-storage token-seconds, reasoning, image/audio input/output, tool-input tokens and supplied server-tool request counts. Cache storage has a reserved unknown channel; current adapters do not receive a supported storage-duration meter. Supplied OpenRouter total credit cost and USD server-tool cost are separate from token estimates. Missing image/tool charges cannot be inferred from the number of images or function calls.

| Source | Accounting semantics |
| --- | --- |
| Groq/OpenAI-compatible | Native input/output are inclusive; cached input and reasoning are detail subsets. Native response metadata takes precedence over SDK synthesized zero/total values. |
| Gemini native | Candidate output excludes thoughts; reasoning and tool-input counts remain separate. Modality details are retained when supplied. |
| LangChain | Input/output totals are normalized inclusive counts, with optional cache/reasoning detail channels. |
| Anthropic native | Input excludes cache reads/writes; those stay separate. Cache TTL buckets refine aggregate writes and must not be added again. |
| Jev | Supplied input/output/total only; other channels and inclusive/exclusive semantics remain unknown. |

`usage_source`, `input_semantics` and `output_semantics` accompany each receipt. Empty usage has unknown semantics. Synchronous Gemini calls observe the existing public SDK `client.models.generate_content` return before LangChain 4.4.0 folds thoughts into output, drops modality details and fills missing counts with zero. The SDK method is wrapped once per cached model instance; no extra transport request is issued. This implementation uses the installed signatures and has a test through the actual SDK/LangChain conversion. Async/streaming model calls are not current runtime entry points and need separate instrumentation before use.

Native OpenRouter/Vertex adapters capture usage immediately after receiving the response and before structured parsing. Jev captures before bounded confidence/target validation. Citation engines and each Scout fallback have receipts. Request context reaches graph nodes; job context also reaches parallel comparison workers through separately copied contexts. A deterministic assertion that skips the planner still makes no planner call or receipt. Deterministic PSI/SEO/security fetches, email and checkout are outside this model-attempt ledger.

Only numeric allowlists, fixed accounting enums, server IDs and bounded model labels persist. Prompts, goals, DOM/text, typed values, URLs, raw response bodies, answers, credentials, headers, exception messages and arbitrary usage extras are omitted. SQL validates receipt identity/result fields and rejects unexpected fields. Legacy `Report.tokens` remains a compatibility summary of successful calls, including its existing missing-as-zero behavior; it is not the financial authority.

## Price inputs and honest estimates

Catalog version `groq-standard-2026-10-06`, source reviewed 2026-10-06:

| Model | Input micro-USD / million tokens | Output micro-USD / million tokens |
| --- | ---: | ---: |
| `openai/gpt-oss-120b` | 150,000 | 600,000 |
| `openai/gpt-oss-20b` | 75,000 | 300,000 |

These are the [published Groq standard list rates](https://console.groq.com/docs/models), used only for an auditable **partial token baseline**. They do not establish a free account's actual invoice. The receipt retains exact integer rates, version, source date, USD currency and `standard_tokens_no_cache_discount` basis. It requires both supplied inclusive input and output, multiplies integer counts by integer rates, and rounds the combined numerator half up once to micro-USD. Detail/subset counts are not added again. Other models/providers have null price versions/rates/estimates. No live pricing lookup or routing change occurs.

This baseline excludes cache discounts, storage, tools, fees, taxes and account-specific agreements. `total_cost_microusd` is always null. Positive cache counts do not authorize an assumed savings figure. Actual statements and reviewed complete tariff/account semantics remain R-S8/R-S15 work. [OpenRouter usage accounting](https://openrouter.ai/docs/cookbook/administration/usage-accounting) reports its `cost` in credits, so it is retained as `openrouter_credits` rather than silently converted to USD. Its explicitly supplied USD server-tool cost is a separate field. Decimal strings/values convert to integer micro-units with half-up rounding; missing/non-finite/negative values remain null. A reported amount and a list-price assumption are distinct evidence.

Additional primary contracts checked: [Groq cache usage](https://console.groq.com/docs/prompt-caching), [Gemini usage fields](https://ai.google.dev/api/generate-content#UsageMetadata), [LangChain usage metadata](https://docs.langchain.com/oss/python/langchain/messages), [Anthropic cache accounting](https://platform.claude.com/docs/en/build-with-claude/prompt-caching), [OpenRouter API fields](https://openrouter.ai/docs/api_reference/overview). Installed package signatures, not a newer documentation example, govern these adapters.

## Verification and handoff

Offline tests cover native cached/thinking/modality/tool responses, missing usage, SDK-generated zeros, failed parsing, Jev abstention, Scout/citation fallback, circuit skips, timeout, context isolation, job IDs/leases, parallel child scans, request replay, startup opt-in and lost completion acknowledgements. Disposable PostgreSQL covers concurrent duplicate acknowledgements, immutable terminal writes, subprocess exit/restart, RLS/RPC grants, bounded/privacy validation, real lost HTTP acknowledgement replay, migration rollback/reapply and existing migration history.

Current local evidence is in ignored `evals/results/restructure-session-7/`. Final full offline API: **1,022 passed, 19 existing PostgREST-dependent skips**, one existing Starlette/AnyIO warning, exit 0 in 294.32 seconds. Fresh final provider/persona/completion consumers: **108 passed** after simplifying the context wrapper. Earlier affected suite: 134 passed; provider/SQL suite: 42 passed before the final comparison-context regression and stricter SQL field requirements, both included in full verification. Whole API Ruff and diff checks passed. Web/extension source was preserved from the completed R-S6/R-S18 slices; this API-only slice did not repeat their unchanged UI builds.

Next independent slice: R-S7a, scoped cache eligibility/freshness/concurrent misses and measured savings. R-S8 must adopt a reviewed financial storage/price contract and preserve uncertain liability; these records do not authorize reservations, settlement, funded admission or paid experiments. Hosted PostgREST permissions/schema reload, migration/flag activation, live-provider usage fidelity, provider bills and deployed multi-worker acceptance remain unverified.
