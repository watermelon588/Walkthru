# Architecture

## System overview
```
Chrome extension (user's browser)               Walkthru API (FastAPI + LangGraph)
────────────────────────────────                ───────────────────────────────────
side panel: pick site, goal, test user ── POST /runs ──────▶ create run + LangGraph thread
content script: page snapshot           ── POST /runs/{id}/observe ─▶ persona agent decides
  (URL, numbered buttons/links/inputs,  ◀── next action ──── click #12 | type #4 "..." | scroll | done | give_up
   visible text, errors; PII masked)
executes the action in the real tab     ... loop until done / give_up / step budget ...
                                                               synthesize report ─▶ Supabase ─▶ report page + email
Server-only scans (no browser): SEO (HTML fetch, robots, sitemap, PageSpeed API), security hygiene (headers, TLS, cookies, public files, secrets in JS).

Web app (React)  ──  Supabase Auth (JWT)  ──  API verifies JWT on every call
Payments: Dodo Payments checkout ─▶ signed webhook ─▶ API ─▶ credits table
```

## Components
| Part | Tech | Status |
|---|---|---|
| Web (landing, login, dashboard, report) | React 19, Vite, TypeScript, Tailwind v4, GSAP + @gsap/react, Phosphor icons, Geist | Landing and login built |
| Auth | Supabase Auth: Google, GitHub, email magic link | UI built, keys not set |
| API | Python 3.12+, FastAPI, LangGraph + Postgres checkpointer, httpx | `/health`, `/runs` step API, persona graph |
| Agent models | Free pool: Groq `openai/gpt-oss-120b` primary, Gemini `gemini-3.1-flash-lite` fallback (`with_fallbacks`). Paid: Claude (Haiku 4.5 or Sonnet 5, T9 eval) once an Anthropic key exists; until then paid rides the free pool | Free pool live |
| Extension | Chrome MV3, TypeScript, WXT, React side panel | Not started |
| Data | Supabase Postgres (RLS on every table) + Storage (screenshots) | Project created; LangGraph checkpoint tables live in it. App schema not started |
| Evals and tracing | LangSmith | Keys set, project `Walkthru` |
| Email | Resend | Not started |
| Payments | Dodo Payments (test mode first) | Not started |
| Hosting | Vercel (web), Oracle Always Free VM or ~$5 VPS (API) | Not started |

## Key decisions
1. **Browser runs on the user's machine, brain on our server.** No Chromium on our server, hosting stays $0-5, logged-in pages work without sharing passwords.
2. **Step loop lives in the extension side panel page**, not the MV3 service worker (Chrome suspends workers after ~30 s idle).
3. **One HTTP call per agent step.** LangGraph `interrupt()` emits the action; `Command(resume=observation)` continues. Postgres checkpointer holds state, so the API is stateless between calls.
4. **Text snapshot first, screenshots rarely** (first impression and when stuck). Tokens are the main cost.
5. **Plain code wherever possible.** SEO and security checks are deterministic code plus one LLM call to explain fixes. Only the persona session is an agent.
6. **Passive security only, on verified domains** (meta tag, DNS TXT or well-known file).
7. **Credits, not tokens,** for billing. One credit = one persona run. Tokens logged per run for margins.
8. **No router yet.** `App.tsx` switches on `location.pathname`. Add react-router with the dashboard (T10). Production host must rewrite all paths to `index.html` (Vercel: `rewrites` in vercel.json).

## Agent graphs (planned)
- `test_run`: preflight (limits, ownership) → first_impression → persona_session per persona → synthesize → deliver.
- `persona_session`: decide (one `PersonaStep`: thought, action, target_id, confusion 0-3) → interrupt for observation → check (goal met, looping, budget) → decide.
- `site_scan`: seo_scan and security_scan in parallel.

## Safety rules (enforced in code, not prompts)
Safe mode on logged-in pages (never click delete / remove / cancel subscription / pay / send / invite / transfer; confirm before any form submit), same-origin only, 25-step and 4-minute caps, stop at CAPTCHA, client-side PII masking before upload, fake test identity for signups.

## Environment variables
See [.env.example](.env.example). Web reads `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_URL`. Never expose service-role keys to the web app.
