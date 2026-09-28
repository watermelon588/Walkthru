# Repository opportunities and launch audit

Reviewed 2026-09-27. Scope: current Walkthru source, handoff/state/architecture, roadmap and task lists, payment implementation, three requested public repositories, and provider documentation. This is an assessment, not an integration or deployment. No paid services enabled, dependencies installed, customer scans run, or third-party source retained.

## Decision

Use selected MIT SEO reference material to improve the existing scanners and fix recipes. Do not install either SEO repository as the production backend. Do not copy MiroFish into Walkthru under the current repository policy. Build the useful experience of interviewing test users around Walkthru's existing recorded journeys. Correct citation measurement before expanding provider coverage.

Walkthru's strongest positioning is an evidence loop: discover a problem, show the affected page and journey step, produce a specific fix, rerun, then measure the result. More agents or a larger checklist alone will not establish quality.

## What already exists

| Capability | Current implementation | Remaining qualification |
|---|---|---|
| Browser journeys and safety | Extension, LangGraph persona runner, owner/visitor/blocked policy, audit records and kill switches | Real-browser safety red-team gate remains |
| SEO and GEO | `scans/seo.py`, `seo_depth.py`, `geo.py`, `geo_depth.py`, fix packs and agent readiness | Several proposed SEO additions overlap these checks |
| Fix and verify | Rerun comparison, stack recipes, fix prompts, MCP | Finding identity collisions undermine ignore/grouping |
| Multiple test users | Custom users, up to six sequential grouped runs, common-problem report | Real grouped journey and production schema verification still required |
| Agency features | Branding/PDF, teams, findings board, chat, Scout, notifications | Live integrations and signed-in UI close-out remain |
| Monitoring | Watch and deploy hooks, citation scheduling | Reliability, provider capacity, citation-change alerts |
| Billing | Founder request/approval, Dodo checkout, signed webhook, entitlements, refunds/disputes | Products, credentials, live verification and reconciliation |
| GitHub fix PRs | Config-only fix PR implementation | GitHub App setup and live verification; repository scanning is a separate unfinished feature |

Evidence: `CURRENT_STATE.md`, `apps/api/app/citations.py`, `apps/api/app/scout.py`, `apps/api/app/billing.py`, `apps/api/app/scans/`, `apps/web/src/components/CitationResults.tsx`, `tasks/todo.md`.

## The three repositories

### ultimate-seo-geo

Its [README](https://github.com/mykpono/ultimate-seo-geo) describes diagnostic scripts, recorded citation sampling, finding verification, SEO drift, crawler logs, internal linking and content workflows. Its [MIT license](https://github.com/mykpono/ultimate-seo-geo/blob/main/LICENSE) permits commercial adaptation with the required copyright and permission notice.

Best candidates: repeated citation sampling with uncertainty; verifying and deduplicating findings; crawler-log analysis; selective content/fix recipes. Compare every candidate with our existing SEO depth, GEO depth and rerun code first. Specific script bodies for citation sampling and finding verification could not be fetched during this review, so their implementation quality is unverified. They are candidates, not vetted drop-in modules.

Adapt small, tested rules to the existing Finding contract and safe fetcher. Pin the source revision, inspect per-file/dependency licenses, retain notices in `apps/api/THIRD_PARTY.md`, and add fixture-based acceptance checks when implementing. Do not run a general audit CLI against arbitrary customer URLs or import its agent instructions wholesale.

### claude-seo

This is an [SEO analysis plugin](https://github.com/AgriciDaniel/claude-seo), not a hosted citation data service. Its public release is [MIT](https://github.com/AgriciDaniel/claude-seo/blob/main/LICENSE). Its [GEO skill](https://github.com/AgriciDaniel/claude-seo/blob/main/skills/seo-geo/SKILL.md) provides useful audit organization and reference material.

Best candidates: evidence-backed recommendations with a verification step, industry-specific recipes, schema eligibility guidance and targeted content review. Our crawler, schema, hreflang, content signals and agent-readiness checks already cover substantial overlap. Reuse selected rules and references, not its full multi-agent runtime. The name does not supply a Claude API account or measure Claude citations. Optional data integrations have their own credentials, costs and terms.

### MiroFish

[MiroFish](https://github.com/666ghj/MiroFish) constructs a simulation from seed material, personas and graph memory, runs interacting agents, generates a report, and lets a user question agents afterward. Its [setup](https://github.com/666ghj/MiroFish/blob/main/README.md) requires an LLM endpoint and Zep configuration and explicitly warns about high consumption. The advertised realism is not evidence of website-conversion prediction accuracy.

Its [AGPL-3.0 license](https://github.com/666ghj/MiroFish/blob/main/LICENSE) conflicts with AGENTS.md's prohibition on copying AGPL code or data. A separate container or API boundary is not automatic legal clearance. A modified network service can have source-offer obligations; whether a particular integration forms a covered combined work requires review of its actual design.

Options:

| Route | Assessment |
|---|---|
| Copy/fork MiroFish into Walkthru | Do not do this under current policy |
| Self-host as a separate service | Technically conceivable, but needs explicit policy/licensing review, operational isolation and cost validation |
| Commercial permission from rights holders | Possible to investigate; no alternative license was verified |
| Third-party hosted simulation API | Possible only with a legitimate provider, documented API, resale/data terms and budget. No production MiroFish API with those guarantees was verified |
| Use underlying OASIS independently | Its [own license is Apache-2.0](https://github.com/camel-ai/oasis/blob/main/LICENSE). Technically promising for later social simulation; audit the exact version and dependencies separately |
| Extend existing Walkthru journeys | Recommended: no new simulation framework needed |

MiroFish's [dependency manifest](https://github.com/666ghj/MiroFish/blob/main/backend/pyproject.toml) includes Flask, Zep, OASIS and CAMEL. It is a separate service stack, not a small FastAPI add-on. OASIS's permissive license does not relicense MiroFish's surrounding code.

Recommended original feature: **Ask your test users**. After three to six existing journeys, ask a persona why it stopped, what information it lacked, and which recorded change might help. Retrieve only that user's actual steps, screenshot references and findings; show evidence links and identify interpretations as hypotheses. Keep first-pass journeys independent so one persona does not bias another. Reuse Scout's bounded retrieval approach, but enforce report ownership and make answers traceable to step ids. Evaluate against human reviews, trap recall, false findings and cost per useful finding. Do not market simulated preference as predicted conversion rate.

## AI answers: what is missing and what is wrong

The visible path is `/app/visibility`, `Visibility.tsx`, `CitationResults.tsx`, API citation routes, `app/citations.py`, and three citation tables. `ENGINES` contains only `web` and `memory`.

| Surface | Current code | Correct expansion |
|---|---|---|
| Groq web search | gpt-oss-120b with browser_search | Keep its own label; it is not Google, Claude or Perplexity |
| Gemini from memory | Mentions without grounded sources | Report citation availability as N/A, not a failed citation |
| Gemini with Google Search | Conditional on `GEMINI_GROUNDING=1` | Separate engine/mode with persisted provenance; verify key/model quota before enabling |
| Google AI Overviews / AI Mode | No adapter | Separate SERP observation integration; never infer these from Gemini output |
| Perplexity | No adapter; explicitly not measured | Sonar API adapter, bounded budget and actual citation extraction |
| Claude | No citation adapter and absent from NOT_MEASURED | Add explicit unavailable state; later Claude web-search adapter |
| ChatGPT | Explicitly not measured | Remain explicit until a supported measurement path exists |

The 2026-09-26 handoff records quota-zero Google grounding on the founder's tested free keys. I did not inspect secret values or retry those live keys. [Google's pricing](https://ai.google.dev/gemini-api/docs/pricing) is model/tier specific; a free allowance on a billed tier is not unlimited free operation. [Gemini grounding](https://ai.google.dev/gemini-api/docs/google-search) produces grounded Gemini answers, not a reproduction of Google's consumer AI search UI.

[Perplexity Sonar](https://docs.perplexity.ai/docs/sonar/quickstart) provides web-grounded answers. [Claude web search](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool) provides source citations. Label these as API observations, since consumer products can differ by system prompt, region, history and model. [DataForSEO's AI Mode endpoint](https://docs.dataforseo.com/v3/serp/google/ai_mode/overview/) is a third-party route for sampled Google AI Mode results, with language/location controls and no user personalization. Review contract, retention and cost before adoption.

### Findings to fix before relying on citation scores

1. **Search results are counted as citations.** `ask_web()` stores all search results, and `analyze()` marks any matching source domain cited. A local fixture with answer `Use OtherApp.` and an unreferenced Acme search result returns `cited=True`. Parse actual answer citation references separately from retrieved results. Preserve raw provider citation metadata.
2. **Grounded Gemini domains come from source titles.** `ask_memory()` calls `domain_of(title)` rather than establishing the source URL's destination. A normal title produces a non-domain string. Prefer validated canonical source hosts; grounding redirect URLs require bounded, SSRF-safe resolution or an honest unresolved state. Use grounding-support references to associate claims with sources.
3. **Memory-only answers dilute the citation denominator.** The UI counts every completed answer in `Cited you`, even those that cannot cite. `Verdict` also says `Not cited` for memory-only answers. Split mention and citation eligibility and show N/A where appropriate.
4. **Domain matching can create false mentions.** `_first()` uses substring search; `notacme.example` currently counts as a mention of `acme.example`. Match normalized URL hosts with boundaries and explicit aliases.
5. **Historical mode is not stable.** Labels and `cites` depend on today's environment flag. Store provider, model, mode, locale, prompt version and measurement version with every observation. Enabling grounding must not relabel old memory-only answers.
6. **Coverage list is incomplete.** Add Claude and Google AI Overviews/AI Mode as distinct unmeasured surfaces. Do not use absence of measurement as zero visibility.
7. **One sample is weak evidence.** Show sample count, date, engine and successful/failed/queued denominators; retain branded versus unbranded prompt groups. Add repeats and uncertainty once capacity permits. Mention order and source order are not search ranking.
8. **Scheduling capacity is insufficient for the advertised allocation at scale.** The default is 20 web answers/day globally, or 140/week before retries. One fully configured Plus account can request 5 sites x 25 prompts = 125 web answers/week. A single site takes at least two daily quotas for 25 web prompts. Replace the UI promise of answers in the next minutes with a queue estimate and capacity-aware admission. Use atomic quotas and leased jobs before multiple workers; the present attempts increment is not an exclusive lease.

If by AI message section you also mean team Scout: `app/scout.py` currently uses workspace-only data and no search tools. Add verified links to its internal reports/findings first. External research should be a separate explicit mode with its own source attribution and budget.

### Cost and token plan

Keep deterministic extraction, matching, deduplication and scoring outside model calls. Reuse fetched HTML; summarize only relevant evidence; bound follow-up context; generate fixes from existing stack recipes. Do not load entire SEO skill libraries into every customer request. Prioritize browser journeys over scheduled research sharing the same quota.

At current published rates, [Sonar low-context requests](https://docs.perplexity.ai/docs/getting-started/pricing) have a $5/1,000 request fee plus token charges. Claude search is $10/1,000 searches plus token charges. An illustrative 400 answers/month at one search each costs $2 in Sonar request fees or $4 in Claude search fees before tokens, retries, other providers and infrastructure. Multiple searches increase cost. These are calculations, not quotes for a complete plan. New paid integrations need the founder's approval under AGENTS.md; none were enabled.

## Prioritized additions

| Priority | Addition | Acceptance evidence |
|---|---|---|
| Before launch | Correct citations, source attribution and honest unavailable states | Fixtures distinguish retrieved, cited, mentioned, unknown and failed |
| Before launch | Stable finding identity across scanner, report, ignore and MCP | Two cookie findings stay distinct; repeated runs remain comparable |
| Next | Source opportunity map, P3.3 | Actual cited pages grouped by source type, with why each opportunity is relevant |
| Next | Ask your test users | Every answer cites recorded steps or explicitly says evidence is absent |
| Next | Targeted page improvements, P3.6 | Quotes old text, proposes replacement, verifies facts and reruns checks |
| Next | Search Console/Bing, P3.1; crawler/referral logs, P3.5 | Read-only permissions; measured traffic separated from synthetic mentions |
| Later | Additional engine adapters and citation-change alerts | Budget controls, provider provenance and reproducible samples |
| Later | OASIS-based audience experiments | Validated incremental value and cost; synthetic conclusions clearly labelled |

Google's [official AI search guidance](https://developers.google.com/search/docs/appearance/ai-features) does not require special AI files or special schema for inclusion. Treat llms.txt and fixed passage-length heuristics as optional guidance, not guaranteed ranking mechanisms. GEO readiness scores cannot guarantee citations.

## Launch checklist, reconciled

Unchecked historical items are not all missing code. The following groups identify remaining work or proof needed before launch. The system-design appendix preserves every open task label for follow-up; its older claims require reconciliation, not blind implementation.

### Engineering and evidence

- [ ] Correct the citation issues above and the known finding-fingerprint collision; remove duplicate alt-text noise and stabilize generated rule ids.
- [ ] Add Python dependency lockfile, CI for API/web/extension tests, builds and lint, dependency/secret scanning, and required checks (SD-9.1, 9.2, 4.7).
- [ ] Finish shared route-class rate limits, per-host politeness, API key expiry/read-only scopes and the planned secret-scanning prefix submission.
- [ ] Version database migrations, verify all recent schemas on the target Supabase project, exercise RLS and account deletion across new tables, and complete a private backup plus restore drill.
- [ ] Deploy durable job processing and shared state: restart-safe reports/watch/citations, idempotent retries, Postgres checkpointer, process supervision, graceful shutdown. The plan calls the queue a launch gate and also a prerequisite for a second process; retain one process until this is resolved and tested.
- [ ] Add structured request-id logs, readiness checks, uptime alerts, incident runbooks, error/latency/queue metrics and deploy/rollback procedure.
- [ ] Close SSRF DNS-rebinding and extension sender/session hardening work; prove prompt-injection and XSS handling with focused checks.
- [ ] Run the complete API/web/extension verification on the release candidate. Current targeted tests do not certify the whole application.
- [ ] Real-browser red-team pass: feed, challenge, account, bulk and Instagram goals, signed-in unverified pages, bot walls, destructive controls and permission stops.
- [ ] Signed-in end-to-end UI: dashboard, report/ignore/rerun, compare/watch, AI answers, billing, notifications/Realtime, teams/invites, settings and mobile layouts.
- [ ] Real grouped journey; screenshot-backed easy/hard journeys; private evidence and public sharing; plain/branded multi-page PDF; finding-to-step proof.
- [ ] Quality checkpoint: hard fixture recall at least 85%, easy fixture and three permitted real sites without false alarms; founder reviews Pro report and applies its fix plan.
- [ ] Measure latency and concurrent capacity with stubbed models, then validate actual provider quotas. Do not overpromise weekly citation capacity.

### Founder and infrastructure

- [ ] Buy/confirm domain, hosting target and region; configure DNS/TLS, API and web origins, redirects and production secrets. Existing docs mix Render beta, Oracle and Google Cloud VM plans; choose one deployment plan.
- [ ] Verify Resend domain and email DNS; configure Supabase SMTP and Google/GitHub OAuth production redirects; keep invitation email confirmation requirements.
- [ ] Rotate Supabase secret key and DB password, exposed test passwords and shared API/MCP credentials; revoke development access not intended for launch.
- [ ] Complete local admin setup with password/TOTP; keep that service on the founder's machine.
- [ ] Verify recent schemas for custom test users, groups, branding, teams, Scout, GitHub, citations, notifications and safety. Conflicting handoff notes do not prove all were applied.
- [ ] Provision PageSpeed key; set and verify Scout provider configuration if advertised; register and test GitHub App if exposing fix PRs. Defer or visibly disable unfinished integrations.
- [ ] Chrome developer account, production extension manifest/origins/id, permission audit, remove unpacked fixed key, listing assets and privacy answers; publish Unlisted as the safety plan specifies.
- [ ] Human/legal review of Terms, Privacy, refund/expiry language and subprocessors; replace placeholder contacts and establish support/security/abuse and incident process.
- [ ] Enable branch protection, production uptime notifications and backup destination; verify a rollback and restore are usable.

### Product launch

- [ ] P0.3/V19 first-impression and landing copy review; V9 landing/pricing/onboarding accuracy; replace placeholder screenshots and publish a representative demo report.
- [ ] Confirm plan allocations, citation caps and Plus availability. Existing billing sells approved 30-day passes, not automatic monthly subscriptions. Copy must match.
- [ ] Complete extension install/connect/domain-verification/safe-mode onboarding and the full stranger path: scan, sign in, install, run, report, share, pay and receive access.
- [ ] Founder validation A1-A4: 30 scans with offer, 20 extension beta users, headline test, and ten verified Supabase-backed launches with feedback. Track conversion and first-run completion.
- [ ] Reconcile launch date. The handoff says October 20/27; the newer launch-track block says October 27/November 3. No date was changed by this audit.

## Payment gateway: what remains

The code already verifies webhook signatures/timestamps/business, re-fetches payment details, validates offers/products, grants a payment-linked entitlement and revokes on refund/dispute. The approval UI now exists as a local admin panel, despite an older line in the billing runbook saying it does not.

1. Complete Dodo account/live verification and enable account 2FA.
2. In test mode create five one-time USD products: Launch $9, Pro founding $15, Pro $19, Plus founding $39, Plus $49. These are existing configured prices, not new pricing recommendations.
3. Set server-only `DODO_PAYMENTS_API_KEY`, `DODO_PAYMENTS_WEBHOOK_KEY`, `DODO_PAYMENTS_BUSINESS_ID`, environment and the five `DODO_PRODUCT_*` ids. Validate them with `scripts/billing.py products`.
4. Configure a public HTTPS `/webhooks/dodo` endpoint and payment, refund and dispute events. For local testing use the runbook's tunnel approach. Follow [Dodo's webhook documentation](https://docs.dodopayments.com/developer-resources/webhooks).
5. Execute request, approval, hosted checkout, webhook and entitlement refresh in test mode. Also test decline, duplicate/reordered webhook, forged redirect, crash/retry, expiry, refund and dispute. A success redirect must never grant access.
6. Complete nightly payment reconciliation and an alert/retry path for paid-but-not-activated cases. Review amount/currency validation: `activate()` compares amounts only when currencies match, so foreign-currency settlement needs a documented, provider-backed validation rule and tests rather than silently skipping amount verification.
7. Before paid models, finish the cost ledger/reservation/release/refund accounting, global/per-user caps and crash reconciliation described in `payment.md`. Do not enable Claude merely because the gateway works.
8. Configure live products/keys/webhook separately after verification, validate again, then conduct the founder's controlled $9 purchase/refund before customers.
9. V10b: offer-ready customer email/banner. In-app offer notifications already exist; external email remains dependent on the domain. V10c: coupons remain unfinished and should use Dodo support if suitable; current code rejects discounts, so coupons need coordinated product validation changes. They are not mandatory for a launch without coupons.

Automatic subscriptions and self-serve checkout are later gates in payment.md. Do not silently switch the approved founder-offer model.

## Deferred product work, not universal launch blockers

P2.1-P2.4 repository connection for code scans, ephemeral code scanning, file/line fixes and safe-template worker; P3.1 Search Console/Bing; P3.3 source/accuracy analysis; P3.4 citation changes in watch alerts; P3.5 AI traffic; P3.6 citability rewrites; P4.1 separately authorized staging scans; P4.5 paid engines; P4.6 conditional cloud runner. Also preview-deploy checks, issue-tracker exports, MCP OAuth, subscriptions/self-serve billing and optional video after evidence validation. Do not reopen built MCP, branding, teams or grouped personas as new features.

## Verification and limits

Ponytail, Graphify and shipping-and-launch skills applied. The existing graph was queried for navigation only: its 2026-09-25 index is stale for citation work. Current source is authoritative. No graph rebuild or claimed token-savings estimate.

`pytest -q tests/test_citations.py tests/test_billing.py`: **46 passed**, with an upstream anyio deprecation warning and a local pytest cache-permission warning. Additional in-memory fixtures reproduced the uncited-search-result and substring-domain false positives and title-as-domain behavior. Passing existing tests therefore does not establish correct citation semantics.

No real payments, live provider benchmark, full release suite or authenticated browser acceptance test was performed. External repository review establishes fit and licensing direction, not a security certification. No application logic was changed.

## Appendix: every unchecked system-design task

This inventory preserves the plan labels, not a claim that every implementation is absent. SD-2.2 request limits and SD-3.1 ownership checks are already checked off and omitted.

| ID | Work | Plan classification | Reconciliation |
|---|---|---|---|
| SD-1.1 | Put the domain behind Cloudflare | Launch gate | Open in plan; deployment completion not independently established. |
| SD-1.2 | CAA record and certificate monitoring | Follow-up / assess | Open in plan; deployment completion not independently established. |
| SD-1.3 | Cloudflare WAF and bot rules (free tier) | Follow-up / assess | Open in plan; deployment completion not independently established. |
| SD-1.4 | Email DNS for our own domain | Launch gate | Open in plan; deployment completion not independently established. |
| SD-1.5 | `security.txt` | Follow-up / assess | Open in plan; deployment completion not independently established. |
| SD-2.1 | A limit for every endpoint class | Launch gate | Open in plan; deployment completion not independently established. |
| SD-2.3 | Per-target politeness | Follow-up / assess | Open in plan; deployment completion not independently established. |
| SD-2.4 | Sign-up and sign-in abuse | Follow-up / assess | Open in plan; deployment completion not independently established. |
| SD-2.5 | Kill switches | Follow-up / assess | Journey kill switches built; verify scan/read-only coverage. |
| SD-3.2 | Bound the auth token cache | Follow-up / assess | Bounded cache already implemented in auth.py; reconcile checklist. |
| SD-3.3 | Check the sender in the extension | Follow-up / assess | Open in plan; deployment completion not independently established. |
| SD-3.4 | Session storage in the extension | Follow-up / assess | Open in plan; deployment completion not independently established. |
| SD-3.5 | Founder admin tools behind a separate role | Follow-up / assess | Local-only password/TOTP/CSRF admin and audit log built; reconcile intended controls. |
| SD-3.6 | Enable Google and GitHub sign-in with production redirect URLs | Launch gate | Open in plan; deployment completion not independently established. |
| SD-4.1 | XSS stays impossible by construction | Follow-up / assess | Open in plan; deployment completion not independently established. |
| SD-4.2 | Security headers on the API too | Follow-up / assess | Open in plan; deployment completion not independently established. |
| SD-4.3 | No internal details in errors | Follow-up / assess | Generic catch-all built; finish request ids and error-detail audit. |
| SD-4.4 | CSRF: document why it does not apply | Follow-up / assess | Open in plan; deployment completion not independently established. |
| SD-4.5 | SSRF: close the DNS rebinding gap | Follow-up / assess | Open in plan; deployment completion not independently established. |
| SD-4.6 | Prompt-injection hygiene | Follow-up / assess | Open in plan; deployment completion not independently established. |
| SD-4.7 | Dependency and secret scanning in CI | Launch gate | Open in plan; deployment completion not independently established. |
| SD-4.8 | Rotate everything that was ever shared or committed | Launch gate | Open in plan; deployment completion not independently established. |
| SD-4.9 | Extension hardening for the store | Launch gate | Open in plan; deployment completion not independently established. |
| SD-5.1 | Versioned migrations | Launch gate | Open in plan; deployment completion not independently established. |
| SD-5.2 | Backups and a restore drill | Launch gate | Open in plan; deployment completion not independently established. |
| SD-5.3 | Indexes for every hot query | Follow-up / assess | Open in plan; deployment completion not independently established. |
| SD-5.4 | RLS regression tests | Follow-up / assess | Open in plan; deployment completion not independently established. |
| SD-5.5 | Personal data inventory | Follow-up / assess | Open in plan; deployment completion not independently established. |
| SD-6.1 | Durable job queue in Postgres | Launch gate | Open in plan; deployment completion not independently established. |
| SD-6.2 | Postgres checkpointer on the VM | Launch gate | Open in plan; deployment completion not independently established. |
| SD-6.3 | Timeouts, retries and circuit breakers everywhere | Follow-up / assess | Open in plan; deployment completion not independently established. |
| SD-6.4 | Graceful shutdown | Follow-up / assess | Open in plan; deployment completion not independently established. |
| SD-6.5 | Idempotency keys | Follow-up / assess | Billing idempotency exists; inspect remaining run/observe retry semantics. |
| SD-6.6 | Process supervision on the VM | Launch gate | Open in plan; deployment completion not independently established. |
| SD-6.7 | Health and readiness | Follow-up / assess | Open in plan; deployment completion not independently established. |
| SD-7.1 | Set latency budgets and measure them | Follow-up / assess | Open in plan; deployment completion not independently established. |
| SD-7.2 | Cache Instant Scans per URL for 10 minutes | Follow-up / assess | Open in plan; deployment completion not independently established. |
| SD-7.3 | Put the VM next to the database | Follow-up / assess | Open in plan; deployment completion not independently established. |
| SD-7.4 | Prerender the marketing pages | Follow-up / assess | Open in plan; deployment completion not independently established. |
| SD-7.5 | Load test before launch | Follow-up / assess | Open in plan; deployment completion not independently established. |
| SD-7.6 | Horizontal scaling (only when SD-6.1, 6.2 and 2.1 are done and one VM is not enough) | Follow-up / assess | Open in plan; deployment completion not independently established. |
| SD-8.1 | Structured logs with request ids | Launch gate | Open in plan; deployment completion not independently established. |
| SD-8.2 | Error tracking and metrics | Follow-up / assess | Open in plan; deployment completion not independently established. |
| SD-8.3 | Uptime and alerting | Launch gate | Open in plan; deployment completion not independently established. |
| SD-8.4 | Security audit log | Follow-up / assess | Partial audit tables built; complete event coverage and owner access. |
| SD-8.5 | Runbooks | Follow-up / assess | Open in plan; deployment completion not independently established. |
| SD-9.1 | CI on every push and pull request | Launch gate | Open in plan; deployment completion not independently established. |
| SD-9.2 | Lock the Python dependencies | Launch gate | Open in plan; deployment completion not independently established. |
| SD-9.3 | Staging environment | Follow-up / assess | Open in plan; deployment completion not independently established. |
| SD-9.4 | API versioning for the extension | Follow-up / assess | Open in plan; deployment completion not independently established. |
| SD-9.5 | One-command deploy and rollback | Follow-up / assess | Open in plan; deployment completion not independently established. |
| SD-9.6 | Remove dev-only code from production | Follow-up / assess | Open in plan; deployment completion not independently established. |
| SD-10.1 | Dodo webhooks done right (V10) | Launch gate | Webhook core built; real gateway test and nightly reconciliation remain. |
| SD-10.2 | Spend guards for paid models | Follow-up / assess | Open in plan; deployment completion not independently established. |
| SD-10.3 | Legal review | Launch gate | Open in plan; deployment completion not independently established. |
| SD-10.4 | Incident and breach process | Follow-up / assess | Open in plan; deployment completion not independently established. |
