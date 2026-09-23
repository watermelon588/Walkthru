# Walkthru Task List

Definition of done: see ROADMAP.md. The v1.1 plan (2026-09-24) comes first; the v1 history below it stays for reference.

## v1.1 plan (2026-09-24)

Order: A runs alongside B. Then C, with D in parallel from 10-01. Launch 10-20, then E and F. Sizes: S = 1-2 files, M = 3-5 files.

### Founder
- [ ] A1 Post 30 free Instant Scans with a "$9 founding Launch Pack" line. Gate: 5 paid of the first 100 scans.
- [ ] A2 Recruit 20 beta users for the unpacked extension. Gate: 5 or more finish a run within 48 hours.
- [ ] A3 Headline test: "Can ChatGPT read your site?" against "Find where users get stuck". Gate: 1.5x or more scan starts.
- [ ] Confirm list prices $19 and $49 (founding $15 and $39), or name others, before V9 changes the landing page.
- [ ] Buy the domain; Chrome Web Store account ($5); Oracle VM; Dodo test mode; enable Google and GitHub sign-in; rotate Supabase secrets.

### Phase B: foundation
- [ ] **V1 Server-owned entitlements** (M)
  - Accept: `POST /runs` ignores client `tier`; a free user gets 403 on `logged_in`, 12 steps at most, first-time visitor only, 402 after 3 runs this month; an active `entitlements` row lifts the limits to its plan; `GET /me/plan` returns plan, limits and runs left; `FREE_RUNS_PER_DAY` stops free runs with a clear message.
  - Verify: pytest for each limit with a crafted request; the side panel shows runs left.
  - Files: `apps/api/app/plans.py` (new), `app/main.py`, `app/db.py`, `schema.sql`, `apps/extension/entrypoints/sidepanel/App.tsx`.
- [ ] **V2 GEO readiness scanner** (M)
  - Accept: `app/scans/geo.py` scores the 7 categories in SPEC.md from pages the audit already fetched, plus `GET /llms.txt` and one citation-bot user-agent probe; findings use `kind="geo"`; `report.geo` has score, band and categories; free scans score the homepage only; the first-impression block is labeled "What AI search sees"; llms.txt is labeled low impact; the probe is worded as a user-agent check.
  - Verify: pytest per category on fixture HTML (SPA shell, blocked OAI-SearchBot, valid and broken JSON-LD, missing H1); live Instant Scan of the portfolio returns a score in 20 s or less.
  - Files: `app/scans/geo.py` (new), `app/agent/schema.py`, `app/agent/report.py`, `apps/web/src/components/ReportView.tsx`, `tests/test_geo.py` (new).
- [ ] **V3 GEO traps and Checkpoint B** (S)
  - Accept: the hard fixture gains 3 GEO traps (robots blocks OAI-SearchBot, a JavaScript-only pricing page, no Organization schema) in `traps.json`; the scorer runs on today's code; misses fixed until recall is 80% or more.
  - Verify: scorer output saved in `docs/decisions.md`.
  - Files: `evals/fixtures/hard/*`, `evals/traps.json`, scan fixes as needed.

#### Checkpoint B
- [ ] pytest, Ruff, web and extension builds green
- [ ] Crafted free request cannot exceed limits
- [ ] Recall is 80% or more; founder reviews one GEO report

### Phase C: paid value
- [ ] **V4 Rerun and compare** (M)
  - Accept: `runs.parent_run_id`; `rerun_of` on `/runs` and `/scans`, owner and same origin checked; `report.comparison` lists fixed, still broken and new by fingerprint (kind, normalized title, URL path), computed in code; report page shows the three lists and a "Rerun" button.
  - Verify: pytest for fingerprint and diff; 3 fixture reruns match a hand check.
  - Files: `schema.sql`, `app/main.py`, `app/agent/report.py`, `ReportView.tsx`, `Report.tsx`.
- [ ] **V5 GEO fix pack** (S)
  - Accept: `app/scans/geo_fixes.py` returns a robots.txt block, JSON-LD (Organization, WebSite, SoftwareApplication), an llms.txt draft and a framework rendering fix (Vite SPA, Next.js, Lovable, Astro); paid plans see all, free sees one; copy buttons.
  - Verify: pytest that generated JSON-LD parses and robots rules allow the citation bots; SPA fixture gets the Vite fix.
  - Files: `app/scans/geo_fixes.py` (new), `app/agent/report.py`, `ReportView.tsx`, `tests/test_geo_fixes.py` (new).
- [ ] **V6 50-page paid site audit** (S)
  - Accept: paid scans use `max_pages=50` and a 60 s budget in a background task; Instant Scan stays at 10 pages and 20 s; coverage shows what was checked.
  - Verify: pytest with a fake 60-page site; free stays 10.
  - Files: `app/scans/site.py`, `app/main.py`.
- [ ] **V7 Evidence and PDF close-out (T18 to T21)** (S)
  - Accept: a fresh screenshot-backed fixture run; private, public and printed PDF views all show step evidence.
  - Verify: manual browser and print check, recorded in CURRENT_STATE.md.
- [ ] **V8 Share loop** (S)
  - Accept: public report `<title>` and description carry the AI readiness score; a "Checked by Walkthru" badge snippet with a backlink on shared reports; the owner can turn it off on paid plans.
  - Verify: page meta checked in the browser; badge links to the landing page.
  - Files: `apps/web/src/pages/Public.tsx`, `ReportView.tsx`, `content.ts`.

#### Checkpoint C
- [ ] Rerun, fix pack and PDF verified on fixtures
- [ ] Founder reviews one full Pro report before launch copy is written

### Phase D: ship (from 10-01, parallel)
- [ ] **V9 Landing and pricing copy** (S): "launch check for apps built with AI" hero, the SPEC.md plans table, Plus as a waitlist, GEO in every plan; `content.ts` only. Verify: web build, lint, phone and desktop check.
- [ ] **V10 Concierge billing** (M): founder inserts `entitlements` rows; then a Dodo test-mode checkout and a signed, idempotent webhook that inserts the row (payment.md). Verify: duplicate webhook grants once; forged signature rejected.
- [ ] **V11 Production and store** (M): domain, Vercel with SPA rewrites, API on the VM under supervision, `CHECKPOINTER=postgres`, Postgres-backed scan limiter, production CORS and extension origin, secrets rotated, store listing submitted by 10-08. Verify: clean-profile store build completes a run in production.

#### Checkpoint D (launch gate)
- [ ] Stranger path: scan, install, run, report, share, pass granted, all in production
- [ ] Launch Tue 2026-10-20: Free, Launch Pack, Pro; Plus waitlist

### Phase E: retention (after launch)
- [ ] **V12 Watch** (M)
  - Accept: `sites` table; weekly job scans due sites (`kind='watch'`), compares with the last watch run, emails only on change; `POST /hooks/deploy/{token}` triggers it, at most once per 10 minutes; branded PDF for Plus.
  - Verify: fixture deploy that blocks OAI-SearchBot sends exactly one email; an unchanged week sends none.
  - Then: open Plus to the waitlist.

### Phase F: depth (November)
- [ ] **V13 Custom test users and several test users per report** (M, Plus)
- [ ] **V14 Cloud runner** (M): only if A2 misses its gate. Headless Chrome on the VM drives the built `inject.js` over CDP (as `evals/e2e_extension.py` does), public pages only, one concurrent run, same safety code.
- [ ] Evaluate an AI citation-tracking add-on for Plus; paid model funded from revenue within payment.md caps.

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
