# Architecture

## System overview
```
Chrome extension (user's browser)               Walkthru API (FastAPI + LangGraph)
────────────────────────────────                ───────────────────────────────────
side panel: pick site, goal, test user ── POST /runs ──────▶ create run + LangGraph thread
content script: snapshot + axe + vitals ── POST /runs/{id}/observe ─▶ persona agent decides
  (URL, numbered buttons/links/inputs,  ◀── next action ──── click #12 | type #4 "..." | scroll | done | give_up
   visible text, errors; PII masked)
executes the action in the real tab
masks fields + captures bounded JPEG    ── private Storage object + evidence metadata ─▶ exact run step
                                        ... loop until done / give_up / step budget ...
                                                               synthesize report ─▶ Supabase ─▶ report page + email
Server-only scans (no browser): accessibility basics (HTML structure and names), mobile performance (PageSpeed API), SEO (HTML, robots, sitemap), GEO readiness (AI crawler access, content before JavaScript, structured data, answerability), and security hygiene (headers, TLS, cookies, public files, secrets in JS).

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
| Data | Supabase Postgres (RLS on every table) + private Storage (screenshots) | `runs` table + RLS live; `run-evidence` bucket and owner/public-report policies are declared in `apps/api/schema.sql` but still need applying to the project |
| Evals and tracing | LangSmith | Keys set, project `Walkthru` |
| Email | Resend (`app/deliver.py`, REST, no SDK) | Built; needs `RESEND_API_KEY` |
| Payments | Dodo Payments (test mode first) | Not started |
| Hosting | Vercel (web), Oracle Always Free VM or ~$5 VPS (API) | Not started |

## Key decisions
1. **Browser runs on the user's machine, brain on our server.** No Chromium on our server, hosting stays $0-5, logged-in pages work without sharing passwords.
2. **Step loop lives in the extension side panel page**, not the MV3 service worker (Chrome suspends workers after ~30 s idle). Chrome does not reliably grant `activeTab` to side panels and `captureVisibleTab` only accepts `activeTab` or `<all_urls>`, so Start Test requests the optional broad host permission in a one-time Chrome prompt. It is used only for the active test tab.
3. **One HTTP call per agent step.** LangGraph `interrupt()` emits the action; `Command(resume=observation)` continues. Postgres checkpointer holds state, so the API is stateless between calls. If the browser journey ends early, authenticated `POST /runs/{id}/stop` atomically marks the run stopped, labels the unconfirmed action as interrupted and starts a partial report.
4. **Text snapshot first, screenshots rarely** (first impression and when stuck). Tokens are the main cost.
5. **Plain code wherever possible.** Accessibility, performance, SEO and security checks are deterministic integrations. LLMs explain and prioritize the evidence; only the persona session is an agent.
6. **Passive security only, on verified domains** (meta tag, DNS TXT or well-known file).
7. **Runs, not tokens,** for billing. One run = one persona journey; plans include a run allowance (SPEC.md). Tokens logged per run for margins.
8. **react-router** for `/`, `/login`, `/app`, `/app/runs/:id`. Production host must rewrite all paths to `index.html` (Vercel: `rewrites` in vercel.json).
9. **Reads bypass the API.** The web app reads `runs` straight from Supabase under RLS; only the API (postgres role) writes. Fewer endpoints, and the DB enforces ownership.
10. **Extension session handoff.** The dashboard sends the Supabase session to the extension id in `VITE_EXTENSION_ID` through `externally_connectable`; the extension refreshes it against Supabase and sends it as a bearer token.
11. **Decision providers are replaceable, LangGraph is not.** The persona graph owns state, interrupts, budgets, and termination. A Jev provider may choose bounded operations and targets; the existing LLM remains responsible for open-ended generation and fallback. Safety stays in deterministic code.
12. **Step evidence is private and bounded.** The extension captures at most eight JPEG frames per run after meaningful actions, hides Scout and masks form controls for the captured paint, then uploads directly to the private `run-evidence` bucket with the user's JWT. The API only accepts a screenshot path beneath the current run id. Reports request one-hour signed URLs; public reports can read evidence only when the owning run is public.
13. **Browser diagnostics belong to journey steps.** The injected script runs bounded axe WCAG A/AA checks and observes LCP, CLS and INP in the tested tab. Each post-action observation is validated by the API and attached to the exact LangGraph step. Deterministic report code turns failing thresholds into prioritized findings; the LLM explains and ranks but does not invent these measurements.

14. **The server owns the plan.** The client never says which tier it is. `POST /runs` reads the caller's entitlement and clamps steps, logged-in access, test user, site and monthly runs before a LangGraph thread exists.
15. **GEO is deterministic and reuses the site audit.** No new crawler, no LLM calls for the score. The SSRF-safe fetcher and the audited page set are shared by SEO, security and GEO.
16. **Over time means comparison, not more runs.** Reruns and weekly watch compare finding fingerprints against the previous result for the same site. Only changes are reported and emailed.

## v1.1 capability map

Build order and dates: [ROADMAP.md](ROADMAP.md). Product rules: [SPEC.md](SPEC.md).

| Module id | Responsibility | Depends on | Status |
|---|---|---|---|
| `entitlements` | Plans in code, active pass per user, server-side limits, usage counts, global free-capacity cap | auth (live) | Built 2026-09-24 |
| `geo-scan` | AI readiness score, GEO findings, "what AI search sees" text | site audit (live) | Built 2026-09-24 |
| `fix-pack` | Copy-paste robots.txt, JSON-LD, llms.txt and framework rendering fixes | `geo-scan` | Planned |
| `rerun-compare` | Fingerprint findings; fixed, still broken, new | `entitlements` | Built 2026-09-24 |
| `fix-prompt` | Paid prompt for the user's coding agent built from the report | `entitlements`, `fix-pack` | Planned |
| `share-loop` | Launch Ready score, live badge, public report meta with the score | `geo-scan` | Planned |
| `email-check` | Signup email records over DNS-over-HTTPS; auth-mailer limits in journey errors | none | Built 2026-09-24 |
| `finding-states` | Ignore a finding with a reason; respected by compare, fix prompt and watch | `rerun-compare` | Built 2026-09-24 |
| `funnel-metrics` | Steps, fields, errors and time to the first useful screen, per run and across reruns | `rerun-compare` | Planned |
| `copy-review` | One model call on homepage and pricing text, paid runs only | `entitlements` | Planned |
| `competitor-compare` | Passive scans of up to 3 competitor URLs next to the user's site | `geo-scan`, `entitlements` | Planned, post-launch |
| `mcp` | Remote MCP server with personal API keys (Plus) | `fix-prompt`, `rerun-compare`, `entitlements` | Planned, post-launch |
| `billing` | Founder-approved 30-day passes through Dodo, per payment.md | `entitlements` | Planned |
| `evidence-pdf` | Close T18 to T21; branded PDF for Plus | `entitlements` | Partly built |
| `watch` | Weekly server-side scan per saved site, deploy webhook, email only on change | `rerun-compare`, `entitlements` | Planned, post-launch |
| `personas-plus` | Custom test users and several test users per report | `entitlements` | Planned, post-launch |
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
- **Pro's 50-page promise:**
  - Today the crawler caps at 20 pages and 20 s.
  - Pro scans run in a background task with `max_pages=50` and a 60 s budget.
  - The result is written to the report when done.
  - Instant Scan keeps 10 pages and 20 s.

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
- **Comparison:** `report.comparison = {fixed, still_broken, new}` is computed in code after synthesis, never by the LLM.
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
- `GET /badge/{site_id}.svg` is an SVG with the latest score, cached for one hour. It is served only when the owner turned the badge on. It links to the public report.

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

### `mcp` (post-launch)
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
- **Limits:** every tool goes through the same entitlement and rate-limit checks as the web API.

### Testing paid plans in development (no spend)
- **Plans are data.** `apps/api/scripts/grant_plan.py EMAIL PLAN DAYS` inserts an `entitlements` row with `source='dev'` for a test account. Expiring the row reverts the account to free. The dev stack has a test account for each plan.
- **No plan uses a paid model.** Paid features are deterministic code, or use the same free chain as free reports. Testing Pro and Plus costs $0 in model calls.
- **pytest** fakes every model call (existing pattern). Plan limits are tested with crafted requests.
- **Dodo test mode:** test products and test cards, no real money. Webhooks fire for test payments like live ones. Locally they reach the API through a tunnel (cloudflared or ngrok); after deploy, through the VM URL. Sources: [Dodo testing process](https://docs.dodopayments.com/miscellaneous/testing-process).
- **Live model checks stay small:** a few runs a day on the free chain. The bakeoff and trap scorer replay saved runs.

### `watch` (post-launch)
- Table `sites(id, user_id, origin, verified_at, watch boolean, deploy_token_hash, last_watch_run_id)`.
- A weekly job thread, the same pattern as `app/retention.py`, runs a server-side scan for due sites (`kind='watch'`). It is compared with `last_watch_run_id` via `rerun-compare`, and an email goes through Resend only when something is new or fixed.
- `POST /hooks/deploy/{token}` (Vercel or Netlify deploy hook) triggers the same scan. It is rate limited to one scan every 10 minutes per site.
- Journeys on deploy need `cloud-runner`, so watch covers the server-side checks only.

### `cloud-runner` (conditional)
- **Why:** removes the install step for public-page journeys.
- **Built only if** fewer than 25% of beta users who click "Run a test" finish a run.
- **How:** the Oracle ARM VM runs headless Chrome. A worker drives the built `inject.js` over CDP, the same way `evals/e2e_extension.py` already does, and calls the same `/runs` step API.
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
- Site audit (`app/scans/site.py`): pages the test user visited (up to 5) are audited on top of the crawl, past a robots.txt block only on an owner-verified domain; a homepage whose only sign-up link is in the footer is reported as a UX finding. GET-only, same-origin, robots.txt honoured, 10 pages by default (hard cap 20) and a 20 s budget, all fixed in code rather than request input. Redirects are followed manually and each hop passes the SSRF guard before it is requested. Findings repeated across pages are merged into one root cause that keeps the affected-page count and URLs. Exposed-file and bundle-secret checks run only on verified domains. Coverage (`site_audit`) is stored in the report so readers see what was and was not checked.

## Runtime choices for this deployment stage
- **Database access:** the API uses Supabase's HTTPS Data API (`app/db.py`), not a Postgres socket. The direct host is IPv6-only and raw Postgres was unreliable from the founder's network; HTTPS goes through Cloudflare and reuses one connection. `python -m app.db` (schema) still uses SQL.
- **Agent state:** LangGraph uses an in-memory checkpointer unless `CHECKPOINTER=postgres`. Use Postgres when the API runs next to the database or on more than one instance.
- **Models:** free chain of Groq gpt-oss-120b, gpt-oss-20b, Qwen, then Gemini 3.5-flash and 3.1-flash-lite (`GROQ_MODELS`, `GEMINI_MODELS`). Each Groq model has its own 8k tokens/min budget; zero retries so a 429 moves on instantly.
- **Report writer:** the report calls (`runtime.call`, first impression and synthesis) try Groq gpt-oss-120b, then OpenRouter Nemotron 3 Ultra (`OPENROUTER_MODELS`, 90 s budget, plain httpx), then the rest of the chain. Persona steps never wait on OpenRouter. Chosen by `evals/model_bakeoff.py`; see docs/decisions.md.

## Journey safety and grounding
- **Goal intent** (`app/agent/goal.py`): before the first step, one fast model call turns the typed goal into an intent and 1 to 4 checkpoints, or refuses it (pay, delete, cancel, spam, attack, another website) with 422 before a run is counted. The persona prompt shows the checklist; `check` ends the run as `done` when the last checkpoint is reached, by an optional URL marker or the model's `progress`. A planner outage falls back to the typed goal.
- **Loop guards** (`persona.check`): three identical steps (including scroll position) end as `stuck`; a third arrival at the same page ends as `looping`, Walkthru's own stop, never reported as a site problem. Observations carry `scroll_pct` and `at_end`; a click that changes nothing is recorded as `no_change` and shown to the test user.
- **Destructive** (pay, buy, checkout, delete, remove, cancel subscription, transfer, unsubscribe): never clicked as a button on any page; on logged-in pages not even typed into. **Sending** (send, invite): only on a domain the signed-in owner verified (meta tag or `/.well-known/walkthru.txt`), only after the owner confirms in the side panel, at most once per run. Plain links may navigate. Enforced in both `app/agent/persona.py::_enforce` and `apps/extension/lib/execute.ts`.
- A run ended at such a button has status `safe_stop`. `mailto:`/`tel:` links are reported as contact methods and never opened.
- Report grounding (`app/agent/report.py`): `problem_steps` defines where something went wrong; `grounded_ux` drops UX findings that cite no such step or restate a scan finding; the writer sees step outcomes, the final page's controls and a local-dev note, and the system prompt forbids unsupported claims.

## Data lifecycle
- Screenshots in the private `run-evidence` bucket expire after 30 days (`EVIDENCE_RETENTION_DAYS`). Runs, steps and reports stay until the owner deletes them. Instant Scan emails are erased after the same window.
- `app/retention.py` owns every deletion. Order is fixed: storage objects (Storage API, since Supabase blocks direct deletes from `storage.objects`), then LangGraph checkpoints (`delete_thread`), then `runs` rows, then the Supabase Auth user for account deletion. A failure stops the sequence with rows intact, so the delete can be retried.
- Routes: `DELETE /runs/{id}` (owner only), `GET /account/export` (JSON of every run the user owns), `POST /account/delete` (body must repeat the account email).

## Safety rules (enforced in code, not prompts)
Safe mode on logged-in pages (never click delete / remove / cancel subscription / pay / send / invite / transfer; confirm before any form submit), same-origin only, 25-step and 4-minute caps, stop at CAPTCHA, client-side PII masking before snapshot upload, form-control masking before screenshot capture, fake test identity for signups. Evidence capture is best-effort and never blocks the journey. Owner stop, time-limit, origin-exit and post-creation extension errors close the API run and preserve a partial report.

## Environment variables
See [.env.example](.env.example). Web reads `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_URL`. Never expose service-role keys to the web app.
