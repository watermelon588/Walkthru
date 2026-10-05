# Architecture

## System overview
```
Chrome extension (user's browser)               Walkthru API (FastAPI + LangGraph)
────────────────────────────────                ───────────────────────────────────
side panel: pick site, goal, test user ── POST /runs ──────▶ create run + LangGraph thread
content script: snapshot + axe + vitals ── POST /runs/{id}/observe ─▶ persona agent decides
  (URL, numbered buttons/links/inputs,  ◀── next action ──── click #12 | type #4 "..." | scroll | wait | done | give_up
   visible text, errors; PII masked)
executes the action in the real tab
masks fields + captures bounded JPEG    ── private Storage object + evidence metadata ─▶ exact run step
                                        ... loop until done / give_up / step budget ...
                                                               synthesize report ─▶ Supabase ─▶ report page + email
Server-only scans (no browser): accessibility basics (HTML structure and names), mobile performance (PageSpeed API), SEO (HTML, robots, sitemap), GEO readiness (AI crawler access, content before JavaScript, structured data, answerability), and security hygiene (headers, cookies, public files, secrets in JS). Planned in v1.2: header quality, TLS, vulnerable libraries, backend exposure, citation tracking, Search Console data, and a VM worker for repository code scans and safe Nuclei templates.

Web app (React)  ──  Supabase Auth (JWT)  ──  API verifies JWT on every call; the API decides the plan
Payments (V1): founder approves ─▶ private Dodo checkout ─▶ signed webhook ─▶ API ─▶ entitlements table
```

## Components
| Part | Tech | Status |
|---|---|---|
| Web (landing, login, dashboard, report) | React 19, Vite, TypeScript, Tailwind v4, GSAP + @gsap/react, Phosphor icons, Geist | Landing, login, dashboard, private report, and public report built |
| Auth | Supabase Auth: Google, GitHub, email magic link. API validates bearer tokens via Supabase Auth (`app/auth.py`) | Live; OAuth providers still to enable in dashboard |
| API | Python 3.12+, FastAPI, LangGraph + Postgres checkpointer, httpx | `/health`, `/runs` step API, persona graph |
| Agent models | Default: Groq `openai/gpt-oss-120b` primary, Gemini `gemini-3.1-flash-lite` fallback. Experimental: TypeSafe Jev `jev-1.13.0` for bounded browser decisions with confidence-gated LLM fallback. Paid: Claude candidate after T9 eval | Free pool live; Jev adapter built and opt-in |
| Extension | Chrome MV3, TypeScript, WXT, React side panel, axe-core | Built: snapshot, redaction, executor, step loop, Scout status, bounded screenshot evidence, WCAG A/AA checks and Core Web Vitals. Real easy-fixture run works; diagnostics rerun pending rebuilt-extension verification |
| Data | Supabase Postgres (RLS on every table) + private Storage (screenshots) | `runs` table + RLS live; `run-evidence` bucket and owner/public-report policies are declared in `apps/api/migrations/0001_initial.sql` and applied |
| Evals and tracing | LangSmith | Keys set, project `Walkthru` |
| Email | Resend (`app/deliver.py`, REST, no SDK) | Built; needs `RESEND_API_KEY` |
| Payments | Dodo Payments (test mode first) | Built, awaiting founder keys (docs/billing.md) |
| Hosting | Vercel (web), Render free (beta API), then a Google Cloud VM paid by UPI prepay (API and worker; Oracle needs a card) | Beta config done |

## Key decisions
1. **Browser runs on the user's machine, brain on our server.** No Chromium on our server, hosting stays $0-5, logged-in pages work without sharing passwords.
2. **Step loop lives in the extension side panel page**, not the MV3 service worker (Chrome suspends workers after ~30 s idle). Chrome does not reliably grant `activeTab` to side panels and `captureVisibleTab` only accepts `activeTab` or `<all_urls>`, so Start Test requests the optional broad host permission in a one-time Chrome prompt. It is used only for the active test tab.
3. **One HTTP call per agent step.** LangGraph `interrupt()` emits the action; `Command(resume=observation)` continues. Postgres checkpointer holds state, so the API is stateless between calls. If the browser journey ends early, authenticated `POST /runs/{id}/stop` atomically marks the run stopped, labels the unconfirmed action as interrupted and starts a partial report.
   Run start/observe/stop accept one UUID `Idempotency-Key` per intent. A service-only PostgreSQL ledger replays completed replies, blocks simultaneous keyed mutations of a run and rejects changed bodies. Running replies include a checkpoint action ID; keyed observations must match it. Unknown outcomes are held for investigation, never automatically re-executed. The extension retries only the frozen HTTP request after API capability negotiation. Legacy no-key clients retain their old behavior without these guarantees. Migration 0003 and deployment details: [run idempotency](docs/run-idempotency.md).
4. **Text snapshot first, screenshots rarely** (first impression and when stuck). Tokens are the main cost.
5. **Plain code wherever possible.** Accessibility, performance, SEO and security checks are deterministic integrations. LLMs explain and prioritize the evidence; only the persona session is an agent.
6. **Passive security only, on verified domains** (meta tag, DNS TXT or well-known file).
7. **Runs, not tokens,** for billing. One run = one persona journey; plans include a run allowance (SPEC.md). Tokens logged per run for margins.
8. **react-router** for `/`, `/login`, `/app`, `/app/runs/:id`. Production host must rewrite all paths to `index.html` (Vercel: `rewrites` in vercel.json).
9. **Reads bypass the API.** The web app reads `runs` straight from Supabase under RLS; only the API (postgres role) writes. Fewer endpoints, and the DB enforces ownership.
10. **Extension session handoff.** The dashboard sends the Supabase session to the extension id in `VITE_EXTENSION_ID` through `externally_connectable`; the extension refreshes it against Supabase and sends it as a bearer token.
11. **Decision providers are replaceable, LangGraph is not.** The persona graph owns state, interrupts, budgets, and termination. A Jev provider may choose bounded operations and targets; the existing LLM remains responsible for open-ended generation and fallback. Safety stays in deterministic code. Provider calls share a process-local circuit breaker: three failures trigger a 60-second cooldown, then one recovery probe. Citation checks preserve their queue during cooldown. [Timeouts, concurrency and verification](docs/provider-resilience.md).
12. **Step evidence is private and bounded.** The extension captures at most eight JPEG frames per run after meaningful actions, hides Scout and masks form controls for the captured paint, then uploads directly to the private `run-evidence` bucket with the user's JWT. The API only accepts a screenshot path beneath the current run id. Reports request one-hour signed URLs; public reports can read evidence only when the owning run is public.
13. **Browser diagnostics belong to journey steps.** The injected script runs bounded axe WCAG A/AA checks and observes LCP, CLS and INP in the tested tab. Each post-action observation is validated by the API and attached to the exact LangGraph step. Deterministic report code turns failing thresholds into prioritized findings; the LLM explains and ranks but does not invent these measurements.

14. **The server owns the plan.** The client never says which tier it is. `POST /runs` reads the caller's entitlement and clamps steps, logged-in access, test user, site and monthly runs before a LangGraph thread exists.
    Anonymous `POST /scans` reuses the newest completed public, free, ownerless scan of the exact stored URL for ten minutes from creation (SD-7.2). The database lookup is shared across processes; hits create no run and spend no daily scan capacity, but still count toward address limits and check current opt-outs, pauses and public-address rules. Paths and queries remain distinct. Redirect aliases are not stored, so only matching destination URLs reuse redirected reports. Concurrent cold misses may still scan independently. Owner/MCP, watch and comparison scans always use their existing fresh-scan paths.
15. **GEO is deterministic and reuses the site audit.** No new crawler, no LLM calls for the score. The SSRF-safe fetcher and the audited page set are shared by SEO, security and GEO. The fetcher (`app/scans/fetch.py`) resolves each host once, refuses any non-public address (metadata endpoints and IPv6 forms hiding a private IPv4 included) and connects to that checked address, so DNS rebinding cannot reach internal services (SD-4.5).
16. **Over time means comparison, not more runs.** Reruns and weekly watch compare finding fingerprints against the previous result for the same site. Only changes are reported and emailed.
17. **Team workspaces: the API decides, RLS backs it up, Realtime only nudges.** Membership and role are read from the database on every team request (non-members get 404). Browsers only read team rows through RLS (`is_team_member`), shared runs and their screenshots through `shared_with_me(run)`, and never see invitations. Seats and ownership change inside locked SQL functions. See [docs/team-collaboration.md](docs/team-collaboration.md).

## Owner history and exact count reads (R-S14a, 2026-10-05)

Dashboard history reads metadata only in descending `(created_at,id)` pages, excludes comparison parts and filters the owner explicitly in addition to RLS. Stored timestamp precision and 32-character hexadecimal run IDs form the continuation boundary. MCP uses the same ordering with owner/site-scoped cursors, database-side literal site filtering, maximum 50 rows and a scalar launch score projection. Detail reports and account exports remain separate. Web continuation ends only after an empty page; the API fills at most `limit + 1` rows through advancing short server-capped subpages.

Daily free/test/scan usage, paid founding offers, completed citation checks and citation engine backlog use `HEAD` with `Prefer: count=exact`; missing exact totals fail closed. Distinct citation batches and complete owner site usage walk slim ID-keyset pages rather than count capped rows. Exact reads describe a statement-time count, not a financial reserve or atomic run admission; those guarantees remain R-S8/R-S9. Existing citation admission locks are retained. Plan-display reuse is account/token scoped for 60 seconds and invalidates on sign-out/account changes and run/billing notifications. It never authorizes a run. See [query inventory and isolated measurement evidence](docs/database-history-queries.md). No index or migration was added; deployed plans remain uninspected.

## Browser navigation contract (R-S3, 2026-10-05)

Current snapshots advertise `navigation_version=3`, an opaque revision and up to twelve scroll containers (ID zero is the window). Controls name their nearest captured container; descriptors include signed pixel offsets, dimensions, available directions and viewport/occlusion/coverage flags. Pane labels share the existing 6,000-character region/row context budget. IDs resolve direct document-local references; changed ancestry, labels, visibility, clipping, modal/overlay coverage or scrollability cause a safe refusal.

`scroll_container_id`, `scroll_direction` and optional `scroll_distance` request up/down/left/right movement capped to 85% of the axis viewport and 1,000 pixels. A null ID with default down/default distance retains legacy window behavior. Modern window instructions become explicit ID zero and require the current capability/revision; old receivers cannot silently ignore new instructions. Hidden/clip pane axes and unsupported RTL/reversed axes decline movement with `no_progress`; negative offsets remain signed. Actual before/after offsets are recorded because browser behavior, including scroll snap, can differ from the request. Primary browser references: [scrollBy](https://developer.mozilla.org/en-US/docs/Web/API/Element/scrollBy), [scrollTop](https://developer.mozilla.org/en-US/docs/Web/API/Element/scrollTop), [scrollLeft](https://developer.mozilla.org/en-US/docs/Web/API/Element/scrollLeft) and [overflow](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/overflow).

Revision-bound `wait` uses `wait_condition=settled|url_changed|text_changed` and `wait_timeout_ms=100..5000` (default 1000). Settlement means 300 ms of stable bounded public text/control/scroll state without an observed busy signal; it does not mean network-idle or goal success. Polling preserves the snapshot registry, excludes editable values and diagnostics, and never repeats a dispatched mutation. Matching operation cancellation and run deadlines stop pending/queued work. Executor feedback is accepted only for the pending action/container and stores actual elapsed time even on browser-throttling overrun; request deadlines stay capped. Repeated no-progress/timeouts end as Walkthru's limit, not a site defect. R-S4 permits delayed matching milestone evidence only after a real preceding action with matching changed/settled wait feedback; pure waiting and scrolling provide no completion proof. Installed-browser/deployed acceptance remains V0/R-S20. Verified behavior and limits: [navigation workflow](docs/restructure-sessions.md#r-s3-controlled-scrolling-and-observation) and [completion contract](docs/task-completion-contract.md).

## v1.1 capability map

Build order and dates: [ROADMAP.md](ROADMAP.md). Product rules: [SPEC.md](SPEC.md).

| Module id | Responsibility | Depends on | Status |
|---|---|---|---|
| `entitlements` | Plans in code, active pass per user, server-side limits, usage counts, global free-capacity cap | auth (live) | Built 2026-09-24 |
| `geo-scan` | AI readiness score, GEO findings, "what AI search sees" text | site audit (live) | Built 2026-09-24 |
| `fix-pack` | Copy-paste robots.txt, JSON-LD, llms.txt and framework rendering fixes | `geo-scan` | Built 2026-09-24 |
| `rerun-compare` | Fingerprint findings; fixed, still broken, new | `entitlements` | Built 2026-09-24 |
| `fix-prompt` | Paid prompt for the user's coding agent built from the report | `entitlements`, `fix-pack` | Built 2026-09-24 |
| `share-loop` | Launch Ready score, live badge, public report meta with the score | `geo-scan` | Built 2026-09-24 |
| `email-check` | Signup email records over DNS-over-HTTPS; auth-mailer limits in journey errors | none | Built 2026-09-24 |
| `finding-states` | Ignore a finding with a reason; respected by compare, fix prompt and watch | `rerun-compare` | Built 2026-09-24 |
| `funnel-metrics` | Steps, fields, errors and time to the first useful screen, per run and across reruns | `rerun-compare` | Built and verified, P0.2 |
| `copy-review` | Screenshot-based first impression checklist and rewrites, one free vision call | `entitlements` | Planned, P0.3 |
| `competitor-compare` | Passive scans of up to 3 competitor URLs next to the user's site | `geo-scan`, `entitlements` | Planned, P0.4 (moved before launch) |
| `rule-ids` | Stable `rule` id on every finding; compare and fix prompts use it with old-report fallback | none | Built and verified, P0.1 |
| `backend-exposure` | Supabase and Firebase detection; read-only row-count probe on verified domains | site audit | Planned, P1.1 |
| `security-parity` | Header quality, CSP, CORS, SRI, vulnerable JS libraries, source maps, secrets, TLS, CAA, takeovers | site audit | Built 2026-09-25 (P1.2) |
| `stack-detect` + `recipes` | Hosting, framework and backend from headers and HTML; per-rule, per-stack fixes in a data file | `rule-ids` | Planned, P1.3 |
| `geo-depth` | Ported geo-optimizer checks, citability score, firewall blocking, entity checks | `geo-scan` | Planned, P1.5 |
| `seo-depth` | Bounded SEO checks and mobile Core Web Vitals on up to five paid-plan pages | site audit | Built and verified, P1.6 |
| `agent-readiness` | Can AI agents use the site: score from axe, journeys and schema | journeys, `geo-scan` | Planned, P1.7 |
| `github-app` | Per-repo install, short-lived installation tokens | auth | Planned, P2.1 |
| `worker` | One-at-a-time jobs on the VM: code scans (gitleaks, osv-scanner, OpenGrep) and safe Nuclei | `github-app`, `entitlements` | Planned, P2.2 and P2.4 |
| `search-data` | Search Console and Bing Webmaster data joined to findings | auth (Google OAuth) | Planned, P3.1 |
| `citation-tracking` | Prompts, free-engine answers, evidence-backed citations, mentions and share of voice | `entitlements`, dedicated Postgres queue | P3.2 built; P3.3 claim accuracy remains planned |
| `mcp` | Remote MCP server with personal API keys (Plus) | `fix-prompt`, `rerun-compare`, `entitlements` | Built 2026-09-25 |
| `billing` | Founder-approved 30-day passes through Dodo, per payment.md | `entitlements` | Built 2026-09-25 (docs/billing.md) |
| `evidence-pdf` | Close T18 to T21; branded PDF for Plus | `entitlements` | Branded PDF built 2026-09-25 (P4.3); V7 close-out open |
| `watch` | Weekly server-side scan per saved site, deploy webhook, email only on change | `rerun-compare`, `entitlements` | Planned, post-launch |
| `personas-plus` | Custom test users and several test users per report | `entitlements` | Built 2026-09-25 (P4.2): `app/plus.py`, `test_users`, `runs.group_id` |
| `teams` | Plus team workspaces: roles, email invitations and invite links, shared reports, findings board with status and owner, chat and comment threads, activity, presence, auto-share | `entitlements`, auth, `rerun-compare` (fingerprints) | Built 2026-09-25 (P4.7): `app/teams.py`, seven `team_*` tables, docs/team-collaboration.md |
| `cloud-runner` | Headless Chrome on the API VM driving the same `inject.js` for public journeys without an install | `entitlements` | Conditional on the extension funnel experiment |

Dependency direction is one way. `entitlements` comes first because every paid promise depends on it.

### `entitlements`
- `app/plans.py`: one dict of plans (free, launch, pro, plus) with limits: runs per period, max steps, logged-in allowed, test users, verified sites, SEO and GEO pages, compare, watch, pdf, white label. No config classes.
- Table `entitlements(id, user_id, plan, starts_at, expires_at, runs_granted, source, created_at)`, owner-readable under RLS, deleted with the account. `scripts/grant_plan.py` grants dev and founder passes.
  - `source` is `founder`, `dodo` or `promo`.
  - V1 rows are inserted by the founder (payment.md concierge flow). Later a verified Dodo webhook writes them.
  - Balances follow payment.md's append-only ledger when billing lands.
- `effective_plan(user_id)`: the active, unexpired row, otherwise free.
- Monthly usage: count of the user's `runs` rows with `kind='test'` since the period start, through PostgREST `Prefer: count=exact`. No counter table.
- `POST /runs` ignores client `tier`.
  - Rejects `logged_in` on free.
  - Clamps `max_steps` to the plan.
  - Rejects a persona outside the plan.
  - Rejects a new site beyond the plan's site count for the month or pass. Local dev servers never count.
  - Returns 402 with a plain message when runs are used up.
- `GET /me/plan` returns the plan, its limits and runs left, so the side panel and dashboard show them.
- The persona graph's `tier` (`free` or `paid`) is now derived from the plan and only selects model routing.
- Global free-capacity guard: `FREE_RUNS_PER_DAY` (default 90, about 80% of the Groq free budget of 3 models × 1,000 requests a day ÷ about 27 calls per run). Past it, free runs get "Free test capacity is used up for today"; paid runs continue on the full chain.
- `FREE_SCANS_PER_DAY` (default 200, 2 model calls each) caps Instant Scans the same way. Both caps count today's `runs` rows, so every API process shares them with no extra table. The per-address limit (5 scans an hour) stays in process memory: production runs one API process; move it to a table only if that changes.

### `geo-scan`
- `app/scans/geo.py`: `audit(root, pages, robots_text, llms, bot_probe) -> GeoResult(score, categories, findings)`. It uses pages the site audit already fetched.
  - `Finding.kind` gains `"geo"`.
  - The report gains `geo: {score, band, categories}`.
  - The report is stored as JSON in `runs.report`, so no SQL migration is needed.
- **Two extra passive requests:**
  - `GET /llms.txt`.
  - One homepage `GET` with the `OAI-SearchBot` user agent, compared with the normal response. A 403 or challenge page becomes "blocked for AI search user agents".
  - A 200 is reported as "not blocked by user agent". Edge networks verify real bots by IP, so the probe cannot prove access.
- **Free:** homepage and `robots.txt` categories only. **Paid:** every audited page.
- **Pro's 50-page promise (built 2026-09-24):**
  - Paid run reports crawl up to 50 pages with a 60 s budget (`site.PAID_MAX_PAGES`, `PAID_TIME_LIMIT`). Reports are already written by a queued job after the run (`app/jobs.py`), so nothing waits on it.
  - Instant Scan and free runs keep 10 pages and 20 s.
  - Measured: 50 pages of python.org in 13.9 s with sequential fetches, so no parallel crawler.

### `fix-pack`
- `app/scans/geo_fixes.py`: pure functions from `GeoResult` and the audited pages to text blocks:
  - a `robots.txt` section allowing citation bots;
  - `Organization`, `WebSite` and `SoftwareApplication` JSON-LD filled from title, description and Open Graph tags;
  - an `llms.txt` draft listing audited pages;
  - a rendering fix picked by framework markers: `id="root"` plus `/assets/index-*.js` means a Vite SPA (prerender or SSG); `__NEXT_DATA__` means Next.js (keep pages server-rendered); Lovable and Astro have their own markers.
- No model calls. Shown in the report with copy buttons.

### `fix-prompt`
- `app/agent/fix_prompt.py`: `build(report, style) -> str`. `style` is `full` or `chat`.
  - A pure function over the stored report JSON and the fix pack. No model call.
  - It uses only findings already in the report, so it cannot add claims.
  - Leaked key values stay masked.
- `GET /runs/{id}/fix-prompt?style=full|chat` (owner only, paid plan) returns text, or a file with `download=1`.
- Not written into `runs.report`. The web app reads reports straight from Supabase under RLS, so anything stored there would be free to read.
- It ends with the fingerprints the next rerun should mark fixed. That makes the rerun the verification step.

### `rerun-compare`
- **Built as automatic comparison** (`app/agent/compare.py`), with no rerun button or `parent_run_id`: when a paid run's report is written, it is compared with the owner's previous run of the same goal (case and spacing ignored) on the same origin. The first run of a goal has no comparison. A failed comparison never loses the report.
- **Fingerprint:** `kind:title`, lower-cased, spacing collapsed and numbers replaced ("3 more pages" matches "5 more pages"). The same rule runs in `lib/runs.ts` for the web app. Model-written UX titles also match on 50% word overlap, because their wording varies between runs.
- **Comparison:** `report.comparison = {fixed, still_broken, new, not_rechecked}` is computed in code after synthesis, never by the LLM. Reports keep every affected page per finding (`report.pages`, from the site audit and GEO), so still-broken findings say which pages were fixed, which are new and which were not re-checked; a finding that vanished only because its pages were not audited again is `not_rechecked`, never `fixed`.
- **Report page:** shows the three lists above the findings.

### `share-loop` (Launch Ready score and badge)
- The score is computed in code from categories the report actually measured:

  | Area | Weight | Basis |
  |---|---:|---|
  | UX | 30 | Journey outcome and UX finding severity |
  | Security | 20 | Security findings |
  | GEO | 20 | The GEO score |
  | SEO | 15 | SEO findings |
  | Speed and accessibility | 15 | Performance and accessibility findings |

  An area that was not measured is shown as "not measured" and its weight is shared among the others. An Instant Scan has no UX area.
- **Ignored findings still count** in the score, so the badge cannot be gamed. They only stop repeating in lists.
- **Built 2026-09-24** (`app/agent/score.py`), with no new table. The score is stored as `report.launch_ready` when a report is written. Each area starts at 100 and loses 25, 10 or 3 points per high, medium or low finding; GEO uses its own score; UX starts from the journey outcome (done or safe stop 100, gave up, stuck or out of steps 50) and counts only when the site was really tested (the owner's Stop, a loop guard or a CAPTCHA leave it out).
- `GET /badge/{run_id}.svg` serves the badge for a **public** report only (sharing is the owner's opt-in; Instant Scans are public), cached one hour. It shows the owner's latest public report for the same site, so a rerun that is shared updates every embedded badge. `GET /badge/{run_id}` redirects a click to that report. Private reports return 404.
- The owner's report page shows the badge with copy-paste HTML and Markdown; the public page shows the score only. The public page title carries the score.

### `email-check`
- `app/scans/email.py` reads DNS over HTTPS with the existing httpx client, from a fixed trusted resolver (`https://cloudflare-dns.com/dns-query`, `accept: application/dns-json`). No new dependency.
- **Checks:** MX, SPF (`v=spf1`), DMARC (`_dmarc.<domain>`, policy). DKIM is only checked when the user names a selector, because selectors cannot be listed.
- **Journey errors map to causes:**
  - "email rate limit exceeded" is Supabase's built-in mailer limit. The fix is your own SMTP.
  - Similar patterns for Firebase and Clerk are added only after one is seen in a real run.
- **Free:** SPF and DMARC. **Paid:** everything above.

### `finding-states`
- Table `finding_states(user_id, origin, fingerprint, state, reason, created_at)`. `state` is `ignored` for now.
- **Report:** shows "ignored" with the reason.
- **Where ignored items are left out:** the fix prompt, rerun "new" and "still broken" lists, and watch emails. They are always kept in the score (see `share-loop`).

### `funnel-metrics`
- A pure function over stored steps: number of steps to reach the goal, fields typed, errors seen, safe stops, and time to the first useful screen from step timestamps.
- Stored in `report.funnel` on paid runs. Compared across reruns through `rerun-compare`.

### `copy-review`
- One `runtime.call(CopyReview, ...)` on the homepage and pricing-page text, using the same free writer chain as the report.
- **Output:** a verdict on the headline, call to action and pricing clarity, plus up to 3 rewrite options, labeled as suggestions.
- Generated only when the run's plan includes it, so free reports never contain it.

### `competitor-compare` (post-launch)
- `POST /compare {site, competitors[<=3]}` runs the Instant Scan pipeline on each URL: 10-page audit, GEO, first impression, and public headers only. Deep security checks never run on sites the user has not verified.
- **Storage:** a `kind='compare'` run with side-by-side categories.
- **Cost:** one model call per URL (first impression). Rate limited per plan.

### `mcp` (built 2026-09-25)
- **As built:** `app/mcp_server.py` on the official SDK (`mcp` 2.x, `MCPServer`), stateless JSON over streamable HTTP, registered as a plain route at `/mcp` (no mounted sub-app, so no trailing-slash redirect on POST). An ASGI wrapper checks the key and the Plus plan on every request and passes the user to the tools through a context variable; the SDK's OAuth resource-server mode was not used because it needs an authorization server. Tool errors use `ToolError` so the agent sees the reason. `scan_site` and `rerun` share `main.run_scan` with Instant Scan, store private owner scans on the paid tier (never the free capacity) and stop at 50 a day per user. Keys: `GET/POST /me/api-keys`, `DELETE /me/api-keys/{id}`, at most 5 active, table locked to the service role. Settings has an "API keys and MCP" section with copy-ready Claude Code and Cursor setup; docs `#mcp`.
- **P1.4 (2026-09-25):** `get_finding(run_id, rule)` returns everything the report holds for one finding; `verify_finding(run_id, rule)` re-runs only the scanner family that produced it (security checks, the site audit for SEO and GEO, accessibility or PageSpeed) on the finding's pages and answers fixed, still broken or not re-checked. `rule` is the finding's `rule` id once P0.1 adds it, else its compare fingerprint or exact title; `get_report` prints each id. Journey (UX) findings are refused with a pointer to the extension. Checks share the daily cap with scans (per-process counter, one API process).
- **Server:** a remote MCP server at `/mcp` over streamable HTTP, mounted in the FastAPI app with the official `mcp` Python SDK. The founder approved the MCP feature on 2026-09-24, and with it this new dependency. Nothing to install on the user's side: they paste the URL and key into Claude Code or Cursor.
- **Auth:** a personal API key in a bearer header.
  - Table `api_keys(id, user_id, name, key_hash, created_at, last_used_at, revoked_at)`.
  - The key is shown once and stored as SHA-256.
  - Plus plan only.
- **Tools:**
  - `scan_site(url)`.
  - `get_report(run_id)`.
  - `get_fix_prompt(run_id)`.
  - `rerun(run_id)`: server-side checks. Journeys rerun in the extension until the cloud runner exists.
  - `list_runs(site)`.
  - `get_finding`, `verify_finding` (P1.4, above).
  - Added 2026-09-27, each calling the web route function as the key's owner (`_as_owner`), so plan checks, limits and ownership are the website's own: `get_plan`; `compare_sites`, `accept_finding`, `reopen_finding`, `share_report` (public link plus badge snippets); `get_site_verification` (the meta tag with where the `<head>` lives per framework, the file and DNS alternatives, and the live check); `list_github_repos`, `open_fix_pull_request` (preview unless `confirm`); `list_ai_answer_sites`, `track_ai_answers`, `get_ai_answers`, `set_ai_prompts`, `check_ai_answers_now`; `list_watched_sites`, `watch_site`, `check_watched_site_now`, `create_deploy_hook` (with a GitHub Actions step). Sites are named by address and matched on host. Deletes (sites, prompts, GitHub connections, keys) stay in the web app on purpose. `get_report` also reads comparison reports.
- **Limits:** every tool goes through the same entitlement and rate-limit checks as the web API.

### Testing paid plans in development (no spend)
- **Plans are data.** `apps/api/scripts/grant_plan.py EMAIL PLAN DAYS` inserts an `entitlements` row with `source='dev'` for a test account. Expiring the row reverts the account to free. The dev stack has a test account for each plan.
- **No plan uses a paid model.** Paid features are deterministic code, or use the same free chain as free reports. Testing Pro and Plus costs $0 in model calls.
- **pytest** fakes every model call (existing pattern). Plan limits are tested with crafted requests.
- **Dodo test mode:** test products and test cards, no real money. Webhooks fire for test payments like live ones. Locally they reach the API through a tunnel (cloudflared or ngrok); after deploy, through the VM URL. Sources: [Dodo testing process](https://docs.dodopayments.com/miscellaneous/testing-process).
- **Live model checks stay small:** a few runs a day on the free chain. The bakeoff and trap scorer replay saved runs.

### `watch` (post-launch)
- Table `sites(id, user_id, origin, verified_at, watch boolean, deploy_token_hash, last_watch_run_id)`.
- Every 30 minutes a `watch_due` job queues one `watch_site` job per due site (`app/jobs.py`), which runs a server-side scan (`kind='watch'`). It is compared with `last_watch_run_id` via `rerun-compare`, and an email goes through Resend only when something is new or fixed.
- `POST /hooks/deploy/{token}` (Vercel or Netlify deploy hook) triggers the same scan. It is rate limited to one scan every 10 minutes per site.
- Journeys on deploy need `cloud-runner`, so watch covers the server-side checks only.

### Flagship modules (v1.2, 2026-09-25)
Build rules and phases: ROADMAP.md. Licences: docs/decisions.md 2026-09-25. Everything below is deterministic unless it says otherwise, and every model call uses the free chain.

- **`rule-ids`:** `Finding.rule` (for example `sec.csp.unsafe_inline`). `compare.fingerprint` uses it when present, the normalized title otherwise, so old reports still compare.
- **`backend-exposure`** (`app/scans/backend.py`): regexes over HTML and same-origin bundles find `*.supabase.co` URLs with an anon key, or a Firebase config. Unverified domains get the explanation only. Verified domains: `GET /rest/v1/` lists exposed tables; `HEAD /rest/v1/<table>?select=*` with `Prefer: count=exact` reads the row count from `Content-Range`; storage bucket listing; Firebase unauthenticated read. Never reads row contents, never writes, 50 tables, 10 s. Same SSRF-safe client as every scan.
- **`security-parity`** (`app/scans/security.py`, `app/scans/tls.py`): rule data in `app/scans/data/` (retire.js repository JSON and gitleaks patterns, refreshed by a script, notices in `apps/api/THIRD_PARTY.md`). TLS and certificate expiry through the `ssl` stdlib; CAA over the DNS-over-HTTPS client from `email-check`.
- **`stack-detect` + `recipes`** (`app/scans/stack.py`, `app/agent/recipes.json`): `{rule: {stack: {file, snippet, check, risk}}}` with a generic fallback. `fix_prompt.py` renders batches with a "stop and verify" step after each.
- **`agent-readiness`:** computed in `report.py` from axe results, the journey outcome, CAPTCHA stops, control stability across reruns and schema; shown next to the GEO score.
- **`github-app`** (`app/github.py`): the App's private key lives in the API env; an installation token is minted per job (valid one hour) and never stored. Table `repos(user_id, site, installation_id, repo_full_name)`.
- **`worker`:** a second process on the VM polling a `jobs` table (`kind`, `run_id`, `status`, `started_at`), one job at a time. Code scan: shallow clone into `tempfile.TemporaryDirectory`, run gitleaks, osv-scanner and OpenGrep (with Walkthru rules in `apps/api/rules/`) as subprocesses with timeouts, parse JSON, mask secrets, delete the directory in `finally`, attach `kind="code"` findings with `path:line` to the run's report. Nuclei: fixed argument list with an allow-list of tags and `-etags intrusive,dos,fuzz`, verified domains only. Render free cannot host it (memory), so it arrives with the Google Cloud VM (V11b): e2-micro (1 GB) with swap first, e2-small (2 GB) only if measured memory needs it.
- **`search-data`:** Google OAuth with the `webmasters.readonly` scope, refresh token stored encrypted server-side; Search Analytics and URL Inspection (2,000 a day per property). Bing Webmaster with the user's own API key.
- **`citation-tracking`:** `citation_sites`, `citation_prompts`, `citation_checks` and `citation_quota`. Groq web search and Gemini memory answers use existing free quotas. Deterministic `citation_evidence.py` verifies answer-to-source references; unresolved and memory-only samples are excluded from citation rates. Saved provenance freezes historical labels and tracked-brand context. A dedicated minute worker uses atomic admission, per-engine attempt quotas and fenced ten-minute leases. Consumer Google AI surfaces, ChatGPT, Perplexity and Claude are unmeasured. See [citation measurement v2](docs/citation-measurement.md) for evidence rules, retries, migration and validation. P3.3 claim accuracy remains unbuilt.

### `teams` (built 2026-09-25)
- **Routes:** `app/teams.py` (APIRouter in `main.py`), full reference in docs/team-collaboration.md section 6. `_member()` loads the caller's member row with the team embedded and answers 404, 403 or 402; `me.can` tells the web app which controls to show.
- **Tables:** `teams`, `team_members`, `team_invites` (API only), `team_runs`, `team_findings`, `team_messages`, `team_events`. Members may `select` their workspace rows; nothing else is granted to browsers. `runs` and `storage.objects` gain a members-read policy through `shared_with_me(run)`.
- **Plan:** a workspace is active while its owner has a Plus pass; otherwise it is read-only. Members need no plan. `TEAM_SEATS` (default 3) counts members plus open email invitations.
- **Invitations:** 24-character base32 codes (120 bits), SHA-256 stored, in the URL fragment of `/join#CODE`. Email invitations need the matching verified email; links can require an email domain. `team_join()` re-checks everything under a row lock.
- **Live updates:** the schema adds the team tables to `supabase_realtime`; `useTeamLive` subscribes with `postgres_changes` and refetches through the API, polling when the socket is down.
- **Tests:** `tests/test_teams_live.py` runs against a real Postgres + PostgREST with Supabase's roles (`tests/live_stack.py`), skipped when the binaries are missing.

### `cloud-runner` (conditional)
- **Why:** removes the install step for public-page journeys.
- **Built only if** fewer than 25% of beta users who click "Run a test" finish a run.
- **How:** the API VM runs headless Chrome. A worker drives the built `inject.js` over CDP, the same way `evals/e2e_extension.py` already does, and calls the same `/runs` step API.
- **Limits:** public pages only, one concurrent run, and the same safety code. Logged-in journeys always stay in the owner's browser.

## Experimental TypeSafe decision path

```text
structured observation + goal + history
             |
             v
one Jev request: operation + click target + type target + goal Noul + confusion Score
             |
       confidence gate
        /           \
 high confidence   low/error/open text
       |                   |
deterministic value      existing LLM
or bounded action           |
        \___________________/
                  |
          code safety enforcement
                  |
            extension executor
```

`PERSONA_DECISION_MODEL=jev` is opt-in. `TYPESAFE_API_KEY` remains server-side. The evaluation model is pinned to `jev-1.13.0`; aliases are not used while thresholds are being measured.

## Agent graphs
- `test_run`: preflight (limits, ownership) → first_impression → persona_session per persona → synthesize → deliver.
- `persona_session`: decide (one `PersonaStep`: thought, action, target_id, confusion 0-3) → interrupt for observation → check (goal met, looping, budget) → decide.
- `site_scan`: accessibility_scan, performance_scan and one bounded site audit in parallel. A missing PageSpeed key is recorded as unavailable, never as a false pass.
- Site audit (`app/scans/site.py`): pages the test user visited (up to 5) are audited on top of the crawl, past a robots.txt block only on an owner-verified domain; a homepage whose only sign-up link is in the footer is reported as a UX finding. GET-only, same-origin, robots.txt honoured, 10 pages and 20 s by default, 50 pages and 60 s for paid run reports, all fixed in code rather than request input. Redirects are followed manually and each hop passes the SSRF guard before it is requested. Findings repeated across pages are merged into one root cause that keeps the affected-page count and URLs. Exposed-file and bundle-secret checks run only on verified domains. Coverage (`site_audit`) is stored in the report so readers see what was and was not checked.

## Runtime choices for this deployment stage
- **Database access:** the API uses Supabase's HTTPS Data API (`app/db.py`), not a Postgres socket. The direct host is IPv6-only and raw Postgres was unreliable from the founder's network; HTTPS goes through Cloudflare and reuses one connection. Migrations still use SQL: `python -m app.migrate` (below).
- **Migrations (SD-5.1):** numbered files in `apps/api/migrations/` (`0001_initial.sql` is the whole schema as of 2026-09-27, formerly `schema.sql`). `python -m app.migrate` applies each pending file once, in order, in one transaction sent as one query, and records it with a checksum in `schema_migrations`; an edited applied file is refused, a failing one leaves no trace, and `down` undoes the latest one through its `.down.sql`. Keepalives and a TCP timeout make a dropped pooler connection fail fast.
- **Politeness to scanned sites (SD-2.3):** at most 2 requests in flight to one host per API process (`fetch._Polite`, held until the response closes) and 30 scans of one host an hour across all users (`main.polite`, the shared counter). Walkthru cannot be used to hammer a site.
- **Rate limits (SD-2.1):** every route has one, counted in Postgres (`rate_limits`, `hit_rate_limit`, one fixed window per key) so it holds across restarts and processes. `app/limits.py`: signed-in routes per user inside `auth.require_user`, routes without sign-in per client address through an app-wide dependency, `/mcp` per API key, business limits (scans, invitations, pull requests, billing, feedback) by their own keys. `429` with `Retry-After`. Fails open when the database is unreachable. The address is `request.client`, so uvicorn runs with `--proxy-headers` behind the proxy.
- **Background work (SD-6.1):** reports, comparisons, watch checks, founder emails, Scout answers and the periodic passes (retention every 6 h, watch every 30 min) are rows in the Postgres `jobs` table, not in-process tasks. `app/jobs.py` runs `JOB_WORKERS` worker threads (default 4) in each API process; `claim_job` hands each job to one worker (`FOR UPDATE SKIP LOCKED`) with a 15-minute lease, a dead worker's job is claimed again when the lease runs out, and failures retry with exponential backoff and jitter. Handlers are safe to run twice (a report that exists is not rewritten). `python -m app.jobs` runs workers as their own process; set `JOB_WORKERS=0` on the API then. Payloads hold ids and the state a job needs, never emails or tokens; finished jobs are deleted after 14 days. Citation checks keep their own queue (`citation_checks`, `claim_citation_job`).
- **Agent state:** development defaults to memory; `APP_ENV=production` requires `CHECKPOINTER=postgres` and refuses startup on missing/unavailable/incompatible persistence. `CHECKPOINT_DATABASE_URL` (otherwise `DATABASE_URL`) must use a direct/session connection. Migration 0002 stores LangGraph state in private `walkthru_checkpoints`; browser/REST roles cannot read it. API lifespan initializes and closes a bounded pool. [Restart drill and request logging](docs/checkpoints-and-request-logs.md).
- **Models:** free chain of Groq gpt-oss-120b, gpt-oss-20b, Qwen, then Gemini 3.5-flash and 3.1-flash-lite (`GROQ_MODELS`, `GEMINI_MODELS`). Each Groq model has its own 8k tokens/min budget; zero retries so a 429 moves on instantly.
- **Free tier only (founder, 2026-09-25):** every plan runs on the free chain until revenue pays for a model within payment.md's caps. The Claude path below stays wired and off.
- **Pro and Plus model (off):** Claude Haiku 4.5 on Google Cloud (Vertex AI) through the `anthropic[vertex]` SDK (approved 2026-09-24), wrapped like the OpenRouter runner: a forced tool call returns the schema. When `CLAUDE_VERTEX_PROJECT` is set, paid runs put Claude first for the goal planner, test user and report writer, with the free chain behind it; free runs never reach it. Each report's `model` field states which models ran. Auth uses Google application default credentials.
- **Report writer:** the report calls (`runtime.call`, first impression and synthesis) try Groq gpt-oss-120b, then OpenRouter Nemotron 3 Ultra (`OPENROUTER_MODELS`, 90 s budget, plain httpx), then the rest of the chain. Persona steps never wait on OpenRouter. Chosen by `evals/model_bakeoff.py`; see docs/decisions.md.

## Journey safety and grounding
- **Goal intent and completion** (`app/agent/goal.py`): before the first step, one fast model call proposes an intent and 1 to 4 checkpoints, or refuses unsafe/off-site goals with 422 before a run is counted. The original owner goal remains authoritative; planner interpretation and persona preferences are subordinate, and model `progress` is advisory. Checkpoints use `kind=navigation|outcome` and optional owner/start-page `text_contains`. Code advances only on fresh matching same-origin route/public-text evidence, in order, without reusing one signal for multiple milestones. Functional outcomes require a declared public phrase; missing expectations and planner outages remain unconfirmed. `check` ends immediately when all checkpoints have recorded evidence. Unsupported completion/abandonment gets one bounded correction, then `agent_lost`; an observed current action error can support `site_block`, while safety/user/bot/budget stops stay distinct. Bounded factual history and report packets preserve milestones and unresolved work. [Completion contract and limitations](docs/task-completion-contract.md).
- **Loop guards** (`persona.check`): three identical steps (including scroll position) end as `stuck`; a third arrival at the same page ends as `looping`, Walkthru's own stop, never reported as a site problem. Observations carry `scroll_pct` and `at_end`; a click that changes nothing is recorded as `no_change` and shown to the test user.
- **Destructive** (pay, buy, checkout, delete, remove, cancel subscription, transfer, unsubscribe): never clicked as a button on any page; on logged-in pages not even typed into. **Sending** (send, invite): only on a domain the signed-in owner verified (meta tag or `/.well-known/walkthru.txt`), only after the owner confirms in the side panel, at most once per run. Plain links may navigate. Enforced in both `app/agent/persona.py::_enforce` and `apps/extension/lib/execute.ts`.
- A run ended at such a button has status `safe_stop`. `mailto:`/`tel:` links are reported as contact methods and never opened.
- Report grounding (`app/agent/report.py`): `problem_steps` defines where something went wrong; `grounded_ux` drops UX findings that cite no such step or restate a scan finding; the writer sees step outcomes, the final page's controls and a local-dev note, and the system prompt forbids unsupported claims.

## Data lifecycle
- Screenshots in the private `run-evidence` bucket expire after 30 days (`EVIDENCE_RETENTION_DAYS`). Runs, steps and reports stay until the owner deletes them. Instant Scan emails are erased after the same window.
- `app/retention.py` owns every deletion. Order is fixed: storage objects (Storage API, since Supabase blocks direct deletes from `storage.objects`), then LangGraph checkpoints (`delete_thread`), then `runs` rows, then the Supabase Auth user for account deletion. A failure stops the sequence with rows intact, so the delete can be retried.
- Routes: `DELETE /runs/{id}` (owner only), `GET /account/export` (JSON of every run the user owns, plus team memberships and their own messages), `POST /account/delete` (body must repeat the account email).
- Team workspaces: deleting a run removes it from every workspace. Account deletion is refused while the user owns a workspace with other members; otherwise their name becomes "Former member" in other people's workspaces, their memberships go, and workspaces they owned alone are deleted with the account.

## Safety rules (enforced in code, not prompts)
Safe mode on logged-in pages (never click delete / remove / cancel subscription / pay / send / invite / transfer; confirm before any form submit), same-origin only, 25-step and 4-minute caps, stop at CAPTCHA, client-side PII masking before snapshot upload, form-control masking before screenshot capture, fake test identity for signups. Evidence capture is best-effort and never blocks the journey. Owner stop, time-limit, origin-exit and post-creation extension errors close the API run and preserve a partial report.

## Public comparisons and ownership verification
- `POST /compare` runs every `compare_part` with public security scope, even for a verified owner. Results preserve `checks`, `scope: public` and crawl truncation so the web client can explain coverage and avoid claiming score gaps between incompatible measurements.
- `GET /verification` returns the existing account proof. Optional `site` validates a public HTTP(S) origin and adds the current user's verification status and full DNS TXT name. DNS, meta and well-known-file proof use the same existing verifier; this endpoint does not grant permissions. The web settings flow recommends DNS to avoid source edits or redeployment.
- `apps/web/src/lib/comparison.ts` owns comparison eligibility and strongest-rival gaps; `ComparisonCharts.tsx` renders accessible native bars and severity stacks without a chart library. Failed or absent measurements remain unmeasured.

## Environment variables
See [.env.example](.env.example). Web reads `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_URL`. Never expose service-role keys to the web app.
