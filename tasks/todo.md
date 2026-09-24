# Walkthru Task List

Definition of done: see ROADMAP.md. The v1.1 plan comes first, in session order (ROADMAP.md "Session plan"). The v1 history below stays for reference. Sizes: S = 1-2 files, M = 3-5 files.

## v1.1 plan (updated 2026-09-24)

### Founder track (in parallel with sessions 1 to 6)
- [x] Confirm prices: Pro $19 and Plus $49, founding $15 and $39 (2026-09-24)
- [ ] A1: 30 free Instant Scans with a "$9 founding Launch Pack" line. Gate: 5 paid of the first 100 scans.
- [ ] A2: 20 beta users on the unpacked extension. Gate: 5 or more finish a run within 48 hours.
- [ ] A3: headline test, "Can ChatGPT read your site?" against "Find where users get stuck". Gate: 1.5x scan starts.
- [ ] Buy the domain by 10-05; Chrome Web Store account ($5); Oracle VM; Dodo account, with live-mode verification started now
- [ ] Enable Google and GitHub sign-in; rotate Supabase secrets before session 6

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
- [ ] **V11 Production and store** (M)
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
- [ ] **V10 Billing with Dodo** (M)
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
- [ ] **V7 Evidence and PDF close-out (T18 to T21)** (S)
  - Accept: a fresh screenshot-backed fixture run; private, public and printed PDF views all show step evidence.
- [ ] **V18 Signup funnel numbers** (S)
  - Accept: `report.funnel` on paid runs holds steps to the goal, fields typed, errors seen, safe stops and time to the first useful screen; compared across reruns.
  - Verify: pytest over stored steps.
- [ ] **V19 Landing copy review** (S)
  - Accept: one free-chain model call on homepage and pricing text; verdicts and up to 3 rewrite options, labeled as suggestions; paid runs only.
  - Verify: pytest with a fake model.

### Session 10 (10-16 to 10-18)
- [ ] **V9 Landing, pricing and onboarding copy** (S)
  - Accept: the "launch check for apps built with AI" hero; the SPEC.md plans table; Plus as a waitlist; onboarding for install, permissions and domain verification.
  - Verify: web build and lint; phone and desktop check.
- [ ] Switch Dodo to live once verification clears

#### Checkpoint D (launch gate)
- [ ] Stranger path in production: scan, install, run, report, share, paid pass
- [ ] Launch Tue 2026-10-20, 2026-10-27 at the latest

### Session 11 (10-21 to 11-01)
- [ ] Fix what real users hit in launch week
- [ ] **V12 Weekly watch and deploy webhook** (M)
  - Accept: `sites` table; a weekly job scans due sites and emails only on change; `POST /hooks/deploy/{token}` at most once per 10 minutes.
  - Verify: a blocked AI crawler on the fixture sends exactly one email; an unchanged week sends none.

### Session 12 (11-02 to 11-08)
- [ ] **V20 Walkthru MCP server** (M)
  - Accept:
    - A remote MCP server at `/mcp` (streamable HTTP, official `mcp` Python SDK).
    - Personal API keys in `api_keys`: shown once, stored as SHA-256, revocable. Plus only.
    - Tools: `scan_site`, `get_report`, `get_fix_prompt`, `rerun`, `list_runs`.
    - The same limits as the web API.
  - Verify: Claude Code connects with a Plus key, scans the fixture, reads the fix prompt and reruns; a revoked or non-Plus key is refused.

### Session 13 (11-09 to 11-15)
- [ ] **V21 Competitor side by side** (M)
  - Accept: `POST /compare` with up to 3 URLs; passive scans only, no deep security on unverified sites; side-by-side report.
  - Verify: pytest and one live comparison.
- [ ] Branded PDF for Plus (your logo, no Walkthru branding)
- [ ] Open Plus to the waitlist

### Session 14 (11-16 to 11-22)
- [ ] **V13 Custom test users and several test users per report** (M, Plus)

### Session 15 (late November, conditional)
- [ ] **V14 Cloud runner**, only if A2 missed its gate: headless Chrome on the VM drives the built `inject.js` over CDP; public pages only, one run at a time, same safety code.

### Next versions (not scheduled)
- [ ] Preview-deploy check (GitHub Action with a PR comment)
- [ ] Findings to GitHub Issues or Linear
- [ ] AI citation tracking add-on
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
