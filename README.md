# Walkthru

**See where strangers get stuck.** Walkthru is the launch check for apps built with AI. AI test users try your real flows (signup, onboarding, dashboard, checkout up to payment) inside your own Chrome, think aloud, and report where they got stuck. The same report covers SEO, AI search readiness (GEO), passive security hygiene, accessibility and mobile performance, with a grounded fix prompt your coding agent can act on.

Built for solo founders, small startups and agencies shipping with Cursor, Lovable, Bolt, v0 or Claude Code.

![Walkthru product overview](apps/web/public/assets/hero-product.png)

- Start here: [handoff.md](handoff.md), [AGENTS.md](AGENTS.md), [CURRENT_STATE.md](CURRENT_STATE.md)
- Product spec: [SPEC.md](SPEC.md) · Architecture: [ARCHITECTURE.md](ARCHITECTURE.md) · Design: [DESIGN.md](DESIGN.md) · Roadmap: [ROADMAP.md](ROADMAP.md)
- System design tracker: [docs/system-design.md](docs/system-design.md) · Deploy: [docs/deploy.md](docs/deploy.md) · Billing: [docs/billing.md](docs/billing.md)

---

## Contents

1. [What one report answers](#what-one-report-answers)
2. [Product screens](#product-screens)
3. [Design and brand](#design-and-brand)
4. [System breakdown](#system-breakdown)
5. [Repository layout](#repository-layout)
6. [Run it locally](#run-it-locally)
7. [Testing and checks](#testing-and-checks)
8. [Plans](#plans)
9. [Safety rules](#safety-rules)

---

## What one report answers

| Question | How Walkthru answers it |
|---|---|
| **Can a stranger get in?** | A persona agent (first-time visitor, phone user, buyer, skeptic, or your own custom test users on Plus) drives the page in your browser one step at a time. Logged-in pages work without sharing a password. Every finding cites a step, a screenshot or a snippet. |
| **Can Google and AI search read you?** | Deterministic SEO and GEO audits: crawlability, structured data, AI crawler access, content before JavaScript, `llms.txt`, plus a copy-paste fix pack (robots rules, JSON-LD, rendering fix for your framework). |
| **Are you leaking anything?** | Passive checks only: headers and CSP quality, cookies, TLS and CAA, exposed files and source maps, keys shipped to the browser, vulnerable CDN libraries, subdomain takeover, and bounded read-only Supabase and Firebase probes on owner-verified domains. Never an attack. |

On top of the report: a **Launch Ready score** with a live badge, automatic **rerun comparison** (fixed, still broken, new), **competitor side by side**, **weekly watch** with deploy hooks, **AI citation tracking** on free engines, **team workspaces** with a findings board, and a remote **MCP server** so Claude Code and Cursor can scan, read fixes, open pull requests and rerun from the editor.

---

## Product screens

Screens rendered from the HTML sources in [`apps/web/design/mocks/`](apps/web/design/mocks) (re-render with `bash apps/web/design/mocks/render.sh`).

| Evidence report | Extension side panel |
|---|---|
| ![Report with Launch Ready score](apps/web/public/assets/report.png) | ![Extension side panel during a run](apps/web/public/assets/extension-panel.png) |
| **Security hygiene** | **SEO and AI search readiness** |
| ![Security findings](apps/web/public/assets/security.png) | ![SEO findings](apps/web/public/assets/seo.png) |

Where a test user got stuck, with the exact step and evidence:

![Stuck close-up](apps/web/public/assets/stuck-closeup.png)

---

## Design and brand

The live product follows [DESIGN.md](DESIGN.md): premium, light and minimal. Geist and Geist Mono only, thin headlines, one quiet accent (`#4d7274`), real photography, slow deliberate motion, and every animation behind `prefers-reduced-motion`. Scout, the walking bird, is the mark and the in-product assistant.

### Doodle direction (exploration, 2026-10-01)

Thirteen exploratory mockups where the founder's original doodles lead the identity. These are studies, not the shipped UI. Brief and per-screen notes: [`apps/web/design/doodle-exploration/DIRECTION.md`](apps/web/design/doodle-exploration/DIRECTION.md).

![Thirteen doodle-direction mockups](apps/web/design/doodle-exploration/overview.jpg)

| Paper Playground (homepage) | Journey Room (evidence report) | MCP Workshop (editor connections) |
|---|---|---|
| ![Paper Playground](apps/web/design/doodle-exploration/mockup-01.png) | ![Journey Room](apps/web/design/doodle-exploration/mockup-07.png) | ![MCP Workshop](apps/web/design/doodle-exploration/mockup-10.png) |
| **Search Atlas (AI readiness)** | **Release Radar (rerun compare)** | **Agency Wall (team findings)** |
| ![Search Atlas](apps/web/design/doodle-exploration/mockup-08.png) | ![Release Radar](apps/web/design/doodle-exploration/mockup-11.png) | ![Agency Wall](apps/web/design/doodle-exploration/mockup-12.png) |

### Campaign posters

Ten posters in ten aspect ratios built from the same artwork and the site's Geist type. Gallery and sources: [`apps/web/design/doodle-posters/`](apps/web/design/doodle-posters).

![Poster collection](apps/web/design/doodle-posters/overview.jpg)

### Launch films

Three 60-second, 1920x1080 launch films made with Hyperframes, each with Scout as the AI test user. Click a frame to open the MP4. Sources, tools and re-render steps: [`apps/web/design/launch-videos/README.md`](apps/web/design/launch-videos/README.md). A 30-second cut lives in [`apps/web/design/launch-video-30s/`](apps/web/design/launch-video-30s).

| A. Ship Friday | B. Every Stranger | C. Not a Scanner |
|---|---|---|
| [![Film A](apps/web/design/launch-videos/posters/A-ship-friday.jpg)](apps/web/design/launch-videos/walkthru-launch-A-ship-friday.mp4) | [![Film B](apps/web/design/launch-videos/posters/B-every-stranger.jpg)](apps/web/design/launch-videos/walkthru-launch-B-every-stranger.mp4) | [![Film C](apps/web/design/launch-videos/posters/C-not-a-scanner.jpg)](apps/web/design/launch-videos/walkthru-launch-C-not-a-scanner.mp4) |
| Product-led: real captures, the agent loop, MCP, the report, a fix pull request. | Bold shapes: a word wheel of features, five coloured Scouts, the findings table. | Editorial manifesto: one phrase per beat, illustrated crowd, real footage. |

---

## System breakdown

```
Chrome extension (your browser)                       Walkthru API (FastAPI + LangGraph)
───────────────────────────────                       ──────────────────────────────────
side panel: site, goal, test user  ── POST /runs ───────────▶ check plan, create run + LangGraph thread
page script: snapshot + axe + vitals ─ POST /runs/{id}/observe ─▶ persona agent decides one action
  (numbered elements, visible text,  ◀── click #12 | type #4 | scroll | done | give_up
   errors; PII masked before upload)
runs the action in the real tab
masked JPEG evidence ───────────────────────────────▶ private Storage, tied to the exact step
                    ... repeat until done, give up or step budget ...
                                                    queued job: scans + report ─▶ Supabase ─▶ report page, email

Server-only scans (no browser): SEO, GEO, security hygiene, accessibility basics, PageSpeed, email DNS
Web app (React) ── Supabase Auth JWT ── API verifies every call; the server decides the plan
Reads: web app reads its own rows straight from Supabase under RLS. Writes: only the API.
```

### Key design decisions

1. **Browser on the user's machine, brain on the server.** No Chromium on our servers, so hosting stays near zero and logged-in pages work without sharing passwords.
2. **One HTTP call per agent step.** LangGraph `interrupt()` emits the next action and `Command(resume=observation)` continues. A Postgres checkpointer holds state, so the API is stateless between calls. Start, observe and stop accept an `Idempotency-Key` ([docs/run-idempotency.md](docs/run-idempotency.md)).
3. **Deterministic code before a model call.** Accessibility, performance, SEO, GEO and security are plain code. Models explain and prioritize evidence; only the persona session is an agent. Scores, comparisons and fix prompts are computed in code and cannot invent findings.
4. **Free tier models only.** Groq `gpt-oss-120b` first, then a Gemini fallback chain, with a shared circuit breaker ([docs/provider-resilience.md](docs/provider-resilience.md)). Paid models stay off until revenue pays for them.
5. **The server owns the plan.** The client never says which tier it is; `POST /runs` clamps steps, sites, test users and logged-in access from the caller's entitlement.

### Components

| Part | What it does | Where |
|---|---|---|
| **Web app** | Landing, pricing, docs, login (Google, GitHub, magic link), dashboard, private and public reports, compare, watch, AI answers (citations), teams, settings with API keys, billing | `apps/web` (React 19, Vite, TypeScript, Tailwind v4, GSAP) |
| **Chrome extension** | Side panel to start a run, page script that snapshots the DOM, masks PII, runs axe WCAG A/AA and Core Web Vitals, executes actions with safety gates, and captures up to eight masked screenshots | `apps/extension` (Chrome MV3, WXT, React) |
| **API** | Run lifecycle, persona graph, scans, reports, entitlements, billing webhooks, teams, watch, citations, MCP | `apps/api/app` (Python 3.12, FastAPI, LangGraph, httpx) |
| **Persona agent** | LangGraph graph with step budgets, loop guards, safe stops on Pay and Delete, optional TypeSafe Jev provider for bounded decisions | `apps/api/app/agent/` |
| **Scanners** | `site` (bounded crawler), `seo`, `seo_depth`, `geo`, `geo_depth`, `geo_fixes`, `security`, `csp`, `tls`, `secrets`, `libraries`, `takeover`, `backend`, `email`, `accessibility`, `performance`, `stack` | `apps/api/app/scans/` |
| **SSRF-safe fetcher** | Resolves each host once, refuses private and metadata addresses (including IPv4 hidden in IPv6), pins the connection to the checked address, and allows at most two concurrent requests per host | `app/scans/fetch.py` |
| **Background jobs** | Durable Postgres queue: `claim_job` with `FOR UPDATE SKIP LOCKED`, leases, retries with backoff, periodic retention and watch scheduling. Survives restarts and runs across processes | `app/jobs.py` |
| **Rate limits** | Shared Postgres limiter per address, account and route (runs, observe, costly endpoints, MCP), plus a per-target politeness cap of 30 scans per host per hour. Fails open if the database is down | `app/limits.py` |
| **Migrations** | Numbered SQL files, each applied in one transaction with a checksum; editing an applied file is refused | `app/migrate.py`, `apps/api/migrations/` |
| **MCP server** | Remote MCP at `/mcp` (streamable HTTP, personal API key, Plus plan) with 23 tools: scan, report, fix prompt, rerun, findings (get, verify, accept, reopen), site verification tag, GitHub repos and fix pull requests, compare, share, AI answers, watch and deploy hooks | `app/mcp_server.py` |
| **Citations** | Tracks whether AI engines name and cite your site for your prompts, with evidence, on a dedicated queue | `app/citations.py`, `app/citation_evidence.py` |
| **Teams** | Workspaces with roles, invitations, shared reports, findings board, threads, activity and Scout in team chat | `app/teams.py`, `app/scout.py` |
| **Billing** | Founder-approved 30-day passes through Dodo Payments with signed webhooks | `app/billing.py`, [docs/billing.md](docs/billing.md) |
| **Admin panel** | Founder-only panel on `127.0.0.1:8020` with password and authenticator code. Never deployed | `apps/api/admin/` |
| **Data** | Supabase Postgres with RLS on every table, private `run-evidence` Storage bucket, LangGraph checkpoints in a private schema | `apps/api/migrations/` |
| **Email** | Resend over REST (report ready, watch changes, team invites) | `app/deliver.py` |
| **Evals and fixtures** | Easy, hard and showcase fixture sites full of traps; LangSmith evals | `evals/` |

---

## Repository layout

```
apps/web/          React 19 + Vite + TypeScript + Tailwind v4 + GSAP
  src/pages/       One file per page (Landing, Login, Dashboard, Report, Compare, Watch, Visibility, Teams, Mcp, ...)
  src/components/  Shared UI (Nav, Pricing, Faq, ScanForm, Footer, Logo, Loading orbs)
  src/lib/         supabase.ts, auth.ts, runs.ts, motion.ts, session handoff to the extension
  src/content.ts   All marketing copy
  public/assets/   Images and product screens
  design/          mocks/, doodle-exploration/, doodle-posters/, launch-videos/, launch-video-30s/, source-images/
apps/api/          FastAPI + LangGraph
  app/             main.py (routes), agent/, scans/, jobs.py, limits.py, migrate.py, mcp_server.py, ...
  migrations/      0001_initial.sql, 0002_agent_checkpoints.sql, 0003_run_idempotency.sql
  admin/           Local founder admin panel
  scripts/         test_user.py, grant_plan.py, billing.py
  tests/           pytest suite
  requirements.lock  Pinned, tested Python dependencies
apps/extension/    Chrome MV3 extension (WXT + React)
  entrypoints/     background, inject (page script), sidepanel
  lib/             snapshot, redact, execute, safety, evidence, api, session
  tests/           vitest
evals/             fixtures/easy, fixtures/hard, showcase, traps.json, serve.py, e2e_extension.py
docs/              Deploy, billing, system design tracker, auth sessions, idempotency, provider resilience, ...
dev.py, dev.cmd    One-command dev stack (development only)
```

---

## Run it locally

### Prerequisites

- **Python 3.12+**
- **Node.js 20.19+** (Vite 8 and WXT)
- **Google Chrome** (for the extension)
- A **Supabase** project (free tier is enough): URL, publishable key, secret key and a Postgres connection string
- A free **Groq** API key and a free **Google AI Studio** (Gemini) key
- Optional: PageSpeed API key, Resend key, LangSmith key, Dodo test-mode keys

### 1. Clone and configure

```bash
git clone https://github.com/watermelon588/Walkthru.git
cd Walkthru
```

Every variable is listed with comments in [`.env.example`](.env.example). Copy the API block into `apps/api/.env` and the `VITE_*` block into `apps/web/.env`. For the extension, copy `apps/extension/.env.beta.example` to `apps/extension/.env`. Never commit any `.env` file.

Minimum for a local run:

| File | Variables |
|---|---|
| `apps/api/.env` | `GROQ_API_KEY`, `GOOGLE_API_KEY`, `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SECRET_KEY`, `DATABASE_URL`, `WEB_URL=http://localhost:5173`, `ALLOW_LOCAL_SCANS=1` (to scan the local fixtures) |
| `apps/web/.env` | `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_URL=http://localhost:8010`, `VITE_EXTENSION_ID` (after loading the extension) |
| `apps/extension/.env` | `VITE_API_URL`, `VITE_WEB_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` |

If your network cannot reach Supabase's direct IPv6 host, use the session pooler string (port 5432) for `DATABASE_URL`. Never use the transaction pooler (6543).

### 2. Install the API and create the database

```powershell
cd apps/api
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.lock
.venv\Scripts\python -m pip install -e . --no-deps
.venv\Scripts\python -m app.migrate            # apply pending migrations (status, down also available)
.venv\Scripts\python scripts/test_user.py      # optional: throwaway account and session for local testing
```

On macOS or Linux use `.venv/bin/python` instead of `.venv\Scripts\python`.

### 3. Install the web app and the extension

```bash
cd apps/web && npm install
```

```bash
cd apps/extension && npm install && npm run build
```

Open `chrome://extensions`, turn on **Developer mode**, click **Load unpacked** and pick `apps/extension/.output/chrome-mv3`. Copy the extension id into `VITE_EXTENSION_ID` in `apps/web/.env`. After every rebuild, click **Reload** on the Walkthru card.

### 4. Start everything with one command (Windows, development only)

From the repository root:

```powershell
.\dev
```

This builds the extension and starts the API (http://localhost:8010), the web app (http://localhost:5173) and the fixture sites (easy :8101, hard :8102, showcase :8103) with labelled output, and restarts the API when its code changes. Ctrl+C stops all of them. `dev.py` and `dev.cmd` are development conveniences and are removed before production.

### Or one process per terminal (any OS)

```bash
# API
cd apps/api && .venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

```bash
# Web app
cd apps/web && npm run dev -- --host 127.0.0.1 --port 5173
```

```bash
# Fixture sites: easy :8101, hard :8102
apps/api/.venv/Scripts/python evals/serve.py
```

### 5. Try a run end to end

1. Check http://127.0.0.1:8010/health.
2. Sign in at http://localhost:5173/login (the dashboard hands your session to the extension).
3. Open http://127.0.0.1:8101 (easy) or http://127.0.0.1:8102 (hard).
4. Open the Walkthru side panel from the Chrome toolbar.
5. Enter a goal such as `Sign up for an account`, pick a test user and click **Start test**.
6. When it finishes, open the report from the side panel or dashboard and check the steps, screenshot evidence, Share, Email me, CSV export and Save PDF.

The showcase fixture (http://127.0.0.1:8103) is a well-built product site whose journeys hold deliberate traps: circular links, a cookie banner, a newsletter pop-up, a dead button, new-tab and external links, content hidden until scrolled, and Pay and Delete buttons Walkthru must never press.

### Useful extras

```powershell
# Drive the built extension's page script in headless Chrome through the real API and model, then print the report
apps\api\.venv\Scripts\python evals\e2e_extension.py https://your-site.vercel.app "Find the projects and a way to get in touch"

# Free accounts get 3 runs a month. Give a test account a dev pass to try paid plans (no payment involved)
apps\api\.venv\Scripts\python apps\api\scripts\grant_plan.py you@example.com pro     # --revoke ends it

# Run background jobs in their own process (set JOB_WORKERS=0 in the API first)
cd apps/api; .venv\Scripts\python -m app.jobs

# Founder admin panel on http://127.0.0.1:8020 (this computer only)
cd apps/api; .venv\Scripts\python -m admin setup; .venv\Scripts\python -m admin
```

To test a real form send on the easy fixture as a verified owner, write your verification token to `evals/.walkthru-token` (git-ignored; see `GET /verification`) and run with `AUTO_CONFIRM=1`. Without it the run stops at the send button.

### Connect your coding agent over MCP (Plus)

Create a key in **Settings, API keys and MCP**, then in your project:

```bash
claude mcp add --transport http walkthru http://localhost:8010/mcp --header "Authorization: Bearer YOUR_KEY"
```

Cursor and other clients take the same URL and header. The full tool list is on the `/docs#mcp` page of the web app.

---

## Testing and checks

All of these must stay green before a push.

```bash
# API
cd apps/api
.venv/Scripts/python -m pytest -q
.venv/Scripts/ruff check .
```

```bash
# Web
cd apps/web
npm run build        # tsc + vite build
npm run lint         # oxlint, 0 warnings
```

```bash
# Extension
cd apps/extension
npm test             # vitest
npx tsc --noEmit && npm run lint
```

CI (`.github/workflows/security.yml`) runs `npm audit`, `pip-audit` against `requirements.lock`, and gitleaks on every push.

---

## Plans

| | Free | Launch Pack | Pro | Plus |
|---|---|---|---|---|
| Price | $0 | $9 once | $19/mo ($15 founding) | $49/mo ($39 founding) |
| Test runs | 3 a month | 20 within 30 days | 40 a month | 150 a month |
| Pages the test user may enter | Public | Public and logged-in | Public and logged-in | Public and logged-in |
| Rerun compare, fix prompt, competitors | No | Yes | Yes | Yes |
| MCP server, weekly watch, team workspaces | No | No | No | Yes |

Full table and what is still coming: [SPEC.md](SPEC.md#plans).

---

## Safety rules

- Passive, read-only checks only. No attack payloads, no fuzzing, no writes to a site's backend.
- Deep checks run only on domains the owner has verified (meta tag, DNS TXT or well-known file).
- The agent never submits payment forms, never solves CAPTCHAs, and asks before any real form send.
- Form fields are masked in snapshots and screenshots before anything leaves the browser.
- Repository code is never kept after a scan.

Licences of reused open source are recorded in [`apps/api/THIRD_PARTY.md`](apps/api/THIRD_PARTY.md).
