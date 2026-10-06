# Walkthru Task List

Definition of done: see ROADMAP.md. Immediate work is the report-quality restructure workflow below (founder direction, 2026-10-04); existing V0 prelaunch sessions remain release prerequisites and preserve their completion history. The v1.2 flagship plan remains the broader roadmap, in phase order (ROADMAP.md "Phases" and "Session plan"). The v1.1 and v1 history below stays for reference. Sizes: S = 1-2 files, M = 3-5 files, L = 6+ files.

Every task follows ROADMAP.md "Build rules": deterministic first, free tier only, reuse open source after a licence check (table in docs/decisions.md, 2026-09-25 "Premium depth"), name each new dependency, never attack a site. "Reuse" lines name the repo and licence to port from. Ported rules keep their notice in `apps/api/THIRD_PARTY.md` (created by the first task that ports code).

## Report-quality restructure workflow (2026-10-04)

Product direction: [root plan](../plan.md). Detailed objectives, likely files, acceptance tests, dependencies and handoffs: [session workflow](../docs/restructure-sessions.md). Sessions are slices of work in this project, not new chats. Later paid-provider evaluation, revised prices, recurring billing, wider staging side effects and deployment remain separately gated; no activation is implied by this checklist.

Founder scope extension: [caching/database/SEO/GEO/report audit and contract](../docs/seo-geo-report-expansion.md). Preserve twenty original IDs plus four suffix slices: **24 planned slices, thirteen complete**. R-S4, R-S5, R-S5a, R-S6, R-S7, R-S7a, R-S8, R-S9, R-S14a and R-S18 are complete; R-S10 is next. Database count findings inform expensive-work admission.

- [x] **R-S1:** bounded structured scanner evidence, safe interrupted/zero-action report grounding and inspectable evidence/diagnostics with legacy compatibility. Completed 2026-10-04: focused backend 61 passed, full API 736 passed/19 existing PostgREST skipped, all API Ruff; web 19 tests/build/lint and 16 real-browser fixture layouts passed. Exact scope, evidence and remaining limits are in the workflow. Mission/report-v2 schemas, assertion engine and general completion proof remain later work.
- [x] **R-S2:** current masked/bounded region/row context, viewport/occlusion and omission coverage; revision-bound DOM targets with stale dispatch refusal and honest `agent_lost` feedback. Completed 2026-10-04: focused API 110 passed, full API 762 passed/19 existing PostgREST skipped and Ruff; extension 128 passed/1 opt-in live-contract skipped, TypeScript/build/zero-warning lint; 15 actual Edge geometry fixtures passed. Update API, reload rebuilt extension and website tab before restarting. Exact contract, artifacts and installed-browser/completion-proof limits are in the workflow.
- [x] **R-S3:** controlled four-direction nested scrolling and bounded observation/wait, current revision/capability checks, measured movement, cancellation and honest timeout/exhaustion. Completed 2026-10-05: API focused 144/full 811 passed, 19 existing PostgREST skipped and Ruff; extension 159 passed/1 opt-in skipped, TypeScript/build/zero-warning lint; web 19 passed/build/lint; 39 actual Edge fixtures passed (24 new, 15 R-S2 regressions). Update API, reload rebuilt extension and website tab before a new run. Exact contract, artifact scope and remaining limits are in the workflow.
- [x] **R-S4:** task/persona separation and outcome-based completion. Completed 2026-10-05: 49 scripted completion regressions, focused API 256 passed, final full API 902 passed/19 existing PostgREST skipped, Ruff and diff checks passed. Exact public milestone evidence replaces model progress and unrelated URL/toast shortcuts; unresolved expectations remain unknown. Includes real PostgreSQL restart/idempotency checks; an existing fixed-window concurrency fixture was stabilized without changing production SQL. See the [completion contract](../docs/task-completion-contract.md) and workflow for evidence, scope and limits.
- [x] **R-S5:** versioned detailed report and legacy consumers. Completed 2026-10-05: full API 915 passed/19 existing skips; final affected prompt/privacy/clean regressions 78 passed; web 42 passed, TypeScript/Vite build, zero-warning lint and API Ruff passed. Isolated Edge 15/15 report checks passed. See [version contract and consumer matrix](../docs/report-v2-contract.md). No migration, paid call or deployment; publication is handled by the separate agent.
- [x] **R-S5a:** chaptered report with web/print/CSV/section-prompt/MCP parity. Completed 2026-10-06: ten code-derived chapters with honest statuses, stable IDs, cross-links and three next actions; `fix-prompt?section=` and MCP `get_report(section, cursor)`/`get_fix_prompt(section)`. full API 930 passed/19 existing skips, final affected suites 98 passed, Ruff; web 46 passed, build/lint; isolated Edge 42/42. See the [chapter contract](../docs/report-v2-contract.md#chapters-r-s5a). No schema, migration, paid call or deployment.
- [x] **R-S6:** one owner-defined synthetic filtered-count assertion with dataset/time/tolerance context, source-bound report evidence and separate UI completion/count verdicts. Completed 2026-10-06: full API 975 passed/19 existing skips, final affected 65 passed, broader consumers 121 passed and Ruff; web 51/build/lint; extension 160 passed/one opt-in skip, TypeScript/build/lint; isolated Edge 47/47. Fixed `./dev` dashboard/account plan CORS by pinning child URLs. [Golden mission and exact scope](../docs/filter-count-assertion.md). No dependency, migration or paid call; publication stays with the separate agent.
- [x] **R-S7:** provider/stage/attempt receipts with supplied cache/reasoning/modality/tool usage, failed-response retention, unknown usage and versioned integer estimates. Completed locally 2026-10-06: full API 1,022 passed/19 existing skips, fresh consumers 108 passed, Ruff/diff green; disposable PostgreSQL replay/concurrency/process-exit/RLS/migration checks. [Contract and activation gate](../docs/provider-usage.md). Recording defaults off; proposed migration 0004 remains unapplied to configured storage. No customer charge, paid call, routing/price change or deployment.
- [x] **R-S7a:** safe scoped Instant Scan reuse. Completed 2026-10-06: `scan_version` invalidation, labelled `fresh`/`reused`/`coalesced` answers with observed time, `fresh: true` fix checks, one scan per page for simultaneous misses, hash-only keys; offline fixture measurement 93.3% reuse over 60 repeat visits, 8 simultaneous misses ran 1 scan. Browser and owner work never reused. See [reuse contract](../docs/scan-reuse.md). No migration, dependency or provider call.
- [x] **R-S8:** atomic run-credit and funded-budget reservation with an explicit settle/release/refund state machine. Completed locally 2026-10-06: proposed migration 0005 (not activated), `RESERVATIONS=off` by default, fail-closed admission before any model call, credit separate from cost; disposable PostgreSQL 13 passed including 20-way and 10-way races and crash after dispatch; wiring 14 passed. See [ledger contract](../docs/run-reservations.md).
- [x] **R-S9:** common admission across web/extension/API/MCP/Scout/watch/citations. Completed locally 2026-10-07: proposed migration 0006 (not activated), one `reserve_work` ledger path for every model/data entry point with per-operation allowances and one funded budget; disposable PostgreSQL 10 new + 20 existing passed, offline wiring 21 passed. See [inventory and contract](../docs/work-admission.md).
- [ ] **R-S10, next:** scope/quote/hard-cap and settlement UI.
- [ ] **R-S11:** compatible stronger-model adapters, disabled by default.
- [ ] **R-S12:** separately authorized capped model comparison, with measured failure/latency/cost results.
- [ ] **R-S13:** targeted fix recheck and honest comparison.
- [ ] **R-S14:** saved bounded suites and tested/not-tested coverage.
- [x] **R-S14a:** slim owner timestamp/ID-paged history and database-filtered MCP; exact counts past row caps; complete site/distinct-batch pagination; account/token-scoped plan displays and query/index evidence. Completed 2026-10-05: API affected 136 passed, legacy fixture follow-up 89 passed and Ruff; final combined full API 902 passed/19 existing PostgREST skipped; web 34/build/lint; 20 actual Edge component checks, 2,500-row migrated SQL history/RLS and five regex checks passed. Initial full run's two failures were repaired; final verification includes all disposable PostgreSQL suites. No migration justified; deployed plans remain uninspected. [Evidence and limitations](../docs/database-history-queries.md).
- [ ] **R-S15:** founder pilots and pricing adoption proposal; no automatic catalog activation.
- [ ] **R-S16:** authorized read-only Search Console data.
- [ ] **R-S17:** grounded keyword/page/intent/content opportunities, measured versus advisory data, current SEO guidance and only a benchmark-qualified narrow Jev fallback. **Advisory mode done locally 2026-10-07:** page/intent map from site copy, Keywords chapter/brief/MCP parity, recalibrated advisory length and h1 checks; measured mode waits on R-S16. See [contract](../docs/keyword-opportunities.md).
- [ ] **R-S17a:** twelve contextual backlink tactics, useful assets/sourced opportunities, distinct GEO/citation guidance and matching prompts/MCP; no autonomous outreach, paid link network or ranking guarantee.
- [x] **R-S18:** bounded PSI/Lighthouse resource/element attribution, reported device/throttling/time context and distinct lab/field p75/single-browser evidence. Completed 2026-10-06: final affected API 112 passed, dedicated attribution 18 passed, whole API Ruff; web 51 passed/build/zero-warning lint; isolated Edge 84/84. Full-run shared fixture races and exact scope are recorded in the [performance contract](../docs/performance-attribution.md). No additional provider/model call, dependency or migration. R-S6 remains owned by the coordinated chat.
- [ ] **R-S19:** truthful evidence annotations/optional actual-frame highlights.
- [ ] **R-S20:** adopted-scope installed-browser/durability/release checks, also clearing the relevant existing V0 gates.

Checkpoints after R-S4, R-S10 and R-S15 distinguish implementation, measured model quality, funded admission and validated paid value. Optional growth/media work is not a requirement to validate the first scoped pilot. Preserve historical unchecked work below; reference it when a restructure slice also addresses the same defect.

## V0 prelaunch sessions, excluding pricing (2026-09-30)

**Estimate: seven focused sessions; allow eight to nine if native Chrome or deployed acceptance exposes additional defects.** This is a work estimate, not a guaranteed launch date. Domain/account setup, inbox access and Chrome Web Store review can add calendar waiting without adding coding sessions. The existing application is substantially built; these sessions activate, harden and verify it rather than rebuild features that passed QA.

**Scope:** address the non-pricing findings from the [local TripBurst QA assessment](../evals/results/qa-2026-09-30/launch-assessment.md). The assessment/logs are ignored local artifacts; confirmed findings and completion checks are preserved here. No price changes, paid-offer copy overhaul, Dodo activation, coupons, paid models or new issue-tracker entries. Founder free-grant functionality and ensuring V0 cannot charge users remain acceptance checks. Pricing concerns stay separately unresolved; this plan does not mark them fixed. Existing roadmap items and their completion history remain intact.

**Baseline:** API 704 passed/19 skipped, extension 64 passed/1 skipped, web 8 passed; lint/type checks/builds passed. Most report, comparison, AI-answer, team, feedback, watch and MCP paths worked live. The current keyed extension start returned 500; old integration-harness success is not installed-extension acceptance. The 19 local PostgREST team-test skips must stay visible until replaced by runnable coverage or explicit live evidence.

### Session 1: Restore the current extension run path (M)

- [x] **V0-S1** Reconcile the connected database with the existing migration runner. QA found only `0001` applied, no `run_requests`, and missing `claim_run_request`, `finish_run_request` and `expire_run_requests`. Reviewed checksums, paused API/worker, backed up legacy checkpoints and applied **existing** `0002_agent_checkpoints.sql` and `0003_run_idempotency.sql` to the connected development database. All legacy row counts preserved, applied checksums match and second application is a no-op. Production order recorded in [the run contract](../docs/run-idempotency.md#session-1-local-activation-2026-09-30).
- [x] Verify schema visibility, keyed start/observe/stop, exact retry replay and request-response expiry. Both live journeys consumed one quota unit and produced one saved run/one report job despite exact request replays. Guarded synthetic expiry removed the cached payload and retained a non-executable tombstone. Isolated retention regression verifies audit/job/rate-limit/request cleanup continues after screenshot cleanup fails.
- [x] **Done when:** the current extension contract completes a read-only TripBurst journey with no missing-RPC 500; retry/stop evidence and migration status are saved. Completed sign-in discovery `814100f3ecf0463c8b5f078dd677784f` (two actions, three replays); pending-action stop `2e7fc3a801114f31955c88e814324a02` (zero actions, two replays). Native permission/safety acceptance remains Session 5; live durable restart remains Session 2.

**Completion evidence (2026-09-30):** focused API selection 72 passed; strengthened retention selection 6 passed; extension 64 passed/1 opt-in skipped. API/eval Ruff and extension type/lint/build passed. Maintained `evals/e2e_extension.py` now sends current request keys/action IDs and can assert replay/quota/stop behavior; Chrome messaging is still stubbed. Local ignored evidence: `evals/results/v0-session-1/` and the two `evals/results/e2e-<run_id>.json` files. Broad shared-data purge was rejected by automatic approval review; safe synthetic expiry and isolated retention tests supplied verification. A separate planning journey gave up after a click; it is not counted as a successful goal. Stop-report grounding defect is recorded in S5 below.

**Verification:** focused migration/idempotency and extension retry tests, API Ruff, extension type/lint/build, live current-client requests. **Dependencies:** none. **Likely files:** `apps/api/app/migrate.py`, existing migrations, `app/db.py`, run routes, extension API client, `docs/run-idempotency.md`; change code only if activation reveals a defect. **Existing work:** SD-6.5 run activation, SD-6.2 migration prerequisites.

### Session 2: Prove production durability and readiness (M, split only if restart defects appear)

**Deferred by founder direction (2026-10-01):** skip the hosting session and resolve other issues first. S2 remains pending; this is not production deployment or durability acceptance. Continued with S3 below.

- [ ] **V0-S2** Prepare the confirmed deployment target using `APP_ENV=production`, `CHECKPOINTER=postgres` and a private checkpoint connection. Install `requirements.lock` followed by the project with `--no-deps`; correct the historical unpinned `pip install .` path. Production must fail startup when durable state is unavailable. Keep local-scan permissions confined to development.
- [ ] Exercise a real current-client journey across an API restart, and a queued report/watch job across worker restart. Prove resume, lease recovery and no duplicate browser action/report/quota charge. Keep founder admin loopback-only. Update deployment instructions to the verified configuration rather than silently choosing a different hosting architecture.
- [ ] **Done when:** a readiness check fails on missing required DB/RPC/checkpoint dependencies and passes on a usable deployment configuration; `/health` remains a liveness check. Required schema readiness must not be inferred from its current 200. Provider readiness must be bounded and avoid a billable call on every health poll.

**Verification:** existing SQL/checkpoint/job tests plus process-restart drill and readiness failure/recovery checks. **Dependencies:** S1. **Likely files:** runtime/checkpoint initialization, `app/main.py`, jobs, deployment configuration, `docs/deploy.md`, `docs/checkpoints-and-request-logs.md`. **Existing work:** SD-6.1/6.2 deployment acceptance, SD-6.6/6.7, SD-9.2. **Founder preparation:** confirm the hosting account/VM, Supabase region and private deployment credentials; no paid service is enabled by this plan.

**S1 environment observation:** some early Windows maintenance Python processes exited with native heap-corruption code `0xC0000374` after SQL committed. Final migration/status/privilege/expiry and live-run checks subsequently exited 0. The local psycopg Python implementation selects libpq 12 despite PostgreSQL 18 tools being installed. Recheck the selected client library and connection lifecycle during S2 before claiming durable production runtime acceptance; no dependency was added or root-cause fix claimed in S1.

### Session 3: Close the auth and privacy contract gaps (M)

- [x] **V0-S3 engineering:** Website logout requests an acknowledged, identity-qualified extension disconnect before SDK sign-out. Missing/failed acknowledgment warns honestly; logout errors remain visible. Exact external sender checks preserved. Challenge-bound connection handoff, serialized credential changes and compare-and-set refresh/401 updates prevent late account A responses disconnecting or resurrecting account B. Sidepanel clears private state and stops dispatching new browser actions after disconnect/account change. Already-dispatched actions may finish; unfinished server runs remain recoverable from the original dashboard.
- [x] Keep the 300-second API validation cache bounded by access-token expiry, and reject expired tokens even before a cached/upstream acceptance. Document this as a revalidation window, not a guaranteed logout-revocation deadline. Cold/warm rejection, refresh expiry, account switching and concurrent refresh tested. Live tester logout: warm validation 200, cold validation 401, revoked refresh 400; upstream access JWT behavior is not universally guaranteed by that observation.
- [ ] **Final acceptance:** Corrected Privacy/Security/Settings now agree on logout, public/team sharing and report-email retention. Engineering checks passed; installed Chrome handoff/logout/account-switch repetition remains S5 because native Chrome automation is unavailable. Founder legal review remains open under the existing safety-plan gate. Real local PostgreSQL policies verified viewer access, private/public report and screenshot isolation, denied membership writes and immediate membership-removal access loss. Existing live viewer/removal QA evidence remains valid baseline; a fresh live cross-account repeat requires specific approval after automatic review rejected creating/granting a new viewer in the existing QA workspace.

**Engineering verification (2026-10-01):** full API **706 passed / 19 existing PostgREST skips**; added real-policy local RLS regression **1 passed**; focused auth/retention/citation SQL **19 passed**. Extension **83 passed / 1 opt-in skipped**; web **13 passed**. TypeScript, lint and production builds passed for web/extension; API Ruff passed. Fixed the citation rollover test's local-date/UTC mismatch without editing an applied migration. Live isolated website sign-in, absent-extension error, sign-out and protected Settings redirect passed; live owner/anonymous private/public RLS reads and tester warm/cold Auth/refresh checks passed. Temporary QA origin/bridge and login fixture removed. [Connection contract and limitations](../docs/auth-sessions.md); ignored evidence `evals/results/v0-session-3/`. No deployment, pricing change, new dependency, schema change, payment or issue created.

**Verification:** auth/handoff regressions, real website-to-extension logout/account-switch checks, live cross-account RLS reads, affected web/extension type/lint/build. **Dependencies:** S1; final native-browser repetition in S5. **Likely files:** web auth/AppShell, extension background/session client, API auth, Privacy/Security/YourData components and tests. **Existing work:** SD-3.2/3.3, SD-10.3 and the agent-safety privacy gate. Price and paid-plan copy are excluded.

### Session 4: Clear sign-in and founder operations (M; setup-dependent)

- [x] **S4 engineering (2026-10-01):** Callback errors use safe, actionable messages; expired/refused callbacks return to usable login controls, and malformed invitation fragments cannot crash `/join`. Invited sign-in returns to `/join`. Network exceptions release sign-in controls; magic-link copy does not invent an expiry time. Access-request response loss rereads saved state once with account fencing and never automatically repeats the POST. Saved requests remain successful when notification queuing fails. Whitespace-only feedback is refused. Founder admin failures show recovery guidance without exposing internal errors; request grants validate the recipient and expose partial success.
- **Verification:** 57 focused API tests and 19 web tests passed; API Ruff, web TypeScript, zero-warning lint, production build and whitespace checks passed. Existing bundle warnings remain. Real browser expired-link recovery and Google back-navigation passed; Google/GitHub reached their real provider login pages. One authorized existing-account magic-link request was accepted, but inbox receipt and successful callback are not yet proven. Both advertised OAuth providers are enabled. Resend app email is unconfigured; Supabase sign-in mail is separate.
- **Live acceptance still open:** authorized inbox link completion, provider authentication/callbacks, invited-account return after a real callback, founder password/fresh-TOTP admin grant/revoke and live notification checks. Only account existence was read; no live grant or payment was performed. Founder must enter credentials directly in the browser. Walkthru runs on 5174/8010 and founder admin on 8020; TripBurst ports remain untouched. Ignored evidence: `evals/results/v0-session-4/`.
- **Browser follow-up:** malformed invitation input reproduced a second URI decoding crash in the global scroll handler; fixed and reloaded successfully to “No invitation here.” Anonymous Team navigation redirected to login. Final web tests/type/lint and rebuilt production bundle passed after this fix.

- [ ] **V0-S4** With an authorized test inbox/provider account, complete a Supabase magic-link callback and Google/GitHub sign-in/callbacks for every provider advertised. Check cancellation, invalid/expired links, private-route redirects and invited-user return to `/join`. Do not confuse Supabase auth-mail delivery with Resend app notifications.
- [ ] Exercise the actual founder password/TOTP admin UI: see QA feedback/request, grant a disposable account access for free, observe its dashboard notification, revoke the grant and confirm Free limits. Resolve or clearly expose save failures. Reproduce the one-off access-request “Failed to fetch” after a server 200; reconcile saved state after response loss before considering an automatic retry.
- [ ] **Done when:** the support/privacy/abuse domain and inboxes are real, and the founder can reliably discover/respond to requests. Either verify free-tier Resend delivery for configured app notifications or explicitly operate via the admin panel and copied invitations with honest unavailable-email states. Test feedback visibility and invite delivery/fallback. No charge or payment setup is needed.

**Verification:** real inbox/provider callbacks, admin fresh-TOTP grant/revoke, feedback/request persistence and duplicate protection, invite acceptance and notification/fallback checks. **Dependencies:** S3, with production callback repetition in S7. **Likely files:** login/auth, feedback/access-request client, admin, delivery/notification configuration and relevant docs. **Founder input:** domain/provider consoles, inbox access and authenticator entry; never save credentials in evidence. If GitHub fix PRs are advertised at V0, also clear its separate GitHub App installation/preview/PR flow on an owned disposable repository; OAuth sign-in alone does not verify that integration.

### Session 5: Installed Chrome acceptance and report correctness (verification-first; allow an extra session for defects)

- [x] **YapChat connection engineering (2026-10-01):** Reproduced stale legacy-marker and dropped-listener failures in the actual injection entrypoint; both failed before the fix. Injection checks a currently registered listener, replaces a stale overlay and acknowledges the main-frame receiver before sending work. A failed dispatched action is never replayed automatically. Connection failures show reload/reopen guidance without unrelated DNS advice or an ongoing first-step wait. Extension **89 passed / 1 opt-in skipped**, TypeScript, zero-warning lint and production build passed. Rebuilt local package uses web **5174** and API **8010** via ignored public `.env.local`; previous manifest pointed to 5173. Corrected the API's ignored local `WEB_URL`, restarted the verified Walkthru process and confirmed both servers return 200 and the API permits origin 5174. Owner-authorized YapChat homepage/login rendered without submitting target forms. Native Chrome reload and successful installed-extension YapChat run remain unchecked below.

- [ ] **V0-S5** Install the intended beta extension in a clean ordinary Chrome profile. Verify its ID, web-origin connection, sidepanel sign-in, Visitor/Owner behavior, stop controls and a complete current-client journey. Use owned TripBurst/fixtures only. Clear the existing hard-fixture safety gate: blocked/bulk goals, injected page instructions, bot wall, signed-in owner form flow, masked snapshots/screenshots and permission prompts. Do not submit target production forms or bypass CAPTCHA. Use authorized fixture data for form sends.
- [ ] Inspect actual CSV downloads and PDF output for report, comparison, workspace and branded exports: values, Unicode/escaping, formula protection, page breaks and complete evidence. Recheck mobile navigation/replay/chat and missing/error states. Fix report scope wording so a browsing-only goal is not presented as a verified signup conversion; keep progress honest during model/report waits.
- [x] Fix the **confirmed S1 stop-report grounding defect**: historical run `2e7fc3a801114f31955c88e814324a02` stopped before the first action, yet claimed Explore trouble and a medium UX finding citing confusion 0/3. **Fixed for newly generated reports in R-S1 (2026-10-04):** unconfirmed actions, custom stop reasons, confusion and termination alone no longer establish a site defect; unfinished journeys without observed failure use a deterministic summary without a writer call. Genuine earlier errors remain eligible, with regression coverage. No target navigation defect was proven by the old stop; its saved report was not regenerated. This does not clear the remaining native-browser S5 gates.
- [ ] **Done when:** installed-extension acceptance and the existing safety-plan native-browser gate pass with saved evidence; exported files are inspected; confirmed rendering/usability defects are fixed. Investigate the one-off landing scan-anchor displacement before declaring it a bug. Recheck AI-answer engine/source coverage, Scout grounding and comparison “Not measured” behavior; do not relabel API answers as measurements of consumer AI products.

**Verification:** ordinary Chrome end-to-end checks, saved sanitized screenshots/export artifacts, affected API/web/extension tests and builds. **Dependencies:** S1-S4. **Likely files:** sidepanel/inject/safety only for reproduced defects, report/export/scope components, small navigation/progress fixes. **Existing work:** agent-safety-plan native pass, V7 evidence/PDF, P3.2 live evidence. The legacy harness cannot satisfy this session's exit criteria.

### Session 6: Prepare a reproducible release and rollback (M)

- [ ] **V0-S6** Prepare production web/API/extension artifacts for the final domain and exact external handoff origin/extension ID. Establish the intended zip or Unlisted distribution path and installation instructions. Remove/exclude dev-only launch helpers, the public agent-lab route and unpacked-only settings from production as appropriate; ensure `ALLOW_LOCAL_SCANS` and founder admin are not publicly enabled. Check whether historical credential-rotation requirements in deployment docs were completed; resolve any outstanding rotations through the founder, never print secrets.
- [ ] Run full required API/web/extension checks and dependency/security checks against the release candidate, with locked installs and documented skips. Configure existing CI/release checks, minimal readiness monitoring, free-model quotas and sanitized support logs. Record backup/recovery and deployment/rollback commands for code and schema; preserve prior applied migrations and stop new runs during an incompatible release.
- [ ] **Done when:** one reviewed release candidate has a known commit/artifact/configuration and a usable rollback/runbook. Assess the 650 kB web chunk and empty initial landing HTML; take a small existing-stack improvement where feasible, or record them as nonblocking post-beta work. Full prerendering/new build dependencies require the existing dependency approval rule and do not expand this session automatically.

**Verification:** full pytest/Ruff, web tests/lint/build, extension tests/type/lint/build, audit/secret checks, production-artifact/config review and rollback rehearsal. **Dependencies:** S1-S5. **Likely files:** CI/deploy configuration, extension manifest/build settings, installation/operations docs; limited frontend changes only if warranted. **Existing work:** SD-4.7, SD-8.1/8.3/8.5, SD-9.1/9.2/9.5/9.6, V11a. Store review time is external waiting, not a guaranteed same-session approval.

### Session 7: Deploy the approved candidate and run a production canary (verification-first)

- [ ] **V0-S7** With release authorization and confirmed hosting access, deploy the exact verified candidate, applying reviewed pending migrations in order before incompatible clients. Set production secrets privately, configure HTTPS/domain/CORS and Supabase redirect URLs, and distribute the matching extension. Keep Dodo checkout and paid providers disabled. Founder admin stays on the founder's machine.
- [ ] From a clean Chrome profile, complete signup/sign-in, scan, extension owner/visitor journey, report/replay/export, comparison, team invite/permissions/Scout, feedback and founder grant/revoke. Check MCP key create/revoke, AI-answer queued/completed/error states and watch/deploy-hook processing after restart. Verify HTTPS/CSP/readiness, cold-start behavior and free-provider quota/failure handling. The target is an owned deployed fixture; avoid scanning unrelated production sites.
- [ ] **Done when:** no unresolved critical/high defect remains in the agreed non-pricing scope, native/deployed acceptance evidence is recorded, founder operations and rollback work, and monitoring can detect failure. If a check fails, hold wider invitations and roll back or fix/retest; do not mark skipped flows passed. Update CURRENT_STATE.md and this checklist with deployed URLs, version, measured limits and any specifically deferred nonblocking items.

**Verification:** saved production canary evidence plus a restart/rollback drill. **Dependencies:** S1-S6 and external domain/provider/distribution prerequisites. **Likely files:** deployment configuration/docs and any narrowly scoped acceptance fixes. This session is planned work; the 2026-09-30 planning update does not itself authorize publishing now.

### Checkpoints and estimation boundaries

- [ ] **After S2:** current idempotent run path and durable restart recovery pass; missing schema no longer hides behind green liveness.
- [ ] **After S5:** auth/founder operations, native extension safety, evidence and exports pass; record confirmed defects separately from unreplicated observations.
- [ ] **After S7:** deployed candidate is verified and recoverable; only then expand beta access.

Founder preparation should start early: hosting target, production domain/contact inboxes, provider callback consoles, authorized test inbox and Chrome distribution access. **Seven sessions assumes these are available and the native pass does not uncover a major new defect.** Use one to two additional sessions for reproduced fixes and retesting if needed; do not compress acceptance to meet the estimate. Feature expansion, paid billing, code scanning, consumer-AI integrations and a full frontend redesign are outside this launch-fix sequence.

## v1.2 flagship plan (2026-09-25)

System design and hardening tasks before going live (SD-1.1 to SD-10.4, with hardness and human flags): [docs/system-design.md](../docs/system-design.md). Claim with `- [~]` there. (added by Claude Code, 2026-09-25)

### Codex completion ledger (updated 2026-09-28)
- [x] SD-6.3 provider resilience: three-failure/60-second circuits, one recovery probe, citation queue preservation and bounded configured model calls. 116 affected tests and Ruff passed. [Details](../docs/provider-resilience.md).
- [x] SD-7.2 public Instant Scan reuse for ten minutes, with private/owner/incomplete/expired reports excluded, current safety rules and address limits preserved. 36 focused tests pass; see CURRENT_STATE.md for full-suite limitations.
- [x] SD-3.3 extension session handoff: exact dashboard sender checks, validated/allowlisted credentials and storage failure handling. Full extension tests, type check, lint and build passed.
- [x] SD-3.2 auth cache: bounded LRU eviction, thread-safe access, expired-entry cleanup and documented validation window. 20 focused tests passed; Ruff clean.
- [x] Repository reuse and launch audit, including MiroFish licence constraints, citation gaps and payment setup: [assessment](../docs/repository-opportunities-and-launch-audit-2026-09-27.md).
- [x] Competitor comparison metric bars, severity stacks, coverage and comparable gaps; public-scope scans and extension handoff. API, web and extension tests/builds passed (CURRENT_STATE.md).
- [x] DNS TXT ownership guidance and verification action; meta/file alternatives retained. Public competitor comparisons do not require ownership; owner journeys still do.
- [x] Dashboard and ReadinessPipeline crashes on partial/comparison reports fixed and type/lint checked.
- [x] P3.2 citation correctness, measurement coverage, source evidence, filters, quota/lease recovery and regression tests: [measurement v2](../docs/citation-measurement.md).
- [ ] P3.2 live showcase checked twice and sustained weekly coverage. Distinct from the completed implementation.
- [x] SD-8.1 structured request logs, safe error diagnostics and support IDs in web/extension errors. Privacy, concurrency, CORS and client regressions pass. [Guide](../docs/checkpoints-and-request-logs.md).
- [x] SD-6.2 code and local verification: production persistence guard, private-schema migration, abrupt process restart, HTTP resume and cleanup tests.
- [ ] SD-6.2 deployment acceptance: migration 0002 applied to development in V0-S1; apply to the production database if pending, configure the confirmed deployment target and verify a live extension journey across restart. Overall SD-6.2 stays partial in system-design.md.
- [x] SD-6.5 run portion: durable start/observe/stop request keys, response replay, action-ID validation, bounded extension retries, report job deduplication and lost-stop recovery. Real PostgreSQL/HTTP and extension-loop regressions pass. [Contract and evidence](../docs/run-idempotency.md).
- [ ] SD-6.5 deployed activation: migration 0003 and current-contract live harness passed in development in V0-S1; production migration/API and native/deployed extension acceptance remain. Payment idempotency remains separate under SD-10.1; overall SD-6.5 stays partial.

### Founder track (now)
- [x] Confirm prices: Pro $19 and Plus $49, founding $15 and $39 (2026-09-24)
- [x] Approve reusing permissive open source and the free-tier-only rule (2026-09-25)
- [ ] A1: 30 free Instant Scans with a "$9 founding Launch Pack" line. Gate: 5 paid of the first 100 scans.
- [ ] A2: 20 beta users on the extension. Gate: 5 or more finish a run within 48 hours.
- [ ] A3: headline test, "Can ChatGPT read your site?" against "Find where users get stuck". Gate: 1.5x scan starts.
- [ ] A4: 10 Supabase-backed launches see their backend exposure result on their verified domain. Gate: 3 say they would pay for it.
- [ ] Buy the domain this week; point `api.<domain>` at Render until the VM is ready
- [ ] Chrome Web Store account ($5); Google Cloud VM by UPI prepay (e2-micro first; e2-small only if the worker needs 2 GB); Dodo live-mode verification started
- [ ] PageSpeed Insights API key (free) into the API env
- [ ] Google Cloud OAuth consent screen with the Search Console read-only scope (start verification early)
- [ ] Create the Walkthru GitHub App (read-only Contents and Metadata) before Phase 2
- [ ] Enable Google and GitHub sign-in; rotate Supabase secrets
- [ ] Decide the plan allocation marked "proposed" in SPEC.md

### Phase 0: honest paid plans (sessions 16 to 18, before any charge)

- [x] **P0.1 Truth pass** (M), done 2026-09-25 by Codex: claims aligned with shipped checks; stable `rule` ids and legacy comparison fallback; local HTTP is a development note; PageSpeed unavailability has a reason.
  - Accept:
    - SPEC, landing, docs and security page claim only checks that exist (SPEC's free security row says TLS; the code has none until P1.2).
    - Plain http on `localhost`, `127.*` and private addresses is never "high"; it is a local-dev note (briefing audit finding).
    - Every `Finding` gets a stable `rule` id (for example `sec.hsts.missing`, `geo.robots.blocks_search_bot`). `compare.fingerprint` prefers `rule` over the title and falls back to the title for old reports.
    - PageSpeed runs when `PAGESPEED_API_KEY` is set; "not measured" keeps its reason otherwise.
  - Verify: pytest that every scanner emits a `rule`; an old report still compares; a localhost scan has no high http finding.
  - Files: `app/agent/schema.py`, `app/agent/compare.py`, every `app/scans/*.py`, SPEC.md, `apps/web/src/content.ts`.
- [x] **P0.2 Signup funnel numbers (V18)** (S), built by Claude Code and closed out by Codex 2026-09-25: distinct fields, deduplicated errors, first-useful timing, saved prior-run comparison and report display verified.
  - Accept: `report.funnel` on paid runs: steps to the goal, fields typed, errors seen, safe stops, time to the first useful screen; compared across reruns.
  - Verify: pytest over stored steps; shown on the report.
- [ ] **P0.3 First impression v2 and landing copy review (V19)** (M)
  - Reuse: none needed; checklist written from the geo-optimizer-skill negative-signals list (MIT) and standard 5-second-test questions.
  - Accept:
    - Input is the first journey screenshot when present (extension already captures it) plus the page text; Instant Scans use text only and say so.
    - A fixed checklist, each item pass or fail with the quoted evidence: says what it is, says who it is for, states an outcome, primary CTA visible, social proof, pricing reachable in one click, contact or company identity.
    - Clarity is computed from the checklist in code, not asked of the model.
    - Copy review (paid): up to 3 rewrites each for headline, subheadline and CTA, each quoting the text it replaces, labelled suggestions.
    - Free vision model from the chain (Gemini Flash free tier; bake-off picks between free vision models); one call per report.
  - Verify: pytest with a fake model; the briefing's clear page is rated clear; no rewrite without a quote.
  - Files: `app/agent/report.py`, `app/agent/schema.py`, `app/agent/runtime.py`, `ReportView.tsx`.
- [x] **P0.4 Competitor side by side (V21), moved up** (M), done 2026-09-25
  - Accept: `POST /compare` with up to 3 URLs; passive scans only; Launch Ready, GEO, SEO and security side by side; rows where a competitor beats the user's site come first.
  - Verify: pytest and one live comparison of 3 real sites.
- [ ] **Checkpoint P0:** every row of SPEC's plans table points at working code or says "coming" with a date; founder reviews one Pro report.

### Phase 1: reasons to pay (sessions 19 to 23, before launch)

- [x] **P1.1 Backend exposure check** (M), built 2026-09-25 by Claude Code (`app/scans/backend.py`, wired in `site.py`, `tests/test_backend.py`, 4 tests). Supabase: config and secret-key detection on every plan; verified domains get HEAD row counts, RPC listing (never called) and public bucket listing, with RLS SQL. Tables come from the OpenAPI list and from `.from()`/`.rpc()` calls in the bundles, because newer publishable keys cannot read the list (found live on Walkthru's own project: `runs` 21 public rows, by design). Firebase Realtime Database read checked. **Still open:** the Firestore unauthenticated read and the hard-fixture trap.
  - Reuse: [Perufitlife/supabase-security-skill](https://github.com/Perufitlife/supabase-security-skill) (MIT), [humora2504/vibeproof](https://github.com/humora2504/vibeproof) (MIT), [GerardoRdz96/rlsgate](https://github.com/GerardoRdz96/rlsgate) (MIT). Not [hand-dot/supabase-rls-checker](https://github.com/hand-dot/supabase-rls-checker) (no licence: ideas only).
  - Accept:
    - Every plan: find a Supabase URL and anon key, or a Firebase config, in HTML and bundles, and explain that security now depends on RLS or rules.
    - Verified domains (paid): read-only probe with the public key only. For each table the public API exposes, a `HEAD` with `Prefer: count=exact` reports how many rows anyone can read. Storage: which buckets list files publicly. RPC: which functions answer anonymously (listed, never called with arguments). Firebase: whether the database or Firestore answers an unauthenticated read.
    - Never stores or shows row contents; never writes; stops at 50 tables; 10 s budget.
    - Fix recipe: the SQL to enable RLS and an owner-only policy per exposed table.
  - Verify: pytest against a recorded fixture API (open table, closed table, public bucket); an unverified domain never sends a probe request.
  - Files: `app/scans/backend.py` (new), `app/scans/site.py`, `app/agent/report.py`, `tests/test_backend.py` (new), `evals/fixtures/hard` traps.
- [~] **P1.2 Security parity** (L), code built 2026-09-25 by Claude Code (`csp.py`, `libraries.py`, `secrets.py`, `tls.py`, `takeover.py`, data in `app/scans/data/`, 35 tests in `tests/test_security_parity.py`, hard-fixture traps X7 to X14). HSTS, TLS, CAA and takeover are covered by recorded-response and local-TLS tests, since an http fixture cannot serve them. Owner-verified real-site false-positive checks remain pending.
  - Reuse:
    - [mdn/mdn-http-observatory](https://github.com/mdn/mdn-http-observatory) (MPL-2.0): rewrite its header tests and scoring in Python (no code copied).
    - [google/csp-evaluator](https://github.com/google/csp-evaluator) (Apache-2.0): port the CSP checks (`unsafe-inline`, `unsafe-eval`, wildcards, missing `object-src`, `base-uri`).
    - [RetireJS/retire.js](https://github.com/RetireJS/retire.js) (Apache-2.0): its `jsrepository.json` data, refreshed weekly, matched against script URLs, banners and file hashes.
    - [gitleaks/gitleaks](https://github.com/gitleaks/gitleaks) (MIT): its `gitleaks.toml` patterns replace our 6 secret regexes (Go regex adjusted to Python).
    - [EdOverflow/can-i-take-over-xyz](https://github.com/EdOverflow/can-i-take-over-xyz) (CC-BY-4.0, attribution): takeover fingerprints for dangling CNAMEs.
    - Python `ssl` stdlib for certificate expiry and TLS version (not sslyze, which is AGPL-3.0).
  - Accept:
    - Header quality, not presence: CSP findings name the weak directive; HSTS max-age and preload; cookie prefixes; SRI on third-party scripts; CORS `*` with credentials or a reflected origin.
    - Vulnerable JavaScript libraries with the CVE and the fixed version.
    - Exposed source maps and more exposed paths (`/.env.local`, `/.env.production`, `/.git/`, backup and dump files, `/server-status`, `phpinfo`), verified domains only.
    - Certificate expires within 21 days; TLS below 1.2; no CAA record (over the existing DNS-over-HTTPS client).
    - Dangling DNS for subdomains found in the crawl, verified domains only.
  - Verify: one hard-fixture trap per new rule, none on the easy fixture; python.org and 2 other real sites show no false alarms.
  - Files: `app/scans/security.py`, `app/scans/tls.py` (new), `app/scans/data/` (retire.js and gitleaks data), `tests/test_security_parity.py` (new), `apps/api/THIRD_PARTY.md` (new).
- [x] **P1.3 Fix plan v2** (M), done 2026-09-25 by Claude Code (`app/scans/stack.py`, `app/agent/recipes.json`, batched plan with stop and verify, manual steps, chat parts; `tests/test_fix_prompt.py`)
  - Accept:
    - Stack detection in code from headers and HTML: Vercel, Netlify, Cloudflare, Render; Next.js, Vite, Astro, Lovable, Bolt; Supabase, Firebase.
    - A recipe per `rule` and stack (for example HSTS in `vercel.json`, `next.config.js`, `netlify.toml` or `_headers`), in a data file, no model call.
    - Batches in order (security, backend exposure, UX blockers, GEO, SEO, accessibility, performance), each ending with "stop and verify".
    - Every finding: why it matters, the change for the detected stack, the risk (CSP starts in report-only mode), and a local check (`curl -sI ... | grep -i strict-transport-security`).
    - Manual steps (DNS, hosting, email provider) listed separately.
    - The chat version is split into batches of 4,000 characters or less instead of "and N more".
  - Verify: pytest that a Vercel and a Netlify fixture get different recipes for the same rule; no secret unmasked; every finding appears once.
  - Files: `app/agent/fix_prompt.py`, `app/agent/recipes.json` (new), `app/scans/stack.py` (new), tests.
- [x] **P1.4 MCP depth** (S), done 2026-09-25 by Claude Code (`get_finding`, `verify_finding`; the MCP test flips a security and an SEO finding after a fix through `/mcp`)
  - Accept: `get_finding(run_id, rule)` returns the full recipe; `verify_finding(run_id, rule)` re-runs only the check behind that rule and answers fixed or still broken; same plan checks and limits as `rerun`.
  - Verify: MCP client test flips one fixture finding after a fix.
- [x] **P1.5 GEO depth pass** (L), done 2026-09-25 (Codex; 200 API tests, Ruff, web build and lint pass)
  - Reuse: [Auriti-Labs/geo-optimizer-skill](https://github.com/Auriti-Labs/geo-optimizer-skill) (MIT): port the checks we lack. Its 47 citability methods are based on Princeton KDD 2024; keep the source note.
  - Accept:
    - AI discovery endpoints (`/.well-known/ai.txt`, `llms-full.txt`), labelled low measured impact.
    - Freshness: visible dates, `dateModified`, sitemap `lastmod`.
    - Negative signals: CTA overload, boilerplate, keyword stuffing.
    - Prompt injection in page content (hidden instructions to AI, HTML comments aimed at models).
    - Trust stack: identity, social proof, external citations, consistency.
    - RAG chunk readiness: sections that stand alone, question headings, answer-first paragraphs.
    - Deterministic citability score per page: statistics with sources, quotations, definitions, comparison tables.
    - Firewall blocking: citation bots get a challenge page (Cloudflare "Block AI bots" pattern) even when robots.txt allows them.
    - Entity: Wikidata search by name and domain (free API); Google Knowledge Graph Search (free key) when set.
    - Fix pack adds an IndexNow key file and a Bing Webmaster submission note (ChatGPT Search leans on Bing's index).
  - Verify: one fixture trap per new check; showcase stays 95 or more; re-weighting documented in SPEC.
  - Files: `app/scans/geo.py`, `app/scans/geo_fixes.py`, `tests/test_geo.py`, SPEC.md.
- [x] **P1.6 SEO depth pass** (M) **DONE (Codex, 2026-09-25); separate from P1.7**
  - Reuse: [puneetindersingh/open-seo-crawler](https://github.com/puneetindersingh/open-seo-crawler) (MIT), [PhialsBasement/LibreCrawl](https://github.com/PhialsBasement/LibreCrawl) (MIT), [kemalai/FreeCrawl-SEO-Tool](https://github.com/kemalai/FreeCrawl-SEO-Tool) (MIT, its 167-check list is the checklist).
  - Accept: hreflang errors; oversized or unsized images and non-modern formats; rich-result schema validation (required properties per type); generic anchor text; pages with one internal link in; pagination; canonical pointing at a noindex or redirected page; mobile Core Web Vitals for the top 5 pages on paid plans through the free PageSpeed quota.
  - Verify: fixture traps and an owner-verified public site show no new depth false alarms. The founder's Vercel portfolio replaced python.org because an unverified production-site crawl was rejected by automatic approval review.
  - [x] Scanner, five-page paid mobile PageSpeed coverage, report UI, fixture tests, and docs implemented; 213 API tests pass, Ruff and web checks pass. The local easy fixture has no new depth findings.
  - [x] Read-only audit of `https://portfolio-web-six-psi-43.vercel.app/`: 1 page, crawl complete, no SEO depth findings; existing HTML-shell findings accurately identify missing server-rendered elements.
- [x] **P1.7 Agent readiness score** (S), done 2026-09-25 by Claude Code (`score.agent_ready`, `app/scans/agent_signals.py`, report section; `tests/test_agent_ready.py`)
  - Accept: 0 to 100 from existing evidence: labelled fields and accessible names (axe), no CAPTCHA before value, stable controls across reruns, SearchAction schema, WebMCP-style labelled forms, and whether the journey reached its goal. Shown next to the GEO score as "Can AI agents use your site?".
  - Verify: pytest over stored runs; the showcase and hard fixtures score differently for the stated reasons.
- [ ] **Checkpoint P1:** hard-fixture recall 85% or more including the new traps; easy fixture and 3 real sites have no false alarms; founder reviews one Pro report and one fix plan applied by a coding agent.

### Launch track (sessions 24 to 26)
- [ ] **IMPORTANT, FIX BEFORE DEPLOYMENT: agent safety, permission and trust plan** ([docs/agent-safety-plan.md](../docs/agent-safety-plan.md)). Site modes (Owner, Visitor, Blocked) decided by the server, blocklist and goal rules, social and commerce actions blocked in code, snapshot perception fixes, honest failure wording, bot-wall handling, rate limits, audit log, kill switch, privacy, terms and Chrome Web Store disclosures. Every GATE item ships with tests before launch. Item 1 (modes, blocklist, goal rules in `app/agent/policy.py`) done 2026-09-26; next is item 2, the per-step action gate.
- [ ] **V11a Domain and store submission** (session 20): `api.<domain>` on Render; production extension build; listing submitted.
- [ ] **V10 Billing with Dodo** (session 24): see the v1.1 entry below.
- [ ] **V10b Offer-ready notice** (after V10, not started; founder asked 2026-09-26 to build later): when the founder sends a payment offer from the admin panel, email the user a link to Plan & billing and show a dashboard banner "Your <plan> offer is ready, pay before <time>". Real customer email needs the domain verified in Resend.
- [ ] **V10c Coupons from the admin panel** (after V10, not started; founder asked 2026-09-26 to build later): the founder creates coupon codes in the local admin panel (`apps/api/admin`): a percentage off (for example 50%), custom code text, optional plan, use limit and end date, for pre-orders and the waitlist. A code entered on Plan & billing lowers the offer price; the server checks it, never the browser. Free passes for friends already work ("Grant free"). Check Dodo's own discount-code support before building our own. Prices are not final: keep them in `billing.PRICES` and the Dodo products, one place each.
- [ ] **V11b Production on the VM** (session 25): see the v1.1 V11 entry; plus a `worker` process for code scans and Nuclei (Phase 2) with its own queue table.
- [ ] **V7 Evidence and PDF close-out; V9 landing, pricing and onboarding copy; Dodo live** (session 26).
- [ ] **Checkpoint D (launch gate):** stranger path in production; launch Tue 2026-10-27, 2026-11-03 at the latest.

### Phase 2: code access (sessions 28 and 29, after launch)

- [ ] **P2.1 GitHub App connect** (M)
  - Accept: Settings > "Connect a repository" installs the Walkthru GitHub App on chosen repos (read-only Contents and Metadata); installation id stored per user and site; short-lived installation tokens are minted per scan and never stored; uninstall or disconnect removes access. Supabase's GitHub sign-in token is not used (it is not refreshed and has no repo scope).
  - Verify: pytest for the token flow with a recorded GitHub API; a disconnected repo cannot be scanned.
  - Files: `app/github.py` (new), `schema.sql` (`repos` table; schema change after launch needs the founder), Settings page.
- [ ] **P2.2 Code scans on the worker** (L)
  - Reuse (each runs as a separate binary on the VM):
    - [gitleaks/gitleaks](https://github.com/gitleaks/gitleaks) (MIT): secrets in the repo and its history.
    - [google/osv-scanner](https://github.com/google/osv-scanner) (Apache-2.0): vulnerable dependencies from lockfiles.
    - [opengrep/opengrep](https://github.com/opengrep/opengrep) (LGPL-2.1, engine only) with **Walkthru's own rules**. Not the Semgrep or Opengrep community rules: both carry the Commons Clause, which forbids selling them.
    - Walkthru rules for AI-built apps: service-role or secret keys in client code, `NEXT_PUBLIC_`/`VITE_` secrets, API routes without an auth check, `dangerouslySetInnerHTML` with request data, SQL built from strings, permissive CORS, `eval`.
    - Supabase migrations: tables without `enable row level security`, policies `using (true)`, `security definer` functions exposed to `anon`. Logic from the MIT Supabase scanners in P1.1.
  - Accept: shallow clone into a temp dir, 2 minute budget, 500 MB cap, deleted in a `finally`; findings join the report as `kind="code"` with file and line; secret values masked.
  - Verify: a fixture repo with planted secrets, a vulnerable package, an open policy and an unauthenticated route yields exactly those findings; the temp dir is gone after success and after failure.
- [ ] **P2.3 File and line in the fix plan** (S): each code-placed finding names `path:line`; web-only findings name the likely file from stack detection.
- [ ] **P2.4 Nuclei with safe templates on verified domains** (M)
  - Reuse: [projectdiscovery/nuclei](https://github.com/projectdiscovery/nuclei) (MIT) and [nuclei-templates](https://github.com/projectdiscovery/nuclei-templates) (MIT).
  - Accept: tags `exposure`, `misconfig`, `takeover`, `tech`, `cve` only; `-etags intrusive,dos,fuzz`; rate limit 10 requests a second; verified domains only; Pro and Plus.
  - Verify: a test asserts the command line can never include an excluded tag; one fixture exposure found.
- [ ] **Checkpoint P2:** fixture repo complete; nothing left on disk; founder reviews one report with code findings.

### Phase 3: measurement (sessions 30 to 32, Plus opens)

- [ ] **P3.1 Search Console and Bing Webmaster connect** (M)
  - Accept: Google OAuth with `webmasters.readonly`; Search Analytics (queries, clicks, impressions, CTR, position, last 28 days) and URL Inspection for audited pages (2,000 a day per property); Bing Webmaster API with the user's own key. Joined to findings: "ranks 11 for X at 3% CTR", "not indexed: reason".
  - Verify: recorded API responses in pytest; live on the founder's own site.
- [x] **P3.2 AI citation tracking** (L), built 2026-09-26 by Claude Code (local): `app/citations.py`, `/citations` routes, `/app/visibility` (AI answers), `tests/test_citations.py`. Engines changed after measuring the free quotas (SPEC.md). Still open: the showcase prompt set tracked twice on real engines (needs a signed-in Plus account).
  - **Correctness and coverage overhaul completed 2026-09-27 (Codex):** verified answer references, strict host matching, stable historical provenance, explicit unsupported surfaces, correct citation denominator, source evidence UI, filters, atomic bounded admission, persisted attempt quotas, leases and retry recovery. Details and validation: [citation measurement v2](../docs/citation-measurement.md). No paid APIs enabled. Live showcase remains open.
  - Reuse: [ai-search-guru/getcito](https://github.com/ai-search-guru/getcito-worlds-first-open-source-aio-aeo-or-geo-tool) (MIT) for the data model (prompts, answers, mentions, citations, share of voice).
  - Accept:
    - Prompts suggested in code from the site's title, headings and category, editable by the owner.
    - Existing engines: Groq gpt-oss with browser search; Gemini from memory. Optional existing Gemini grounding remains off by default. Google AI Overviews/AI Mode, ChatGPT, Perplexity and Claude show "not measured".
    - Mentions, verified citations and share of mentions against named competitors are computed in code. Mention and source order are not search rankings.
    - Atomic daily attempt caps, global spacing, bounded backlog and recoverable leases govern the shared free capacity. Weekly is a scheduling cadence, not a guaranteed completion time.
    - Existing limits: Launch Pack one snapshot of 10 prompts; Pro 10 prompts per site on the web engine; Plus 25 prompts per site on both engines. No pricing or allocation changes in this overhaul.
  - Verify: pytest with recorded answers; the showcase prompt set tracked twice.
- [ ] **P3.3 Sources and accuracy** (M): sources grouped by type (the user's site, competitors, Reddit, G2, Product Hunt, YouTube, Wikipedia, listicles) with "get listed here" actions; accuracy compares the answer's price and feature claims with the site's own pages (one free-chain call per answer, labelled).
- [ ] **P3.4 Weekly watch and deploy webhook (V12)** (M): watch, deploy hook and change email built 2026-09-25 (`app/watch.py`, `/watch`, `/hooks/deploy/{token}`, `tests/test_watch_compare.py`); still open: as in the v1.1 entry, plus tracking changes (a lost citation, a new competitor) in the same once-per-change email.
- [ ] **P3.5 AI traffic** (M): upload a server or Vercel log; count hits by AI crawler and status (reuse geo-optimizer-skill's `geo logs` bot list, MIT); optional GA4 Data API connect for visits referred by chatgpt.com, perplexity.ai, gemini.google.com and copilot.
- [ ] **P3.6 Citability rewrites** (S): for the 3 weakest pages by citability score, one free-chain call each, suggestions quoting the text they replace.
- [ ] **Checkpoint P3:** stable week-over-week tracking on the showcase; Plus opens with watch, tracking, MCP, competitor compare and branded PDF.

### Phase 4: Plus depth and paid engines (revenue-gated)
- [ ] **P4.1 Opt-in active scan of a staging URL** (Plus): [zaproxy/zaproxy](https://github.com/zaproxy/zaproxy) (Apache-2.0) in Docker on the worker; verified domain, an owner-entered staging URL, a signed confirmation per scan, one at a time. Never on production URLs.
- [x] **P4.2 Custom test users and several test users per report (V13).** Done 2026-09-25 by Claude Code (`app/plus.py`, Settings > Your test users, side panel multi-select, `TestUsersCompared` on every report of a set). Ideas from [neuhai/UXAgent](https://github.com/neuhai/UXAgent) (no licence: ideas only) and [m-naw/ux-explore](https://github.com/m-naw/ux-explore) (Apache-2.0).
- [x] **P4.3 Branded PDF for Plus.** Done 2026-09-25 by Claude Code (Settings > Branded PDF reports, `BrandCover`, print CSS; checked by rendering the PDF).
- [x] **P4.7 Team workspaces (team collaboration).** Done 2026-09-25 by Claude Code (cloud): `app/teams.py`, seven `team_*` tables with RLS and Realtime, pages under `/app/team`, `/join`, Share to workspace. Reference and UI brief: docs/team-collaboration.md.
  - [ ] UI polish pass by the local agent (docs/team-collaboration.md section 10).
  - [ ] Founder: apply the schema, keep Supabase "Confirm email" on, decide seats and viewer pricing (section 11).
  - [ ] Email notifications for mentions and assignments (Resend), after the sending domain exists.
  - [ ] Shared run quota for teams (billing decision first).
- [x] **P4.4 Fix pull request** (done 2026-09-25 by Claude Code: `app/github.py`, Settings > GitHub, report > Open a fix pull request; config-only changes; `tests/test_github.py`) through the GitHub App (Contents and Pull requests write, a separate opt-in); the owner approves each PR.
- [ ] **P4.5 Paid engines and Claude Haiku** (ChatGPT and Perplexity tracking; Haiku for journeys and reports) when payment.md's caps allow.
- [ ] **P4.6 Cloud runner (V14)**, only if A2 missed its gate.

## v1.1 plan (2026-09-24, kept for history; open items moved into v1.2 above)

### Session 1 (09-25 to 09-26)
- [x] **V1 Server-owned plans** (M), done 2026-09-24
  - Accept:
    - `app/plans.py` holds the plan limits from SPEC.md; table `entitlements`.
    - `POST /runs` ignores the client's `tier`.
    - A free user gets 403 on `logged_in`, 12 steps at most, first-time visitor only, and 402 after 3 runs this month.
    - An active `entitlements` row lifts the limits to its plan.
    - `GET /me/plan` returns plan, limits and runs left.
    - `FREE_RUNS_PER_DAY` stops free runs with a clear message.
    - `scripts/grant_plan.py EMAIL PLAN DAYS` grants a dev pass; `--revoke` expires it.
  - Verify: pytest per limit with crafted requests; the side panel and dashboard show runs left; the grant script switches the test account to Pro and back.
  - Files: `apps/api/app/plans.py` (new), `app/main.py`, `app/db.py`, `schema.sql`, `scripts/grant_plan.py` (new), side panel `App.tsx`.

### Session 2 (09-27 to 09-29)
- [x] **V2 GEO readiness scanner** (M), done 2026-09-24
  - Accept:
    - `app/scans/geo.py` scores the 7 categories in SPEC.md from pages the audit already fetched, plus `GET /llms.txt` and one citation-bot user-agent probe.
    - Findings use `kind="geo"`; `report.geo` has score, band and categories.
    - Free scans score the homepage only.
    - The first-impression block is labeled "What AI search sees".
    - llms.txt is labeled low impact; the probe is worded as a user-agent check.
  - Verify: pytest per category on fixture HTML (SPA shell, blocked OAI-SearchBot, valid and broken JSON-LD, missing H1); a live Instant Scan of the portfolio returns a score in 20 s or less.
  - Files: `app/scans/geo.py` (new), `app/agent/schema.py`, `app/agent/report.py`, `ReportView.tsx`, `tests/test_geo.py` (new).

### Session 2b (09-24, added after the portfolio loop run)
- [x] **V22 Goal intent and loop guards** (M), done 2026-09-24
  - `app/agent/goal.py`: one fast model call turns the typed goal into an intent and 1 to 4 checkpoints; unsafe or off-site goals get 422 before a run is used; an outage falls back to the typed goal.
  - The test user sees the checklist and where each step led; code ends the run when the last checkpoint is reached (by URL marker or the model's `progress`).
  - Guards: a third arrival at the same page ends the run as `looping` (Walkthru's limit, never a site finding); scroll position is part of the observation and of the stuck check; a click that changes nothing is recorded.
  - Report: the owner's Stop is never a problem step; the planner's intent is given to the report writer.
  - Side panel: goal suggestions read from the page's links; shows how the goal was understood.
  - `evals/fixtures/showcase` (:8103): strong GEO plus journey traps (circular stories, cookie banner, newsletter pop-up, dead button, new-tab and external links, content hidden until scrolled, Pay and Delete buttons).

### Session 3 (09-30 to 10-01)
- [x] **V3 GEO traps and Checkpoint B** (S), done 2026-09-24: 18/22 (82%), see docs/decisions.md
  - Accept:
    - The hard fixture gains 3 GEO traps in `traps.json`: robots.txt blocks OAI-SearchBot, a JavaScript-only pricing page, no Organization schema.
    - The scorer runs on today's code, and misses are fixed until recall is 80% or more.
  - Verify: scorer output recorded in `docs/decisions.md`.
- [x] **V16 Signup email check** (S), done 2026-09-24
  - Accept:
    - `app/scans/email.py` reads MX, SPF and DMARC over DNS-over-HTTPS (Cloudflare JSON endpoint, existing httpx client).
    - Free shows SPF and DMARC; paid shows all.
    - The journey error "email rate limit exceeded" maps to "Supabase's built-in mailer limit: set up your own SMTP".
  - Verify: pytest with recorded DNS answers; the Tripverse run's report shows the SMTP fix.
  - Files: `app/scans/email.py` (new), `app/agent/report.py`, `tests/test_email_check.py` (new).

#### Checkpoint B
- [x] Tests, lint and builds green; crafted free requests cannot exceed limits; recall 80% or more (82%); founder reviews one GEO report

### Session 4 (10-02 to 10-03)
- [x] **V4 Rerun and compare** (M), done 2026-09-24 as automatic comparison with the previous run of the same goal (no parent_run_id); live rerun on the hard fixture: 0 fixed, 0 new, 35 still broken
  - Accept:
    - New column `runs.parent_run_id`.
    - `rerun_of` on `/runs` and `/scans`, with owner and same origin checked.
    - `report.comparison` lists fixed, still broken and new by fingerprint (kind, normalized title, URL path), computed in code.
    - The report shows the three lists and a Rerun button.
  - Verify: pytest for fingerprint and diff; 3 fixture reruns match a hand check.
  - Files: `schema.sql`, `app/main.py`, `app/agent/report.py`, `ReportView.tsx`, `Report.tsx`.
- [x] **V17 Ignore a finding** (S), done 2026-09-24 (`finding_states` table needs applying: see CURRENT_STATE.md)
  - Accept:
    - Table `finding_states`. The owner marks a finding ignored, with a reason. Paid plans only.
    - Ignored items leave the fix prompt, the "new" and "still broken" lists and watch emails.
    - They stay in the Launch Ready score.
  - Verify: pytest; the report shows "ignored" with the reason.

### Session 5 (10-04 to 10-05)
- [x] **V5 GEO fix pack** (S), done 2026-09-24
  - Accept:
    - `app/scans/geo_fixes.py` returns a robots.txt block, JSON-LD (Organization, WebSite, SoftwareApplication), an llms.txt draft, and a rendering fix for the framework (Vite SPA, Next.js, Lovable, Astro).
    - Paid plans see all of it; free sees one fix.
    - Copy buttons.
  - Verify: pytest that the JSON-LD parses and the robots rules allow citation bots; the SPA fixture gets the Vite fix.
- [x] **V15 Agent fix prompt** (S), done 2026-09-24
  - Accept:
    - `app/agent/fix_prompt.py` builds `full` and `chat` prompts from a stored report and the fix pack, with no model call, skipping ignored findings.
    - `GET /runs/{id}/fix-prompt` returns 402 on free, text for paid owners, and `walkthru-fixes.md` with `download=1`.
    - Key values are masked.
    - It ends with the fingerprints a rerun should mark fixed.
    - Copy and Download buttons; on free it is locked and shows a count.
  - Verify: pytest that every finding appears once, no unmasked secret appears, and free gets 402. The chat style stays under 4,000 characters (Estimate: the Lovable and Bolt chat limit; confirm before shipping).

- [x] **Claude Haiku 4.5 for Pro and Plus, wired and off** (founder approved `anthropic[vertex]` on 2026-09-24): turns on with `CLAUDE_VERTEX_PROJECT`; free chain behind it; free plans never reach it.

- [x] **Fix-loop gaps found by the founder's showcase test (2026-09-24), fixed the same day:** reports keep every affected page per finding (`report.pages`); the fix prompt lists them all; the comparison reports pages fixed, new and not re-checked, and a finding whose pages were not audited again is "not re-checked", never "fixed".
  - The fix prompt lists at most 3 pages per finding (evidence is cut to 3), so an agent following it exactly cannot finish. List every affected page in the prompt.
  - The comparison matches by title only: "Few section headings" showed as still broken although all three listed pages were fixed, because a different page (welcome.html) now had it. Compare page by page and say "fixed on 3 pages, new on welcome.html".
  - Crawl limits can make a finding look fixed (a new link pushed changelog.html out of the 10-page crawl). V6 raises paid crawls to 50 pages; the comparison should mention pages not re-audited.

### Session 6 (10-06 to 10-08)
- [ ] Founder: Google Cloud project with billing prepaid by UPI (Rs 500 to 1,000); enable Vertex AI and Claude Haiku 4.5 in Model Garden; create a service account key; set `CLAUDE_VERTEX_PROJECT` and `GOOGLE_APPLICATION_CREDENTIALS`.
- [ ] Measured comparison, about $1 to $2: Claude Haiku 4.5 against the free chain on the same hard and showcase journeys (trap recall, false dones, speed, cost). Decide what the pricing page may claim.
- [ ] **V11 Production and store** (M), moved: V11a (session 20) and V11b (session 25) in v1.2
  - Accept:
    - Domain and HTTPS.
    - Vercel with SPA rewrites.
    - API on the VM under process supervision, with `CHECKPOINTER=postgres`.
    - [x] Global `FREE_SCANS_PER_DAY` cap (done 2026-09-24, counted from `runs` rows, so shared across processes).
    - One API process on the VM, so the in-memory per-address scan limit holds; a Postgres-backed one only if the API ever runs several processes.
    - Production CORS and extension origin.
    - Secrets rotated.
    - Error logging and a health check.
    - Store listing submitted on 10-08.
  - Verify: a clean Chrome profile runs the production build end to end.

### Session 7 (10-09 to 10-10)
- [x] **V8 Launch Ready score, badge and share loop** (S), done 2026-09-24: badge for every shared report (no opt-in table); keyed by report id, follows the latest shared report of that site
  - Accept:
    - The score counts measured areas only: UX 30, security 20, GEO 20, SEO 15, speed and accessibility 15. An unmeasured area's weight is shared among the others.
    - `GET /badge/{site_id}.svg` shows the latest score, cached one hour, only when the owner turned it on. It links to the public report.
    - Public report meta carries the score.
  - Verify: pytest for the weighting; the badge renders and updates after a rerun.
- [x] **V6 50-page paid audit** (S), done 2026-09-24 (moved up from session 7; paid run reports were already background tasks)
  - Accept: paid scans use 50 pages and a 60 s budget in a background task; Instant Scan stays at 10 pages and 20 s; coverage shows what was checked.
  - Verify: pytest with a fake 60-page site.

### Session 8 (10-11 to 10-13)
- [ ] **V10 Billing with Dodo** (M), moved to v1.2 session 24. Code built 2026-09-25 with 35 tests (docs/billing.md); open until a real test-mode payment passes with the founder's keys.
  - Accept, all per payment.md:
    - Access request.
    - Founder approval creates an offer.
    - A one-use private Dodo checkout (test mode).
    - A signed, idempotent `POST /webhooks/dodo` inserts the `entitlements` row.
    - Refunds suspend the pass.
  - Verify: a test-mode payment grants exactly one pass; duplicate, forged and out-of-order webhooks change nothing; a checkout redirect without a webhook grants nothing.

#### Checkpoint C
- [ ] Rerun, fix prompt, fix pack, badge and test-mode billing verified; founder reviews one full Pro report

### Session 9 (10-14 to 10-15)
- [ ] **V7 Evidence and PDF close-out (T18 to T21)** (S), moved to v1.2 session 26
  - Accept: a fresh screenshot-backed fixture run; private, public and printed PDF views all show step evidence.
- [x] **V18 Signup funnel numbers** (S), moved to P0.2 and done there 2026-09-25
  - Accept: `report.funnel` on paid runs holds steps to the goal, fields typed, errors seen, safe stops and time to the first useful screen; compared across reruns.
  - Verify: pytest over stored steps.
- [ ] **V19 Landing copy review** (S), moved to P0.3 (now screenshot-based)
  - Accept: one free-chain model call on homepage and pricing text; verdicts and up to 3 rewrite options, labeled as suggestions; paid runs only.
  - Verify: pytest with a fake model.

### Session 10 (10-16 to 10-18)
- [ ] **V9 Landing, pricing and onboarding copy** (S), moved to v1.2 session 26
  - Accept: the "launch check for apps built with AI" hero; the SPEC.md plans table; Plus as a waitlist; onboarding for install, permissions and domain verification.
  - Verify: web build and lint; phone and desktop check.
- [ ] Switch Dodo to live once verification clears

#### Checkpoint D (launch gate)
- [ ] Stranger path in production: scan, install, run, report, share, paid pass
- [ ] Launch Tue 2026-10-20, 2026-10-27 at the latest

### Session 11 (10-21 to 11-01)
- [ ] Fix what real users hit in launch week
- [x] **V12 Weekly watch and deploy webhook** (M), moved to P3.4; built 2026-09-25 (`app/watch.py`, `sites` table, `/hooks/deploy/{token}`)
  - Accept: `sites` table; a weekly job scans due sites and emails only on change; `POST /hooks/deploy/{token}` at most once per 10 minutes.
  - Verify: a blocked AI crawler on the fixture sends exactly one email; an unchanged week sends none.

### Session 12 (11-02 to 11-08)
- [x] **V20 Walkthru MCP server** (M), done 2026-09-25: verified live with the official MCP client (all five tools, revoked key refused)
  - Accept:
    - A remote MCP server at `/mcp` (streamable HTTP, official `mcp` Python SDK).
    - Personal API keys in `api_keys`: shown once, stored as SHA-256, revocable. Plus only.
    - Tools: `scan_site`, `get_report`, `get_fix_prompt`, `rerun`, `list_runs`.
    - The same limits as the web API.
  - Verify: Claude Code connects with a Plus key, scans the fixture, reads the fix prompt and reruns; a revoked or non-Plus key is refused.

### Session 13 (11-09 to 11-15)
- [x] **V21 Competitor side by side** (M), done under P0.4 on 2026-09-25
  - Accept: `POST /compare` with up to 3 URLs; passive scans only, no deep security on unverified sites; side-by-side report.
  - Verify: pytest and one live comparison.
- [x] Branded PDF for Plus (your logo, no Walkthru branding), moved to P4.3, done 2026-09-25
- [ ] Open Plus to the waitlist

### Session 14 (11-16 to 11-22)
- [x] **V13 Custom test users and several test users per report** (M, Plus), moved to P4.2, done 2026-09-25

### Session 15 (late November, conditional)
- [ ] **V14 Cloud runner** (moved to P4.6), only if A2 missed its gate: headless Chrome on the VM drives the built `inject.js` over CDP; public pages only, one run at a time, same safety code.

### Next versions (not scheduled)
- [ ] Preview-deploy check (GitHub Action with a PR comment)
- [ ] Findings to GitHub Issues or Linear
- [x] AI citation tracking add-on, now P3.2 on free engines (implementation complete; live showcase validation remains open above)
- [ ] Self-serve checkout after payment.md's V2 gate

## v1 history

## Founder tasks
- [ ] Accounts: ~~Supabase~~, ~~LangSmith~~, ~~Gemini key~~, ~~Groq key~~, Google PageSpeed Insights API key, Anthropic (deferred, free providers for now), Dodo (test mode), Resend, Vercel
- [ ] Chrome Web Store developer account ($5 one-time)
- [ ] Check Dodo payout KYC (fallback Lemon Squeezy / Polar)
- [ ] Oracle Cloud Always Free VM (fallback $5 VPS)
- [ ] 20 community sites lined up for week-3 beta

## Week 1 (Sep 21–27): prove the loop
- [x] T1 Monorepo scaffold
- [x] T1b Landing page (final: Silver base + borrowed sections, see DESIGN.md)
- [x] T1c Login page UI (Supabase: Google, GitHub, magic link). Needs Supabase keys to go live.
- [x] T2 Fixture sites with seeded UX/SEO/security traps (M)
  - Done 2026-09-18: `evals/fixtures/{easy,hard}`, 18 traps in `evals/traps.json`, `python evals/serve.py` (easy :8101, hard :8102), `tests/test_fixtures.py` proves every trap.
- [x] T3 Extension skeleton: side panel + content script snapshot (numbered elements, text, errors) + redaction (M)
  - Done 2026-09-18: `apps/extension` (WXT, React 19). `lib/snapshot.ts`, `lib/redact.ts`, side panel UI. 7 vitest. Manual load unpacked pending (founder's Chrome).
- [x] T4 Action executor + safe-mode filter + same-origin/step caps (S)
  - Done 2026-09-18: `lib/execute.ts` (click/type/scroll/back, dry run, safe mode), `sidepanel/run.ts` loop (per-site permission, same-origin stop, 4 min cap, confirm before submit on logged-in pages). Manual run on fixture pending.
- [x] T5 Server step API + `persona_session` graph with interrupt/resume + Postgres checkpointer + interrupted-run stop/report recovery (M)
  - Done 2026-09-18: `apps/api/app/agent/`, `/runs` routes, 9 pytest with fake model. Postgres saver and a real Groq model were verified against the signup flow; LangSmith tracing is configured.
- [x] Checkpoint A: extension completes the easy fixture flow end to end (passed; see CURRENT_STATE.md)

## Week 2 (Sep 28–Oct 4): report + scans
- [x] T6 `first_impression` + `synthesize` + report JSON (M)
  - Done 2026-09-18: `app/agent/report.py` graph (first_impression, seo_scan, security_scan in parallel, then synthesize), `Report` schema, saved to `runs.report`, tokens logged.
- [x] T7 `seo_scan` (plain checks + PSI API + LLM content review) (M)
  - Done 2026-09-18: `app/scans/seo.py` (title, description, h1, canonical, viewport, lang, noindex, alt, OG, robots, sitemap; PageSpeed when key set). Content review lives in first_impression.
- [x] T8 `security_scan` (headers, TLS, cookies, exposed files, JS secret patterns) + domain verification (M)
  - Done 2026-09-18: `app/scans/security.py`; exposed files and bundle secrets only on verified domains (meta tag or /.well-known/walkthru.txt; `GET /verification`). SSRF guard in `scans/fetch.py`.
- [ ] T9 Eval runner: % traps found, $ per run, free vs paid model → docs/decisions.md (S)
  - [x] Session 8A: deterministic seeded-trap scorer, per-kind recall, token-price cost calculation, JSON/Markdown output, optional LangSmith experiment upload
  - [ ] Session 8B: capture real hard-fixture reports from the free and paid models, compare against the quality/cost gates, record the model decision in `docs/decisions.md`
  - Verify: `cd apps/api && .venv/Scripts/python -m pytest -q && .venv/Scripts/ruff check .`
  - Gate: at least 80% of all seeded traps found, free run at most $0.02, paid run at most $0.20
- [x] Checkpoint B: ≥ 80% traps found; cost measured (82% recall and measured tokens per run, 2026-09-24, docs/decisions.md)

## Week 3 (Oct 5–11): product surface
- [x] T10 Supabase schema + RLS + auth (web + extension token handoff) (M)
  - Done 2026-09-18: `apps/api/schema.sql` (runs + RLS), `app/auth.py` (bearer check via Supabase Auth), `app/db.py`; web `lib/auth.ts`, `RequireAuth`; extension gets the session from the dashboard (externally_connectable) and refreshes it.
- [x] T11 Dashboard: sites, runs, Instant Scan (no install) (M)
  - 2026-09-18: `/app` lists runs and scans, Instant Scan form, connect-extension button. Sites list deferred (runs are keyed by site already).
- [x] T12 Report page + share link + CSV/Sheet export + email (M)
  - 2026-09-18: `ReportView` (summary, first impression, top fixes, findings, think-aloud), `/r/:id` public page, Share (public link), Export CSV (Sheets via File > Import), Email me (Resend when key set).
- [ ] T13 Chrome Web Store submission (review can take days) (S)
- [ ] Checkpoint C: 20 community sites tested, feedback collected

## Week 4 (Oct 12–18): money + launch
- [x] T14 Plans + credits + Dodo checkout + webhook + limits (M): plans and limits 2026-09-24 (V1), Dodo 2026-09-25 (V10, docs/billing.md). The credit ledger stays open under Billing below.
- [ ] T15 Deploy (Vercel + VM), rate limits, error logging (M)
- [ ] T16 Landing page wired to real signup, pricing, demo report (S)
- [ ] Checkpoint D: stranger installs → tests → pays, in production
- [ ] Launch Tue Oct 20

## Competitive quality roadmap

- [x] T17A Opt-in TypeSafe Jev decision adapter with confidence and LLM fallback
  - [x] Request construction and response mapping tests
  - [x] Deterministic test identity for known form fields
  - [x] Provider/confidence metadata saved per step
  - [x] Default LLM behavior unchanged unless explicitly enabled
- [ ] T17B Real easy/hard browser benchmark and final provider decision
- [ ] T18 Step evidence contract: timestamps, execution result, transition, screenshot reference
  - [x] API/extension contract, run-scoped path validation and backward-compatible report types
  - [x] Define and automate evidence retention (30 days, `app/retention.py`); real stored-run verification is the founder's fresh extension run
- [ ] T19 Bounded screenshot capture and private storage
  - [x] Eight-frame cap, meaningful-action capture policy, private JWT upload, field masking and disclosure
  - [ ] Apply the `run-evidence` bucket policy in Supabase and complete public plus logged-in manual checks
- [ ] T20 Interactive three-pane evidence timeline
  - [x] Responsive step list, evidence viewer, inspector, loading/unavailable/legacy states and keyboard-operable controls
  - [ ] Link normalized findings to exact journey steps and complete desktop/phone visual QA with stored evidence
- [ ] T21 Screenshot filmstrip replay and shareable PDF
  - [x] Play, pause, previous, next and canonical print action
  - [ ] Render and visually inspect a multi-page PDF with real evidence
- [ ] T22 Optional continuous video only after filmstrip validation
- [x] T23 Accessibility and performance evidence
  - [x] Static HTML accessibility checks for language, heading order, image alternatives and control names
  - [x] PageSpeed-backed mobile performance findings with an explicit unavailable state
  - [x] Accessibility and performance cards in private, public and PDF reports
  - [x] Add browser-level axe and Web Vitals evidence tied to exact journey steps
- [x] T24 Bounded full-site SEO and verified passive-security aggregation (closed 2026-09-23)
  - [x] Backend bounded crawler, robots and same-origin rules, redirect SSRF validation, root-cause aggregation and report contract (`eefd34a`, local branch `1`)
  - [x] API regression suite: 71 pytest pass and Ruff clean
  - [x] Restore npm dependencies after the interrupted pnpm attempt (lockfile unchanged, generated leftovers removed)
  - [x] Crawl-coverage UI in private, public and print/PDF reports; no overflow at 320, 768, 1024, 1440 px
  - [x] Report contract test asserts `site_audit`; legacy reports render because the section is conditional; unverified audits asserted never to request exposed-file paths
  - [x] Passive smoke on python.org: 3 pages in 1.4 s, truncation reported, repeated issues aggregated with page counts
  - [x] Instant Scan of the easy fixture through the real form: public report shows 4 audited pages and aggregated findings; docs updated, both commits pushed
- [ ] T25 Rerun comparison, multi-persona synthesis, schedules, then integrations (rerun comparison done in V4 and schedules in V12; multi-persona is P4.2; integrations open)

### Competitive quality checkpoints

- [ ] Decision checkpoint: Jev hybrid clears the quality gate or is rejected with evidence
- [ ] Evidence checkpoint: every meaningful step has reproducible visual proof
- [ ] Experience checkpoint: timeline, replay, and PDF pass browser/PDF review
- [ ] Launch-readiness checkpoint: UX, accessibility, SEO, performance, and passive security share one prioritized report

## Project completion checklist

### Evidence and privacy

- [ ] Run a fresh screenshot-backed easy fixture journey with axe and Web Vitals
- [ ] Verify private evidence, public sharing and a multi-page PDF in a real browser
- [ ] Link report findings to exact journey steps where evidence exists
- [x] Define and automate screenshot retention and cleanup (2026-09-23)
- [x] Add user data export and deletion for runs, reports and evidence (2026-09-23)

### Store and legal

- [x] Replace placeholder Privacy, Terms and Security links with real pages (2026-09-24; legal review still open)
- [x] Document screenshot collection, masking, retention, subprocessors and deletion (Privacy page)
- [ ] Audit Chrome permissions and production `externally_connectable` origins
- [ ] Produce store listing, screenshots, support contact and submit T13
- [ ] Enable and verify Google and GitHub OAuth production redirects

### Billing

- [ ] Founder approves final pricing and included credits
- [x] Implement Dodo checkout and signed, idempotent webhook handling (2026-09-25, `app/billing.py`)
- [ ] Implement credit ledger, run reservation, consumption and refund rules
- [x] Test duplicate/delayed webhook, failed checkout and refund paths (automated, 35 tests; a live test-mode payment closes V10)

### Production

- [ ] Buy/configure production domain and HTTPS
- [ ] Deploy web with SPA rewrites and API with process supervision
- [ ] Configure production CORS, extension id, Supabase redirects, Resend and PageSpeed
- [x] Replace per-process scan limiting with a shared production limiter (SD-2.1, Claude Code; shared counter applied 2026-09-27)
- [x] Add structured error logging and request references (SD-8.1, Codex 2026-09-28); existing `/health` retained
- [ ] Add dependency readiness checks and uptime alerts (SD-6.7, SD-8.3)
- [ ] Document database backup, restore and migration procedures
- [ ] Split web and extension bundles if the 500 kB warnings remain
- [ ] Rotate development credentials before launch

### Launch validation

- [x] Replace placeholder screenshots with current product captures (2026-09-27: four real report crops; hero is the animated HeroDemo; hero-product and extension-panel placeholders are unused)
- [ ] Publish one representative public demo report
- [ ] Add extension install, permission, safe-mode and verification onboarding
- [ ] Test 20 community sites and triage failures
- [ ] Confirm privacy-minimized analytics contain no DOM, credentials or evidence
- [ ] Complete stranger install to test to report to share to payment checkpoint

### Deferred until founder resumes

- [ ] T17B Jev/Groq/Gemini benchmark and provider decision
- [ ] T22 continuous video research
- [ ] Safe single-click browser-session resume
- [ ] T25 rerun comparison, multi-persona synthesis, schedules and integrations
