# Prelaunch fixes and change record

Updated: 31 October 2026.

This records the F1-F6 corrections requested after the [27 October feature audit](feature-audit-2026-10-27.md). The original audit describes baseline commit `2725be45d624d7a9a5854abb37cb833d44704da1`; this file describes the subsequent local changes. The changes have not been committed, pushed or deployed by these fix sessions.

Publication follow-up, 1 November: the founder requested publishing these changes. Fresh release checks passed for web (55 tests/build/lint) and extension (177 tests, one skip/build/typecheck/lint). The full API run had 1,282 passes, 19 skips and one route-inventory failure: `/ready` was missing from the ownership classification. Added its public operational-status classification; all 64 ownership/readiness tests and API lint then passed. No application behavior changed in that follow-up, and the full suite was not repeated after the test-only correction. See [current release record](../CURRENT_STATE.md) for publication preparation; earlier stage counts below remain historical. Deployment and live feature acceptance are separate.

## Status

| Audit ID | Change | Status |
| --- | --- | --- |
| F1 | Score journey outcomes from confirmed evidence | Corrected for newly calculated scores |
| F2 | Keep normal Supabase public configuration out of findings and penalties | Corrected for new reports |
| F3 | Scope cookie advice to observed attributes and uncertain purpose | Corrected for new reports; full offline API verification passed |
| F4 | Preview rendering when third-party font CSS fails | Corrected; all three variants render with external fonts blocked |
| F5 | Database readiness beyond the liveness endpoint | Added `/ready` for bounded Data API and stale-queue checks |
| F6 | Web toolchain dependency advisories | Patched; fresh full and omit-dev npm audits both report zero vulnerabilities |

## F1: readiness follows completion evidence

### Problem

A `safe_stop` report could say its journey was blocked while giving UX 100 and full goal credit. Internal budgets and lost-agent states could reduce a site's score without a recorded website failure. Rerun stability also inferred success from terminal labels.

### Changes

- Journey scoring validates the version 2 assessment and matches its stop reason to the run status.
- Full completion credit requires all declared checkpoints, matching milestone text and executed-step evidence on the same recorded URL. Text comparison ignores case and whitespace differences.
- Safety stops, budgets, loops, owner stops and unsupported legacy terminal labels leave unproved journey components unmeasured. They do not establish completion or a site defect.
- Genuine browser-observed UX findings remain scored if an interruption happens later. Independent static measurements retain their existing weights.
- Rerun stability requires proven completion in both reports and uses validated counts of actions with recorded outcomes.
- Completion notes describe declared UI evidence; they do not certify backend persistence, email delivery or other unobserved effects.

Implementation: [score.py](../apps/api/app/agent/score.py). Contract: [task completion and scoring](task-completion-contract.md#readiness-scoring-f1-correction-2026-10-31).

Regression coverage: [test_score_evidence.py](../apps/api/tests/test_score_evidence.py), with updated [Launch Ready](../apps/api/tests/test_launch_ready.py) and [agent readiness](../apps/api/tests/test_agent_ready.py) fixtures. Twenty-eight new cases cover unsupported/invalid reports, blocked and interrupted runs, actual UX errors, orphan or mismatched milestones, normalized text and action counts, and proven reruns.

## F2: public Supabase configuration is context

### Problem

A normal Supabase project URL and anon/publishable key generated a low-severity security finding and repair task. Public configuration alone lowered a measured security score from 100 to 97.

### Changes

- Normal Supabase client configuration no longer creates a finding, repair task or score penalty.
- Discovery remains informational in `report.stack.backend` and `report.stack.evidence.backend`. The context contains the public project URL and fixed explanatory text, without captured key values.
- Configuration found only in same-origin JavaScript bundles survives the site-audit/report flow, including when independent stack detection fails.
- Genuine backend findings retain project-specific repair-check URLs through stack evidence. Removing the false finding does not replace those URLs with placeholders.
- Browser-exposed secret/service-role keys remain high-severity findings. Existing verified-owner probe restrictions and read-only probe behavior remain in place.

Implementation: [backend.py](../apps/api/app/scans/backend.py), [site.py](../apps/api/app/scans/site.py), [report.py](../apps/api/app/agent/report.py) and [fix_prompt.py](../apps/api/app/agent/fix_prompt.py).

Regression coverage: [public configuration](../apps/api/tests/test_public_backend_config.py), [context and repair URLs](../apps/api/tests/test_backend_context.py), and updated [backend tests](../apps/api/tests/test_backend.py). Seventeen new cases cover inline/bundle sources, legacy/current key forms, preserved secret penalties, graph context and repair instructions.

Reference: [Supabase API-key guidance](https://supabase.com/docs/guides/getting-started/api-keys). The presence of public configuration does not prove either a security failure or correct access-control policies. Other backend findings, including the existing Firebase classification, were outside this correction.

## F3: cookie purpose and attribute checks are separate

### Problem

The scanner treated every cookie as a session cookie. `_ga=...; Path=/; Secure; SameSite=Lax` therefore received a medium missing-HttpOnly finding and lowered an otherwise clean security score from 100 to 90. Shared repair recipes could then generate unrelated session, Next.js or Supabase-auth changes for analytics and CSRF cookies.

### Changes

- Missing HttpOnly is inferred only for a conservative set of session-like names. The finding explicitly says the purpose and need for JavaScript access remain unconfirmed; adding HttpOnly is conditional on confirming a server-only session design.
- Analytics, CSRF, preferences and unknown names do not receive a missing-HttpOnly penalty merely because JavaScript can read them.
- Missing Secure on HTTPS and missing/invalid SameSite remain attribute advice. For cookies without a session-like name, these are low-severity observations rather than asserted session vulnerabilities. Missing SameSite guidance acknowledges browser defaults and asks for a policy appropriate to the actual flow.
- `SameSite=None` without Secure remains a concrete medium-severity attribute violation, independently of the cookie's purpose.
- Existing `__Host-` and `__Secure-` requirements remain checked. `__Http-` and `__Host-Http-` also enforce their required HttpOnly attribute. Prefix findings describe supporting-browser constraints, without inferring authentication purpose.
- Cookie evidence retains the name and attributes with the value replaced by `[hidden]` before the finding is stored or used in a prompt.
- The shared cookie recipe no longer inserts blanket session-cookie snippets. Full and chat prompts use the finding's specific proposed change, with guidance about JavaScript consumers and cross-site behavior. Generic, Next.js and Supabase stacks follow the same rule.
- Existing cookie rule IDs remain compatible; no report schema, dependency or database migration is required.

Implementation: [security.py](../apps/api/app/scans/security.py) and [recipes.json](../apps/api/app/agent/recipes.json).

Regression coverage: [cookie purpose and generated prompts](../apps/api/tests/test_cookie_purpose.py) and [attributes, prefixes and value redaction](../apps/api/tests/test_cookie_attributes.py). Thirty-seven new cases cover the audit example, client/unknown names, session uncertainty, transport/policy severity, full/chat prompts across stacks, prefix requirements and redaction. Existing hard/easy fixture and security-parity checks remain in the verification suite.

References: [MDN Set-Cookie attributes and prefixes](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Set-Cookie), [MDN cookie configuration](https://developer.mozilla.org/en-US/docs/Web/Security/Practical_implementation_guides/Cookies), and [Google Analytics cookie usage](https://developers.google.com/analytics/devguides/collection/ga4/tag-options).

### Cookie interpretation limits

Cookie names are heuristics, not proof of sensitivity, authentication, an exploit or a need for JavaScript access. A custom-named authentication cookie may need a manual review that a passive response cannot supply. Cookie values are not used to classify purpose; the scanner does not sign in, execute a CSRF test or change cookies to establish purpose. Low-severity missing-policy advice is not a demonstrated exploit.

## F4: preview rendering without external font CSS

Removed Google Fonts `@import` statements from [fresh.css](../apps/web/src/variants/fresh.css), [darkroom.css](../apps/web/src/variants/darkroom.css) and [markup.css](../apps/web/src/variants/markup.css). The previews use their existing bundled Geist and system-font fallbacks. Their typography can differ from the former external display fonts; no font package or network dependency was added.

Before the fix, isolated Edge reproduced the CSS-preload failure and blank content for **all three** variants with Google Fonts blocked. After the fix, the real production bundle renders all three at 1280px and 390px with the route loader dismissed, no page errors and no Google Fonts requests. Screenshots were inspected. [Three source regressions](../apps/web/tests/variantFonts.test.ts) also prevent reintroducing blocking external font imports. This addresses the font failure; it does not decide whether `/variants` or other developer previews belong in a public release.

## F5: database readiness is separate from health

Added `GET /ready` in [main.py](../apps/api/app/main.py). Its [database helper](../apps/api/app/db.py) performs a HEAD of `runs` selecting only `id` with limit 0, then reads at most one overdue queued job's metadata. Both requests use 1-second connection and 2-second per-phase timeouts, without the normal database retries. This is a timeout per network phase, not a guaranteed two-second overall deadline.

| Condition | HTTP status | Response status |
| --- | --- | --- |
| Both reads succeed and no job is overdue by more than 120 seconds | 200 | `ready` |
| Database, permission, HTTP, timeout or response-parsing failure | 503 | `not_ready` |
| An overdue queued job exists | 503 | `not_ready` |

All readiness responses use `Cache-Control: no-store`. Error details are generic and omit credentials, exceptions and job identifiers. `/ready` is exempt from database-backed rate-limit counters in [limits.py](../apps/api/app/limits.py), so monitoring neither writes those counters nor inherits their retries. Existing `/health` behavior, including its legacy stale-queue signal, is preserved.

Use `/ready` to monitor **server Data API read access and the overdue queue**, rather than interpreting `/health` as database readiness. This is not proof of user-specific RLS permissions, checkpoint writes/recovery, successful provider requests, worker throughput or an entire browser journey. Empty queues do not prove a worker is running. No provider call or paid operation is performed by the endpoint. SD-6.7's broader provider-readiness work remains separate.

[Sixteen readiness regressions](../apps/api/tests/test_readiness.py) cover success, dependency failures, stalled jobs, generic errors, caching, no rate-limit writes, bounded request shapes, timeouts and legacy health compatibility. RED verification was 14 failed / 2 passed before implementation.

## F6: patched web toolchain and reproducible lockfile

Fresh full and omit-dev npm audits reproduced the two high-severity package findings before changes. Updated the existing Vite development dependency in [package.json](../apps/web/package.json) and the resolved dependency tree in [package-lock.json](../apps/web/package-lock.json):

| Package | Before | After |
| --- | --- | --- |
| Vite | 8.3.0 | 8.3.5, declared as `^8.3.5` |
| source-map-js, shared by PostCSS and Tailwind | 1.2.1 | 1.2.2 |
| PostCSS, required by patched Vite | 8.5.28 | 8.5.32 |
| Rolldown and its optional platform bindings | 1.2.9 | 1.2.16 |

The related `nanoid` and `@oxc-project/types` versions also follow the updated transitive requirements. Lockfile review found 21 existing package entries updated, no added/removed package names, no new direct dependency and unchanged MIT/BSD-3-Clause license families. No forced major upgrade or override was used. Installed Node 22.18.0 satisfies the declared Vite/Rolldown engine requirement of Node `^20.19.0 || >=22.12.0`; existing React and Tailwind plugin peer ranges accept Vite 8.

References: [source-map-js advisory and fixed 1.2.2](https://github.com/advisories/GHSA-68fv-2mgg-jv7q), [Vite/launch-editor advisory and patched Vite range](https://github.com/advisories/GHSA-698v-4r3x-3vcv). The initial npm audit captured the other applicable Vite advisories as well. The resulting audit status is a current registry-advisory result, not a whole-application security certification.

Verification after a clean `npm ci --ignore-scripts --no-audit --no-fund`:

- Full `npm audit --json`: **0 vulnerabilities**; `npm audit --omit=dev --json`: **0 vulnerabilities**, both exit 0.
- `npm ls` confirms the patched deduplicated versions and no invalid dependency tree.
- All **55 web tests**, lint, TypeScript and production build pass. Existing bundle-size and ineffective-dynamic-import warnings remain.
- Isolated Edge renders the production landing page, login page and all three variants at desktop and mobile widths, after loader dismissal, with no page errors. All external requests are blocked; local screenshots/JSON are retained.
- A separate loopback Vite smoke check serves the application HTML and transforms the React TypeScript entry successfully, then stops its own server.

This stage changes web dependency files only, plus documentation. API and extension suites were not rerun for this dependency-only correction. No cloud setting, provider, pricing, schema or application behavior was changed.

## Verification record

| Fix stage | New cases | Focused suite | Full offline API suite | API lint |
| --- | --- | --- | --- | --- |
| F1 | 28 | 125 passed | 1,213 passed, 19 skipped | Passed |
| F2 | 17 | 128 passed | 1,230 passed, 19 skipped | Passed |
| F3 | 37 | 162 passed | 1,267 passed, 19 skipped | Passed |
| F4 | 3 web | All 55 web tests passed; lint, TypeScript and build passed; 3 variants at desktop/mobile in isolated Edge | Not rerun for this quick follow-up | Web lint passed |
| F5 | 16 API | 37 affected API tests passed | Not rerun for this quick follow-up | Passed |
| F6 | Registry audit reproduction | Clean install; full/omit-dev audits zero; all 55 web tests, lint/TypeScript/build, dev-server smoke and five-page desktop/mobile browser smoke pass | Not rerun; web dependencies only | Web lint passed |

Each bug correction has tests that failed before its implementation. F3's purpose reproduction was 22 failed / 8 passed; its additional attribute/privacy reproduction was 7 failed. Green focused verification includes related scanner, report, recipe, comparison/contract and reuse checks as appropriate to each stage. Counts are stage-specific. The last complete API run was after F3; F4/F5 used the affected health/readiness/rate-limit/DB-HTTP/observability suite for the requested quick follow-up. Existing build warnings about bundle size and ineffective dynamic imports remain.

Ignored local evidence directories:

- `evals/results/f1-fix-20261031/`: `score-evidence-red.log`, `score-focused-final.log`, `api-verified.log`, `api-verified-junit.xml`.
- `evals/results/f2-fix-20261031/`: `public-config-red.log`, `context-red.log`, `fix-context-red.log`, `focused-final.log`, `api-full.log`, `api-junit.xml`.
- `evals/results/f3-fix-20261031/`: `cookie-purpose-red.log`, `cookie-attributes-red.log`, `focused-first.log`, `api-lint.log`, `api-full.log` and `api-junit.xml`. Final full-suite exit: 0 in 576.23 seconds, with one existing dependency deprecation warning.
- `evals/results/f4-f5-fix-20261031/`: `fonts-red.log`, `readiness-red.log`, `api-focused.log`, web test/lint/build logs, `browser-red.log`, `browser-green.log`, JSON results and screenshots. Browser requests outside the isolated local origin were aborted.
- `evals/results/f6-fix-20261031/`: full/omit-dev before/after audit JSON, clean-install logs, `dependency-tree.log`, `lockfile-review.json`, final web test/lint/build logs, `dev-smoke.log`, browser JSON and screenshots. Final verification ran after the clean install completed.

Full API verification uses a loopback-only socket guard, dummy cloud/database settings, disabled tracing/provider flags and disposable local PostgreSQL fixtures. All 19 existing skips require the unavailable compatible PostgREST integration fixture. The F5 focused run also used the socket guard and dummy settings, with mocked database responses. No live model calls, external scans, SMTP delivery, payment, cloud-resource changes or deployed acceptance were performed. F4 changes only preview CSS; extension code is unchanged.

## Existing reports and next work

Saved report fields are not rewritten or migrated. Start a new scan/journey or regenerate an affected report to obtain corrected stored scores, findings and cookie evidence. Scanner/report source changes invalidate Instant Scan reuse, so older cached scans are not reused as current after the updated application starts. Previously stored cookie values are not retroactively redacted by F3.

F1-F6 are addressed locally within the scopes above. Installed-extension, live-provider, team PostgREST/RLS, checkpoint-write/recovery, worker acceptance and deployed checks remain open in the [full audit](feature-audit-2026-10-27.md). The separate API dependency vulnerability scan remains unperformed. See [CURRENT_STATE.md](../CURRENT_STATE.md) for the latest working state.
