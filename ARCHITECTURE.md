# Architecture

## System overview
```
Chrome extension (user's browser)               Walkthru API (FastAPI + LangGraph)
────────────────────────────────                ───────────────────────────────────
side panel: pick site, goal, test user ── POST /runs ──────▶ create run + LangGraph thread
content script: page snapshot           ── POST /runs/{id}/observe ─▶ persona agent decides
  (URL, numbered buttons/links/inputs,  ◀── next action ──── click #12 | type #4 "..." | scroll | done | give_up
   visible text, errors; PII masked)
executes the action in the real tab
masks fields + captures bounded JPEG    ── private Storage object + evidence metadata ─▶ exact run step
                                        ... loop until done / give_up / step budget ...
                                                               synthesize report ─▶ Supabase ─▶ report page + email
Server-only scans (no browser): SEO (HTML fetch, robots, sitemap, PageSpeed API), security hygiene (headers, TLS, cookies, public files, secrets in JS).

Web app (React)  ──  Supabase Auth (JWT)  ──  API verifies JWT on every call
Payments: Dodo Payments checkout ─▶ signed webhook ─▶ API ─▶ credits table
```

## Components
| Part | Tech | Status |
|---|---|---|
| Web (landing, login, dashboard, report) | React 19, Vite, TypeScript, Tailwind v4, GSAP + @gsap/react, Phosphor icons, Geist | Landing, login, dashboard, private report, and public report built |
| Auth | Supabase Auth: Google, GitHub, email magic link. API validates bearer tokens via Supabase Auth (`app/auth.py`) | Live; OAuth providers still to enable in dashboard |
| API | Python 3.12+, FastAPI, LangGraph + Postgres checkpointer, httpx | `/health`, `/runs` step API, persona graph |
| Agent models | Default: Groq `openai/gpt-oss-120b` primary, Gemini `gemini-3.1-flash-lite` fallback. Experimental: TypeSafe Jev `jev-1.13.0` for bounded browser decisions with confidence-gated LLM fallback. Paid: Claude candidate after T9 eval | Free pool live; Jev adapter built and opt-in |
| Extension | Chrome MV3, TypeScript, WXT, React side panel | Built: snapshot, redaction, executor, step loop, Scout status and bounded evidence capture. Real easy-fixture run works; evidence rerun pending Storage policy application |
| Data | Supabase Postgres (RLS on every table) + private Storage (screenshots) | `runs` table + RLS live; `run-evidence` bucket and owner/public-report policies are declared in `apps/api/schema.sql` but still need applying to the project |
| Evals and tracing | LangSmith | Keys set, project `Walkthru` |
| Email | Resend (`app/deliver.py`, REST, no SDK) | Built; needs `RESEND_API_KEY` |
| Payments | Dodo Payments (test mode first) | Not started |
| Hosting | Vercel (web), Oracle Always Free VM or ~$5 VPS (API) | Not started |

## Key decisions
1. **Browser runs on the user's machine, brain on our server.** No Chromium on our server, hosting stays $0-5, logged-in pages work without sharing passwords.
2. **Step loop lives in the extension side panel page**, not the MV3 service worker (Chrome suspends workers after ~30 s idle). Chrome does not reliably grant `activeTab` to side panels and `captureVisibleTab` only accepts `activeTab` or `<all_urls>`, so Start Test requests the optional broad host permission in a one-time Chrome prompt. It is used only for the active test tab.
3. **One HTTP call per agent step.** LangGraph `interrupt()` emits the action; `Command(resume=observation)` continues. Postgres checkpointer holds state, so the API is stateless between calls.
4. **Text snapshot first, screenshots rarely** (first impression and when stuck). Tokens are the main cost.
5. **Plain code wherever possible.** SEO and security checks are deterministic code plus one LLM call to explain fixes. Only the persona session is an agent.
6. **Passive security only, on verified domains** (meta tag, DNS TXT or well-known file).
7. **Credits, not tokens,** for billing. One credit = one persona run. Tokens logged per run for margins.
8. **react-router** for `/`, `/login`, `/app`, `/app/runs/:id`. Production host must rewrite all paths to `index.html` (Vercel: `rewrites` in vercel.json).
9. **Reads bypass the API.** The web app reads `runs` straight from Supabase under RLS; only the API (postgres role) writes. Fewer endpoints, and the DB enforces ownership.
10. **Extension session handoff.** The dashboard sends the Supabase session to the extension id in `VITE_EXTENSION_ID` through `externally_connectable`; the extension refreshes it against Supabase and sends it as a bearer token.
11. **Decision providers are replaceable, LangGraph is not.** The persona graph owns state, interrupts, budgets, and termination. A Jev provider may choose bounded operations and targets; the existing LLM remains responsible for open-ended generation and fallback. Safety stays in deterministic code.
12. **Step evidence is private and bounded.** The extension captures at most eight JPEG frames per run after meaningful actions, hides Scout and masks form controls for the captured paint, then uploads directly to the private `run-evidence` bucket with the user's JWT. The API only accepts a screenshot path beneath the current run id. Reports request one-hour signed URLs; public reports can read evidence only when the owning run is public.

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
- `site_scan`: seo_scan and security_scan in parallel.

## Safety rules (enforced in code, not prompts)
Safe mode on logged-in pages (never click delete / remove / cancel subscription / pay / send / invite / transfer; confirm before any form submit), same-origin only, 25-step and 4-minute caps, stop at CAPTCHA, client-side PII masking before snapshot upload, form-control masking before screenshot capture, fake test identity for signups. Evidence capture is best-effort and never blocks the journey.

## Environment variables
See [.env.example](.env.example). Web reads `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_URL`. Never expose service-role keys to the web app.
