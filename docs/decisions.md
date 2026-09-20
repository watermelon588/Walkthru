# Decisions

## T9: Free and paid model selection

**Status:** Pending real browser benchmark

### Measurement contract

- Dataset: 18 seeded traps in `evals/traps.json`, split evenly across UX, SEO, and passive security.
- Recall: a trap counts as found only when a conservative phrase appears in the captured report or browser-run steps.
- Cost: use provider or LangSmith `cost_usd` when available. Otherwise calculate from separate input and output token counts using the rates current on the experiment date.
- Gates: at least 80% overall recall, free run at most $0.02, paid run at most $0.20.

### 2026-09-19 deterministic baseline

| Candidate | Overall | UX | SEO | Security | Cost / run |
|---|---:|---:|---:|---:|---:|
| Deterministic homepage scans | 11/18 (61%) | 0/6 (0%) | 6/6 (100%) | 5/6 (83%) | unknown |

This is a boundary check, not a model result. The homepage scanners correctly find every SEO trap and five security traps. The insecure signup form and all UX traps require the extension to traverse the flow.

### Decision still needed

Capture the same hard-fixture goal with the free pool and each paid candidate through the real extension. Score and publish those captured runs with `evals/runner.py`, then choose the least expensive candidate that clears the recall gate. Do not change `PAID_MODEL` before that comparison.

## T9: Jev as the browser decision layer

**Status:** Benchmark candidate, not adopted

### Finding

Jev 1.13 is a TypeSafe System One model. It consumes text or structured text state and returns typed `Choice`, `Score`, and `Noul` decisions with probabilities. It does not generate prose, explanations, code, images, audio, or video. The official model card lists a price of $0.042 per million input tokens, free output tokens, a 64k request context, and a 32k state-plus-longest-question limit.

This matches part of Walkthru's browser loop unusually well. The extension already converts the page into at most 120 indexed controls, below Jev Choice's documented 255-option maximum. A single Jev call could choose the operation and compatible target while also scoring goal completion, stuck probability, and confusion. LangGraph can remain the orchestrator because its nodes can call Jev, an LLM, or plain code.

Jev cannot replace every current LLM call. Free-text form values that are not known test identity fields still need deterministic generation or a small generative model. Persona think-aloud, first impressions, summaries, findings, and fixes also require generation. A post-run LLM can turn the structured trace into human-readable evidence without putting prose generation on every browser step.

### Candidate architecture

1. Keep the extension snapshot, redaction, safety executor, LangGraph state, checkpointer, and reports.
2. Replace only the persona graph's hot-path action selection with one Jev request containing speculative parallel questions for operation, target, goal completion, stuck state, and confusion.
3. Use deterministic test identity values first. Call a small text model only for genuinely open-ended input.
4. Generate persona narration and report prose after the run from the structured trace.
5. Gate low-confidence decisions to the existing LLM or stop safely.

### Risks

- Jev 1.13 is newly released and its public browser-agent evidence is narrow. Browser Use reports three successful repeats of one Google Flights task, not a general reliability benchmark.
- TypeSafe documents weaker performance on indirection, numeric precision, long irrelevant state, adversarial content, and non-English inputs.
- Jev accepts text only, so screenshot understanding still needs a vision-capable model if Walkthru later tests canvas-heavy or visually ambiguous interfaces.
- TypeSafe offers zero data retention only on enterprise plans. Authenticated page data still needs the existing client-side redaction and a vendor/privacy review.

### Decision gate

Add Jev as a third candidate in Session 8B, using the same easy and hard fixture captures and the existing 18-trap scorer. Do not replace the free pool unless the hybrid clears the same recall gate, completes the easy flow reliably, and materially improves median step latency and cost.

Sources: [TypeSafe introduction](https://docs.typesafe.ai/introduction), [model and pricing](https://docs.typesafe.ai/models), [Jev 1.13 limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13), and [Browser Use Jev Ultrafast](https://github.com/browser-use/jev-ultrafast).

### 2026-09-20 live API experiments

The official TypeSafe skill was installed globally and Jev `jev-1.13.0` was called through the documented HTTP API. The key is stored only in ignored `apps/api/.env`.

| Design | Easy decisions | Median latency | Mean input tokens | Mean operation confidence |
|---|---:|---:|---:|---:|
| One combined action-target Choice | 5/5 | 625 ms | 938 | 0.896 |
| Speculative operation and compatible targets | 5/5 | 382 ms | 1,044 | 0.966 |

The speculative fan-out shape is the implementation candidate. It completed homepage CTA selection, email, password, submit, and goal detection correctly. On the ambiguous hard homepage it selected the exact footer `Create account` link five times with confidence 1.0. That is efficient but may under-represent how a person reacts to the more prominent vague `Continue` and `Proceed` buttons, so persona fidelity remains unproven.

Risk probes supported conservative fallback:

- After a misleading action opened a newsletter modal, operation confidence fell to 0.38 and target confidence to 0.44.
- Adversarial page text did not cause a destructive selection, but TypeSafe's documented adversarial-content limitation means code safety remains mandatory.
- With 120 visible controls, Jev selected element 120 correctly in 638 ms using 6,809 input tokens.

**Decision:** build an opt-in hybrid adapter with a 0.50 starting confidence floor, deterministic values for known identity fields, and LLM fallback for low confidence, provider errors, and open-ended typing. Keep the existing LLM as the default until the real hard-fixture benchmark clears the product recall gate. Pin `jev-1.13.0` during evaluation.

Additional sources: [HTTP API](https://docs.typesafe.ai/api), [structured state](https://docs.typesafe.ai/concepts/state), [confidence routing](https://docs.typesafe.ai/confidence), and [speculative fan-out](https://docs.typesafe.ai/patterns/fan-out).
