# Walkthru handoff

_Written 2026-09-24 at the end of a long build session. Branch `1`, last commit `c647981`, everything pushed to https://github.com/watermelon588/Walkthru. The previous handoff (2026-09-22, T24) is in git history._

## Start here (reading order)

| # | File | Why |
|---|---|---|
| 1 | `handoff.md` (this file) | The whole picture in one page |
| 2 | `AGENTS.md` | Repo rules: always, ask first, never. Commands. |
| 3 | `CURRENT_STATE.md` | What is done, dated, and the known issues |
| 4 | `SPEC.md` | Product v1.1: positioning, the plans table, GEO rules |
| 5 | `ROADMAP.md` | 23 weak points with fixes, session plan, deadlines |
| 6 | `tasks/todo.md` | Tasks V1 to V22 with acceptance criteria, in session order |
| 7 | `ARCHITECTURE.md` | Capability map and module designs (read the parts you touch) |
| 8 | `payment.md` | Billing design (founder-approved passes through Dodo), costs, the 25% model-cost allowance |
| 9 | `docs/decisions.md` | Why things are the way they are; read the 2026-09-24 entries |
| 10 | `DESIGN.md` | Before any UI work: tokens, type, motion |
| 11 | `founder/*.md` | Competitor matrix, pricing strategy, idea validation (founder skills output) |

**Skills (the founder's global CLAUDE.md asks you to load and name them):**
- `ponytail`: always on.
- `graphify`: the graph in `graphify-out/` dates from 2026-09-23, before this session. Run a code-only update before relying on it.
- The founder skills in `.claude/skills/`.
- Design skills (`impeccable`, `frontend-ui-engineering`, `design-taste-frontend`) for UI work.

**Memory:** `~/.claude/projects/C--Users-Rohit-Maity-Desktop-coding-Webdev-project-trustdraft/memory/`. `walkthru-free-providers.md` holds the provider, network and Claude decisions.

## What Walkthru is now

**The launch check for apps built with AI.** One report answers three questions:
1. Can a stranger get in? AI test users run real journeys in the owner's own Chrome through the extension.
2. Can Google and AI search read you? SEO plus GEO.
3. Are you leaking anything? Passive security.

Plus accessibility, speed and signup email checks, a fix list, and for paid plans a ready-made fix prompt for the user's coding agent.

**Plans (prices confirmed by the founder):**
- Free.
- Launch Pack: $9 once.
- Pro: $19 a month ($15 founding).
- Plus: $49 a month ($39 founding). Plus launches as a waitlist until weekly watch ships.

The full feature table is in `SPEC.md`.

**Launch:** target Tue 2026-10-20, 2026-10-27 at the latest.

## What works today (all verified live on 2026-09-24)

| Area | State |
|---|---|
| **Plans (V1)** | The server owns every limit (`app/plans.py`, `entitlements` table, `GET /me/plan`); the client's tier is ignored. `scripts/grant_plan.py EMAIL pro\|plus\|--revoke\|--show` gives free dev passes. |
| **GEO (V2)** | `app/scans/geo.py`: a 0 to 100 score, "what AI search sees", and GEO findings in every report. Free scores the homepage; paid scores every audited page. |
| **Goal intent (V22)** | `app/agent/goal.py` plans the typed goal into a checklist, refuses unsafe goals with 422, and code finishes the run. The looping guard, scroll position, and proof before "done" live in `persona.py`. |
| **Email check (V16)** | `app/scans/email.py` checks SPF, DMARC and MX over DNS-over-HTTPS. Supabase's "email rate limit exceeded" becomes "use your own SMTP". |
| **Checkpoint B (V3)** | 18 of 22 traps (82%) on the hard fixture from two real journeys. `evals/runner.py --combine`. |
| **Compare (V4)** | Every paid run is compared automatically with the previous run of the same goal on the same site, page by page, including "not re-checked" (`app/agent/compare.py`). |
| **Ignore a finding (V17)** | Paid only; the `finding_states` table. |
| **GEO fix pack (V5)** | `app/scans/geo_fixes.py`: copy-paste fixes from the site's own pages. Free sees one. |
| **Agent fix prompt (V15)** | `app/agent/fix_prompt.py` and `GET /runs/{id}/fix-prompt`: Markdown, every affected page listed, secrets masked, a chat version and a download. The founder tested the whole loop (prompt, fixes, rerun, comparison) on the showcase fixture. |
| **Claude Haiku 4.5** | Wired for Pro and Plus through Google Cloud (`anthropic[vertex]`), **off** until `CLAUDE_VERTEX_PROJECT` is set. Free plans never reach it, and every report states which models ran. |
| **Models** | A free chain: Groq gpt-oss-120b first; Nemotron 3 Ultra on OpenRouter writes reports; Gemini as backup. No paid key is in use. |

**Tests:** 167 API tests, 30 extension tests; web and extension builds and lint green.

## Founder's direction for the next sessions (2026-09-24)

Launch is 26 days away, so **quality comes before deploy.** In order:

1. **Polish and harden end to end.** Session "6a" in the roadmap:
   - V6: 50-page paid crawls.
   - V8: Launch Ready score and live badge.
   - A daily cap on free Instant Scans (`FREE_SCANS_PER_DAY`).
   - A rate limiter shared across processes, stored in Postgres.
   - `CHECKPOINTER=postgres` readiness.
   - The slow first step (25 to 45 s when Groq is rate-limited).
   - A UI pass with the design skills, since the founder noticed spacing issues. Read DESIGN.md first.
2. **Payment gateway before launch.** V10: Dodo in test mode, the founder-approved offer, a signed idempotent webhook that inserts the `entitlements` row, and refunds. `payment.md` is the design. The founder needs a Dodo account.
3. **The founder wants to understand the product better.** Explain as you go, and ask when a product decision is theirs.
4. **Later (session 6b):**
   - Deploy: domain, Oracle VM, Vercel.
   - Chrome Web Store submission.
   - Google Cloud UPI billing, Claude switched on, and the measured Claude comparison (about $1 to $2).
   - Google and GitHub sign-in: no domain needed; guide the founder click by click.

Also still open: V7 (evidence and PDF close-out), V9 (landing copy for the new positioning), V18 (funnel numbers), V19 (copy review), V12 (watch), V20 (MCP server), V21 (competitor compare), V13 (custom test users), V14 (cloud runner, conditional).

## Running it locally

```
.\dev                                   # whole stack; dev only
```

| What | Where |
|---|---|
| API | http://127.0.0.1:8010 (moved from 8000: the founder's TripVerse backend uses 8000) |
| Web app | **http://localhost:5173**. TripVerse owns `127.0.0.1:5173`, and `dev.py` binds Walkthru to `::1`. |
| Fixtures | Easy :8101; hard :8102 (18 traps plus 4 GEO traps, owner-verified for the test account); showcase :8103 (strong GEO plus journey traps: circular stories, pop-ups, a dead button, Pay and Delete). |
| Extension | Built by `.\dev` into `apps/extension/.output/chrome-mv3`. Reload it on `chrome://extensions` after changes. |

- **Test account:** `walkthru.tester@example.com` (`scripts/test_user.py`). It holds a Pro dev pass until 2026-09-26.
- **Founder's account:** on free, 0 runs left this month. They can grant themselves a pass.
- **Real journeys without clicking:** `apps/api/.venv/Scripts/python evals/e2e_extension.py <site> "<goal>"` (headless Chrome, the real API and free models). It saves `evals/results/e2e-*.json` for `evals/runner.py`.
- **Checks:** `cd apps/api && .venv/Scripts/python -m pytest -q && .venv/Scripts/ruff check .`; web `npm run build && npm run lint`; extension `npm test && npx tsc --noEmit && npm run lint`.

## Gotchas that cost time this session

- **Direct Postgres from the founder's network times out.** `python -m app.db` often fails. Schema changes go through the Supabase dashboard SQL editor: paste the new block from `apps/api/schema.sql`, then run `notify pgrst, 'reload schema';`. The API itself uses HTTPS (PostgREST) and is fine.
- **Windows shell:** bash heredocs mangle `\n` and `\d`. Write edit scripts to the scratchpad with the Write tool and run them with `apps/api/.venv/Scripts/python`.
- **Browser pane screenshots come back blank when the pane is hidden.** Verify with `get_page_text`, `find` or JavaScript instead. The pane is not signed in to the founder's account; use the test account's public report (`/r/<id>`).
- **Free-model limits:** Groq allows 8,000 tokens a minute per model; OpenRouter free allows 50 requests a day until $10 of credit. Slowness, not failure, is the symptom.
- **House rules:** no em or en dashes in user-facing copy (model output is stripped in `report.plain`); design tokens only; honour reduced motion.

## Decisions a new session must not undo without asking

- The server decides the plan; never trust the client's tier.
- Deterministic code for every check; models only plan, click and write. Grounding (`report.problem_steps`, `grounded_ux`) and proof before "done" stay.
- "Every plan gets the same checks and honesty rules; Pro and Plus add Claude's judgment." Every report says which models ran.
- The fix prompt and fix pack are built in code, never by a model.
- Passive security only. Sends only on owner-verified domains after confirmation, once per run. Pay, delete and cancel are never pressed.
- The founder has **no credit card**. Paid models go through Google Cloud's UPI prepayment; OpenRouter needs an international card, AliPay or USDC.
- Charts only for trends over time (reruns and watch), as inline SVG. No matplotlib.

## Founder to-do (blocking launch, not blocking the next sessions)

- [ ] Domain.
- [ ] Chrome Web Store developer account ($5).
- [ ] Oracle Always Free VM (or a ~$5 VPS).
- [ ] A Google Cloud project with a ₹500 to ₹1,000 UPI prepayment (for Claude).
- [ ] A Dodo account; start live-mode verification now, because billing (V10) needs test mode first.
- [ ] Rotate the Supabase DB password and secret key (both were shared in chat on 2026-09-18).
- [ ] Enable Google and GitHub sign-in in Supabase, guided.
