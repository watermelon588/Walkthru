# Current State

_Last updated: 2026-09-18_

## Done
- Product defined: Walkthru. [SPEC.md](SPEC.md), [tasks/plan.md](tasks/plan.md), [tasks/todo.md](tasks/todo.md).
- Monorepo scaffold: `apps/api` (FastAPI `/health` + test), `apps/web` (Vite React TS).
- **Landing page final** (`apps/web/src/pages/Landing.tsx`): Silver base with sections borrowed from the explored variants. See DESIGN.md.
- Placeholder product screenshots rendered from `apps/web/design/mocks/`. Founder photos picked and named in `public/assets/`.
- **Login page** (`/login`, `apps/web/src/pages/Login.tsx`): Google, GitHub and email magic link via Supabase. Inline validation, sending, sent and error states. Shows "not configured" until keys are set.
- Footer with tagline, about text and link columns.
- **Renamed to Walkthru.** Brand lives in `apps/web/src/brand.ts` (name, tagline, description, bird logo). Logo, favicon, page titles, footer, mocks all updated.
- New visuals: `agent-eye.jpg` in "How it works", `login.jpg` (blurred figure in a lounge chair) on the login page.
- Design pass against design-taste-frontend: nav shows bird only, screenshots trimmed and shown at natural size, quote section turned into a full-bleed band (no more 3 split sections in a row), hero headline fits 2 lines.
- Docs: AGENTS.md, ARCHITECTURE.md, DESIGN.md, SKILLS.md, this file.
- **Agent core (T5, 2026-09-18).** `apps/api/app/agent/`: `schema.py` (Observation, PersonaStep wire contract), `safety.py` (danger words, same-origin, caps), `persona.py` (LangGraph `decide -> act(interrupt) -> check` loop, 4 built-in personas, fake test identity, code-level safe mode), `runtime.py` (free = Gemini via `FREE_MODEL`, paid = Claude via `PAID_MODEL`, MemorySaver unless `DATABASE_URL` set). Routes: `POST /runs`, `POST /runs/{id}/observe`, `GET /runs/{id}`. 9 pytest with a scripted fake model. Session-by-session plan in [tasks/plan.md](tasks/plan.md).

## In progress
- Auth wiring: needs a Supabase project (founder).
- Agent loop verified against a real model (Groq gpt-oss-120b) with the Supabase Postgres checkpointer on 2026-09-18: two-step signup flow, sensible actions, state persisted.

## Next up
1. Founder: in the Supabase dashboard enable Google and GitHub providers and add `http://localhost:5173` to redirect URLs (keys are already in both `.env` files). Rotate the DB password and secret key before launch (shared over chat).
2. Session handling: read the session after redirect, sign out, protect app routes.
3. Add react-router and the dashboard shell (T10), then point `redirectTo` in Login.tsx at `/app`.
4. Session 2: T2 fixture sites. Session 3: T3 extension snapshot. Session 4: T4 executor + loop, Checkpoint A with a real model.

## Known issues and notes
- Scan form and pricing buttons are front end only (T11, T14 wire them).
- Privacy, Terms and Security pages do not exist yet (footer links are `#`). Required before launch.
- Domain not bought yet (`brand.domain` is a placeholder). `agent-eye.jpg` is 735px wide, a bit soft on large screens.
- Two portraits are low resolution (persona-phone, persona-buyer, under 1000px wide).
- Production hosting must rewrite all paths to `index.html` for `/login` to work on refresh.
- Remote: https://github.com/watermelon588/Walkthru.git. First commit made 2026-09-18, not pushed yet.
- No Anthropic budget for now: everything runs on free providers (Groq, Gemini). Fallback chain lives in `apps/api/app/agent/runtime.py`.

## Checks (last run)
- `npm run build`: pass. `npm run lint`: 0 warnings. `pytest`: 9 passed. `ruff`: clean.
- Landing: all 12 images load, no horizontal overflow at 375px and 1024px.
- Login: invalid email error and not-configured message verified in the browser.
