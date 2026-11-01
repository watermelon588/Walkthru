# Walkthru feature audit, 27 October 2026

## Verdict

**The local automated checks are green, but the application is not verified end to end and several report-quality defects remain.** Passing existing tests does not establish that every advertised feature is working correctly. In particular, readiness scores can contradict the report's evidence-backed outcome.

**31 October follow-up:** F1-F3 scoring, public-config and cookie-purpose corrections are complete for new calculations/reports. F4 removes blocking preview font imports; F5 adds bounded database/queue readiness at `/ready`; F6 patches the web dependency tree, with fresh full/omit-dev npm audits reporting zero vulnerabilities. [Consolidated F1-F6 fix record and verification scope](prelaunch-fixes-2026-10-31.md). Existing saved reports are not automatically regenerated. Integration/deployed acceptance gaps remain open. The original audit evidence and counts below describe the 27 October checkout.

Audited checkout: `2725be45d624d7a9a5854abb37cb833d44704da1`, initially clean. The audit began with the 26 October request and completed on 27 October. No application source, dependencies, migrations, pricing, cloud resources or live accounts were changed. New files are this report, the state update and ignored local QA artifacts.

## Checks and boundaries

| Check | Current result | What it proves |
| --- | --- | --- |
| Full API suite | **1,185 passed, 19 skipped**, one dependency deprecation warning | Offline contracts and disposable local PostgreSQL tests across 84 test modules |
| API Ruff | Passed | Current configured lint rules |
| Web tests | **52 passed** | Report/CSV contracts, history pagination, auth and session fencing, plan cache and related pure/client logic |
| Web lint, TypeScript, production build | Passed | Buildable current frontend; bundle-size and ineffective-dynamic-import warnings remain |
| Extension tests | **177 passed, one opt-in skip** | Snapshot, privacy, browser action, retry, navigation, assertion, suite and handoff logic |
| Extension lint, TypeScript, WXT production build | Passed | Buildable current MV3 package; not an installed-browser acceptance result |
| Rendered frontend | **47/47 checks passed** in the final controlled-boundary pass, zero page errors and zero unconfigured fixture endpoints | Actual React pages with synthetic session/Supabase/API boundaries; no live authentication or data persistence |
| PDF artifact | Eight pages, 8,682 extracted text characters; scope and authority chapter present | The synthetic report renders to a parseable PDF; not every branded/permission/error case |
| npm dependency audit | Web: **two high-severity package findings**; extension: zero reported with `--omit=dev` | Registry advisory matches, not demonstrated exploits or a full supply-chain audit |

API tests used a socket guard allowing loopback only, dummy Supabase/DB settings, tracing off and optional provider/reservation flags off. PostgreSQL fixtures were disposable local clusters. No model requests, SMTP deliveries, real checkout, live target scans or cloud operations were performed. Browser requests to external services were blocked or fulfilled with synthetic data; Google Fonts CSS was replaced by an empty local response in the final render pass.

All 19 API skips are in `tests/test_teams_live.py`: the local Postgres-plus-PostgREST fixture requirements were unavailable. Other local PostgreSQL suites ran. The extension's native side-panel opt-in case was not enabled. No missing dependency was installed to turn a skip into a pass.

Browser coverage includes 15 public/error/preview paths, nine anonymous protected-route redirects, ten synthetic signed-in page renders, six 390-pixel mobile overflow checks, magic-link submission and OAuth-error recovery UI, and four Free-plan gates. The additional preview-route observation completes the 47 checks. Desktop and mobile dashboard/report screenshots were visually inspected. This was isolated headless Edge using the installed Playwright runtime, not the founder's signed-in Chrome profile. The first pass was 46/47 and the font-blocking failure was reproduced before the final font-response-controlled pass; both failing logs are retained.

Ignored evidence directory: `evals/results/feature-audit-20261026/`. It contains test/build/lint logs, `api-junit.xml`, `suite-summary.json`, route/configuration-presence inventory, browser harness/results/screenshots, PDF and offline counterexamples. Configuration evidence records booleans only, never secret values.

## Confirmed findings

### F1. High: scores claim success without confirmed completion

Sources: [score.py](../apps/api/app/agent/score.py), [report.py](../apps/api/app/agent/report.py), [report_contract.py](../apps/api/app/agent/report_contract.py).

The version 2 assessment correctly labels a `safe_stop` run as `blocked`. However, `JOURNEY` gives that status UX 100 and `REACHED` includes `safe_stop`. With no recorded steps or confirmed checkpoints, the current scoring functions return:

- Launch Ready: **100**, UX **100**.
- Agent readiness: **100**, including "The test user reached the goal" and "An agent following the same path can finish the task."
- The same report assessment: **blocked**, with no completion proof.

For a `budget` stop with the same absence of evidence, both scores are **50** and the note says an agent would likely stop at the same point. Reaching Walkthru's own cap is not evidence of a site failure. Scores are generated after the assessment, so this is a real disagreement between current production code paths, not a hypothetical missing future contract.

**Required change:** use the assessment and confirmed checkpoints as scoring evidence. Safety stops should not imply successful completion, and internal caps/loss should not establish site failure. Add regression tests for blocked, unconfirmed and unsupported legacy states; preserve genuine observed site failures. Existing tests passing did not catch this contradiction.

Reproduction: ignored `probes.py` and `probes.json`, keys `score_without_goal_proof_safe_stop` and `score_without_goal_proof_budget`.

**Resolution, 31 October:** readiness now requires a supported assessment, matching run status and checkpoint text tied to executed-step evidence on the same URL. Unproved terminal labels leave journey components unmeasured, while real earlier browser-observed UX issues remain scored after an interruption. Rerun stability requires both runs' proven completion and validated action counts. Regression tests cover the original contradiction, legacy/invalid reports, interruptions, static-score preservation and malformed milestone evidence. Historical stored score fields still require report regeneration or a new run; no database rewrite is included.

Verification: **125 focused tests passed; full offline API suite 1,213 passed, 19 existing PostgREST-dependent skips; whole API Ruff passed.** The 28 new regression cases include failures observed before their fixes. Evidence is under ignored `evals/results/f1-fix-20261031/` (`api-verified.log`, `api-verified-junit.xml`). No external provider/model call or cloud operation was used.

### F2. Medium: normal Supabase public configuration reduces security score

Source: [backend.py](../apps/api/app/scans/backend.py), `check`, with [score.py](../apps/api/app/agent/score.py).

An inline synthetic Supabase URL plus a publishable key, with `verified=False` and no database requests, yields a low security finding: "Your site reads Supabase straight from the browser." Its own explanation says this is normal. A report with only this signal changes its security score from **100 to 97**.

**Required change:** keep public configuration discovery informational and unscored. Reserve scored findings for exposed secrets or evidenced authorization/configuration failures. Preserve verified-domain restrictions on read-only probes.

Reproduction: `probes.json`, `normal_public_config_penalty`.

**Resolution, 31 October:** normal anon/publishable configuration no longer produces a security finding, fix task or score penalty. Discovery remains in `report.stack.backend` and `report.stack.evidence.backend`, including bundle-only configuration and independent stack-detector failure. The context retains only the public project URL and a fixed explanation, never key values; actual backend findings still get project-specific fix checks. Secret/service-role key findings and verified-owner probe restrictions remain in place. This follows [Supabase's key guidance](https://supabase.com/docs/guides/getting-started/api-keys). Source changes invalidate old Instant Scan cache entries, but existing saved reports require a new scan or regeneration.

Verification: **128 focused tests passed; full offline API suite 1,230 passed, 19 existing PostgREST-dependent skips; whole API Ruff passed.** Seventeen new regression cases cover public/privileged key forms, inline/bundle sources, scoring, context propagation and project-specific repair instructions. RED evidence and full-suite results are recorded under ignored `evals/results/f2-fix-20261031/` (`api-full.log`, `api-junit.xml`) and in CURRENT_STATE.md. No live backend was probed.

### F3. Medium: non-session cookies receive session-cookie remediation

Source: [security.py](../apps/api/app/scans/security.py), `_cookie`.

Synthetic `_ga=GA1.1.1234.5678; Path=/; Secure; SameSite=Lax` produces a **medium** "missing HttpOnly" finding, recommending HttpOnly on session cookies even though this cookie is an analytics identifier. The generic checker does not distinguish an authentication cookie from a cookie intentionally accessible to browser scripts.

**Required change:** make cookie purpose and uncertainty explicit; avoid prescribing HttpOnly or session-level severity solely from the existence of an analytics cookie. Keep prefix, transport and actual authentication-cookie checks.

Reproduction: `probes.json`, `analytics_cookie_warning`.

**Resolution, 31 October:** the scanner no longer infers a missing-HttpOnly defect from an analytics/client/unknown cookie alone. Session-like names still trigger a conditional warning with explicit uncertainty about purpose and JavaScript access. Other missing transport/SameSite attributes retain lower-severity advice; SameSite=None without Secure and browser-prefix constraints remain separate medium-severity checks. Cookie values are masked in new evidence. The shared cookie recipe now uses the finding-specific fix instead of adding generic session, Next.js or Supabase-auth snippets. [Implementation, tests and interpretation limits](prelaunch-fixes-2026-10-31.md#f3-cookie-purpose-and-attribute-checks-are-separate).

Verification: **162 focused tests passed; full offline API suite 1,267 passed, 19 existing PostgREST-dependent skips; whole API Ruff passed**, including the existing hard/easy fixtures and security-parity checks. Thirty-seven new cases cover purpose, severity, generated prompts across stacks, attributes, prefixes and value redaction. The final full-suite exit was 0 in 576.23 seconds, with one existing dependency deprecation warning. Ignored evidence: `evals/results/f3-fix-20261031/` (`api-full.log`, `api-junit.xml`). No live cookie or account was inspected or changed.

### F4. Medium, preview-only: blocked external font CSS can blank `/variants`

Sources: [Variants.tsx](../apps/web/src/variants/Variants.tsx) and `apps/web/src/variants/{fresh,darkroom,markup}.css`.

The initial browser pass produced a blank `/variants` page and `Unable to preload CSS ... FreshEyes-4pj8IpRn.css` when external requests were blocked. The referenced local asset exists. Reproduction with direct filesystem-backed local asset responses failed again. The local CSS imports `fonts.googleapis.com`; blocking that import makes the stylesheet preload fail and the nested lazy preview has no recovery boundary.

The final browser pass supplies an empty successful Google Fonts stylesheet response, allowing the existing bundled/local fallback fonts. This tests the distinction between a valid fallback font response and a failed external stylesheet dependency; it does not fix the application.

**Required change:** make preview rendering resilient to an unavailable third-party font stylesheet, or deliberately exclude the preview routes from a release. This is a preview-route availability issue, not evidence that normal dashboard pages have failed or that customer data is exposed.

Evidence: `browser-first-pass.json`, `browser-recheck.log`, compiled CSS and the final browser result. `/agent-lab` and `/variants` are both included in the production frontend's route table; decide explicitly whether they belong in the public release.

**Resolution, 31 October:** removed Google Fonts imports from all three variant stylesheets, using existing bundled/system fallbacks. Isolated Edge reproduced blank content in all three original variants with external fonts blocked; all three now render at desktop/mobile with their route loader dismissed, zero page errors and zero Google Fonts requests. Three new source regressions; all 55 web tests, lint, TypeScript and build pass. Existing build warnings remain. Release policy for developer previews is separate. Evidence: `evals/results/f4-f5-fix-20261031/`.

### F5. Operational limitation: `/health` is not database readiness

Source: [main.py](../apps/api/app/main.py), `health`.

Replacing `db.oldest_waiting_job` with a synthetic database exception still returns `{"status":"ok"}`. This matches the current code's liveness/queue design, but cannot verify that authenticated reads, checkpoints or reports can access the database.

**Required launch check:** use a separate readiness signal or an authenticated DB/queue/checkpoint drill. Do not treat a green `/health` as proof the whole backend works. This is a documented monitoring gap, not a reproduced authentication bypass.

**Resolution, 31 October:** added `/ready` for bounded server Data API reads of runs and overdue queued jobs. It returns uncached generic 503 on dependency errors or stalls, without leaking job details or writing rate counters. Existing `/health` behavior is preserved. Sixteen new cases; 37 affected API checks and whole API Ruff pass. Readiness excludes provider operation, user-specific RLS, checkpoint writes and worker throughput; those acceptance drills remain required. Full API suite not rerun for this requested quick pass. [Contract and limits](prelaunch-fixes-2026-10-31.md#f5-database-readiness-is-separate-from-health).

### F6. Web toolchain has unresolved high-severity advisories

Current `npm audit --omit=dev --json` identifies:

- `source-map-js`, high: indexed source-map section offsets can cause event-loop denial of service; affected range `>=1.0.0 <1.2.2`. [Advisory](https://github.com/advisories/GHSA-68fv-2mgg-jv7q).
- `vite`, high: installed 8.3.0 matches multiple advisories affecting 8.3.0 through 8.3.2, including Windows editor command handling and development-server file/middleware issues. [Example advisory](https://github.com/advisories/GHSA-698v-4r3x-3vcv).

Although the command omits development dependencies, the dependency graph includes build-tool packages through runtime-declared tooling. Their presence does not mean a deployed static bundle exposes a Vite development server. Review and patch the toolchain and lockfile in a controlled change, then rerun checks. No dependency updates or automatic `npm audit fix` were performed. The API dependency vulnerability scan was not run because `pip-audit` was not installed; Ruff/pytest are not substitutes for that scan.

**Resolution, 31 October:** updated Vite 8.3.0 to 8.3.5 and source-map-js 1.2.1 to 1.2.2, with compatible transitive toolchain updates. No new direct dependency or major override. Clean installation succeeds; fresh full and omit-dev npm audits both report **zero vulnerabilities**. All 55 web tests, lint, TypeScript/build, Vite dev-server smoke and landing/login/three-variant desktop/mobile production-browser smoke pass. Build warnings remain. API/extension suites and the separate API dependency audit were not rerun/performed for this web-only dependency correction. [Versions, evidence and limits](prelaunch-fixes-2026-10-31.md#f6-patched-web-toolchain-and-reproducible-lockfile).

## Feature-by-feature status

"Offline pass" below refers to fresh tests against the current code, not a live-provider or deployed acceptance claim.

| Feature area | Verified now | Remaining condition or issue |
| --- | --- | --- |
| Landing, docs, pricing, privacy, security, bot page, 404 | Production render and mobile checks; router/build pass | Content/legal/founder policy review is separate; no production SEO measurement |
| Sign-in, session, account switching, logout | API auth and web/extension fencing tests; anonymous guards; synthetic magic-link success and OAuth-error UI | Actual mail receipt and real Google/GitHub callbacks not exercised |
| Dashboard and run history | Web history/keyset pagination/cache tests, API owner-history tests, synthetic dashboard/mobile rendering | Live Supabase latency and installed-account repetition not measured |
| Instant Scan and crawls | Scan, fetch pinning, robots, soft-file/soft-404, reuse/coalescing and bounded crawl tests | No live scan; no blanket claim of CWV or all-site coverage |
| Extension connection and browser execution | 177 tests plus type/lint/build; handoff, stale target rejection, waits/scrolls, retries, redaction and safety covered | Actual installed Chrome permission prompts, side panel and website-to-extension round trip still need acceptance |
| Agent goal completion and decisions | Completion/action gate/persona/navigation tests pass; F1 scoring corrected 31 October | Older saved scores require regeneration; live model quality not measured |
| Count assertions and reruns | Assertion/recheck/compare tests; missing or changed coverage stays distinct | Actual owner dataset and installed-browser rerun not exercised |
| Saved suites | Suite validation, serial state/outcome/recovery/account-fencing tests | Whole suite in an installed Chrome profile not run |
| Report chapters, fix prompts and CSV | Contract/parity/grounding/version tests; actual report rendering; F1-F3 scoring/classification/cookie fixes completed 31 October | Older reports not regenerated; no new model-written report evaluated |
| Screenshots, regions, replay and PDF | Evidence/region tests, actual report UI and synthetic PDF inspection | Real storage upload/signed URL/expiry and every branded export variant not verified |
| SEO foundations | Deterministic scanner and depth suites pass | PageSpeed key absent; keyword demand/rank/volume and Search Console connection not measured |
| Keyword/content recommendations | Opportunity and advisory chapter tests pass | Page-derived hypotheses, not measured keyword research |
| GEO and authority/backlinks | Deterministic GEO/fix-pack and 12-tactic advisory contracts pass | Link index, outreach, acquired links and guaranteed AI ranking are not features verified here |
| AI citations/mentions | Parsing, evidence, quota, queue and related local SQL tests pass; synthetic tracked-sites UI | No fresh live engine/source-URL/claim-accuracy check; previous source-capture gaps remain unverified |
| Security, email DNS and backend exposure | Security parity/backend/DNS fixtures and ownership gates pass; F2 public-config and F3 cookie-purpose corrections 31 October | Cookie purpose remains heuristic; no live target probes or actual inbox-delivery check |
| Plans, usage quotes and work admission | Plan, quote, reservation/admission and SQL tests pass; synthetic billing/usage UI | Receipt/reservation/admission migrations and paid candidates remain optional/inactive in the documented deployment; no billing activation performed |
| Payments and paid access | 37 billing tests pass with fakes | Dodo key absent locally; no actual checkout, charge, webhook delivery or refund tested |
| MCP and API keys | Protocol/tool/auth/plan-gating tests and synthetic MCP/free-gate UI | Real editor connection and issued/revoked live key not exercised |
| Weekly watch and deploy hooks | Watch/compare/job/retention/notification contracts pass; synthetic watch/free-gate UI | No hosted scheduler/restart, real deploy webhook or notification email delivery |
| Custom personas and branding | Plus/plan/profile/branding contracts, settings rendering | No live save or fully inspected branded PDF round trip |
| Team collaboration | Team policy/API unit tests and synthetic team shell | **19 real PostgREST integration tests skipped**; live invitations, shared reports, chat/realtime and cross-account RLS not reverified |
| GitHub fix PRs | GitHub request/auth/path/change-preview contract tests; configuration presence checked | No actual installation, repository write or PR creation; no external messages sent |
| Feedback, access requests and founder operations | API/admin/request tests, feedback and billing shell rendering | No real inbox, authenticator/password interaction or live access grant/revoke |
| Persistence, jobs, quotas and recovery | Disposable PostgreSQL suites pass; F5 adds bounded database/queue `/ready` checks | Hosted restart, user RLS, provider operation, checkpoint writes and worker acceptance remain |

Configuration presence only: local API Supabase/DB and free-provider keys exist; `RESEND_API_KEY`, `PAGESPEED_API_KEY`, `DODO_PAYMENTS_API_KEY` and direct `ANTHROPIC_API_KEY` are absent. GitHub App configuration exists but was not used. Existence of a key is not evidence that a provider, OAuth callback or integration works. Hostinger business email is separate from application notification delivery. No SMTP bring-your-own-credentials feature was established by this audit.

## Next actions

1. Regenerate affected historical reports before relying on their saved scores/findings. F1-F3 are corrected as of 31 October; the changes do not rewrite previously stored reports or cookie evidence.
2. Decide which development previews ship and keep dependency audits in the release checks. F4's external font failure and F6's known web advisories are corrected locally.
3. Run team integration with a compatible local PostgREST fixture and a genuine installed Chrome safety/connection/goal/suite/replay pass on owned fixtures.
4. Complete provider-dependent acceptance only with appropriate configuration and authorized accounts: PageSpeed, mail/OAuth, citation source evidence, editor MCP and GitHub. Keep real payments and paid models outside this audit's scope.
5. Before any cloud restart or deployment, re-check the founder's spending preference, current credit/billing status and the existing deployment acceptance gates. This audit did not resume the paused hosting work or verify VM/AutoPay status.

No "all features working" or production-ready conclusion is justified until these gaps are closed.
