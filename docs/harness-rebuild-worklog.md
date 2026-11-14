# Harness rebuild: implementation record

Started 2026-11-13; verification continued 2026-11-14. This record covers H1-H3 of [the dedicated plan](harness-rebuild-plan.md). It is separate from the original six-run audit and does not claim improved live-site completion rates.

## Delivered control loop

`START -> prepare -> decide -> guard -> act -> assess -> check -> journal`

Guard sends recoverable target refusals through `recover -> act`, and terminal proposals directly to `check`. Journal returns running sessions to `prepare`; terminal sessions end. Only `decide` calls a decision provider. Its existing one-correction limit is retained. Interrupt re-entry does not repeat that call.

Editable diagram: [Excalidraw](walkthru-harness-rebuild.excalidraw), [SVG](walkthru-harness-rebuild.svg), [PNG](walkthru-harness-rebuild.png).

## Exactly what crosses each boundary

| Node | Reads from prior state | Writes | Deterministic decision |
|---|---|---|---|
| prepare | Current observation, plan, confirmed count, earlier assessment and recovery events | harness_context; preparation event | Identify missing route/outcome predicate; list current available control IDs |
| decide | Original owner objective, persona, checklist, bounded factual action history, observation, harness_context | proposal and token count | Existing terminal correction remains bounded; model progress cannot advance state |
| guard | Proposal, current elements and revision, verification/safety scope, previous sends, recovery history | Guarded step, refusal code, recovery target, guard event; clears proposal | Enforce safety and freshness; allowlist provider metadata; refuse forged outcomes |
| recover | Refused target and current revision | A settled wait replacing the rejected action; recovery event; clears recovery target | One refresh per target and two per run, only for navigation version 3 with a revision |
| act | Last guarded step | Temporary resume_payload after checkpoint resume | Interrupt exposes one action to the executor; no model call |
| assess | Before observation, resumed observation, action, earlier real actions, ordered predicates, optional owner assertion | After observation, action outcomes/evidence, assertion result, reason events; clears resume_payload | Reject stale-target outcomes; match fresh same-origin evidence; prevent duplicate-signal completion |
| check | Updated outcomes, proofs, safety notes, step budget, action history | Confirmed count and evidence; status | Completion, safety, repetition and loop checks determine whether execution can continue |
| journal | Updated status, action, confirmed count | Final event for this decision cycle | Running loops to prepare; terminal ends |

Both provider interfaces receive this context: regular prompt messages and the typed Jev request. Recent history now includes the observed target label and result URL, not just an element number. The provider still proposes an action; the harness owns permission and proof.

## Decisions and trade-offs

1. Keep the existing completion matcher; add explicit rejection reasons. This exposes missing expectations without quietly turning an uncertain task into a successful easier task. A malformed plan can still fail; autonomous plan grounding is H4.
2. Refresh an unavailable target before abandoning it. This can recover a transient overlay or layout change. It cannot reveal a permanently off-screen control; directional reveal needs observed geometry and remains planned. Refresh never replays the refused click, type or send, and cannot itself confirm completion.
3. Canonicalize repetition by action semantics. A click cannot evade detection by changing scroll container, direction or text fields. Scroll position and direction remain relevant for actual scrolling. The existing movement and action-budget checks remain.
4. Store explanations as typed, code-owned events. The log contains sequence, browser step, node, reason, action, target ID, checkpoint, progress and optional status. It excludes raw prompts, form values and provider reasoning. Events are capped at 256; recovery is disabled near that cap so truncation cannot reset its budget.
5. Preserve report context through normal completion and owner-stop paths. The queue retains worklog, plan and owner assertion fields. The stopped-run retry path also retrieves available checkpoint context. Old or unavailable checkpoints still produce a partial report.
6. Add an optional report JSON field, with no relational migration. Legacy reports without it continue to validate. The shared private/public report view renders the log using code-owned explanations and ordinary printable content. It is an execution explanation, not another website finding.
7. Keep existing provider routing, dependencies, safety scope and account entitlements. Extra deterministic nodes add checkpoint writes and state-processing overhead; no additional model stage was introduced. Recovery consumes the existing browser-action budget. Measure latency and cost before rollout.

## Reproducible demonstration

Run `apps/api/.venv/Scripts/python evals/harness_demo.py` from the repository root. [The JSON artifact](harness-rebuild-demo.json) records actual graph transitions with synthetic observations and a scripted decision provider. It makes no provider or live-site calls and creates no account run.

| Scenario | Result | What it demonstrates |
|---|---|---|
| Temporarily unavailable target | wait, click, done; two scripted decision calls | Safe refresh followed by a newly guarded action and matching public outcome |
| Missing functional finish condition | Three clicks, then stuck; no confirmed checkpoint | New page text cannot fill an undeclared expectation or manufacture success |

These are harness regression examples, not live screenshots or proof of general reliability. The original audit remains the live evidence baseline.

## Validation and remaining gates

Focused tests cover graph resume, false completion, safety, bounded recovery, repeated actions, report-job serialization, owner stop/retry, report compatibility and metadata spoofing. Web tests cover malformed/legacy logs, safe explanations and bounded rendering inputs. Final command results are recorded in the dedicated plan and CURRENT_STATE.md.

H4 remains the next implementation phase: capture trustworthy destinations and section/document identity, distinguish navigation from functional outcomes, validate the initial task contract, and permit bounded revisions without weakening the original objective. H5 then measures capability on independently specified and held-out tasks. H6 addresses scanner/summary claim scope, cost accounting and deployed operation.

Do not treat this graph expansion as a measured cure for hallucination. Real-site trials, production queue/checkpoint behavior, installed-extension acceptance, and report browser/print visual inspection remain rollout gates. Existing in-flight checkpoints need a compatibility trial or draining before graph deployment.

## H4a: observed destinations (2026-11-14)

- The original observation exposed labels but no link destinations. Added optional `Element.destination`, captured from same-site HTTP(S) anchors. Credentials, query-bearing links, unsafe fragments, encoded/unsupported paths and existing privacy-mask matches are omitted. Cross-origin base URLs cannot disguise a destination. Destinations share the existing 6,000-character context budget and are dropped whole rather than truncated into a different route.
- Both normal prompt rendering and typed provider state now receive destinations. The planner is told to use observed routes and distinguish fragments from pages.
- New planner-generated navigation checkpoints receive code-owned `requires_observed_destination` provenance. Unless the route was explicitly specified by the owner, prepare/assess require an exact observed destination before accepting route proof. A future observation can satisfy that requirement without rewriting the objective. A matching URL by itself cannot rehabilitate a guessed route.
- New model-generated fragment predicates report `section_evidence_required`; there is no section-completion claim. Functional outcomes still need their declared success evidence. Legacy checkpoints retain prior semantics for compatibility.
- This deliberately favors honest uncertainty over guessed completion. Query-driven apps, handler-only navigation, and section visibility need further observation contracts. No automatic route replacement, goal weakening, model upgrade or live-site reliability claim is included.
- Verification: 139 focused API regressions and changed-file Ruff passed. Extension: 188 passed, one existing opt-in skip; TypeScript, lint and build passed. Web: production build, lint and three worklog tests passed. No installed-browser or live-site improvement measurement was performed for H4a.
