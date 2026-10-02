# AGENTS.md

Instructions for any AI coding agent (Claude Code, Codex, Cursor) working in this repo. Read this first, then CURRENT_STATE.md.

## What this project is
Walkthru: AI test users try a website's flows (signup, dashboard, checkout) in the user's own browser, then report where they got stuck, plus SEO and passive security hygiene. B2B SaaS for indie developers, small startups and agencies. Product spec: [SPEC.md](SPEC.md).

## Read before working
| File | When |
|---|---|
| [handoff.md](handoff.md) | First, in a new session. The whole picture and the reading order. |
| [CURRENT_STATE.md](CURRENT_STATE.md) | Always. What is done, what is next, known issues. |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Any backend, extension, agent or data work. |
| [DESIGN.md](DESIGN.md) | Any UI work. Tokens, type, motion rules. |
| [SKILLS.md](SKILLS.md) | Picking which agent skill to load for a task. |
| [tasks/todo.md](tasks/todo.md) | Picking the next task. |

## Repo layout
```
apps/web/        React 19 + Vite + TS + Tailwind v4 + GSAP. Landing, login, (soon) dashboard and report pages.
  src/pages/     One file per page (Landing, Login, Dashboard, Report)
  src/components/Shared.tsx   Nav, Pricing, Faq, ScanForm, Closing, Footer, Asset, Words, class constants
  src/lib/       supabase.ts (client), auth.ts (useSession, signOut), runs.ts (Supabase reads), motion.ts
  src/content.ts All marketing copy. Edit copy here, not in components.
  public/assets/ Images. *.png screenshots are placeholders rendered from design/mocks.
  design/        mocks/ (HTML sources for placeholder screenshots), source-images/ (originals, not shipped)
apps/api/        FastAPI + LangGraph. app/agent/ (persona graph), app/auth.py, app/db.py, app/migrate.py, migrations/ (numbered SQL), scripts/test_user.py
apps/extension/  Chrome MV3 extension (WXT + React). entrypoints/ (background, inject, sidepanel), lib/ (snapshot, redact, execute, safety, api), tests/
evals/           Fixture sites (fixtures/easy, fixtures/hard, traps.json, serve.py) + LangSmith evals (T9, not started)
```

## Commands
```
# everything at once (DEV ONLY; remove dev.py and dev.cmd before production)
.\dev              # API :8010, web :5173, fixtures :8101/:8102, extension build

# web
cd apps/web && npm install
npm run dev        # http://localhost:5173
npm run build      # tsc + vite build, must pass
npm run lint       # oxlint, must be 0 warnings
bash design/mocks/render.sh   # re-render placeholder screenshots (uses local Edge)

# api
cd apps/api && python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.lock && .venv/Scripts/python -m pip install -e . --no-deps
# pinned, tested versions (SD-9.2); to upgrade, regenerate requirements.lock with the command at its top and rerun the tests
.venv/Scripts/python -m pytest -q
.venv/Scripts/ruff check .
.venv/Scripts/python -m app.migrate       # apply pending migrations/NNNN_*.sql (also: python -m app.db); `status`, `down`
.venv/Scripts/python scripts/test_user.py # throwaway account + session for local testing
.venv/Scripts/python scripts/grant_plan.py EMAIL pro   # dev pass to test paid plans for free (--revoke to end it)
.venv/Scripts/python -m admin setup   # once: founder admin password + authenticator code (writes hashes to .env)
.venv/Scripts/python -m admin         # founder admin panel on http://127.0.0.1:8020 (this computer only, never deployed)

# extension
cd apps/extension && npm install
npm run build      # then chrome://extensions > Load unpacked > apps/extension/.output/chrome-mv3
npm test           # vitest
npx tsc --noEmit && npm run lint

# fixtures
apps/api/.venv/Scripts/python evals/serve.py   # easy :8101, hard :8102
```

## Rules
- **Git attribution:** use the founder's configured Git identity for work performed with AI tools. Do not add Claude, Codex, OpenAI or other AI tools as commit authors, co-authors or PR attribution. Preserve credit for any actual human contributors.
- **Always:** keep build and lint green; use design tokens (`bg-bg`, `text-ink`, `text-muted`, `border-line`, `bg-surface`, `text-accent`, `text-danger`), never raw hex in components; honor `prefers-reduced-motion` for every animation; label every input; handle loading, error and empty states.
- **Always (v1.2 build rules, ROADMAP.md):** deterministic code before a model call; free-tier models and APIs only; reuse open source after checking its licence (docs/decisions.md 2026-09-25) and keep its notice in `apps/api/THIRD_PARTY.md`.
- **Ask first:** adding dependencies not listed in ARCHITECTURE.md (permissive open source is approved in principle; still name it in the task), schema changes after launch, switching on any paid model or API, changing pricing.
- **Never:** commit secrets or `.env`; use em dashes in user-facing copy; add a new accent color; send attack payloads, fuzz, or write to a site's backend; probe a domain the owner has not verified (read-only probes only); active-scan a production URL; copy code or data from AGPL, Commons Clause, Elastic or unlicensed repos; keep repository code after a scan; submit payment forms from the agent; solve CAPTCHAs.
- **Schema changes:** a new numbered file in `apps/api/migrations/` (plus `.down.sql` when reversible). Never edit an applied migration; the runner refuses it.
- Simplest working solution first (see the ponytail skill). No abstractions for one caller.
- Update CURRENT_STATE.md at the end of every working session.
