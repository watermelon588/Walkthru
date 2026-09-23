# Spec: Walkthru v1.1, the launch check

_Updated 2026-09-24 after the competitor, pricing and validation review in `founder/`. Replaces the v1 spec. Build order and weak points: [ROADMAP.md](ROADMAP.md). System design: [ARCHITECTURE.md](ARCHITECTURE.md)._

## Objective

**Positioning:** the launch check for apps built with AI. One report answers three questions before and after every launch:

1. **Can a stranger get in?** AI test users walk through real flows (landing, signup, onboarding, dashboard, checkout up to payment) in the owner's own Chrome, think aloud, and show where they got stuck. Logged-in pages work without sharing a password.
2. **Can Google and AI search read you?** SEO plus **GEO (AI search readiness)**: whether ChatGPT, Claude, Perplexity and Google's AI answers can fetch, understand and quote the site.
3. **Are you leaking anything?** Passive security hygiene: headers, cookies, exposed files, keys in JavaScript. Never an attack.

Plus accessibility and mobile performance evidence, and one fix list ranked by impact.

**Why this position:** "AI users test your site" is a crowded category ([Meerkat](https://runmeerkat.com/pricing), [CanaryUsers](https://www.canaryusers.ai/), [Swarm](https://www.useswarm.co/), [Uxia](https://www.uxia.app/), checked 2026-09-24). None of them lists SEO, GEO or security. GEO tools ([Otterly](https://www.frase.io/blog/the-10-best-ai-visibility-tools-in-2026)) never try a flow. Walkthru is the only one report that covers all of it, and the only one that tests logged-in pages inside the owner's own browser session. Details: `founder/competitor-matrix.md`.

**Users:**
- **Primary:** solo founders and two-person teams shipping apps built with Cursor, Lovable, Bolt or v0.
- **Secondary:** agencies handing sites to clients.

**Product rules:**
- **Free reports are exactly as good as paid ones.** Plans unlock where a test can go and what happens over time, never a better answer.
- **Every claim is grounded.** Findings cite a step, a URL, a header or a snippet. Walkthru never blames the site for its own stops.
- **GEO claims are honest.** Walkthru measures readiness (can AI search fetch and understand you). It does not promise citations or rankings, and it labels low-evidence checks such as `llms.txt` as low impact.

## Plans

The founder asked for this finalized plan on 2026-09-24. Prices: list price, with the founding price in brackets for the first 50 customers, locked for 12 months. V1 paid access follows [payment.md](payment.md): founder-approved 30-day passes through Dodo, no auto-renewal until the V2 gate.

| | Free | Launch Pack | Pro | Plus |
|---|---|---|---|---|
| Price | $0 | $9 once | $19/mo ($15 founding) | $49/mo ($39 founding) |
| Instant Scan (no install) | 5 an hour per address, 10 pages | Included | Included | Included |
| **AI readiness score (GEO)** | Homepage score and top 3 fixes | Full site | Full site, up to 50 pages | Full site, up to 50 pages, every site |
| **"What AI search sees"** | Yes | Yes | Yes | Yes |
| **GEO fix pack** (robots.txt rules, JSON-LD, llms.txt draft, rendering fix for your framework) | Preview of 1 fix | Yes | Yes | Yes |
| **GEO and SEO watch** (weekly, email only on change, deploy webhook) | No | No | No | Yes |
| Test runs | 3 a month | 20 within 30 days | 40 a month | 150 a month |
| Pages the test user may enter | Public pages | Public and logged-in | Public and logged-in | Public and logged-in |
| Test users | First-time visitor | All 4 | All 4 | All 4 + custom test users |
| Steps per run | 12 | 30 | 30 | 30 |
| Rerun and compare (fixed, still broken, new) | No | Yes | Yes | Yes |
| SEO | 10 pages | 50 pages | 50 pages | 50 pages |
| Security hygiene | Headers, TLS, cookies | + exposed files and leaked keys on verified domains | Same as Launch Pack | Same as Launch Pack |
| One real form send on a verified domain, after you confirm | No | Yes | Yes | Yes |
| Evidence report with screenshots, PDF | Web report | PDF | PDF | PDF with your own logo, no Walkthru branding |
| Verified sites | 1 | 1 | 2 | 5 |
| Shareable public report with AI readiness badge | Yes | Yes | Yes | Yes |

**GEO in every plan.** GEO checks are deterministic, so they cost nothing in model calls:
- **Free:** the hook. "Can ChatGPT read your site?"
- **Pro:** full-site readiness plus the fix pack.
- **Plus:** keeps it working, with alerts when a deploy blocks an AI crawler, drops structured data or empties the HTML sent before JavaScript runs.

**Not sold in V1:** AI citation tracking ("does ChatGPT mention you for this prompt"). It costs model and search calls on every check and needs its own evaluation. Candidate Plus add-on after launch.

**Plus launches as a waitlist** until weekly watch and branded PDFs ship (ROADMAP phase E). Nothing is sold before it exists.

## How it works

```
Chrome extension (client)                    Walkthru API (FastAPI + LangGraph)
side panel: goal + test user     ── start ─▶ entitlement check (plan, runs left, steps, logged-in, site)
content script: snapshot page    ── observe ▶ persona agent decides the next action
executes the action in the tab   ◀─ action ── click | type | scroll | done | give_up
                                  ... loop until done / give_up / safe stop / budget ...
                                              report: journey + SEO + GEO + security + a11y + performance
                                              compare with the previous run of the same site and goal

Server only (no browser): Instant Scan, site audit, GEO readiness, security hygiene,
weekly watch (Plus), deploy webhook (Plus).
```

The step loop, safety model, redaction, evidence and grounding are unchanged from v1. See ARCHITECTURE.md.

## GEO readiness (new)

Deterministic scanner in `apps/api/app/scans/geo.py`. It reuses the pages, `robots.txt` and homepage the site audit already fetched. The only extra requests are `GET /llms.txt` and one homepage GET with a citation-bot user agent. Scored 0 to 100:

| Category | Points | Checks |
|---|---|---|
| AI crawler access | 25 | `robots.txt` allows the citation bots (OAI-SearchBot, ChatGPT-User, Claude-SearchBot, ClaudeBot, PerplexityBot, Googlebot, Bingbot, Applebot) (15). The homepage answers a citation-bot user agent with 200 rather than 403 or a challenge page (10). Blocking training-only bots (GPTBot, Google-Extended, CCBot) is reported as a choice, not a fault. |
| Content without JavaScript | 20 | Homepage HTML contains the main text before JavaScript runs (15). Key pages (pricing, about, docs, features) are not empty shells (5). Most AI crawlers do not run JavaScript, and many AI-built apps are single-page apps. |
| Structured data | 15 | Valid JSON-LD (5). Organization or WebSite (4). A page-type schema: SoftwareApplication, Product, FAQPage or Article (4). Schema with 5 or more useful properties (2). |
| Answerability | 15 | One H1 (3). Descriptive H2s (3). A plain paragraph early on the page (3). Lists or tables (3). Concrete numbers (3). |
| Entity and trust | 10 | Same name in title, og:site_name, schema and H1 (4). About, contact and privacy or pricing pages linked (4). sameAs links to public profiles (2). |
| Meta | 10 | Title, description, canonical, Open Graph. The score reuses SEO signals; findings stay in the SEO section so nothing is reported twice. |
| llms.txt | 5 | Present and well formed. Labeled "low measured impact" ([Otterly study](https://otterly.ai/blog/the-llms-txt-experiment/)). |

- **Score bands:** 0 to 35 critical, 36 to 67 foundation, 68 to 85 good, 86 to 100 excellent.
- **Reference:** the category model adapts [geo-optimizer-skill](https://github.com/auriti-labs/geo-optimizer-skill) (MIT). It is re-weighted toward checks with evidence, and implemented on Walkthru's SSRF-safe fetcher rather than added as a dependency.
- **"What AI search sees":** the existing first-impression call already reads the HTML before JavaScript. The report labels it that way. On a JavaScript shell it says plainly that AI search sees an empty page.
- **Fix pack:** deterministic templates filled from the audited pages. They cover robots.txt rules, JSON-LD blocks, an llms.txt draft, and a rendering fix for the detected framework (Vite single-page app, Next.js, Lovable, Astro).

## Agent design, safety, tech stack

Unchanged from v1: `persona_session` graph (decide, interrupt, check); destructive actions never run; sends only on verified domains after the owner confirms, once per run; same-origin; CAPTCHA stop; redaction before upload; passive security only on verified domains; fake test identity. Stack: Chrome MV3 + WXT + React; React 19 + Vite + Tailwind v4 web; FastAPI + LangGraph API; Supabase; free model chain (Groq, OpenRouter writer, Gemini); Dodo; Resend. See ARCHITECTURE.md.

## Commands
```
.\dev                                                    # whole local stack (dev only)
cd apps/api && .venv/Scripts/python -m pytest -q && .venv/Scripts/ruff check .
cd apps/web && npm run build && npm run lint
cd apps/extension && npm test && npx tsc --noEmit && npm run lint && npm run build
```

## Testing strategy
- **pytest** for every deterministic check, including each GEO category on fixture HTML: an SPA shell, blocked bots, valid and broken JSON-LD. Also entitlement limits (a free user cannot start a logged-in run or exceed 12 steps, whatever the client sends), finding fingerprints for rerun comparison, and the watch diff.
- **Hard fixture:** gains GEO traps: `robots.txt` blocking OAI-SearchBot, a JavaScript-only pricing page, missing Organization schema. They are counted in the trap scorer.
- **Extension:** vitest for snapshot, redaction and safety. **Evals:** trap recall and cost per run in LangSmith.

## Boundaries
- **Always:** server decides the plan and limits; safe mode; redaction; verified domain for deep security checks; honest labels on low-evidence GEO checks; log tokens per run.
- **Ask first:** new dependencies, paid-tier model, schema changes after launch, price changes after this spec.
- **Never:** active attacks, CAPTCHA solving, payment submission, promising AI citations or rankings, a weaker free report, committing secrets.

## Success criteria
- Instant Scan returns SEO, GEO score, "what AI search sees" and security headers in 20 s or less for a 10-page site.
- GEO scanner flags every GEO trap on the hard fixture; overall trap recall is 80% or more (Checkpoint B).
- A free account cannot start a logged-in run, a 13th step or a 4th monthly run, whatever the client sends.
- A rerun marks every prior finding fixed, still broken or new, and matches a hand check on 3 fixture reruns.
- Paid run cost is $0.20 or less; free run is $0.02 or less.
- Validation (founder/validate-idea.md): 5 of the first 100 Instant Scans convert to a $9 Launch Pack, and 25% of beta users who click "Run a test" finish a run.
- Chrome Web Store listing approved before launch (Oct 20). 50 community sites tested and 5 paying by 2026-11-30.

## Open questions
- Keep the exact list prices ($19 and $49) or adjust after experiment 1?
- Cloud runner (public journeys without installing the extension): build only if experiment 2 shows fewer than 25% of beta users finish a run after clicking "Run a test".
