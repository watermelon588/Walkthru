# Model selection for Pro and Plus

Date: 2026-10-04. Recommendation for evaluation, not an accepted model switch or paid activation.

## Recommendation

**Superseded priority after the founder's live-testing feedback:** invest in the live controller first. Evaluate Sonnet 5.5 for goal interpretation and live decisions, with full GLM 5.3 as the cheaper challenger and Grok 4.7 as an optional third candidate. Keep the existing report writer while measuring traversal. The earlier Flash-Lite controller plus stronger report recommendation is no longer the proposed route. Detailed source audit, model compatibility, economic constraints and phased work: [Live decision quality plan](live-decision-quality-plan.md).

Sonnet is a candidate, not a measured winner. Its current API requires changes to the existing Haiku adapter: no non-default sampling or forced tool choice, documented structured output, explicit effort and complete usage accounting. Pro and Plus should share the selected decision quality. No paid activation or price/allocation change is made here. The price comparison and cheap routing illustration below remain background economics, not the current recommended controller policy.

## Existing implementation and economics

- SPEC.md and app/plans.py: Pro 40 runs, Plus 150; up to 30 steps per paid run. List prices $19/$49, founding $15/$39. V1 uses founder-approved 30-day access passes, not automatically renewing subscriptions.
- payment.md's latest table allocates 25% of net after its recorded transaction fee: founding Pro $3.50 ($0.0875/run at full use), founding Plus $9.26 ($0.06173/run); standard Pro $4.46 ($0.1115/run), standard Plus $11.66 ($0.07773/run). These are existing design assumptions, not newly verified payment-provider fees. Watch/Scout/citation calls share provider resources; the full allowance is not available exclusively to journeys.
- apps/api/app/agent/runtime.py uses one paid model for both plans. Enabling CLAUDE_VERTEX_PROJECT puts Claude first on paid step/planner/report routes. PERSONA_DECISION_MODEL defaults to llm; Jev is opt-in and its browser quality gate is still open.
- persona.py resends all rendered prior steps, including narration, and current indexed elements/page text on each decision. report.py grounds the final report against recorded steps and deterministic findings.
- Claude adapter has no cache_control and collapses input/output usage into total_tokens. Financial cost reservation/ledger is still unbuilt. Run limits alone do not enforce the provider allowance. Model labels are hardcoded to Haiku and need truthful routing metadata if changed.
- The final paid winner remains subject to T9 real-browser recall/cost evaluation in docs/decisions.md. Current free chain remains active until a paid activation decision is made.

## Price comparison

USD per million uncached text tokens, ordinary synchronous requests, checked against primary provider docs. Claude global Google endpoint rates; other rows direct provider rates. Reseller, region, tools, cache and reasoning usage can change bills.

| Model | Input | Output | Illustrative cost: 50k input + 6k billed output |
| --- | ---: | ---: | ---: |
| Qwen 3.8 Flash, documented global route | $0.113 | $0.382 | $0.00794 |
| GLM 5.3 Flash | $0.15 | $0.50 | $0.01050 |
| Gemini 3.1 Flash-Lite | $0.25 | $1.50 | $0.02150 |
| Claude Haiku 4.5 | $1 | $5 | $0.08000 |
| Grok 4.7 | $2 | $6 | $0.13600 |
| Claude Sonnet 5.5 | $2 | $10 | $0.16000 |
| Claude Opus 5.5 | $4 | $20 | $0.32000 |
| Claude Fable 5.1 | $10 | $50 | $0.80000 |

Illustration only, not measured run tokens or equal output quality. Different tokenizers and reasoning lengths require measuring the actual same-task invoice. Claude documents about 30% higher token counts with its newer tokenizer, varying by content. Regional/multi-region Claude endpoints have a premium over global.

Sources: [Google Claude pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing), [Claude tokenizer/platform notes](https://platform.claude.com/docs/en/about-claude/pricing), [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing), [Grok pricing](https://docs.x.ai/developers/models), [GLM pricing](https://docs.z.ai/guides/overview/pricing), [Qwen pricing](https://www.alibabacloud.com/help/en/model-studio/model-pricing).

## Illustrative routed run

Historical cheap-controller scenario, superseded for the quality-first proposal. See the linked live decision plan for Sonnet/GLM controller costs.

Assume actions consume 40k input/4k output and one report consumes 10k input/2k output:

- Flash-Lite actions: $0.016.
- Haiku report: $0.020. Total $0.036; 40 runs $1.44, 150 runs $5.40.
- Sonnet report: $0.040. Total $0.056; 150 runs $8.40, leaving only $0.86 of founding Plus allowance for other model work.
- Route Sonnet instead of Haiku on 20% of reports: average $0.040/run, 150 runs $6.00. This is a proposed budget envelope, not a quality/confidence policy or measured escalation frequency. Adding a second report rather than substituting it costs more.

Retries, planner/first-impression calls, uncertainty escalation, failures, reasoning, watch and Scout are extra unless explicitly included in measured totals. Target a routine journey/report average around $0.03-0.04, leaving room within the all-feature allowance. Do not treat the historical $0.20 T9 ceiling as a sustainable average.

## Optimization and selection work

1. Record per-request input, output/reasoning, cache-write/read, provider/model/endpoint and USD price version, including failures/fallbacks. Reserve an upper-bound cost before a paid call; enforce user and global budgets.
2. Compact old history into deterministic progress/failed-action records; keep recent outcomes, exact errors, completion evidence and persona context. Select relevant visible controls without erasing ambiguous choices that a real visitor would face.
3. Keep short schema-constrained action replies; preserve concise persona narration because it is part of the product. Use operation-specific output budgets rather than 2048 tokens for every call.
4. Separate stable safety/tool instructions from dynamic progress to permit prefix caching. Claude's documented minimum is 4096 tokens for Haiku 4.5 and 512 for Sonnet 5.5; do not assume a short system prompt is cacheable or pad irrelevant content blindly. Include writes/TTL/hits in cost measurements. [Caching rules](https://platform.claude.com/docs/en/build-with-claude/prompt-caching).
5. Use deterministic safety/validation and observable failure signals for escalation; do not trust an LLM's self-reported confidence alone. Jev's calibrated decision scores require the existing persona-fidelity gate before promotion.
6. Compare current free baseline, Flash-Lite, Haiku, Sonnet, Qwen Flash, GLM Flash and Grok on the same easy/hard fixtures plus representative owner-verified journeys. Measure correct safe completion, seeded finding recall, invented claims, invalid targets/schema failures, repeat actions, persona fidelity, p50/p95 latency and billed cost including fallback.
7. Prefer report replay for economical initial screening, then real installed-Chrome acceptance for decision candidates. Final selection is least expensive route meeting the product gates; do not make a universal quality claim from price tables.

No API calls to paid models, provider enablement, dependency change, code change, pricing change or benchmark was performed for this comparison.
