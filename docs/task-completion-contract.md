# R-S4 task completion contract

Implemented 2026-10-05. This is bounded browser-state evidence, not a backend or whole-application certification. See [the workflow](restructure-sessions.md#r-s4-finish-the-task-for-the-right-reason).

The owner's original `goal` remains the task authority. The planner's `intent` is a subordinate interpretation; built-in and custom persona preferences govern reactions and safe path choices only. Model `progress` is advisory and is replaced by the code-confirmed count. Neither persona impatience nor generated narration establishes completion, a website defect or an unstated business rule. Jev receives the same objective, checkpoints, confirmed count and milestone evidence as the generative decision path.

## Declaring the finish condition

`Checkpoint` keeps the existing `description` and optional `url_contains`, with two optional, backward-compatible fields:

| Field | Meaning |
| --- | --- |
| `kind` | `navigation` means opening a specified route; `outcome` means a functional result and is the default for missing legacy fields. |
| `text_contains` | An exact public finish phrase, at most 160 characters, declared by the owner in the goal or present in the initial public page text/notices. Unknown phrases stay null. |

The planner cannot introduce a finish phrase absent from these inputs. Known functional objective verbs also prevent weakening the final checkpoint to URL-only navigation. This conservative vocabulary guard is not complete semantic validation of arbitrary natural-language tasks. The original goal remains visible in every decision prompt. Ambiguous business rules and missing finish expectations remain unresolved; R-S6 adds a declared fixture/assertion path.

For a functional goal, the owner can state a finish condition in their goal, for example `Create an account; finish when the page says "Account created"`. A page-only objective can declare a navigation marker such as `/pricing`. Planner failure preserves the literal owner goal with unknown expectations; it cannot fall back to accepting any URL change.

## What counts as evidence

- A navigation milestone requires a newly matching route on the original HTTP(S) origin. Hostnames and return-URL query parameters cannot satisfy a path marker. The existing URL-marker substring semantics retain token boundaries, so a declared prefix such as `/work/skyguide` can match `/work/skyguide-ai`; it is not exact page-content proof.
- A functional milestone requires its declared public phrase to appear freshly in page text or notices. Same-URL SPA transitions are supported. If it also specifies a URL marker, both signals must match. Filled field values, element labels, model narration, unrelated notices, pre-existing phrases, blank signals, negated confirmations and conflicting visible errors are insufficient.
- Scroll movement alone cannot establish an outcome. A bounded wait may observe delayed matching evidence after a real earlier click/type, with matching executor `changed`/`settled` feedback. Pure waits, timeouts, aborts and stale/refused actions supply no proof.
- Evidence advances checkpoints in order. Different signals in one transition can satisfy several milestones; the same signal cannot be counted repeatedly to skip unrelated work. Code records `checkpoint_evidence` plus optional `additional_checkpoint_evidence` on the executed step, and the ordered evidence list in the private checkpoint state. Each record identifies checkpoint, step, URL, signal and matched public marker. Provider metadata cannot supply these fields or execution outcomes.

Completion stops in code when every checkpoint has evidence, avoiding a further model call or mutation. A false `done`, or abandonment without an observed website failure, gets one bounded correction toward the original task. Continued unsupported abandonment ends as `agent_lost`, preserving unresolved checkpoints. Missing expectations are not silently invented to make a run appear successful.

## Stops and factual memory

| Outcome | Meaning |
| --- | --- |
| `done` | Every declared checkpoint has matching observed evidence. |
| `gave_up` with step code `site_block` | The controller abandons after a new observed action error still present on the current page. |
| `stuck` | Repeated actual control attempts exhaust the existing loop guard; this does not itself prove a defect. |
| `agent_lost` | Unconfirmed completion, missing/unusable targets, observation exhaustion or controller abandonment without a new observed site error. |
| `safe_stop` | Visitor/action/confirmation restrictions or a prevented repeat send. This is not task completion. |
| `captcha` / `bot_wall` | An observed human/bot-protection boundary; never bypassed. |
| `budget` / `looping` | Existing step or navigation-loop limits, with partial checkpoint proof retained. |
| `stopped` | Existing owner Stop endpoint and extension stop handoff, with interrupted pending actions. |

Initial observed safety/bot/stale boundaries stop before a decision call. Safety refusals cannot establish website errors. Earlier genuine action failures remain available to the report.

Decision history has a 6,000-character cap: confirmed milestones, selected earlier failed/refused alternatives with omission counts, and eight recent factual actions/outcomes. Typed values and model narration are not resent. The current checklist still lists all unresolved work. Report synthesis receives sanitized milestone evidence separately from its trimmed narration context; the existing saved report JSON and legacy consumers remain compatible.

## Verification and remaining limits

`tests/test_completion.py` provides 49 offline scripted cases, including unrelated redirects/toasts, same-URL success, delayed wait, persona conflict, false progress/done, ambiguous goals, conflicting/negated/pre-existing messages, missing expectations, same-origin/route markers, observed site blocks, stale/safety/bot stops, budgets, forged provider metadata, confirmation reuse and compact factual history. The final focused controller/report/safety suite passed 256 tests. Related goal, persona, Jev, navigation, report and stop regressions remain in the existing suites. The real PostgreSQL restart drill declares guide navigation and confirms the recovered action's milestone without another model call.

Final combined full API verification passed **902 tests, with 19 existing PostgREST-dependent skips**, one existing Starlette/AnyIO warning and exit 0 in 526.71 seconds. This includes all disposable PostgreSQL/checkpoint/restart/idempotency suites. Whole API Ruff and diff checks passed. Broad sandbox verification also passed 862 tests before the final full run. An existing rate-limit concurrency fixture could legitimately cross its fixed UTC minute and admit another batch; it now uses one window ending within an hour of database setup, retaining exactly 20 admissions out of 50, total count, bounded retry and separate rollover/permission checks. Production SQL is unchanged. Local logs and disposable test data are ignored under `evals/results/restructure-session-4/`; final evidence is `api-full-final-c.log` and fresh `api-full-final-20261005c` basetemp. Tracing was disabled and `WEB_URL` was set only for the test process.

These tests do not measure live model quality or clear native installed-extension/deployed acceptance. Public text matching cannot establish backend persistence, email delivery, authorization, dataset correctness or causal certainty. A matching page can still contain misleading text; arbitrary-language planner/checkpoint fidelity and more precise functional expectations require owner review and later assertions. Closed shadows, iframes, snapshot truncation and changed application handlers retain the R-S2/R-S3 limits. Saved legacy reports are not regenerated. No provider activation, dependency, price, database migration or deployment is bundled into R-S4.
