# Walkthru Roadmap v1.2, the flagship plan

_Updated 2026-09-25 after the premium depth review (docs/decisions.md, 2026-09-25 "Premium depth"). Product: [SPEC.md](SPEC.md). System: [ARCHITECTURE.md](ARCHITECTURE.md). Tasks with acceptance criteria: [tasks/todo.md](tasks/todo.md). Earlier evidence: `founder/competitor-matrix.md`, `founder/pricing-strategy.md`, `founder/validate-idea.md`._

## Finish line

Walkthru is launched when a stranger can:
1. Get a free Instant Scan with an AI readiness score and see what AI search sees.
2. Install the extension, test a public or logged-in flow safely, and get a truthful evidence report.
3. Fix things with a fix plan their coding agent can follow, and rerun to see what changed.
4. Share the report.
5. Pay for a pass.

The server must enforce every plan limit.

**Flagship bar (new):** every report section must be at least as useful as the best free tool for that area, then add what no free tool does: one report, plain words, a fix for the detected stack, and a rerun that proves the fix.

## Build rules for every phase (founder, 2026-09-25)

1. **Deterministic code first.** A model call is allowed only where judgement or writing is the product (journeys, first impression, copy review, report summary, rewrite suggestions).
2. **Free tier only.** No paid model or paid API until revenue covers it (payment.md caps). Claude Haiku 4.5 stays wired and off. Free engines only for AI citation tracking.
3. **Reuse open source before writing from scratch.** Check the licence first (table in docs/decisions.md). MIT, Apache-2.0, BSD and CC-BY can be ported or used with their notice kept. MPL-2.0 logic is rewritten, not copied. LGPL tools run as separate binaries. AGPL, Commons Clause, Elastic and "no licence" repos are ideas only, never code or data.
4. **Name every new dependency in its task.** AGENTS.md "ask first" still applies; the founder approved permissive open source in principle on 2026-09-25.
5. **Nothing that attacks a site.** Read-only probes only on owner-verified domains. Active scans only against an owner-entered staging URL (Phase 4). No payloads, fuzzing or denial of service, ever.

## Weak points and the exact fix

Items 1 to 23 were found on 2026-09-24; 24 to 32 on 2026-09-25. Each fix has a task in `tasks/todo.md`.

| # | Weak point | Evidence | Exact fix | Task |
|---|---|---|---|---|
| 1 | "AI test users" is a crowded category | Meerkat, CanaryUsers, Swarm and Uxia all sell it; CanaryUsers from $9 | Reposition as "the launch check for apps built with AI": journeys, SEO, GEO and security in one report | V9 |
| 2 | Paid plans mostly sell volume | Pro's list was runs, export and email | Paid value is where the test goes (logged-in pages), how deep the checks go (probes, code, tracking) and what happens over time | V4, V5, V12, Phases 1 to 3 |
| 3 | Nothing brings a user back after launch week | No reruns, schedules or alerts | Rerun and compare in Pro; weekly watch, citation tracking and deploy webhook | V4, V12, P3.2 |
| 4 | Free tier looks tiny next to Meerkat | Free-provider capacity is about 110 full runs a day for all users | Compete on the no-install Instant Scan, same quality as paid. Journeys stay at 3 a month | V2, V8 |
| 5 | Journeys need an extension; every competitor starts from a URL | Install step before first value | Instant Scan first; cloud runner only if fewer than 25% finish a run | A2, V14 |
| 6 | No GEO while search moves to AI answers | No module | GEO scanner, fix pack, depth pass, then tracking | V2, V5, P1.5, P3.2 |
| 7 | Plan limits were not enforced | The client sent `tier` | Server-owned entitlements | V1 (done) |
| 8 | Pro at $15 was thin | $14.00 net against $12.00 worst case | Pro $19, Plus $49 | V9, V10 |
| 9 | Pro promised 50-page SEO; crawler capped at 20 | `site.py` | 50 pages, 60 s | V6 (done) |
| 10 | Only 4 test users, one per run | Side panel has 4 personas | Custom and several test users per report | V13 (P4.2) |
| 11 | No trigger on deploy | None | Deploy webhook runs the watch scan | V12 (P3.4) |
| 12 | Free-model capacity has a ceiling | About 110 full runs a day | Daily caps counted in the database | V1 (done) |
| 13 | Rate limiter per process; checkpointer in memory | `main.py` | Daily caps in the database (done); `CHECKPOINTER=postgres` on the VM | V11 |
| 14 | Report quality gate unproven | Recall 61% on 2026-09-19 | GEO traps, recall 82% | V3 (done) |
| 15 | Evidence and PDF not verified in a real browser | T18 to T21 open | Fresh fixture run, then private, public and PDF checks | V7 |
| 16 | Not deployed on a VM, no domain | Render beta only | Domain now, API on a Google Cloud VM paid by UPI (Oracle needs a card) | V11 |
| 17 | Chrome Web Store not submitted | T13 open | Submit with the final API domain | V11a |
| 18 | Billing not built; founder has no credit card | payment.md | Concierge passes, then Dodo | V10 |
| 19 | No growth loop | Private reports | Launch Ready score and badge | V8 (done) |
| 20 | No proof anyone will pay | 0 paying users | Experiment A1 | A1 |
| 21 | GEO can overpromise | llms.txt has weak evidence | Low-impact labels; never promise citations | V2 (done) |
| 22 | Plus sold before it exists | Weekly scans not built | Plus is a waitlist until watch, tracking and branded PDF ship | V9, P3 |
| 23 | Test user never knew when to stop | Portfolio looped 11 steps | Goal planner and loop guards | V22 (done) |
| 24 | **Passive security is below the free ZAP baseline** | Header presence only (not quality), 5 exposed paths, 6 secret patterns | Security parity pass built on ported open-source rules | P1.2 |
| 25 | **Paid features promised before they were built** | The 2026-09-25 audit found missing copy review, funnel numbers, competitor comparison and TLS checks. Funnel and comparison are now built; PageSpeed still needs a free key; copy review and TLS remain planned. | SPEC now labels future checks and target dates; P0.1 and P0.2 close the implemented parts before any charge. | P0.1/P0.2/P0.4 done; P0.3/P1.2 pending |
| 26 | **First impression is shallow** | Text only, 5 fields; the briefing audit caught it rating a clear page 0 of 3 | Screenshot-based checklist with evidence, plus rewrites | P0.3 |
| 27 | **Fix prompt is generic** | One-line fix per finding; code only for GEO; the chat version cuts off with "and N more" | Stack-aware recipes, batches with checkpoints, local verify commands, exact files once a repo is connected | P1.3, P2.3 |
| 28 | **The top real risk for AI-built apps is not checked** | 98% of scanned Supabase-backed AI apps had a flaw; CVE-2025-48757 exposed 170+ Lovable databases | Read-only backend exposure check on verified domains | P1.1 |
| 29 | **GEO measures readiness only** | What Otterly ($29), Peec and Profound sell is prompt and citation tracking | Citation tracking on free engines, sources, share of voice, accuracy | P3.2, P3.3 |
| 30 | **SEO has no real search data** | No Search Console or Bing data | Connect GSC and Bing Webmaster (free APIs) | P3.1 |
| 31 | **No code access** | GitHub sign-in gives no lasting repo token | GitHub App with read-only contents; code scans on the worker VM | P2.1, P2.2 |
| 32 | **No paid model budget** | Free chain only | Deterministic first; free engines; Haiku switched on only from revenue | Build rule 2 |

## Phases

Phase 0 and Phase 1 come before launch. Each phase ends with a checkpoint the founder reviews.

### Phase 0: honest paid plans (before any charge)
Everything the plans table already promises must exist, and every claim must be true.
- **P0.1 Truth pass:** SPEC and site copy match the code (TLS, cookies); plain http on local addresses is never "high"; PageSpeed key set (founder); stable `rule` id on every finding (needed by recipes, compare and MCP).
- **P0.2 Signup funnel numbers (V18).**
- **P0.3 First impression v2 and landing copy review (V19):** screenshot-based, fixed checklist with evidence, headline, subheadline and CTA rewrites. Free vision model.
- **P0.4 Competitor side by side (V21), moved up:** it is in the Launch Pack and Pro rows today.
- **Checkpoint P0:** every row of SPEC's plans table points at working code or is marked "coming" with a date.

### Phase 1: reasons to pay (before launch)
All deterministic, all $0 in model calls.
- **P1.1 Backend exposure check:** Supabase tables readable without login (row counts only), public storage buckets, callable functions; Firebase open rules. Detection on every plan; read-only probe on verified domains.
- **P1.2 Security parity:** header quality (Mozilla HTTP Observatory and Google CSP Evaluator logic), CORS, vulnerable JavaScript libraries (retire.js data), exposed source maps, gitleaks secret patterns, more exposed paths, certificate expiry and TLS version, CAA, subdomain takeover fingerprints, SRI.
- **P1.3 Fix plan v2:** stack detection, per-stack recipes, batches with checkpoints, local verify commands, risk notes, manual steps, chat version split into batches.
- **P1.4 MCP depth:** `get_finding` and `verify_finding` (re-check one finding without a full rerun). Coordinate with the MCP owner.
- **P1.5 GEO depth pass:** port geo-optimizer-skill's remaining checks (AI discovery endpoints, freshness signals, negative signals, prompt injection in content, trust stack, RAG chunk readiness, deterministic citability score); firewall and Cloudflare AI-bot blocking; IndexNow and Bing indexing hints; Wikidata and Knowledge Graph entity check.
- **P1.6 SEO depth pass:** port checks from the MIT crawlers (hreflang, image weight and dimensions, rich-result schema validation, anchor text, internal link graph, pagination, mixed canonical and noindex), per-page Core Web Vitals on paid plans through the free PageSpeed quota.
- **P1.7 Agent readiness score:** can an AI agent complete the flow: labelled fields, accessible names, no CAPTCHA before value, stable controls, SearchAction, WebMCP hints, journey outcome.
- **Checkpoint P1:** the hard fixture gains backend, security and GEO traps; recall 85% or more with no false alarms on the easy fixture and 3 real sites.

### Launch track (in parallel, founder order: harden, pay, deploy)
V10 billing, V11 production and store, V7 evidence and PDF, V9 landing and pricing copy. See the session plan.

### Phase 2: code access (after launch, Pro and Plus)
- **P2.1 GitHub App:** the user picks repos; read-only Contents and Metadata; installation tokens; disconnect removes access.
- **P2.2 Code scans on the worker VM:** throwaway shallow clone, deleted after the scan. gitleaks (secrets), osv-scanner (vulnerable dependencies), OpenGrep engine with Walkthru's own rules for AI-built app patterns, Supabase migrations checked for RLS and policies that pass for everyone.
- **P2.3 File and line in the fix plan** for every finding the code scan can place.
- **P2.4 Nuclei with safe templates on verified domains:** exposures, misconfigurations, takeovers, technologies; `intrusive`, `dos` and `fuzz` excluded; rate limited.
- **Checkpoint P2:** a seeded fixture repo yields every planted secret, vulnerable package and open policy; nothing is left on disk after a scan.

### Phase 3: measurement (GEO and SEO depth, Plus opens)
- **P3.1 Search Console and Bing Webmaster connect:** real queries, clicks, impressions, CTR, position and indexing, joined to page findings ("ranks 11 for X at 3% CTR: rewrite the title").
- **P3.2 AI citation tracking:** suggested prompts, weekly checks on Gemini with Google Search grounding and Groq Compound (free quotas), mention, citation, position, share of voice against competitors. ChatGPT and Perplexity are labelled "not measured" until revenue pays for their APIs.
- **P3.3 Sources and accuracy:** which third-party pages AI answers cite for your category (Reddit, G2, Product Hunt, listicles) as "get listed here" actions; whether AI states your pricing and features correctly.
- **P3.4 Weekly watch and deploy webhook (V12)**, now including tracking changes.
- **P3.5 AI traffic:** AI crawler hits from an uploaded server log; AI referral visits through the GA4 Data API (optional connect).
- **P3.6 Citability rewrites:** per-page suggestions from the deterministic score, one free-chain call per page, labelled suggestions.
- **Checkpoint P3:** a tracked prompt set on the showcase site gives stable week-over-week numbers; Plus opens.

### Phase 4: Plus depth and paid engines (revenue-gated)
- **P4.1 Opt-in active scan (ZAP) of a staging URL** on a verified domain, Plus only, with a signed owner confirmation.
- **P4.2 Custom test users and several test users per report (V13).**
- **P4.3 Branded PDF.**
- **P4.4 Fix pull request from the GitHub App** (Contents write, owner approves each PR).
- **P4.5 Paid engines and Claude Haiku**, switched on only when payment.md's caps allow.
- **P4.6 Cloud runner (V14)**, only if experiment A2 missed its gate.

## Deadlines

| Milestone | Target | Realistic | Depends on |
|---|---|---|---|
| **Launch:** Free, Launch Pack and Pro with Phases 0 and 1 | Tue 2026-10-27 | **Tue 2026-11-03** | Store review, Dodo live verification, domain bought now |
| **Phase 2** (code access) | 2026-11-17 | 2026-11-24 | Google Cloud VM running the worker |
| **Plus opens** (tracking, watch, MCP, competitor compare, branded PDF) | 2026-12-08 | 2026-12-15 | Phase 3 checkpoint |
| **Self-serve checkout** | 2026-12 | After the payment.md gate | 10 reconciled passes, 30 days of cost data |

Launch moved one week (from 10-20, realistic 10-27) because Phases 0 and 1 answer "why not use the free tools?". The store submission no longer waits for the VM: `api.<domain>` points at Render first, then the VM, so the extension build never changes.

## Session plan

One session is one focused working block. Every session ends green, updates CURRENT_STATE.md and this file, and is pushed to branch `1`. Task details: `tasks/todo.md`.

**Done so far:** V1, V2, V3, V4, V5, V6, V8, V15, V16, V17, V20, V22, the v0.5 friends beta.

| # | Dates | Tasks | Done when |
|---|---|---|---|
| 16 | 09-26 to 09-27 | P0.1 truth pass; P0.2 funnel numbers (V18) | SPEC matches code; `rule` ids on every finding; funnel compares across a rerun |
| 17 | 09-28 to 09-29 | P0.3 first impression v2 and copy review (V19) | The briefing's clear page is rated clear; rewrites cite the text they replace |
| 18 | 09-30 to 10-01 | P0.4 competitor side by side (V21); **Checkpoint P0** | Side by side for 3 URLs; every plan row points at code |
| 19 | 10-02 to 10-04 | P1.1 backend exposure check | Fixture Supabase with an open table is caught, row count only, verified domain only |
| 20 | 10-05 to 10-07 | P1.2 security parity; **V11a domain and store submission** | Each new rule has a fixture trap; store listing submitted |
| 21 | 10-08 to 10-09 | P1.3 fix plan v2; P1.4 MCP depth | A Vercel and a Netlify fixture get different, correct recipes; `verify_finding` flips one finding |
| 22 | 10-10 to 10-12 | P1.5 GEO depth; P1.7 agent readiness | New GEO traps found; showcase stays 95 or more |
| 23 | 10-13 to 10-14 | P1.6 SEO depth; **Checkpoint P1** | Recall 85% or more; no false alarms on easy and 3 real sites |
| 24 | 10-15 to 10-17 | V10 billing with Dodo (test mode) | Exactly one pass per payment; forged and duplicate webhooks do nothing |
| 25 | 10-18 to 10-20 | V11b production on the VM (`CHECKPOINTER=postgres`, worker process) | Clean Chrome profile runs production end to end |
| 26 | 10-21 to 10-23 | V7 evidence and PDF; V9 landing, pricing and onboarding copy; Dodo live | Stranger path: scan, install, run, report, share, pay |
| Launch | 10-27 (11-03 at the latest) | Show HN, Product Hunt, Indie Hackers, r/SaaS, r/SideProject | |
| 27 | 10-28 to 11-03 | Fixes from real users | |
| 28 | 11-04 to 11-10 | P2.1 GitHub App; P2.2 code scans | Fixture repo findings complete; clone deleted |
| 29 | 11-11 to 11-17 | P2.3 file and line; P2.4 safe Nuclei; **Checkpoint P2** | Fix plan names files; Nuclei never runs an excluded tag |
| 30 | 11-18 to 11-24 | P3.1 GSC and Bing connect | Real queries joined to findings on the founder's site |
| 31 | 11-25 to 12-01 | P3.2 citation tracking; P3.3 sources and accuracy | Showcase prompt set tracked twice with stable numbers |
| 32 | 12-02 to 12-08 | P3.4 watch and deploy webhook; P3.5 AI traffic; P3.6 rewrites; branded PDF (P4.3); **open Plus** | One email per real change |
| 33+ | December onward | Phase 4 by revenue | |

**Founder track (now):**
- Buy the domain this week and point `api.<domain>` at Render.
- Chrome Web Store account ($5); Google Cloud VM paid by UPI prepay (Oracle needs a Visa or Mastercard card). Start on the Always Free e2-micro (1 GB) with swap and one job at a time; move to e2-small (2 GB) only if code scans or Nuclei do not fit, after measuring.
- Dodo account: start live-mode verification now.
- PageSpeed Insights key (free); Google Cloud OAuth consent screen for Search Console (the `webmasters.readonly` scope may need Google's verification, which takes time, so start before Phase 3).
- Create the GitHub App (free) before Phase 2.
- Enable Google and GitHub sign-in; rotate the Supabase secrets.

### Demand experiments (founder, 2026-09-25 to 10-04)
- **A1:** 30 free Instant Scans of real launches with a "$9 founding Launch Pack" line. **Gate:** 5 paid out of the first 100 scans.
- **A2:** 20 beta users load the extension. **Gate:** 5 or more finish a run within 48 hours. Below that, V14 moves up.
- **A3:** headline test, "Can ChatGPT read your site?" against "Find where users get stuck". **Gate:** 1.5x scan starts.
- **A4 (new):** show 10 Supabase-backed launches their backend exposure result (with permission, on their verified domain). **Gate:** 3 or more say they would pay for it; if so it leads the landing page.

## Testing Pro and Plus without spending money

- **No plan uses a paid model.** Paid depth is deterministic code, open-source scanners on the API VM, and free API quotas.
- **Plans are rows in a table.** `grant_plan.py EMAIL pro 30` makes a test account Pro for 30 days.
- **Payments:** Dodo test mode, test cards, no real money.
- **Unit tests** fake every model call and every external API. Live checks use a few free-chain runs a day.
- **Scanner tests** run against fixtures only: a fixture Supabase schema, a fixture repo with planted secrets and packages, fixture headers. Real third-party sites are scanned passively, and probes run only on the founder's own verified domains.

## Deferred on purpose
- T17B Jev benchmark.
- T22 continuous video.
- Browser-session resume.
- Findings to GitHub Issues or Linear, Slack: after Phase 3.

## Definition of done for every task
- Acceptance criteria have deterministic tests; API pytest and Ruff green; web and extension type check, lint, tests and builds green when touched.
- Every new check has a trap on the hard fixture and is absent on the easy fixture.
- Every ported rule keeps its licence notice (`apps/api/THIRD_PARTY.md`).
- Browser-facing work checked at phone and desktop widths with a clean console.
- Security-sensitive changes include an abuse-case review.
- No secrets, `.env`, build output or caches committed.
- `CURRENT_STATE.md`, `tasks/todo.md` and the affected docs match reality; commit and push to branch `1`.
