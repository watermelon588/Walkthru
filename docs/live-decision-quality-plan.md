# Live browser decision quality plan

Date: 2026-10-04. Status: proposed implementation and evaluation plan, not a paid activation or a measured model winner.

## Decision to evaluate

Spend the quality budget on the live controller first. The report can only interpret what the journey actually observed. This supersedes the cheap Flash-Lite controller recommendation in the earlier model-selection discussion.

- **First quality candidate: Claude Sonnet 5.5 through Google Cloud.** Use it for goal interpretation and live decisions. Its image input support offers a path for complex visual layouts, and the project already has an AnthropicVertex integration. This is an engineering recommendation to test, not proof that it beats every alternative on Walkthru.
- **Lower-cost challenger: full GLM 5.3**, not GLM Flash. Compare the same text/action context. It currently accepts text only, so it cannot participate in an identical screenshot-assisted comparison.
- **Optional third candidate: Grok 4.7**, if neither leading route meets quality, latency or economic gates. It supports images and has cheaper output than Sonnet; those facts do not establish browser decision accuracy.
- Keep the existing report writer during controller evaluation. Only compare paid report writers after the captured journey is trustworthy. More report latency is acceptable; invented findings are not.
- Pro and Plus should share the chosen controller quality. Existing differences remain run/site/persona/watch allowances. No plan prices, allocations or production routing change in this plan.

No model guarantees zero hallucinations. The deliverable is measured improvement in grounding, correct completion, recovery, stopping and persona fidelity. An agent reaching a genuinely broken flow must report that block rather than fabricate success.

## Phase 0: documentation discovery (completed for this plan)

Read repo instructions, handoff, CURRENT_STATE, relevant ARCHITECTURE and task entries, SPEC, payment, model-selection notes; inspect the agent runtime/persona/goal/schema, extension snapshot/execute/evidence/run loop, and eval patterns. Two discovery agents gathered source facts; the parent consolidated this plan. No live model requests or journeys were run.

### Verified implementation limits

| Current behavior | Source | Consequence |
| --- | --- | --- |
| Controller receives indexed DOM text, not screenshots; geometry is discarded | `apps/api/app/agent/persona.py:89-106,131-137`; `apps/extension/lib/snapshot.ts:137-169` | Stored screenshot evidence does not make the controller visually aware. Duplicate labels lack row/panel context. |
| Visibility checks dimensions/CSS, not occlusion or viewport intersection; 120 controls emitted | `snapshot.ts:23-25,37-43,172-194` | Dense dashboards can omit the desired control or include controls behind a modal. |
| Body text first 6,000 characters, prompt first 4,000 | `snapshot.ts:150-156`; `persona.py:89-106` | Later scrolled content can lack accompanying explanatory text. |
| Scroll always moves window down by 0.85 viewport height | `apps/extension/lib/execute.ts:40-46`; `apps/api/app/agent/schema.py:9,78-86` | No way to request an inner pane, upward scroll, smaller amount or explicit observation/wait. |
| IDs reassigned at each snapshot, no observation revision in action | `snapshot.ts:137-149,217-219`; `execute.ts:52-55` | Old IDs are not persistent identities. DOM changes during inference pose a stale-target risk; incidents have not been measured. |
| `_confirmed` checks whether last click/type navigated or showed any notice; otherwise returns true | `persona.py:259-264` | It is not goal proof. Done after scrolling can pass; an unrelated toast/navigation can validate progress; a successful same-URL SPA update can be rejected. |
| Model progress or URL substrings can terminate a journey | `persona.py:148-163,217-223`; `apps/api/app/agent/goal.py:36-39` | Complex completion conditions are insufficiently grounded. |
| Missing model targets become scroll | `persona.py:311-317` | Recovery can hide a target-grounding error behind another irrelevant action. |
| Every previous action and persona thought is resent | `persona.py:109-137` | Input cost grows with journey length; historical IDs and narration can distract from current state. |
| One paid route powers planner, decisions and writing, with free fallback | `apps/api/app/agent/runtime.py:90-100,103-129,145-167` | Enabling the current flag does not produce the proposed stage-specific quality policy. |

These are source-established limitations. They do not attribute a particular founder-observed failure without its trace. Improving observations and available actions gives a stronger model the information and controls it needs; it does not replace model judgment with a scripted journey.

### Allowed provider APIs and references

- Claude: existing `AnthropicVertex(...).messages.create(...)`; Google model ID `claude-sonnet-5-5`. Copy the request/response patterns from the [migration guide](https://platform.claude.com/docs/en/models/sonnet-5-5/migration-guide) and [structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs), using Google-supported features. Native JSON output is preferred for one PersonaStep response. Verify schema compatibility and refusal/truncation handling.
- Sonnet migration: omit non-default sampling settings and forced `tool_choice: tool/any`; current `temperature=0`/forced-answer adapter is incompatible. Adaptive thinking uses `output_config.effort`; thinking contributes to billed output and latency. Use documented settings and inspect the installed SDK before coding. Start evaluation at medium effort, comparing low only when quality remains acceptable.
- GLM: copy the general metered API Quick Start from [GLM 5.3](https://docs.z.ai/guides/llm/glm-5.3), `POST https://api.z.ai/api/paas/v4/chat/completions`, model `glm-5.3`. Documentation presents multiple account/protocol endpoints; verify the chosen account's paid API route. `thinking.type=enabled`; `reasoning_effort=low|high|max`, default max. Screen low, then high on failures. Do not assume thinking can be disabled or that a consumer Coding Plan funds product API usage.
- Cache: use documented `cache_control` patterns in [Claude caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching). Sonnet minimum 512 tokens; stable prefixes must match and writes cost money. Do not pad useless text to meet a threshold.
- Read [Google Claude setup](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/partner-models/claude/use-claude) for credentials, endpoint availability and model access. Trial credits do not establish partner-model payment coverage.

## Cost envelope

USD per million tokens, ordinary synchronous requests, before taxes. Sonnet row is Google global; GLM/Grok rows are direct provider rates. Regional Claude routes cost more. Resellers can differ.

| Candidate | Uncached input | Billed output | Proposed role |
| --- | ---: | ---: | --- |
| Claude Sonnet 5.5 | $2.00 | $10.00 | Quality-first controller and planner candidate |
| GLM 5.3 | $1.40 | $4.40 | Cheaper text controller challenger |
| Grok 4.7 | $2.00 | $6.00 | Optional multimodal challenger |

Sources: [Google pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing), [GLM pricing](https://docs.z.ai/guides/overview/pricing), [Grok pricing](https://docs.x.ai/developers/models/grok-4.7). Tokenizers, reasoning lengths, retries and image usage differ, so equal token assumptions are not equal-task invoices.

Illustrations, not measured costs:

| Scenario | Sonnet controller | GLM controller | Total with illustrative $0.01 report |
| --- | ---: | ---: | --- |
| 20 decisions, each 1,000 input + 100 total billed output | $0.0600 | $0.0368 | $0.0700 / $0.0468 |
| 30 decisions, same per-decision assumption | $0.0900 | $0.0552 | $0.1000 / $0.0652 |
| Larger context: total 40k input + 4k billed output | $0.1200 | $0.0736 | $0.1300 / $0.0836 |

The 100 output-token assumption includes all billed output, including reasoning; a short visible action does not ensure it. Planner/first-impression calls, images, retries, failed requests and other features are extra here. The report amount is an assumption, not the measured current writer bill. Cache savings are not assumed.

Existing `payment.md` planning allowances, using its recorded fee assumptions: founding Pro $3.50/40 = $0.0875 per included run; founding Plus $9.26/150 = $0.06173. Standard Pro $0.1115; standard Plus $0.07773. Watch/Scout/citation work shares these allowances. A $0.10 full-use journey costs $4/Pro pass and $15/Plus pass, before other features. The historical $0.20 eval ceiling is not an affordable routine average.

Therefore: benchmark quality first; optimize exact context/cache/reasoning next; choose a cheaper candidate only if it passes the same quality gates. If qualified routes still exceed the allowance, present the measured tradeoff for a separate founder decision on margins, allocations or prices. Do not silently downgrade to an unreliable controller or silently change purchased limits.

## Phase 1: build a live-decision benchmark and usage record

**Implement:** Copy the real action/observation capture and idempotent action pattern in `evals/e2e_extension.py:153-344`, and offline scoring structure in `evals/runner.py`. Add controller-specific expectations to owner-controlled fixtures. Preserve existing trap scoring; report recall alone does not measure successful traversal. Record action/outcome, model/effort/route, request latency, input/output/cache counts, retries/fallback and cost, with redacted payloads.

Start with eight tasks: ordinary signup; form validation/correction; same-URL dashboard completion; duplicate row buttons; nested scrolling/upward return; modal/lazy-load states; deliberately broken flow; vague goal requiring scope. Test contrasting personas. Label intended goal evidence and legitimate blocked outcomes independently of model output.

**Verify:** Capture current free baseline without changing its policy; human review false completion and agent-loss versus site failure. Replay recorded snapshots for inexpensive action screening; real browser reruns remain necessary because different actions change later observations.

**Guard:** No task traces with raw secrets, no unverified production targets, no payment submission. No paid comparison before a separately approved bounded evaluation. Logs must include failures, not only successful requests.

## Phase 2: separate planner, controller and writer routes

**Implement:** Reuse `runtime.make_model`, `structured` and `claude` entry points, with small explicit per-stage options; keep LangGraph. Copy documented native structured-output pattern for Sonnet rather than renaming the Haiku constant. Validate against PersonaStep. Preserve response block handling and classify refusal, truncation and provider failures. Set truthful per-stage provenance, avoiding the hardcoded Haiku label.

Compare Sonnet adaptive medium with lower effort later. Add a GLM general API adapter using existing approved HTTPX if no new dependency is needed. Report writer remains existing route during comparisons. Keep paid candidates off by default. Do not silently count a free fallback as a Sonnet run; expose any fallback and ensure it meets the tested policy.

**Verify:** Offline mocked requests match provider docs and installed SDK signatures; schema/refusal/truncation/timeout responses work. The discovery agent observed installed Anthropic SDK 1.6.0 has `output_config`, `thinking` and `cache_control`, but does not expose `temperature` on Messages.create; reproduce this check and test legacy Haiku compatibility too. Paid smoke tests remain a later approved gate.

**Guard:** No forced tools or temperature-zero trick as a claim of grounding. Structured JSON guarantees shape, not correct choice. Do not force 100-token output caps that truncate reasoning or JSON.

## Phase 3: improve decision context and browser controls

**Implement:** Reuse geometry computed in `snapshot.ordered`, existing `redact`, and `settle(doc, quietMs=300, maxMs=2000)` at `snapshot.ts:199`. Extend matching Python/TypeScript contracts together with bounded region/row/dialog context, viewport intersection, disabled/selected states, form constraints/options and scroll-container state. Prefer viewport-relevant text over the start of the entire document. Include an observation revision and target fingerprint; re-observe rather than executing an outdated or changed target.

Proposed new action fields, not existing APIs: scroll container reference, direction and bounded viewport-relative distance; bounded wait/observe and select-option support where needed. Derive DOM execution from the existing executor's native browser methods. Keep semantic target IDs as the main click mechanism.

For visual ambiguity, evaluate a masked current screenshot alongside DOM context. Reuse masking/capture in `apps/extension/entrypoints/inject.ts` and `lib/evidence.ts`; preserve the eight-frame cap initially. Stored screenshot metadata is not an image input. Implement an authenticated bounded image handoff and test masking before using provider image blocks; account for tokens, capture failure, disclosures and retention. GLM text-only must not receive images.

**Verify:** Duplicate labels, overlay occlusion, virtualized rows, inner-pane scrolling, upward scrolling, delayed load, native select and field correction. Rejected stale action triggers a fresh observation, not a guessed click. Observe keyboard/custom widget gaps explicitly; don't claim universal browser support.

**Guard:** No whole-DOM dumps, unlimited screenshots, unmasked fields, model-generated arbitrary JS/selectors, or arbitrary coordinate clicks that bypass existing safety. Do not expand permissions casually.

## Phase 4: align goal, persona and completion evidence

**Implement:** Reuse existing `goal.plan`, `SessionState`, action outcome capture at `persona.py:183-200` and one-action interrupt/resume graph. Give the controller a task contract: intended outcome, constraints, provided synthetic test data and observable finish condition. Persona preferences affect choices and hesitation; they do not excuse inventing controls or forgetting the owner's goal. Keep short persona narration separate from internal action justification and recorded outcome.

Distinguish a working last action from proof of goal completion. Require cited observed milestone evidence for progress/done, including same-URL state changes. Generic URL change, unrelated toast or scrolling is insufficient. Vague goals with materially different interpretations need a scoped goal selected by the owner before execution; harmless bounded interpretations should be disclosed rather than invented silently.

Maintain explicit outcomes: completed, genuine site block/persona abandonment, safety stop, owner stop, insufficient instruction, controller/provider failure. Reuse existing supported states where possible; coordinate any required wire changes. Report actual uncertainty and incomplete coverage. Retain the existing behavior that controller loss is not automatically a site defect.

**Verify:** No false done after scroll or unrelated navigation/toast; same-URL success can finish; stale/missing targets are controller limitations; legitimate broken flows remain findings. Test contradictory persona/task inputs and correction of invalid filled fields. Do not reward forced task completion at the cost of persona fidelity.

**Guard:** No unrestricted autonomous goal invention, self-reported confidence as proof, or successful navigation treated as proof of business outcome. Preserve payment/delete/CAPTCHA and domain/confirmation controls.

## Phase 5: optimize and select within a bounded paid evaluation

**Implement:** Replace repeated full narration with a compact factual state (milestones/evidence, recent actions, failed alternatives and remaining goal). Keep exact current errors, relevant fields and ambiguity. Split stable instructions/schema from dynamic state for documented prefix caching. Record cache writes/hits rather than projecting guaranteed savings. Reserve provider cost before requests and enforce user/global limits; the existing run quota is insufficient. Any persistence/schema additions need separately reviewed numbered migrations under repo rules.

After offline readiness, propose a **$10 maximum initial paid evaluation**, not authorized by this plan: eight tasks x two repeats x Sonnet/GLM = 32 paid journeys plus free baseline, stopping early at the cap. Estimate actual per-request liability before starting. Optional Grok is a separate bounded extension, not automatically funded. Expand the best routes to a larger held-out fixture suite and installed-Chrome acceptance before production selection.

Proposed acceptance targets, to agree before executing: at least 95% correct completion on explicitly feasible, clear held-out tasks; zero unsafe actions and zero unsupported completions in the suite; at least 90% correct clarification/blocked outcomes; preserve historical at least 80% seeded-trap recall. Report sample size and uncertainty; zero observed failures does not prove zero future failures. Measure p50/p95 decision latency, loops, target/schema errors, persona fidelity and **total cost per correctly completed flow**, including failed attempts.

Choose GLM only if it meets the same gates, does not materially regress completion/persona fidelity versus Sonnet, and materially lowers actual cost. Otherwise retain Sonnet as the quality candidate and resolve the economic shortfall explicitly. Do not run two models or a verifier model on every click by default.

**Verify:** Full-use Pro/Plus scenario includes planner/report/retries and other features; cache hit/miss and budget exhaustion are exercised. Long journeys fit the measured run time limit; any latency budget change is explicit and tested. Benchmark enhancements separately from the model switch to identify which change helped.

**Guard:** No paid activation, API enablement, dependency purchase or pricing edit until separately authorized. Do not treat monthly promotional credits or low API prices as evidence of task quality.

## Phase 6: final verification and staged adoption

Confirm every provider setting against official docs and actual account availability. Run API pytest/Ruff, extension Vitest/TypeScript/lint/build, and web build/lint if UI/contracts changed. Add meaningful regressions for termination, stale targets, scrolling and budget behavior. Complete real installed-extension acceptance on owned fixtures, including signed-in flows and safe stops. Review reports against captured evidence and distinguish not tested from passed.

Record the measured chosen route, usage/price version, benchmark failures, sample size, feature allowance and rollback policy in docs/decisions, ARCHITECTURE and CURRENT_STATE. A founder-approved, small paid beta precedes general adoption. Paid configuration remains off until that separate activation.

Later deeper dashboard analysis should split an owner-defined journey into bounded subgoals, retaining factual page/state memory and completion evidence. Evaluate coverage, virtualized widgets and interrupted-run recovery before raising page/step limits. Larger context windows alone do not guarantee correct long journeys or affordable plans.

## Current execution status

Only analysis and documentation were completed. No app code, model configuration, dependency, database schema, provider account, plan price or run limit changed. No paid request, benchmark or deployment was performed. Documentation whitespace verification is recorded in the session completion.
