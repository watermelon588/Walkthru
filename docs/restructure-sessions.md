# Walkthru restructure: session workflow

Date: 2026-10-04. Source of product direction: [root plan](../plan.md). This is an implementation workflow in the existing project, not a request to create separate chats, scheduled jobs or deployments.

**R-S1, R-S2 and R-S3 completed; next session: R-S4.** The completed scope is bounded reporting, current browser context, stale-target protection and bounded browser navigation below. The full mission engine, financial wallet and report-v2 redesign remain later work. Later sessions remain proposals until their work is started and verified.

**Scope extension (2026-10-04):** founder requests cache/cost efficiency, database pagination/index verification, practical keywords/backlinks and clearly separated report chapters. The [audited extension](seo-geo-report-expansion.md) is the detailed contract, including all twelve backlink tactics and the Distribb review. Preserve the original twenty IDs; add four pending slices, R-S5a/R-S7a/R-S14a/R-S17a. There are now **24 planned slices, three complete**, not twenty sessions with hidden extra work. Optional provider integrations and outreach are not activated by the plan.

## Working contract

- Read AGENTS.md, CURRENT_STATE.md and the relevant architecture/task sections at each session start. Preserve unrelated local changes and the old V0/roadmap task history.
- Each session produces one reviewable slice, focused tests and an explicit handoff. If it grows beyond a focused working session, split it and leave the unfinished acceptance criteria visible. Session counts are an ordering aid, not a duration or launch promise.
- Use current code and installed package signatures as authority. File lists below identify likely touch points, not a requirement to create every proposed module or abstraction.
- No paid model activation, provider purchase, paid request, changed price, recurring checkout, migration activation or external outreach is implied by this workflow. Use existing free defaults and offline/scripted models until an applicable action is authorized. New dependencies and expanded staging side effects follow AGENTS.md.
- Safety and honest coverage apply to every tier. A navigation test does not verify signup; a public crawl does not verify an authenticated dashboard; a sampled assertion does not certify the whole application.
- Golden signup setup initially uses a human-prepared test account or the existing verified-owner, single-confirmed-submit contract. Wider create/edit/signup testing needs a separately reviewed staging policy and test-data cleanup design. Never submit payments, solve CAPTCHAs or probe unauthorized roles.

## Session index and dependencies

| Session | Reviewable outcome | Depends on | Root-plan phase |
| --- | --- | --- | --- |
| R-S1 | Richer bounded synthesis evidence and truthful interrupted-run UX, inspectable evidence | Existing report contract | 1 |
| R-S2 | Current, region-aware browser observations | R-S1 | 2 |
| R-S3 | Controlled scrolling and bounded observation/wait | R-S2 | 2 |
| R-S4 | Task/persona separation and proven completion | R-S2, R-S3 | 2 |
| R-S5 | Versioned report contract and legacy rendering | R-S1, R-S4 | 1 |
| R-S5a | Distinct report chapters and export/prompt/MCP parity | R-S5 | 1, 6 |
| R-S6 | One owner-defined read-only assertion path | R-S4, R-S5 | 2 |
| R-S7 | Durable provider-attempt and usage records | Existing job/runtime contracts | 3 |
| R-S7a | Scoped cache reuse, freshness and measured savings | R-S7; R-S9 for expensive new dispatch | 3 |
| R-S8 | Atomic reservation and settlement | R-S7; reviewed schema | 3 |
| R-S9 | Shared expensive-work admission across entry points | R-S8 | 3 |
| R-S10 | Quote, cap and settlement UI | R-S5, R-S9 | 3 |
| R-S11 | Stronger-model adapters, disabled by default | R-S4, R-S7 | 2, 3 |
| R-S12 | Separately authorized, capped model comparison | R-S6, R-S9, R-S11 | 2, 4 |
| R-S13 | Targeted recheck proves the chosen fix | R-S6, R-S10 | 5 |
| R-S14 | Saved suites and honest coverage | R-S13 | 5 |
| R-S14a | Slim paged queries, authoritative counts and index evidence | Existing database contracts; read before R-S9, finish before R-S20 | 3, 5, 8 |
| R-S15 | Pilot evidence and pricing adoption proposal | R-S10, R-S12, R-S13 | 4, 5 |
| R-S16 | Read-only Search Console data connection | R-S9; connector authorization | 6 |
| R-S17 | Page/query opportunities and grounded growth plan | R-S16; or explicitly no-data advisory mode | 6 |
| R-S17a | Earned-link opportunity plans and citation-aware solutions | R-S5a, R-S17; R-S9 for fresh research | 6 |
| R-S18 | Resource/element-specific performance diagnosis | Existing metrics; R-S5 | 6 |
| R-S19 | Annotated evidence and optional actual-frame highlight | R-S5, R-S9, R-S13 | 7 |
| R-S20 | Installed-browser, durability and release validation | Adopted core sessions and existing V0 gates | 8 |

R-S7 can proceed after the report slice without waiting for all controller work. Adaptive follow-ups, shared contract edits and migrations stay sequential. Do not enable a paid customer route just because an adapter or pricing document exists.

The new slice suffixes preserve history, not strict calendar order. R-S14a query/count discovery can start early; authoritative bounded counts are a gate for R-S9 admission. R-S7a reuse needs only existing free/offline routes initially; any newly dispatched research must wait for R-S9. R-S5a is a priority before adding more growth output, so the report stays usable as depth increases.

## R-S1: improve the existing report without a broad rewrite

**Objective:** the writer receives the useful evidence already collected; an interrupted journey cannot be sold as a UX failure; existing finding evidence is fully inspectable. Keep the current persisted report shape so old reports continue to work.

**Work and files:** `apps/api/app/agent/report.py`, focused report/diagnostic tests under `apps/api/tests/`, `apps/web/src/components/ReportView.tsx` and `BrowserDiagnostics.tsx` if needed for issue inspection. Use the existing `Finding`, scan merge and report rendering patterns. Add a bounded structured scan packet with detail, existing fix/evidence/rule and affected-page context where available. Bound prompt size and explain omitted scope rather than silently dropping whole evidence classes. Do not load private raw values or screenshot pixels into this text-only writer path.

**Acceptance:**

- [x] The synthesis prompt preserves meaningful scan details/evidence beyond titles, with deterministic total/per-item bounds and truthful truncation/coverage context. Tests exercise oversized and missing legacy fields.
- [x] The zero-executed-action owner-stop example produces no invented Explore/UX failure; unconfirmed/interrupted actions and Walkthru safety/provider/controller limits cannot support alleged site defects by themselves. Confirmed site errors before a stop remain eligible. The synthesis prompt distinguishes the stated navigation scope from verified signup completion; general controller false-done and expected-outcome proof remain R-S4.
- [x] Full permitted finding evidence and captured diagnostic issues are readable on narrow and wide layouts; old report shapes remain renderable. No new schema version, model activation or price change is bundled into this slice.

**Verification:** scripted-model report/grounding tests, affected browser-diagnostic tests, API Ruff; web TypeScript/build/zero-warning lint and a browser check of long evidence, missing evidence and legacy report rendering. Include existing report/model prompt expectations affected by the new context. Offline tests must not regenerate saved reports with live models. A test that merely echoes the implementation is insufficient; use the saved false-report shape and a genuine error-before-stop counterexample.

**Dependency:** current report and scan contracts. **Handoff:** exact changed files, focused/full checks performed, browser evidence, remaining claim-grounding limits and next session. Root phase 1 is only partially delivered; mission schemas and assertions remain R-S5/R-S6. If application checks pass but an enabled browser surface is unavailable, record engineering completion with UI acceptance pending and keep the session's final checkbox open.

**Completion evidence (2026-10-04):** backend changes are `report.py`, `tests/test_report.py` and new `tests/test_report_trust.py`; web changes are `ReportView.tsx`, `BrowserDiagnostics.tsx` and `EvidenceTimeline.tsx`. The writer gets a sanitized 19,500-character JSON packet, representative findings across kinds, affected URLs and explicit omissions; latest observed failures survive history trimming. Unfinished journeys without observed failures bypass inference and use deterministic summaries/fixes. Stored reports were not regenerated and their schema is unchanged.

**Checks:** focused backend 61 passed (23 trust cases); clean full API **736 passed, 19 PostgREST-dependent skipped**, one upstream deprecation warning; all API Ruff passed. Web **19 tests passed**, production build/TypeScript and lint passed. Full API used process-only `WEB_URL=http://localhost:5173`, `LANGSMITH_TRACING=false`, `-p no:cacheprovider` and fresh ignored `evals/results/restructure-session-1/pytest-final-20261004c` as absolute `--basetemp`. Approved execution outside the sandbox was needed for disposable local PostgreSQL restricted-token initialization; the final full run exited 0.

**Browser evidence:** 16 actual-component isolated Edge layouts at 320/768/1024/1440 across interrupted, legacy, zero-action and scan cases; keyboard disclosure, all eight retained diagnostic issues and capture-limit notice, full printed evidence, no overflow/exceptions/external requests. Local artifacts: `C:/Users/Rohit Maity/.codex/visualizations/2026/10/03/01a102f7-edd6-75e1-9180-6a7f6644e648/report-ui-qa.json`, `report-ui-320.png`, `report-ui-1440.png`. Temporary fixtures were removed. This does not clear installed-extension or deployed V0 acceptance.

**Remaining limits at the R-S1 handoff:** R-S2 was next and is now complete below. General goal completion proof remains R-S4; richer/versioned report and semantic evidence grounding remain R-S5; actual model-attempt provenance remains R-S7. Current summary/fix caps and configured model label remain. No paid models, prices, schemas, dependencies, commit, push or deployment were activated.

## R-S2: make dense-page observations usable

**Objective:** resolve current visible controls in their actual region, row and overlay context without widening data capture indiscriminately.

**Files:** `apps/extension/lib/snapshot.ts`, `apps/api/app/agent/schema.py`, `persona.py`, and focused snapshot/observation tests. Inspect existing masking and element resolution before changing the shared contract.

**Acceptance:**

- [x] Duplicate labels carry sufficient current row/region context; obscured/irrelevant controls are distinguishable and observation limits are reported.
- [x] Target references are bound to the observation revision and stale targets cause a safe refresh/stop rather than a different click.
- [x] API and extension agree on bounded optional fields; older client observations remain supported or receive explicit version recovery.

**Verification:** modal-over-background, duplicate Edit buttons, rerender, hidden/offscreen and dense-control fixtures; extension tests/type/lint/build and affected API validation tests. **Dependency:** R-S1. **Handoff:** contract fields, fixture evidence, old-client handling and unresolved occlusion/geometry cases.

**Completion evidence (2026-10-04):** extension `snapshot.ts`, `execute.ts`, `redact.ts` and sidepanel `run.ts`; API `schema.py`, `persona.py`, `typesafe.py` and stale-outcome exclusion in `report.py`, with focused regression tests. Observation fields are optional `revision`, element `region`/`row`/`in_view`/`occluded`, and `elements_truncated`/`candidate_limit_reached`/`omitted_elements`/`context_truncated`. Region/row labels are capped at 160 characters each and 6,000 aggregate characters; the extension keeps 120 controls from at most 800 candidates, reporting cap omissions as a lower bound. Masking precedes upload/truncation, excludes editable and hidden-ancestor text and leaves raw semantic fingerprints only in document memory.

**Action and compatibility contract:** the API stamps `observation_revision` after provider metadata/safety replacement only for click/type; scroll/back/terminal steps receive null. Captured references, ancestors, full semantic context, resolved link/form destinations, form ownership, public field state and current hit availability are rechecked before dispatch and after scroll/focus/confirmation. A stale refusal stops as `agent_lost` without another decision call or causal attribution of unrelated errors/notices/evidence; earlier real failures remain eligible. API legacy observations and idempotent response replay remain supported. The current sidepanel refuses old-page/old-API target actions before dry-run and displays recovery instructions after durable stop. **Use the updated API, reload the rebuilt extension and reload the website tab before restarting.** Old installed extensions cannot retroactively enforce the new guards.

**Checks:** focused API **110 passed**; full API **762 passed, 19 existing PostgREST-dependent skipped**, one existing upstream Starlette/AnyIO warning; Ruff passed. Final full run exited 0 in 412.52 seconds using process-only `WEB_URL=http://localhost:5173`, `LANGSMITH_TRACING=false`, `-p no:cacheprovider` and absolute ignored `evals/results/restructure-session-2/api-full-verify-20261004a` basetemp. Approved execution outside the Windows sandbox was required for disposable local PostgreSQL setup. Extension **128 passed, 1 opt-in live-contract skipped**; TypeScript, zero-warning oxlint and WXT production build passed.

**Browser evidence:** **15/15 actual Edge geometry fixtures passed** through built `inject.js` on a secure local file origin with a Chrome runtime messaging shim and HTTP(S) blocked. Fixtures cover duplicates, ordinary/native modal overlays, offscreen/clipped controls, replacement/recycled rows, open shadows/hidden/inert hosts, post-scroll/post-focus changes, confirmation, disabled/state changes and expanded-text privacy/coverage. Headless foreground-focus emulation preserved a strict post-focus empty-value/refusal assertion. Dense 830-control observation measured **459 ms including settle and cached diagnostics**, with 680 omitted controls as a lower bound; this is a local sample, not a production timing guarantee. Ignored artifacts: `evals/results/restructure-session-2/geometry-qa.json`, `geometry-qa.py` and `geometry-fixtures.js`.

**Remaining limits at the R-S2 handoff:** R-S3 controlled nested scrolling and bounded wait/observation was next and is now complete below. Conservative center-hit testing may stop on partially covered controls; closed/unsupported shadows, iframes, transient application changes and handler-only state changes remain limits. These checks protect observable target semantics, not full goal-completion proof (R-S4). The shim does not establish installed-sidepanel or deployed durability acceptance (existing V0/R-S20 gates). No new dependency, paid model/API, price, schema/migration, live provider call, commit, push or deployment was activated. Unrelated local work and R-S1 history are preserved.

## R-S3: controlled scrolling and observation

**Objective:** the controller can inspect an inner pane, move in either direction and wait for a bounded state change.

**Files:** `apps/extension/lib/execute.ts`, snapshot/action schema and executor tests; `persona.py` only for the necessary prompt/action integration.

**Acceptance:**

- [x] Scroll specifies a currently observed container/direction and bounded distance; window scrolling retains a safe legacy fallback.
- [x] Wait/observe has a bounded deadline and returns the settled state or an explicit timeout, without repeating a dispatched mutation.
- [x] Nested-panel, infinite-list and no-scroll cases report actual progress and respect stop/budget signals.

**Completed 2026-10-05.** Observations advertise `navigation_version=3` and at most twelve scroll containers, including window ID zero, nearest-container IDs on controls, signed offsets, dimensions and available-direction/coverage flags. Pane labels share the existing 6,000-character additional context budget. Explicit observed IDs, modern window instructions and every wait are revision-bound; legacy null-container down-by-window scrolling remains supported. Requests move up/down/left/right, capped to 85% of the selected axis viewport and 1,000 pixels. Direct captured references reject stale, replaced, reparented, renamed, hidden, covered or no-longer-scrollable panes. Hidden/clip pane axes and unsupported RTL/reversed axes return `no_progress` without moving.

**Wait and feedback contract:** `settled`, `url_changed` and `text_changed` request a 100-5,000 ms deadline (default 1,000); settled requires 300 ms of stable bounded public state without an observed busy signal. Public-state reads cap scanned nodes at 2,000, body text at 6,000 characters and control states at 120; they are a bounded observation of the page. Pure polling preserves captured revisions and excludes private field values, Scout churn and diagnostics. It never repeats a dispatched click/type/send/back. Operation IDs, matching cancellation, bounded queued-cancellation tombstones and pre-dispatch/post-read/run-loop deadline checks prevent late continuation. Feedback records `moved`/`no_progress`, `settled`/`changed`/`timeout`/`aborted`, actual elapsed time (serialization cap 600,000 ms, distinct from the 5,000 ms request cap) and measured scroll offsets. The API accepts it only for the pending action/container and preserves exact keyed reply replay. Repeated navigation exhaustion stops as `agent_lost`; wait or unmoved scroll does not attribute unrelated errors as website defects. Movement/settlement alone grants no goal proof. Web replay labels wait, timeout, interruption and no movement explicitly.

**Verification:** focused API **144 passed**; final full API **811 passed, 19 existing PostgREST-dependent skipped**, one existing upstream Starlette/AnyIO warning, exit 0 in 392.60 seconds; API Ruff passed. Final isolated basetemp: `evals/results/restructure-session-3/api-full-verify-20261004c`, process-only localhost `WEB_URL`, tracing disabled and cacheprovider disabled. Extension **159 passed, 1 opt-in live-contract skipped**, TypeScript, zero-warning lint and final WXT build passed. Web **19 passed**, TypeScript/Vite build and lint passed, with existing bundle-size/dynamic-import warnings.

**Browser evidence:** final built `inject.js` passed **39/39 actual Edge fixtures**: **24 R-S3 checks plus 15 R-S2 geometry regressions**. Secure local file origin, Chrome runtime messaging shim, foreground-focus emulation and HTTP(S) blocked; no API, provider or account calls. Cases include four-direction nested movement, safe legacy window fallback, no-scroll/edges, one-dispatch lazy loading/infinite mutations, stale/covered/hidden panes, wait immediate/change/timeout/abort, operation isolation/concurrency, short/expired deadlines, private values/Scout churn and signed unsupported layouts. Ignored artifacts: `evals/results/restructure-session-3/scroll-wait-qa.json`, `scroll-wait-qa.py` and `scroll-wait-fixtures.js`. Offline Edge and disposable PostgreSQL verification required approved execution outside the Windows sandbox.

**Limits and handoff:** **R-S4 is next**, task/persona separation and proven completion. Bounded public state can miss changes beyond text/control/node caps; settlement is neither network-idle nor task success. Requested scroll distance is capped, while browser scroll snap can alter actual movement; measured offsets remain authoritative. Closed shadows, iframes, handler-only changes and unsupported reversed axes remain limits. The shim does not prove installed-sidepanel/deployed durability acceptance (existing V0/R-S20 gates). Update API, reload rebuilt extension and reload the website tab before a new run. No new dependency, paid model/API, pricing, schema/migration, live provider call, commit, push or deployment. **Dependency:** R-S2.

## R-S4: finish the task for the right reason

**Objective:** task competence and persona preference are separate, and completion requires evidence for the requested outcome.

**Files:** `apps/api/app/agent/persona.py`, `goal.py`, `schema.py`, `tests/test_persona.py`, `test_goal.py` and owned eval fixtures where needed.

**Acceptance:**

- [ ] Owner objective/checkpoints remain authoritative; persona impatience/preferences cannot silently replace them or invent business rules.
- [ ] Navigation, a generic toast or a scroll alone cannot confirm an unrelated goal; same-URL SPA success can confirm a matching declared milestone.
- [ ] Site block, controller loss, user stop, safety stop and budget stop remain distinct, and compact factual history preserves unresolved work.

**Verification:** clear and ambiguous goals, unrelated notices, same-URL transitions, false done, legitimate site block and persona conflict fixtures. Use scripted models first. **Dependency:** R-S2/R-S3. **Handoff:** completion contract, tested cases, unresolved ambiguity and model-ready context baseline.

**Checkpoint A:** R-S1 through R-S4 demonstrate truthful reports and current-state actions on owned fixtures. This does not select a paid model or clear native installed-extension acceptance.

## R-S5: version the richer report

**Objective:** introduce report v2 with evidence references and detailed issue records while continuing to display existing reports.

**Files:** report/schema, `apps/web/src/lib/runs.ts`, `ReportView.tsx` and version/compatibility tests. Split UI detail into a follow-up slice if contract and rendering exceed a session. New relational records are not required merely to version report JSON.

**Acceptance:**

- [ ] New report records distinguish observed facts, expected/actual result, hypotheses, recommendations, reproduction and acceptance test; missing expectations are unknown rather than invented.
- [ ] Coverage/outcome/limitations come first; substantive claims reference permitted evidence. No minimum defect count or verbosity requirement.
- [ ] Legacy JSON, export/fix-prompt/compare consumers and private/public access keep their intended behavior; unknown versions fail clearly.

**Verification:** versioned serialization, legacy fixtures, false/unsupported evidence refs, clean mission and export compatibility; UI check for expanded detail and scope. **Dependency:** R-S1/R-S4. **Handoff:** version contract and consumer migration matrix; schema activation only if separately required and authorized.

## R-S5a: make the dossier readable by section

**Objective:** distinguish UX, accessibility, performance, SEO, keywords/content, authority/backlinks, GEO, AI citations and security/email, with evidence/coverage separately available. Follow the [chapter contract](seo-geo-report-expansion.md#report-chapters-one-navigable-dossier).

**Files/patterns:** R-S5 report version/section mapping; existing `ReportView.tsx`, `GeoReadiness.tsx`, `EvidenceTimeline.tsx`, exports and `runs.ts`; deterministic `agent/fix_prompt.py` batches and MCP `get_report`/`get_finding`/`get_fix_prompt`. Inspect components before editing; follow DESIGN.md. Preserve old kind enums unless the versioned contract adopts section metadata; opportunities are not automatically defects.

**Acceptance:**

- [ ] Coverage and three next actions lead; contents navigation, prominent numbered headings and plain-language summaries work on narrow screens and keyboard. Relevant empty/unavailable sections retain honest status.
- [ ] Issues have one primary section, stable IDs and cross-links; facts, hypotheses and marketing opportunities remain distinguishable. AI citation evidence retains its independent sampling date/source.
- [ ] Web, print/export, generated section prompts and bounded MCP retrieval agree on IDs, recommendations, evidence and limitations. Existing tools keep compatibility; section/cursor arguments are documented new APIs, not assumed existing ones.
- [ ] Full details are inspectable, not forced into the first screen; private/shared/legacy access and redaction remain intact.

**Verification:** clean/interrupted/legacy/long multi-section fixtures, keyboard and mobile/desktop review, printed evidence and prompt/MCP contract parity. No live inference needed. **Dependency:** R-S5. **Handoff:** inspected dossier, consumer compatibility matrix and pending independent citation embedding/connector inputs.

## R-S6: one meaningful assertion

**Objective:** verify one declared read-only dashboard/filter outcome against owner-supplied synthetic expectations.

**Files:** goal/persona/report integration, a small assertion module only if necessary, and owned fixture/eval tests. Reuse collected outcomes; do not build a general testing DSL.

**Acceptance:**

- [ ] A declared record/filter/count assertion yields passed, failed, blocked or inconclusive with evidence and dataset/time/tolerance context.
- [ ] Missing, stale or inaccessible expected data is inconclusive; visible UI assertions do not claim backend authorization or persistence.
- [ ] Human-prepared auth and current side-effect boundaries are preserved; assertion failure does not imply that the controller failed to reach the state.

**Verification:** matching/mismatching/stale datasets and genuine blocked flow; no external live-data probe or broad backend credentials. **Dependency:** R-S4/R-S5. **Handoff:** the golden mission and exact assertion/fixture needed for comparison.

## R-S7: record model attempts and cost inputs

**Objective:** retain provider usage per attempt and stage instead of only a combined token count.

**Files:** `apps/api/app/agent/runtime.py`, relevant job/provider adapters, provider tests and a proposed numbered migration only if durable attempt records require it.

**Acceptance:**

- [ ] Input/output/cache/reasoning/image/tool charges are separately represented where supplied; missing usage stays unknown, not zero.
- [ ] Durable operation IDs distinguish attempts/retries/stages and keep credentials, private payloads and unrestricted model text out of cost logs.
- [ ] Price versions and currency/micro-unit arithmetic produce auditable estimates without charging customers or changing routing.

**Verification:** fake provider responses with cached/thinking/missing usage, timeout and repeated acknowledgements; migration/RLS checks if storage changes are approved. **Dependency:** existing runtime/job contracts. **Handoff:** usage contract, price source date, unknown-usage policy and measured versus assumed cost fields.

## R-S7a: reuse safely and prove the savings

**Objective:** reduce repeated work without presenting old observations as a new test. Audit the existing ten-minute anonymous public cache before building another cache service.

**Files/patterns:** `db.recent_public_scan`, `main.instant_scan`, `jobs.py` stored-report guard, `tests/test_scan_cache.py`, request idempotency tests and R-S7 attempt records. Consult current primary caching docs for the exact provider/model/installed SDK; client/graph `lru_cache` is not inference caching.

**Acceptance:**

- [ ] Distinguish saved-report reads, exact request replay, eligible result reuse, deterministic artifact reuse and provider prefix hits. Keys include permitted scope/privacy, evidence hash and scanner/prompt/report/model versions; timestamps and cached/fresh labels are visible.
- [ ] Expiry, version change, revocation/deletion and simultaneous misses cannot leak private data or double-dispatch equivalent eligible work. No raw credentials or typed values in keys. Fresh fix checks bypass stale evidence; changed DOM/account/state cannot reuse a browser action.
- [ ] Supported provider cache usage is recorded with input/output/reasoning/write/storage fields as applicable; unknown values stay unknown and fallback costs count. Implicit provider hits may occur without explicit configuration; absent code does not prove zero hits.
- [ ] Owned/offline measurements report hit rate, p50/p95 and avoided work. Paid economics remain estimates until separately authorized observations; no guaranteed savings percentage.

**Verification:** cached versus fresh public scan, private/public separation, revocation, concurrent misses, version/TTL changes, worker loss and mocked provider hit/miss/unknown usage. **Dependency:** R-S7; R-S9 for expensive new dispatch. **Handoff:** eligibility matrix, measured savings and provider support gaps.

## R-S8: reserve and settle money atomically

**Objective:** prevent concurrent overspend and preserve uncertain liability through crashes.

**Files:** existing billing/database/job patterns, narrowly scoped reservation/ledger records and SQL concurrency tests. Review additive migrations before activation; never edit applied SQL.

**Acceptance:**

- [ ] Concurrent admission atomically reserves the accepted maximum from available service balance/global funded budget and fails closed if authoritative storage is unavailable.
- [ ] Settlement/release/replay is idempotent; crashed/uncertain attempts cannot be freed merely because a worker lease expired.
- [ ] Reporting capacity is reserved, refunds/grants have explicit ownership, and money uses integer units plus versioned prices.

**Verification:** real isolated SQL races, insufficient balance, replay, crash after provider response and out-of-order reconciliation; no live checkout needed. **Dependency:** R-S7 and reviewed storage contract. **Handoff:** ledger authority, state machine, migration status and pending failure cases.

## R-S9: admission applies everywhere

**Objective:** web, extension, API, MCP, Scout, watch and citation work share the same spend authority.

**Files:** existing start/job routes, `app/mcp_server.py`, `scout.py`, `watch.py`, `citations.py`, `plans.py` and admission tests. Split independent entry-point wiring into sub-sessions if necessary, retaining one complete inventory.

**Acceptance:**

- [ ] Every model/data/media entry point authorizes owner/workspace/key scope and reserves before dispatch; no alternate free pool or client-selected wallet/price.
- [ ] Admission counts and balances are authoritative under concurrency and cannot undercount through API row limits; use R-S14a query/count findings before activation.
- [ ] Scheduled work has an accepted cap; quotas/concurrency and stopped-job policies compose with financial reservations.
- [ ] Existing request replay cannot debit or execute twice; sending a stored template/report does not unnecessarily regenerate it.

**Verification:** explicit entry-point coverage matrix, unauthorized/cross-workspace keys, queued/watch/citation races and insufficient funds. **Dependency:** R-S8. **Handoff:** inventory of covered operations and disabled/uncovered routes; customer paid adoption stays off until the inventory is complete.

## R-S10: customers see scope and the hard cap

**Objective:** show an understandable estimate/maximum and settled usage with a deliverable partial report.

**Files:** relevant dashboard/extension start controls, API quote DTO/client, report usage display and focused tests. Use design tokens and accessible loading/error/empty states.

**Acceptance:**

- [ ] Quote pins scope/price version/maximum, and acceptance binds the run to that quote rather than a stale client estimate.
- [ ] Cap/stop/resume displays remaining scope and partial evidence; no silent overage, automatic top-up or unqualified cheaper-model replacement.
- [ ] API/MCP receives the same quote semantics and clear connected-browser prerequisites; settlement history explains released unused reserve.

**Verification:** stale quote, declined acceptance, cap/stop, timeout uncertainty and narrow-screen flows. **Dependency:** R-S5/R-S9. **Handoff:** quote UX/API contract and decisions still pending on customer terms.

**Checkpoint B:** the wallet/reservation/entry-point/quote path passes storage races and recovery checks with fake providers. No actual paid model or price is activated by passing it.

## R-S11: prepare qualified adapters, keep them disabled

**Objective:** implement current documented Sonnet/GLM candidate requests and truthful stage provenance behind explicit opt-in.

**Files:** `runtime.py`, provider schemas/tests and provider configuration docs. Read the exact current primary APIs and installed SDK signatures; use the [live decision plan](live-decision-quality-plan.md).

**Acceptance:**

- [ ] Candidate structured output/tool/effort/thinking/image behavior matches actual provider support; no model-name-only swap of incompatible Haiku requests.
- [ ] Mocked usage/parse/fallback/error cases satisfy R-S7 and the admission hooks; credentials remain private and absent-default candidates cannot run.
- [ ] Free defaults remain unchanged; controller and report routing/provenance are separate. No hidden paid fallback.

**Verification:** offline mocked transport/parse/caching/circuit tests and package compatibility; do not use live provider requests as an adapter unit test. **Dependency:** R-S4/R-S7. **Handoff:** disabled configuration contract, supported modality differences and exact authorization/budget required by R-S12.

## R-S12: measure model quality under a cap

**Objective:** compare Sonnet, full GLM and the existing baseline on identical eligible owned cases; add Grok only if the evidence warrants it.

**Files:** `evals/` harness, held-out fixtures, result summarizer and evaluation documentation. No runtime default changes merely because the harness exists.

**Acceptance:**

- [ ] Explicit founder/provider budget authorization precedes paid execution; the dollar/task/call cap, price date and dataset are recorded. Ordinary paid customer routes remain gated.
- [ ] Correct completion, false done, wrong actions, recovery, safe stops, persona fidelity, p50/p95 latency and loaded cost per correctly completed task include failures/retries and sample sizes.
- [ ] Text-only comparison is separated from screenshot-assisted comparison; a broken-site block is not falsely scored as a controller failure. No zero-hallucination or universal winner claim.

**Verification:** harness dry run with scripted models, then only the authorized bounded live comparison; independently inspect a sample of evidence. **Dependency:** R-S6/R-S9/R-S11. **Handoff:** measured results, remaining budget, adoption recommendation and unresolved quality/economic gate. Without authorization, complete the dry-run harness and preserve the live gate as pending.

## R-S13: verify a selected fix

**Objective:** rerun the disputed assertion and show what was fixed, still fails or was not retested.

**Files:** existing compare/fix-prompt/report paths, assertion identity and targeted-run UI/tests. Reuse current fingerprints with explicit assertion identity where needed.

**Acceptance:**

- [ ] Targeted recheck preserves declared environment/data/viewport assumptions and evidence; materially changed conditions invalidate a direct comparison.
- [ ] Missing coverage never means fixed; clean/failed assertions are distinct from absent findings or renamed UX titles.
- [ ] Existing compare/fix prompts remain compatible and recheck cost uses the shared quote/reservation path.

**Verification:** same-condition fix, partial coverage, changed fixture and duplicate-finding cases; one owner-local/manual fix and rerun if authorized. **Dependency:** R-S6/R-S10. **Handoff:** a complete example a developer can independently reproduce, repair and recheck.

## R-S14: saved suites and coverage

**Objective:** combine bounded scenarios without promising exhaustive application testing.

**Files:** mission/run orchestration and saved template storage/UI, jobs and suite tests. Any new schema follows reviewed migrations/RLS.

**Acceptance:**

- [ ] Scenario/assertion scope, per-phase budgets and auth handoffs survive stop/resume and worker recovery.
- [ ] Coverage lists tested, blocked and not-tested states; discovered routes are separate from promised assertions.
- [ ] Schedule/API cannot invent an authenticated browser session; owner-local work waits for connection and public watch remains server scanning.

**Verification:** multi-scenario budget stop/resume, account/session change, absent browser and partial coverage. **Dependency:** R-S13. **Handoff:** bounded suite example, capacity/latency evidence and unattended-runner exclusions.

## R-S14a: database reads stay bounded as history grows

**Objective:** inspect actual filters/order/RLS/indexes, page long histories and avoid loading report/evidence JSON to draw list rows. This slice can start early and does not depend on saved suites shipping.

**Files/patterns:** `apps/web/src/lib/runs.ts:listRuns`, `app/db.py:runs_for_user/test_runs_since/free_runs_today/recent_public_scan`, MCP `list_runs`, existing team ID cursors and citation batched reads; migrations and query tests. Follow [Supabase query optimization](https://supabase.com/docs/guides/database/query-optimization). Repository indexes do not prove deployed schema.

**Acceptance:**

- [ ] Query/index inventory includes owner lists, public cache lookup, jobs, citation scheduling/history, teams and admission counts. Inspect deployed plans only with authorized access; add indexes when measured patterns justify overhead.
- [ ] Lists use slim projections, bounded continuation and deterministic tie handling; owner history has a `(created_at, id)` cursor or documented equivalent. MCP filters/limits in the database. Detail loads and bounded exports remain separate.
- [ ] Navigation works beyond fifty reports with equal timestamps/concurrent inserts, no cross-owner records; invalid cursors fail clearly. Preserve existing keyset chat/event behavior; scope client plan-display caches to account/session and reset on sign-out.
- [ ] Admission uses server-side exact/atomic counts where needed, never length of a row-capped result. Financial reservations remain R-S8 authority; an index is not a concurrency fix.
- [ ] Justified schema changes use new migrations, reviewed activation and RLS/rollback checks. Never edit applied SQL. Reconcile stale documentation that currently claims exact counts are already implemented.

**Verification:** isolated large histories, response bytes and p50/p95, read-only `EXPLAIN (ANALYZE, BUFFERS)` on eligible test queries, count-over-row-cap cases, tied cursors and privacy. Do not run mutating admission RPCs to collect plans. **Dependency:** existing database contracts; count findings gate R-S9, final performance proof gates R-S20. **Handoff:** query/index matrix, measured bottlenecks, migration status and uninspected live plans.

## R-S15: pilots and pricing decision, not automatic activation

**Objective:** validate the packet's paid value and propose an adoptable subscription-plus-prepaid catalog from measured costs.

**Files:** `founder/` outputs, `plan.md`, proposed updates to SPEC/payment/catalog docs only after the applicable decision. No live price or entitlement modification as routine cleanup.

**Acceptance:**

- [ ] Independently reproducible finding, time saved, repairs/retests, disputes, actual provider cost and human review labor are recorded; stated pilot thresholds remain hypotheses.
- [ ] Proposed PAYG/Pro/Plus prices/grants/cancellation/refund/failure policy preserve verified historical purchases and distinguish service balance from provider tokens or API credentials.
- [ ] Founder reviews the concrete adoption result before prices, subscriptions, checkout, external outreach or paid customer execution are activated; no demand is inferred from compliments.

**Verification:** recompute loaded margins/fees from actual statements, simulate included/purchased grant expiry and cancellation, review migration/customer terms. **Dependency:** R-S10/R-S12/R-S13; research preparation can occur earlier. **Handoff:** recorded adopt/revise/defer decision and exact actions separately authorized. Existing catalog stays in force until adoption.

**Checkpoint C:** one trustworthy scoped dossier, fix/recheck path and cost model are demonstrated. Broader growth/media are optional workstreams, not prerequisites for validating this narrow pilot. No outreach or sale is performed just to clear a checklist.

## R-S16: read-only search data

**Objective:** connect owner-authorized Search Console query/page data with explicit windows and coverage.

**Files:** small connector/auth path, scoped storage/UI and tests; existing SEO crawl remains the technical base. Use the primary Search Analytics docs linked in the root plan.

**Acceptance:**

- [ ] Read-only ownership/scopes, secure token handling, revocation and account separation are tested; real OAuth interaction requires authorization.
- [ ] Returned query/page metrics retain dates, filters, dimensions and incomplete/top-row sampling limits.
- [ ] No data/expired access is usable and honest; model/data work still uses admission.

**Verification:** mocked OAuth/API/row-limit fixtures and only authorized read-only live acceptance. **Dependency:** R-S9 and connector authorization. **Handoff:** source/retention contract and available versus missing customer metrics.

## R-S17: actionable SEO/GEO opportunities

**Objective:** produce a prioritized page/query/content/internal-link plan grounded in site facts and available search evidence.

**Files:** current SEO/GEO/citation/fix modules, growth report UI and tests. Add only the smallest opportunity transform needed.

**Acceptance:**

- [ ] Suggested topic/keyword intent maps to actual pages and business brief; measured query demand is distinguished from hypotheses and no invented volume/difficulty appears.
- [ ] Keyword direction includes target page, primary/supporting intent, quoted copy, proposed title/description/outline, named internal links and success measurement. Label sparse prelaunch, owner-query and approved external-research modes.
- [ ] CTR/content trends, near-page-one opportunities, brand/nonbrand and cannibalization use consistent sourced windows and explicit incompleteness. Search Console is not arbitrary competitor keyword/backlink data.
- [ ] Rewrites quote the source text; briefs do not invent product claims or citations. Technical accessibility, content advice and sampled answer visibility remain separate.
- [ ] Next action and retest/measurement window are explicit; no rank/traffic/citation guarantee or paid keyword integration without a separate budget decision.
- [ ] Recalibrate strict 60/160-character and exactly-one-H1 heuristics against current primary guidance; advisory presentation checks are not proven ranking failures. Update conflicting fix recipes as well as findings.
- [ ] Deterministic scanning/aggregation comes first. Jev may be benchmarked as a narrow confidence-gated fallback for ambiguous bounded intent/opportunity classification, not a crawler or universal abstraction. Measure fallback rate, correctness, full cost and end-to-end p50/p95 against the simpler route before adoption.

**Verification:** search-data and no-data fixture modes, contradictory business claims, partial query windows, dated answer provenance. **Dependency:** R-S16 for measured mode; advisory mode explicitly states missing demand data. **Handoff:** example opportunity map and optional research inputs still unbuilt.

## R-S17a: useful authority and citation recommendations

**Objective:** cover twelve requested backlink tactics as a contextual catalog, recommending only supported opportunities. Produce reader-focused solutions without building a publishing/outreach agent.

**Files/patterns:** R-S17 opportunities, existing safe fetch/evidence/redaction, citation provenance, R-S5a chapters and deterministic fix-prompt/MCP consumers. Read [the tactic matrix and Distribb review](seo-geo-report-expansion.md). No third-party code copy until a permissive license is confirmed; no paid platform integration by default.

**Acceptance:**

- [ ] Lost links, mentions, free tools, lists, competitor editorial sources, broken links, outdated guides, statistics, reporter requests, infographics, article/video and exchange risks have supported/prerequisite-missing/not-applicable states. No fabricated publisher/history data.
- [ ] Each opportunity identifies a sourced target when available, source/date, asset/page, reader benefit, factual prerequisites, effort and follow-up measurement. New-site asset briefs without external demand remain advisory.
- [ ] Exchanges/triangular networks and automated ranking-link placement are not promoted as shortcuts. Legitimate paid placements are qualified; drafts/media briefs require factual/rights review and separately scoped execution.
- [ ] GEO readiness, backlinks and verified AI citations remain distinct. Mentions/memory answers do not become citations; failures/unavailable samples do not become zero visibility. Preserve provider/prompt/date/source and sample size.
- [ ] The same opportunities reach web/print/section prompts/MCP with access checks, bounds and admission. No connection or prompt automatically emails, publishes, registers profiles or places links.

**Verification:** history/no-history exports, real versus invented mentions, unsupported sources, nonapplicable tactics, exchange-policy fixtures and cited/mentioned/unmeasured examples; prompt/MCP parity. Sources stay within owner-verification policy or authorized supplied/licensed data. **Dependency:** R-S5a/R-S17; R-S9 for new research. **Handoff:** actionable authority/citation example, source/rights gaps and deferred publishing/outreach work.

## R-S18: performance diagnosis with attribution

**Objective:** enrich existing real measurements with the actual resource/element and test conditions instead of generic compression advice.

**Files:** `scans/performance.py`, browser diagnostics/report/UI and affected performance tests.

**Acceptance:**

- [ ] Relevant PSI/Lighthouse audits/attribution are retained with bounds, URL, device, timing and measurement source; unavailable metrics remain unavailable.
- [ ] Single-browser observations, lab runs and population field p75 values are never conflated; missing field data cannot be presented as healthy.
- [ ] Proposed fixes reference the measured opportunity/resource; estimated opportunity savings are labelled estimates, not real conversion gains.

**Verification:** lab-only/field/unavailable/partial audit fixtures and current documented response signatures. **Dependency:** R-S5 and existing metrics. **Handoff:** attribution contract and any separate CrUX/connectivity prerequisite.

## R-S19: visual evidence that remains truthful

**Objective:** annotate real issue locations; optionally export a bounded actual-frame highlight after evidence is trusted.

**Files:** extension evidence metadata, `EvidenceTimeline`, report media export and private-storage/retention tests. Split clip rendering into a later sub-session if it requires a new dependency or extra permissions.

**Acceptance:**

- [ ] Highlight regions refer to the actual frame/viewport and redaction remains intact; suggested treatments are labelled, while verified before/after requires a matched rerun.
- [ ] Clips use actual frames/events and timestamps; eight screenshots are not sold as continuous recording.
- [ ] Shared/private access, deletion, output size, retention/egress charge and accessible playback/reduced motion are tested. No hidden tab capture or personal inbox access.

**Verification:** masking, expired evidence, narrow viewport, share/RLS and export tests plus real artifact inspection. **Dependency:** R-S5/R-S9/R-S13; licence/permission review for new media capability. **Handoff:** inspected sample, cost/storage limits and continuous-recording exclusions.

## R-S20: prove the adopted release path

**Objective:** clear the release gates for the scope actually adopted, not every optional proposal.

**Files:** relevant CI/deploy/readiness/checkpoint docs and existing V0-S2/S5/S6/S7 acceptance work; no new deployment target is implied.

**Acceptance:**

- [ ] Installed Chrome extension proves session handoff, permissions, masking, actions/stop/resume and legacy recovery; mocked Chrome messaging alone is insufficient.
- [ ] Durable API/worker restart, financial settlement/reconciliation, auth/RLS/retention and rollback pass with actual supported packages and required schema versions.
- [ ] Declared quality/latency/price terms match measured scope and sample sizes; full relevant checks and known skips are reported, with unsupported completion/unsafe cases blocking release.

**Verification:** API pytest/Ruff, extension tests/type/lint/build, web tests/build/lint, SQL/migration/concurrency checks and installed-browser/deployed acceptance on owned fixtures. Broaden checks when a new failure or change justifies it. Paid services/deployment require the applicable authorization; preserve completed local work if an external gate remains pending.

**Dependency:** adopted core sessions, pilot/model decision and existing V0 release gates. **Handoff:** exact versions/configuration, tests/evidence, unresolved skips, rollback procedure and founder adoption/launch decision. Passing a finite suite is not a zero-hallucination promise.

## End-of-session handoff template

Record this in CURRENT_STATE.md only after verification, and update the corresponding task entry:

```text
Session ID and scope:
Delivered behavior and changed files:
Verification commands/results and inspected artifacts:
Untested live/native/paid/schema gates:
Known limitations and pending decisions:
Authorization used; purchases/routing/prices changed, if any:
Next dependent session and prerequisites:
```

Do not mark a session complete because its code was written. A partially verified slice stays partial. Never convert the master plan's historical estimates or proposals into shipped features.
