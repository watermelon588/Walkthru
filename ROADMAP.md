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
| 9 | Pro promises 50-page SEO; the crawler caps at 20 pages and 20 s | `app/scans/site.py` `MAX_MAX_PAGES = 20` | Paid scans run in the background with 50 pages and a 60 s budget | V6 |
| 10 | Only 4 test users, one per run; competitors run "flocks" | Side panel has 4 personas | Plus: custom test users and several test users merged in one report | V13 |
| 11 | No trigger on deploy (CanaryUsers runs on every push) | None | Plus deploy webhook runs the server-side watch scan | V12 |
| 12 | Free-model capacity has a ceiling | About 110 full runs a day across 3 Groq models | Global `FREE_RUNS_PER_DAY` guard with a clear message; paid runs keep the full chain; fund a paid model from revenue only | V1 |
| 13 | Rate limiter per process; checkpointer in memory | `main.py` notes both | Postgres-backed scan limiter and `CHECKPOINTER=postgres` on the production VM | V11 |
| 14 | Report quality gate unproven | Hard-fixture recall last measured at 61% (11 of 18) on 2026-09-19 | Add GEO traps, rerun the scorer, fix misses until 80% or more (Checkpoint B) | V3 |
| 15 | Evidence and PDF not verified in a real browser | T18 to T21 open | Fresh fixture run with screenshots, then private, public and PDF checks | V7 |
| 16 | Not deployed, no domain | Phase 6 open | Domain, Vercel, Oracle VM, production CORS and extension origin | V11 |
| 17 | Chrome Web Store not submitted; review takes days | T13 open | Legal pages are done; submit by 2026-10-08 | V11 |
| 18 | Billing not built; founder has no credit card | payment.md | Concierge passes: founder-granted `entitlements` rows first, then Dodo test-mode checkout and webhook | V10 |
| 19 | No growth loop | Reports are private by default and carry no mark | Public report shows the AI readiness score in its page meta, plus a "Checked by Walkthru" badge with a backlink | V8 |
| 20 | No proof anyone will pay | 0 paying users | Experiment 1 before billing code: 5 of 100 Instant Scans convert to the $9 pack | A1 |
| 21 | GEO can overpromise | llms.txt has weak evidence; a user-agent probe cannot prove real bot access | Weight llms.txt at 5 of 100 and label it; phrase the probe as "blocked for AI search user agents"; never promise citations | V2 |
| 22 | Plus sold before it exists | Weekly scans not built | Launch Plus as a waitlist; open it when watch and branded PDF ship | V9, V12 |

## Build order

```text
A  Validate demand (founder, no code) ─────────────────────────────┐
B  V1 entitlements ─▶ V2 geo-scan ─▶ V3 GEO traps + Checkpoint B      │
C  V4 rerun-compare, V5 fix-pack, V15 agent fix prompt,              │
   V6 50-page audit, V7 evidence and PDF, V8 share loop               ├─▶ Launch Oct 20
D  V9 landing and pricing copy, V10 concierge billing,               │   (Free, Launch Pack, Pro;
   V11 deploy + store submission (starts in parallel with B)         │    Plus waitlist)
E  V12 watch + deploy webhook + branded PDF ─▶ open Plus ───────────┘
F  V13 custom and multiple test users; V14 cloud runner (conditional)
G  V2 billing: self-serve checkout after payment.md's gate
```

## Phases

### Done
- **Phase 0 to 2** (2026-09-18 to 2026-09-23): the agent loop, report, site audit, evidence capture, retention, export and delete.
- **2026-09-24 additions:**
  - Truthful journeys: field state, step outcomes, safe sends, grounding.
  - The report-writer model bakeoff.
  - Privacy, Terms, Security and Docs pages.
  - Domain verification UI.

### A: Validate demand (2026-09-25 to 10-04, founder, runs alongside B)
- **A1:** post 30 free Instant Scans of real launches in Indie Hackers, r/SaaS and r/SideProject, with a "$9 founding Launch Pack" line. **Gate:** 5 paid out of the first 100 scans.
- **A2:** 20 beta users load the extension unpacked. **Gate:** 5 or more finish a run within 48 hours. Below that, V14 moves up.
- **A3:** headline test, "Can ChatGPT read your site?" against "Find where users get stuck". **Gate:** the GEO headline gets 1.5x or more scan starts. If it wins, it leads the landing page (V9).

### B: Foundation (2026-09-25 to 10-02)
- **Outcome:** the server owns the plan, and GEO appears in every report.
- **Tasks:** V1 entitlements, V2 geo-scan, V3 GEO traps and Checkpoint B.
- **Gate:**
  - A free account cannot exceed its limits through a crafted request.
  - Instant Scan shows the AI readiness score in 20 s or less.
  - Hard-fixture trap recall is 80% or more.

### C: Paid value (2026-10-03 to 10-11)
- **Outcome:** Pro is worth $19 without counting runs.
- **Tasks:** V4 rerun-compare, V5 fix-pack, V15 agent fix prompt, V6 50-page paid audit, V7 evidence and PDF, V8 share loop.
- **Gate:**
  - A rerun on the fixture shows correct fixed, still broken and new lists.
  - The fix pack produces valid JSON-LD and robots rules for the SPA fixture.
  - A PDF with screenshots prints correctly.

### D: Ship (2026-10-01 to 10-18, parallel)
- **Outcome:** strangers can install, pay and use it in production.
- **Tasks:** V9 landing and pricing copy, V10 concierge billing, V11 deploy, security hardening and store submission (by 10-08).
- **Gate:** a clean Chrome profile installs the store build, signs in, runs a test, gets the report, shares it and receives a founder-approved Dodo test-mode pass.

### Launch: Tuesday 2026-10-20
- **Sold:** Free, Launch Pack and Pro. Plus is a waitlist.
- **Channels:** Show HN, Product Hunt, Indie Hackers, r/SaaS, r/SideProject, and build-in-public posts. Every post offers a free AI readiness score.

### E: Retention (2026-10-21 to 11-15)
- **Tasks:** V12 weekly watch, deploy webhook and branded PDF. Then open Plus to the waitlist.
- **Gate:**
  - A deploy that blocks OAI-SearchBot on the fixture sends exactly one alert email.
  - An unchanged week sends none.

### F: Depth (2026-11)
- **V13:** custom test users and several test users per report.
- **V14:** cloud runner, only if A2 failed.
- **Also:** evaluate an AI citation-tracking add-on for Plus, and a paid model funded by revenue (payment.md caps).

### G: Self-serve billing
- Replace founder approval with instant checkout only after payment.md's V2 gate: 10 reconciled passes, 30 days of cost data, and a tested spend cap.

## Candidate features (proposed 2026-09-24, founder picks)

| Feature | Plan | Why an indie founder pays for it | Size | When |
|---|---|---|---|---|
| **Ignore a finding** ("won't fix" with a reason) | Pro | Reruns, the fix prompt and watch alerts stop repeating accepted items. Without it, Plus alerts become noise | S | Before launch |
| **Launch Ready score and live badge** | Free | One number across UX, GEO, SEO, security and speed. The badge is an embeddable image showing the latest score: a backlink on every site that shows it | S | Before launch |
| **Signup email check** | Free: SPF and DMARC. Paid: full | Signups die when confirmation emails fail. Checks the domain's email DNS records passively over DNS-over-HTTPS, with no new dependency. Recognizes auth-provider email limits, such as Tripverse's "email rate limit exceeded" from Supabase's built-in mailer, and gives the fix (your own SMTP) | S | Before launch |
| **Walkthru for coding agents** (MCP server plus personal API key) | Plus | Claude Code or Cursor can run a scan, read the fix prompt, fix the code, and rerun to verify, without leaving the editor | M | After launch, with Plus |
| **Competitor side by side** (up to 3 URLs) | Pro | "How does my landing page, GEO and SEO compare to theirs?" Passive scans only; deep security stays owner-only | M | After launch |
| **Signup funnel numbers** | Pro | Steps to sign up, form fields, errors seen, time to the first useful screen, compared across reruns. Deterministic from the journey | S | After launch |
| **Preview-deploy check** (GitHub Action with a PR comment) | Plus | Catches a GEO, SEO or security regression before merge. Journeys join once the cloud runner exists | M | After watch |
| **Findings to GitHub Issues or Linear** | Plus | One click per finding, with evidence | M | After Plus has users |
| **Landing copy review** | Launch Pack and up | Headline, call-to-action and pricing clarity with rewrite options. One model call, labeled as suggestions | S | Optional |

**Not planned:**
- **Uptime monitoring:** free tools already do it.
- **Active checks such as database or RLS probing:** these break the passive-only rule.
- **Heatmaps and analytics:** a different product.

## Deferred on purpose
- T17B Jev benchmark.
- T22 continuous video.
- Browser-session resume.
- Slack, Linear and GitHub integrations: after Plus has paying users.

## Definition of done for every task
- Acceptance criteria have deterministic tests; API pytest and Ruff green; web and extension type check, lint, tests and builds green when touched.
- Browser-facing work checked at phone and desktop widths with a clean console.
- Security-sensitive changes include an abuse-case review.
- No secrets, `.env`, build output or caches committed.
- `CURRENT_STATE.md`, `tasks/todo.md` and the affected docs match reality; commit and push to branch `1`.
