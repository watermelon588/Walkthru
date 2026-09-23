# Walkthru v1 — Task List

Definition of done: tests pass, lint clean, manual check done, SPEC updated if behavior changed.

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
