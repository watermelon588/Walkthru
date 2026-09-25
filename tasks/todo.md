# Walkthru Task List

Definition of done: see ROADMAP.md. The v1.2 flagship plan comes first, in phase order (ROADMAP.md "Phases" and "Session plan"). The v1.1 and v1 history below stays for reference. Sizes: S = 1-2 files, M = 3-5 files, L = 6+ files.

Every task follows ROADMAP.md "Build rules": deterministic first, free tier only, reuse open source after a licence check (table in docs/decisions.md, 2026-09-25 "Premium depth"), name each new dependency, never attack a site. "Reuse" lines name the repo and licence to port from. Ported rules keep their notice in `apps/api/THIRD_PARTY.md` (created by the first task that ports code).

## v1.2 flagship plan (2026-09-25)

System design and hardening tasks before going live (SD-1.1 to SD-10.4, with hardness and human flags): [docs/system-design.md](../docs/system-design.md). Claim with `- [~]` there. (added by Claude Code, 2026-09-25)

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
- [ ] **P1.2 Security parity** (L)
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
- [ ] **P1.3 Fix plan v2** (M)
  - Accept:
    - Stack detection in code from headers and HTML: Vercel, Netlify, Cloudflare, Render; Next.js, Vite, Astro, Lovable, Bolt; Supabase, Firebase.
    - A recipe per `rule` and stack (for example HSTS in `vercel.json`, `next.config.js`, `netlify.toml` or `_headers`), in a data file, no model call.
    - Batches in order (security, backend exposure, UX blockers, GEO, SEO, accessibility, performance), each ending with "stop and verify".
    - Every finding: why it matters, the change for the detected stack, the risk (CSP starts in report-only mode), and a local check (`curl -sI ... | grep -i strict-transport-security`).
    - Manual steps (DNS, hosting, email provider) listed separately.
    - The chat version is split into batches of 4,000 characters or less instead of "and N more".
  - Verify: pytest that a Vercel and a Netlify fixture get different recipes for the same rule; no secret unmasked; every finding appears once.
  - Files: `app/agent/fix_prompt.py`, `app/agent/recipes.json` (new), `app/scans/stack.py` (new), tests.
- [ ] **P1.4 MCP depth** (S, coordinate with the MCP owner first)
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
- [ ] **P1.7 Agent readiness score** (S)
  - Accept: 0 to 100 from existing evidence: labelled fields and accessible names (axe), no CAPTCHA before value, stable controls across reruns, SearchAction schema, WebMCP-style labelled forms, and whether the journey reached its goal. Shown next to the GEO score as "Can AI agents use your site?".
  - Verify: pytest over stored runs; the showcase and hard fixtures score differently for the stated reasons.
- [ ] **Checkpoint P1:** hard-fixture recall 85% or more including the new traps; easy fixture and 3 real sites have no false alarms; founder reviews one Pro report and one fix plan applied by a coding agent.

### Launch track (sessions 24 to 26)
- [ ] **V11a Domain and store submission** (session 20): `api.<domain>` on Render; production extension build; listing submitted.
- [ ] **V10 Billing with Dodo** (session 24): see the v1.1 entry below.
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
- [ ] **P3.2 AI citation tracking** (L)
  - Reuse: [ai-search-guru/getcito](https://github.com/ai-search-guru/getcito-worlds-first-open-source-aio-aeo-or-geo-tool) (MIT) for the data model (prompts, answers, mentions, citations, share of voice).
  - Accept:
    - Prompts suggested in code from the site's title, headings and category, editable by the owner.
    - Engines on free quotas: Gemini 2.5 Flash with Google Search grounding (free tier lists 500 grounded requests a day, shared; verify on our key) and Groq Compound (free-tier daily limit; `compound-mini` was retired 2026-09-21). ChatGPT and Perplexity show "not measured".
    - Mention, citation (the grounding sources), position and share of voice against named competitors, computed in code from the answer text and sources.
    - A daily cap counted in the database, like `FREE_RUNS_PER_DAY`, shares the free quota fairly; checks queue when it is used up.
    - Proposed limits: Launch Pack one snapshot of 10 prompts; Pro 10 prompts weekly on Gemini; Plus 25 prompts per site weekly on both engines.
  - Verify: pytest with recorded answers; the showcase prompt set tracked twice.
- [ ] **P3.3 Sources and accuracy** (M): sources grouped by type (the user's site, competitors, Reddit, G2, Product Hunt, YouTube, Wikipedia, listicles) with "get listed here" actions; accuracy compares the answer's price and feature claims with the site's own pages (one free-chain call per answer, labelled).
- [ ] **P3.4 Weekly watch and deploy webhook (V12)** (M): as in the v1.1 entry, plus tracking changes (a lost citation, a new competitor) in the same once-per-change email.
- [ ] **P3.5 AI traffic** (M): upload a server or Vercel log; count hits by AI crawler and status (reuse geo-optimizer-skill's `geo logs` bot list, MIT); optional GA4 Data API connect for visits referred by chatgpt.com, perplexity.ai, gemini.google.com and copilot.
- [ ] **P3.6 Citability rewrites** (S): for the 3 weakest pages by citability score, one free-chain call each, suggestions quoting the text they replace.
- [ ] **Checkpoint P3:** stable week-over-week tracking on the showcase; Plus opens with watch, tracking, MCP, competitor compare and branded PDF.

### Phase 4: Plus depth and paid engines (revenue-gated)
- [ ] **P4.1 Opt-in active scan of a staging URL** (Plus): [zaproxy/zaproxy](https://github.com/zaproxy/zaproxy) (Apache-2.0) in Docker on the worker; verified domain, an owner-entered staging URL, a signed confirmation per scan, one at a time. Never on production URLs.
- [ ] **P4.2 Custom test users and several test users per report (V13).** Ideas from [neuhai/UXAgent](https://github.com/neuhai/UXAgent) (no licence: ideas only) and [m-naw/ux-explore](https://github.com/m-naw/ux-explore) (Apache-2.0).
- [ ] **P4.3 Branded PDF for Plus.**
- [ ] **P4.4 Fix pull request** through the GitHub App (Contents and Pull requests write, a separate opt-in); the owner approves each PR.
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
- [ ] **V10 Billing with Dodo** (M), moved to v1.2 session 24
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
- [x] **V18 Signup funnel numbers** (S), completed under P0.2 on 2026-09-25
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
- [ ] **V12 Weekly watch and deploy webhook** (M), moved to P3.4
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
- [ ] Branded PDF for Plus (your logo, no Walkthru branding), moved to P4.3 (ships with Plus in session 32)
- [ ] Open Plus to the waitlist

### Session 14 (11-16 to 11-22)
- [ ] **V13 Custom test users and several test users per report** (M, Plus), moved to P4.2

### Session 15 (late November, conditional)
- [ ] **V14 Cloud runner** (moved to P4.6), only if A2 missed its gate: headless Chrome on the VM drives the built `inject.js` over CDP; public pages only, one run at a time, same safety code.

### Next versions (not scheduled)
- [ ] Preview-deploy check (GitHub Action with a PR comment)
- [ ] Findings to GitHub Issues or Linear
- [ ] AI citation tracking add-on, now P3.2 on free engines
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
- [ ] Checkpoint A: extension completes the easy fixture flow end to end

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
- [ ] Checkpoint B: ≥ 80% traps found; cost measured

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
- [ ] T14 Plans + credits + Dodo checkout + webhook + limits (M)
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
- [ ] T25 Rerun comparison, multi-persona synthesis, schedules, then integrations

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

- [ ] Replace placeholder Privacy, Terms and Security links with real pages
- [ ] Document screenshot collection, masking, retention, subprocessors and deletion
- [ ] Audit Chrome permissions and production `externally_connectable` origins
- [ ] Produce store listing, screenshots, support contact and submit T13
- [ ] Enable and verify Google and GitHub OAuth production redirects

### Billing

- [ ] Founder approves final pricing and included credits
- [ ] Implement Dodo checkout and signed, idempotent webhook handling
- [ ] Implement credit ledger, run reservation, consumption and refund rules
- [ ] Test duplicate/delayed webhook, failed checkout and refund paths

### Production

- [ ] Buy/configure production domain and HTTPS
- [ ] Deploy web with SPA rewrites and API with process supervision
- [ ] Configure production CORS, extension id, Supabase redirects, Resend and PageSpeed
- [ ] Replace per-process scan limiting with a shared production limiter
- [ ] Add structured error logging, health checks and uptime alerts
- [ ] Document database backup, restore and migration procedures
- [ ] Split web and extension bundles if the 500 kB warnings remain
- [ ] Rotate development credentials before launch

### Launch validation

- [ ] Replace placeholder screenshots with current product captures
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
