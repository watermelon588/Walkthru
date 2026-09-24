# Walkthru Roadmap v1.1

_Updated 2026-09-24. Product: [SPEC.md](SPEC.md). System: [ARCHITECTURE.md](ARCHITECTURE.md). Tasks with acceptance criteria: [tasks/todo.md](tasks/todo.md). Evidence behind this plan: `founder/competitor-matrix.md`, `founder/pricing-strategy.md`, `founder/validate-idea.md`._

## Finish line

Walkthru is launched when a stranger can:
1. Get a free Instant Scan with an AI readiness score and see what AI search sees.
2. Install the extension, test a public or logged-in flow safely, and get a truthful evidence report.
3. Fix things and rerun to see what changed.
4. Share the report.
5. Pay for a pass.

The server must enforce every plan limit.

## Weak points in the current plan, and the exact fix

Found in the 2026-09-24 review. Each fix has a task in `tasks/todo.md`.

| # | Weak point | Evidence | Exact fix | Task |
|---|---|---|---|---|
| 1 | "AI test users" is a crowded category | Meerkat, CanaryUsers, Swarm and Uxia all sell it; CanaryUsers from $9 | Reposition as "the launch check for apps built with AI": journeys, SEO, GEO and security in one report | V9 |
| 2 | Paid plans mostly sell volume | Pro's list was runs, export and email | Paid value is where the test goes (logged-in pages) and what happens over time (compare, fix pack, watch, branded PDF) | V4, V5, V12 |
| 3 | Nothing brings a user back after launch week | No reruns, schedules or alerts | Rerun and compare in Pro; weekly watch and deploy webhook in Plus | V4, V12 |
| 4 | Free tier looks tiny next to Meerkat (about 170 runs in month one against our 3) | Free-provider capacity is about 110 full runs a day for all users | Compete on the no-install Instant Scan: 10 pages of SEO, GEO, security and "what AI search sees", same quality as paid. Keep journeys at 3 a month. | V2, V8 |
| 5 | Journeys need an extension; every competitor starts from a URL | Install step before first value | Instant Scan gives value with no install. Measure the extension funnel (experiment 2); build the cloud runner only if fewer than 25% finish a run | A2, V14 |
| 6 | No GEO while search moves to AI answers | No module | Deterministic GEO scanner in every plan, fix pack in paid plans, GEO watch in Plus | V2, V5, V12 |
| 7 | **Plan limits are not enforced** | The client sends `tier`; `logged_in` is open to everyone; the side panel hardcodes 12 steps | Server-owned entitlements; `POST /runs` clamps everything; `GET /me/plan` | V1 |
| 8 | Pro at $15 is thin; Team at $39 with 250 runs loses money at $0.20 a run | $14.00 net against $12.00 worst-case cost; $37.04 net against $50.00 | Pro $19 (founding $15, 40 runs); Plus $49 (founding $39, 150 runs) | V9, V10 |
| 9 | Pro promises 50-page SEO; the crawler caps at 20 pages and 20 s | `app/scans/site.py` `MAX_MAX_PAGES = 20` | Paid scans run in the background with 50 pages and a 60 s budget | V6 (done 2026-09-24) |
| 10 | Only 4 test users, one per run; competitors run "flocks" | Side panel has 4 personas | Plus: custom test users and several test users merged in one report | V13 |
| 11 | No trigger on deploy (CanaryUsers runs on every push) | None | Plus deploy webhook runs the server-side watch scan | V12 |
| 12 | Free-model capacity has a ceiling | About 110 full runs a day across 3 Groq models | Global `FREE_RUNS_PER_DAY` guard with a clear message; paid runs keep the full chain; fund a paid model from revenue only | V1 |
| 13 | Rate limiter per process; checkpointer in memory | `main.py` notes both | Postgres-backed scan limiter and `CHECKPOINTER=postgres` on the production VM | V11 |
| 14 | Report quality gate unproven | Hard-fixture recall last measured at 61% (11 of 18) on 2026-09-19 | Add GEO traps, rerun the scorer, fix misses until 80% or more (Checkpoint B) | V3 |
| 15 | Evidence and PDF not verified in a real browser | T18 to T21 open | Fresh fixture run with screenshots, then private, public and PDF checks | V7 |
| 16 | Not deployed, no domain | Phase 6 open | Domain, Vercel, Oracle VM, production CORS and extension origin | V11 |
| 17 | Chrome Web Store not submitted; review takes days | T13 open | Legal pages are done; submit by 2026-10-08 | V11 |
| 18 | Billing not built; founder has no credit card | payment.md | Concierge passes: founder-granted `entitlements` rows first, then Dodo test-mode checkout and webhook | V10 |
| 19 | No growth loop | Reports are private by default and carry no mark | Launch Ready score, live badge with a backlink, score in public report meta | V8 |
| 20 | No proof anyone will pay | 0 paying users | Experiment 1 before billing code: 5 of 100 Instant Scans convert to the $9 pack | A1 |
| 21 | GEO can overpromise | llms.txt has weak evidence; a user-agent probe cannot prove real bot access | Weight llms.txt at 5 of 100 and label it; phrase the probe as "blocked for AI search user agents"; never promise citations | V2 |
| 22 | Plus sold before it exists | Weekly scans not built | Launch Plus as a waitlist; open it when watch and branded PDF ship | V9, V12 |
| 23 | The test user followed the typed goal literally and never knew when to stop | A real portfolio run circled four "NEXT CASE" pages for 11 steps, then the report blamed the site | Goal planner (intent plus checklist, finished in code), looping guard, scroll position, owner Stop never counted as a site problem, suggested goals | V22 (done 2026-09-24) |

## Scope (decided 2026-09-24)

- **Prices:** confirmed. Pro $19 (founding $15), Plus $49 (founding $39), Launch Pack $9, Free.
- **Features by plan:** SPEC.md has the table.
- **Accepted:**
  - GEO readiness.
  - The agent fix prompt.
  - Rerun and compare.
  - Ignore a finding.
  - The Launch Ready score and badge.
  - The signup email check.
  - Signup funnel numbers.
  - The landing copy review.
  - Competitor side by side.
  - The Walkthru MCP server (Plus).
  - Weekly watch with a deploy webhook (Plus).
  - Custom test users (Plus).
- **Next versions, not in this roadmap:**
  - The preview-deploy check (GitHub Action).
  - Findings to GitHub Issues or Linear.
  - AI citation tracking.

## Deadlines

| Milestone | Target | Realistic | Depends on |
|---|---|---|---|
| **Launch:** Free, Launch Pack and Pro, live Dodo payments through founder-approved passes | Tue 2026-10-20 | **Tue 2026-10-27** | Chrome Web Store review, Dodo live-mode verification, domain and VM ready by 10-06 |
| **Plus opens** (watch, MCP, competitor compare, branded PDF) | 2026-11-15 | **2026-11-22** | Launch stable; watch email tested |
| **Self-serve checkout** (no founder approval) | 2026-12 | After the payment.md gate | 10 reconciled passes, 30 days of cost data, a tested spend cap |

**Why the buffer week:**
- **Chrome Web Store review** can take days, longer for a new developer account. The extension needs the production API address, so it cannot be submitted before deploy (session 6).
- **Dodo live mode** needs the business verified. That timeline is on Dodo's side, so start it now.
- **All build work** fits inside 10-20; the buffer only covers those two outside waits.

## Session plan

One session is one focused working block with Claude. Every session:
- Ends green (tests, lint, builds).
- Updates CURRENT_STATE.md and this file.
- Is pushed to branch `1`.

Task details and acceptance criteria are in `tasks/todo.md`.

| # | Dates | Tasks | Done when |
|---|---|---|---|
| 1 | 09-25 to 09-26 | V1 server-owned plans, dev grant script, `GET /me/plan`, runs left in side panel and dashboard | A crafted free request cannot exceed any limit; `grant_plan.py` switches a test account to Pro and back |
| 2 | 09-27 to 09-29 | V2 GEO readiness scanner and report section | The portfolio's Instant Scan shows a GEO score and "What AI search sees" in 20 s or less |
| 2b | 09-24 (done) | V22 goal intent and loop guards, suggested goals, showcase test site | Portfolio goal plans to 3 checkpoints; circles end as `looping`; showcase scores 99 |
| 3 | 09-30 to 10-01 | V3 GEO traps and Checkpoint B; V16 signup email check | Trap recall 80% or more; Tripverse's email error maps to "use your own SMTP" |
| 4 | 10-02 to 10-03 | V4 rerun and compare; V17 ignore a finding | 3 fixture reruns match a hand check; ignored items leave lists but stay in the score |
| 5 | 10-04 to 10-05 | V5 GEO fix pack; V15 agent fix prompt | Fix prompt for the SPA fixture lists every finding once, secrets masked; free gets 402 |
| 6 | 10-06 to 10-08 | V11 production: domain, Vercel, API on the VM, `CHECKPOINTER=postgres`, shared scan limiter, CORS and extension origin, secrets rotated; **store submission on 10-08** | A clean Chrome profile runs the production build end to end |
| 7 | 10-09 to 10-10 | V8 Launch Ready score, badge and share loop; V6 50-page paid audit | Badge SVG shows the latest score; Pro audit covers 50 pages in 60 s or less |
| 8 | 10-11 to 10-13 | V10 billing: access request, founder approval, Dodo test checkout, signed idempotent webhook, entitlement grant | Test-mode payment grants exactly one pass; duplicate and forged webhooks do nothing |
| 9 | 10-14 to 10-15 | V7 evidence and PDF close-out; V18 signup funnel numbers; V19 landing copy review | PDF with screenshots prints; funnel numbers compare across a rerun |
| 10 | 10-16 to 10-18 | V9 landing page, pricing and onboarding copy; Checkpoint D; switch Dodo to live after verification | A stranger goes from scan to install to report to paid pass, in production |
| Launch | 10-20 (10-27 at the latest) | Show HN, Product Hunt, Indie Hackers, r/SaaS, r/SideProject | |
| 11 | 10-21 to 11-01 | Fixes from real users; V12 weekly watch and deploy webhook | A blocked AI crawler on the fixture sends exactly one email |
| 12 | 11-02 to 11-08 | V20 Walkthru MCP server and API keys | Claude Code scans, reads the fix prompt and reruns through MCP with a Plus key |
| 13 | 11-09 to 11-15 | V21 competitor side by side; branded PDF; **open Plus** | Side-by-side report for 3 URLs; PDF without Walkthru branding |
| 14 | 11-16 to 11-22 | V13 custom test users and several test users per report | Plus user defines a test user and gets one merged report |
| 15 | late 11 | V14 cloud runner, only if experiment A2 missed its gate | Public journey runs without the extension |

**Founder track, in parallel with sessions 1 to 6:**
- Experiments A1 to A3 (below).
- Buy the domain.
- Chrome Web Store account ($5).
- Oracle VM.
- Dodo account: start live-mode verification now.
- Enable Google and GitHub sign-in.
- Rotate the Supabase secrets.

### Demand experiments (founder, 2026-09-25 to 10-04)
- **A1:** 30 free Instant Scans of real launches in Indie Hackers, r/SaaS and r/SideProject, with a "$9 founding Launch Pack" line. **Gate:** 5 paid out of the first 100 scans.
- **A2:** 20 beta users load the extension unpacked. **Gate:** 5 or more finish a run within 48 hours. Below that, V14 moves up.
- **A3:** headline test, "Can ChatGPT read your site?" against "Find where users get stuck". **Gate:** 1.5x or more scan starts for the GEO headline, which then leads the landing page.

## Testing Pro and Plus without spending money

- **No plan uses a paid model.** Every paid feature is deterministic code or the same free model chain as free reports. Paid plans sell reach and follow-up, not a better model.
- **Plans are rows in a table.** `grant_plan.py EMAIL pro 30` makes a test account Pro for 30 days. One account per plan covers Free, Launch Pack, Pro and Plus.
- **Payments:** Dodo test mode, test cards, no real money. Webhooks reach the local API through a tunnel, then the VM.
- **Unit tests** fake every model call. Live checks use a few free-chain runs a day.
- **Only cost before launch:** the $5 store fee and the domain. A paid model is added only after revenue, within payment.md's caps.

## Deferred on purpose
- T17B Jev benchmark.
- T22 continuous video.
- Browser-session resume.
- Preview-deploy check, GitHub Issues and Linear export, Slack: next versions.

## Definition of done for every task
- Acceptance criteria have deterministic tests; API pytest and Ruff green; web and extension type check, lint, tests and builds green when touched.
- Browser-facing work checked at phone and desktop widths with a clean console.
- Security-sensitive changes include an abuse-case review.
- No secrets, `.env`, build output or caches committed.
- `CURRENT_STATE.md`, `tasks/todo.md` and the affected docs match reality; commit and push to branch `1`.
