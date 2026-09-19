# Current State

_Last updated: 2026-09-19_

## Done
- Product defined: Walkthru. [SPEC.md](SPEC.md), [tasks/plan.md](tasks/plan.md), [tasks/todo.md](tasks/todo.md).
- Monorepo scaffold: `apps/api` (FastAPI `/health` + test), `apps/web` (Vite React TS).
- **Landing page final** (`apps/web/src/pages/Landing.tsx`): Silver base with sections borrowed from the explored variants. See DESIGN.md.
- **Agent identity lab** (`/agent-lab`): Scout, Trace and three colour-only Scout variants rendered as draggable SVG birds, each with a name and current activity. All use the confirmed GSAP Observe motion with overlapped SVG joints. The prototype is intentionally not linked from production navigation yet.
- Placeholder product screenshots rendered from `apps/web/design/mocks/`. Founder photos picked and named in `public/assets/`.
- **Login page** (`/login`, `apps/web/src/pages/Login.tsx`): Google, GitHub and email magic link via Supabase. Inline validation, sending, sent and error states. Shows "not configured" until keys are set.
- Footer with tagline, about text and link columns.
- **Renamed to Walkthru.** Brand lives in `apps/web/src/brand.ts` (name, tagline, description, bird logo). Logo, favicon, page titles, footer, mocks all updated.
- New visuals: `agent-eye.jpg` in "How it works", `login.jpg` (blurred figure in a lounge chair) on the login page.
- Design pass against design-taste-frontend: nav shows bird only, screenshots trimmed and shown at natural size, quote section turned into a full-bleed band (no more 3 split sections in a row), hero headline fits 2 lines.
- Docs: AGENTS.md, ARCHITECTURE.md, DESIGN.md, SKILLS.md, this file.
- **Agent core (T5, 2026-09-18).** `apps/api/app/agent/`: `schema.py` (Observation, PersonaStep wire contract), `safety.py` (danger words, same-origin, caps), `persona.py` (LangGraph `decide -> act(interrupt) -> check` loop, 4 built-in personas, fake test identity, code-level safe mode), `runtime.py` (free = Gemini via `FREE_MODEL`, paid = Claude via `PAID_MODEL`, MemorySaver unless `DATABASE_URL` set). Routes: `POST /runs`, `POST /runs/{id}/observe`, `GET /runs/{id}`. 9 pytest with a scripted fake model. Session-by-session plan in [tasks/plan.md](tasks/plan.md).

- **Fixture sites (T2, 2026-09-18).** `evals/fixtures/easy` (Acme Notes: clean signup flow, good SEO, security headers) and `evals/fixtures/hard` (Zentrix: 18 seeded traps, 6 UX, 6 SEO, 6 security, listed in `evals/traps.json`). `python evals/serve.py` serves both with per-site headers; `python -m pytest tests/test_fixtures.py` proves each trap is present on hard and absent on easy.

- **Extension (T3 + T4, 2026-09-18).** `apps/extension` (WXT 0.21, React 19, vitest). `lib/snapshot.ts` numbers visible interactive elements (open shadow roots included), collects page text and visible errors, flags CAPTCHA, tags elements with `data-walkthru-id`. `lib/redact.ts` masks emails, long numbers and key-like tokens before upload. `lib/execute.ts` runs one step (click, type via native setters, scroll, back) with a dry-run mode and the safe-mode filter. `entrypoints/sidepanel/run.ts` is the step loop: requests host access for the site's origin only, injects `inject.js` on demand, one `/runs` call per step, stops on leaving the origin or after 4 minutes, asks before any form submit on logged-in pages. Manifest permissions: activeTab, sidePanel, scripting, tabs, optional hosts. Build: `npm run build` in `apps/extension`, load unpacked from `apps/extension/.output/chrome-mv3`.

- **Spine (T10 + parts of T11, T12, 2026-09-18).** Auth: the API checks `Authorization: Bearer` against Supabase Auth (`app/auth.py`, cached 5 min); every `/runs` route needs it and returns 404 for another user's run. Data: `apps/api/schema.sql` creates `public.runs` with RLS (owner select only); apply with `python -m app.db`. The API writes runs (`app/db.py`, psycopg pool); the web app reads them straight from Supabase. Web: react-router, `/app` dashboard (run list, empty/loading/error states, Connect extension button) and `/app/runs/:id` report (outcome, steps, confusion, think-aloud). `RequireAuth` redirects to `/login`; login redirects to `/app`. Extension: dashboard hands the session to the extension via `externally_connectable` (needs `VITE_EXTENSION_ID` in `apps/web/.env`); the panel sends a bearer token and refreshes it through Supabase. `scripts/test_user.py` creates a throwaway account and prints a session for local testing.

- **Report pipeline, Instant Scan, share, export, email (T6, T7, T8, T11, T12, 2026-09-18).** `app/agent/report.py` is a LangGraph with three parallel branches (`first_impression` LLM, `seo_scan` code, `security_scan` code) joined by `synthesize` (LLM). It runs in the background when a persona run ends (`finish_run`) and synchronously for `POST /scans` (Instant Scan, no login, 5 per IP per hour, public report). Scans: `app/scans/seo.py`, `app/scans/security.py`, `app/scans/fetch.py` (SSRF guard, `ALLOW_LOCAL_SCANS=1` for fixtures). Full security scan only on verified domains (`GET /verification` gives the token; meta tag or `/.well-known/walkthru.txt`). Every LLM call goes through `runtime.call` and logs tokens into `runs.tokens`. Email via Resend (`app/deliver.py`, no-op without a key). Web: `ReportView`, `/r/:id` public page with a "Tested with Walkthru" header, Share / Export CSV / Email me on `/app/runs/:id`, Instant Scan form on the landing page and dashboard (navigates to the public report). Extension panel links to the report when a run ends.

- **Eval tooling (T9 session 8A, 2026-09-19).** `evals/runner.py` scores captured run/report JSON against all 18 seeded traps, reports overall and per-kind recall, calculates cost only from exact cost or separate input/output usage, emits Markdown or JSON, and optionally publishes an immutable code-evaluator dataset and experiment to LangSmith. `evals/traps.json` now carries conservative match phrases. Local passive-scan baseline: 11/18 overall, SEO 6/6, security 5/6, UX 0/6. Method and pending decision live in `docs/decisions.md`.

- **Easy-fixture CSP fix (2026-09-19).** The signup handler moved from blocked inline JavaScript to `/signup.js`, so the fixture keeps `default-src 'self'` and the Create account flow can reach `/welcome.html`. A regression test verifies the CSP-compatible script setup; browser inspection showed no console warnings or errors.
- **Groq structured-output fix (2026-09-19).** The live easy-fixture run reached `/welcome.html`, but Groq returned plain `done` while forced tool calling was enabled, causing a 400 `tool_use_failed` response and an extension-level `Failed to fetch`. The free pool now uses Groq's strict native JSON-schema output for `openai/gpt-oss-120b`; a regression test locks the model configuration and a live provider check returned a valid `PersonaStep` object.
- **Jev feasibility review (2026-09-19).** Jev is a strong candidate for the browser loop's bounded action and target decisions, but it cannot replace generative calls for open-ended form text, persona narration, first impressions, summaries, or fixes. The proposed hybrid keeps LangGraph and the deterministic extension executor, uses Jev on the hot path, escalates uncertain or text-generating work to an LLM, and generates report prose after the run. It must pass the existing hard-fixture eval before adoption. Full rationale and sources are in [docs/decisions.md](docs/decisions.md).

## In progress
- **Checkpoint A final retry pending:** the extension is loaded in real Chrome and now completes the easy signup UI through `/welcome.html`. Rerun once against the restarted API to verify the Groq structured-output fix closes the run as `done` and produces the report.
- Auth wiring: needs a Supabase project (founder).
- Agent loop verified against a real model (Groq gpt-oss-120b) with the Supabase Postgres checkpointer on 2026-09-18: two-step signup flow, sensible actions, state persisted.

## Next up
1. Founder: in the Supabase dashboard enable Google and GitHub providers and add `http://localhost:5173` to redirect URLs (keys are already in both `.env` files). Rotate the DB password and secret key before launch (shared over chat).
2. Checkpoint A in the founder's Chrome: load unpacked, copy the extension id into `apps/web/.env` as `VITE_EXTENSION_ID`, restart web, sign in at `/app`, click Connect extension, then run a test on `http://127.0.0.1:8101`.
3. Session 8B: capture the hard fixture through the real extension with the free, paid, and Jev-hybrid candidates, score with `evals/runner.py`, publish to LangSmith, and finalize `docs/decisions.md`.
4. Then T13 store submission, T14 billing, T15 deployment, and T16 launch wiring.

## Known issues and notes
- Pricing buttons are front end only until T14 wires checkout. Instant Scan is live through `POST /scans`.
- Sign-in is email magic link or OAuth only; the throwaway password account from `scripts/test_user.py` is for local testing.
- `externally_connectable` only allows `http://localhost:5173`; add the production origin before launch.
- Privacy, Terms and Security pages do not exist yet (footer links are `#`). Required before launch.
- Domain not bought yet (`brand.domain` is a placeholder). `agent-eye.jpg` is 735px wide, a bit soft on large screens.
- Two portraits are low resolution (persona-phone, persona-buyer, under 1000px wide).
- Production hosting must rewrite all paths to `index.html` for `/login` to work on refresh.
- Client-side early stops such as leaving the tested origin do not yet close the API run, so that run can remain `running` in the dashboard. Add an authenticated stop endpoint and call it from the extension before T13.
- Remote: https://github.com/watermelon588/Walkthru.git. Pushed 2026-09-18.
- No Anthropic budget for now: everything runs on free providers (Groq, Gemini). Fallback chain lives in `apps/api/app/agent/runtime.py`.

## Checks (last run)
- web: `npm run build` pass, lint 0 warnings. api: `pytest` 39 passed, `ruff` clean. extension: `vitest` 7 passed (+1 live contract test with `WALKTHRU_TOKEN`), `tsc` clean, `wxt build` pass, lint clean.
- Live on 2026-09-18: authenticated run written to Supabase; anonymous REST read returns nothing, owner read returns the row; API without token is 401; dashboard and report render for the test account.
- Live on 2026-09-18: Instant Scan of the hard fixture returned 15 findings in 15 s for 1,372 tokens; public page renders; persona run report generated in the background after the run ended.
- Evals on 2026-09-19: scorer unit suite 9 passed; hard-fixture passive scan scored 11/18 with all SEO traps and five of six security traps found. Real free/paid browser-run comparison is still pending.
- Landing: all 12 images load, no horizontal overflow at 375px and 1024px.
- Agent lab: TypeScript, Vite build and oxlint pass; five birds and both GSAP motion modes verified in browser; arrow-key movement and position reset re-verified. `prefers-reduced-motion` keeps the SVG parts static.
- Login: invalid email error and not-configured message verified in the browser.
