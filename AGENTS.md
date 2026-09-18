# AGENTS.md

Instructions for any AI coding agent (Claude Code, Codex, Cursor) working in this repo. Read this first, then CURRENT_STATE.md.

## What this project is
Walkthru: AI test users try a website's flows (signup, dashboard, checkout) in the user's own browser, then report where they got stuck, plus SEO and passive security hygiene. B2B SaaS for indie developers, small startups and agencies. Product spec: [SPEC.md](SPEC.md).

## Read before working
| File | When |
|---|---|
| [CURRENT_STATE.md](CURRENT_STATE.md) | Always. What is done, what is next, known issues. |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Any backend, extension, agent or data work. |
| [DESIGN.md](DESIGN.md) | Any UI work. Tokens, type, motion rules. |
| [SKILLS.md](SKILLS.md) | Picking which agent skill to load for a task. |
| [tasks/todo.md](tasks/todo.md) | Picking the next task. |

## Repo layout
```
apps/web/        React 19 + Vite + TS + Tailwind v4 + GSAP. Landing, login, (soon) dashboard and report pages.
  src/pages/     One file per page (Landing.tsx, Login.tsx)
  src/components/Shared.tsx   Nav, Pricing, Faq, ScanForm, Closing, Footer, Asset, Words, class constants
  src/lib/       supabase.ts (client), motion.ts (useReveal GSAP hook)
  src/content.ts All marketing copy. Edit copy here, not in components.
  public/assets/ Images. *.png screenshots are placeholders rendered from design/mocks.
  design/        mocks/ (HTML sources for placeholder screenshots), source-images/ (originals, not shipped)
apps/api/        FastAPI + LangGraph (scaffold only so far)
apps/extension/  Chrome MV3 extension (WXT + React). entrypoints/ (background, inject, sidepanel), lib/ (snapshot, redact, execute, safety, api), tests/
evals/           Fixture sites (fixtures/easy, fixtures/hard, traps.json, serve.py) + LangSmith evals (T9, not started)
```

## Commands
```
# web
cd apps/web && npm install
npm run dev        # http://localhost:5173
npm run build      # tsc + vite build, must pass
npm run lint       # oxlint, must be 0 warnings
bash design/mocks/render.sh   # re-render placeholder screenshots (uses local Edge)

# api
cd apps/api && python -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m pytest -q
.venv/Scripts/ruff check .

# extension
cd apps/extension && npm install
npm run build      # then chrome://extensions > Load unpacked > apps/extension/.output/chrome-mv3
npm test           # vitest
npx tsc --noEmit && npm run lint

# fixtures
apps/api/.venv/Scripts/python evals/serve.py   # easy :8101, hard :8102
```

## Rules
- **Always:** keep build and lint green; use design tokens (`bg-bg`, `text-ink`, `text-muted`, `border-line`, `bg-surface`, `text-accent`, `text-danger`), never raw hex in components; honor `prefers-reduced-motion` for every animation; label every input; handle loading, error and empty states.
- **Ask first:** adding dependencies not listed in ARCHITECTURE.md, schema changes after launch, changing the paid-tier LLM, changing pricing.
- **Never:** commit secrets or `.env`; use em dashes in user-facing copy; add a new accent color; run active security probes; submit payment forms from the agent; solve CAPTCHAs.
- Simplest working solution first (see the ponytail skill). No abstractions for one caller.
- Update CURRENT_STATE.md at the end of every working session.
