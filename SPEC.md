# Spec: Walkthru v1

## Objective
Small teams ship websites without ever watching a stranger use them. Walkthru gives them one evidence report with:
1. **AI test users** walk through real flows (landing → signup → dashboard) in the team's own browser, think aloud, and show where they get stuck.
2. **SEO check** of the pages visited (and the whole site on paid plans).
3. **Accessibility and mobile performance checks** with concrete evidence and an explicit unavailable state when PageSpeed is not configured.
4. **Security hygiene check** (passive: headers, cookies, exposed files, leaked keys in JS). Not a pentest.

Plus a plain-English fix list, ranked by impact.

**Users:** indie devs and students (free, community), small startups and agencies (paid).

## How it works (architecture)
```
Chrome extension (client)                    Walkthru server (FastAPI + LangGraph)
─────────────────────────                    ──────────────────────────────────────
side panel: pick goal + persona  ── start ─▶ create run, LangGraph thread
content script: snapshot page    ── observe ▶ persona agent decides next action
  (URL, numbered buttons/links/    ◀─ action ── {click #12 | type #4 "…" | scroll | done | give_up}
   inputs, visible text, errors)
executes action in the real tab   ── observe ▶ … loop until done/give_up/budget …
                                               synthesize report
                                  ◀─ report ── report page + email
Server-only (no browser needed): static accessibility checks, PageSpeed Insights mobile performance, SEO scan (HTML, robots, sitemap), and security hygiene (headers, TLS, cookies, exposed files, secrets in JS bundles).
```
- The **loop runs in the extension side panel page** (not the MV3 service worker, which Chrome suspends).
- Each step = one HTTP call. Server resumes the LangGraph thread with the observation (`interrupt` / `Command(resume=…)`), Postgres checkpointer holds state. Server is stateless between calls.
- **Logged-in pages work without sharing passwords**: the agent uses the session already open in the user's browser.
- Text snapshot by default; screenshots (`captureVisibleTab`, JPEG) only for the first impression and when the agent is stuck. Keeps tokens low.

## Plans (Dodo Payments)
| Plan | Price | Includes |
|---|---|---|
| Free | $0 | Instant Scan of your homepage (first impression, SEO basics, security headers), no install. Extension: 3 AI test runs/month, public pages only, 1 persona, 12 steps per run |
| Launch Pack | $9 one-time | 20 runs within 30 days, all Pro features |
| Pro | $15/month | 60 runs, logged-in pages (dashboard, settings, checkout-up-to-payment), all personas, 30 steps, full-site SEO (up to 50 pages), full security hygiene, re-run compare, CSV/Google Sheet export, email reports |
| Team | $39/month | 250 runs, 5 sites, custom personas, weekly scheduled scans by email, shared reports |

Credit = one persona run. Tokens logged per run for margin tracking.

## Agent design (LangGraph)
- `test_run` graph: `preflight` (plan limits, site check) → `first_impression` (screenshot + page text: what is this, who is it for, what would you click, trust signals) → `persona_session` per persona → `synthesize` (dedupe, severity, evidence, top fixes, clarity & conversion review) → `deliver`.
- `persona_session` (the agent): `decide` (in character, one action + think-aloud + confusion 0–3, with memory of tried paths) → `interrupt` for observation → `check` (goal reached? loop on same page 3×? budget?) → back to `decide`.
- `site_scan` graph (server-only, parallel): `accessibility_scan`, `performance_scan`, `seo_scan` and `security_scan`. The synthesis LLM explains and prioritizes their deterministic evidence.

## Safety rules (non-negotiable)
- **Safe mode on logged-in pages:** the agent never clicks elements whose text/aria matches delete/remove/cancel subscription/pay/purchase/send/invite/transfer; never submits payment forms; asks the user in the side panel before any form submit on logged-in pages.
- Same-origin only; step and time caps; stops at CAPTCHA and reports it.
- **Redaction before upload:** emails, long numbers, and input values are masked in the snapshot; user is told what is sent.
- **Server security scans only on verified domains** (meta tag / DNS TXT / well-known file). Passive checks only: no fuzzing, no injection payloads, no brute force.
- Fake test identity for signups.

## Tech Stack
- **Extension:** Chrome MV3, TypeScript, WXT, React side panel.
- **Web:** React + Vite + TypeScript, Tailwind v4, Motion, Phosphor icons, Geist font. Supabase auth.
- **Server:** Python 3.12+, FastAPI, LangGraph + Postgres checkpointer, `langchain-google-genai` (free tier model) and `langchain-anthropic` (paid tier), httpx, selectolax, Resend, Dodo SDK.
- **Data:** Supabase (Postgres, Auth, Storage for screenshots). **Evals:** LangSmith. **Hosting:** Vercel (web), Oracle Always Free VM or ~$5 VPS (server).

## Commands
```
cd apps/api && .venv/Scripts/python -m pip install -e ".[dev]" && .venv/Scripts/uvicorn app.main:app --reload
.venv/Scripts/python -m pytest -q && .venv/Scripts/ruff check .
cd apps/web && npm install && npm run dev | npm run build
cd apps/extension && npm install && npm run dev | npm run build   # loads unpacked in Chrome
```

## Project Structure
```
apps/api/        FastAPI + LangGraph (graphs/, scans/, billing/, routes/)
apps/web/        landing + dashboard + report pages
apps/extension/  MV3 extension (sidepanel/, content/ snapshot + executor)
evals/           fixture sites with seeded UX/SEO/security traps + runner
```

## Testing Strategy
- pytest: accessibility, performance, SEO and security checks, redaction, plan limits, Dodo webhook signature, step API contract.
- Extension: unit tests for snapshot + safe-mode filter (vitest).
- **Fixture sites with seeded traps** (hidden signup, silent form error, missing meta description, no HSTS, key in JS bundle) = quality evals in LangSmith: % traps found, $ per run.

## Boundaries
- **Always:** safe mode, redaction, verified domain for security scan, log tokens per run.
- **Ask first:** new deps beyond this spec, paid-tier model change, schema changes after launch.
- **Never:** active attacks, CAPTCHA solving, payment submission, storing page content longer than the report needs, committing secrets.

## Success Criteria
- 3-page public flow test finishes in ≤ 3 min; report ≤ 30 s after run.
- ≥ 80% of seeded traps found on fixture sites.
- Paid run cost ≤ $0.20; free run ≤ $0.02.
- Chrome Web Store listing approved before launch.
- 50 community sites tested, 5 paying by 2026-11-30.
