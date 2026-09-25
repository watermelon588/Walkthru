# Spec: Walkthru v1.2, the launch check

_Updated 2026-09-25 after the premium depth review (docs/decisions.md, "Premium depth"). v1.1 was written 2026-09-24 after the competitor, pricing and validation review in `founder/`. Build order, phases and weak points: [ROADMAP.md](ROADMAP.md). System design: [ARCHITECTURE.md](ARCHITECTURE.md)._

## Objective

**Positioning:** the launch check for apps built with AI. One report answers three questions before and after every launch:

1. **Can a stranger get in?** AI test users walk through real flows (landing, signup, onboarding, dashboard, checkout up to payment) in the owner's own Chrome, think aloud, and show where they got stuck. Logged-in pages work without sharing a password.
2. **Can Google and AI search read you?** SEO plus **GEO (AI search readiness)**: whether ChatGPT, Claude, Perplexity and Google's AI answers can fetch, understand and quote the site.
3. **Are you leaking anything?** Security hygiene at least as deep as the free ZAP baseline, plus what AI-built apps get wrong most: a database readable without login (Supabase RLS, Firebase rules). Read-only probes run only on owner-verified domains; with a connected repository, code scans find secrets, vulnerable packages and open policies. Never an attack.

Plus accessibility and mobile performance evidence, an agent readiness score (can AI agents use your site), and one fix plan for the detected stack that a coding agent can follow batch by batch.

**Why this position:** "AI users test your site" is a crowded category ([Meerkat](https://runmeerkat.com/pricing), [CanaryUsers](https://www.canaryusers.ai/), [Swarm](https://www.useswarm.co/), [Uxia](https://www.uxia.app/), checked 2026-09-24). None of them lists SEO, GEO or security. GEO tools ([Otterly](https://www.frase.io/blog/the-10-best-ai-visibility-tools-in-2026)) never try a flow. Walkthru is the only one report that covers all of it, and the only one that tests logged-in pages inside the owner's own browser session. Details: `founder/competitor-matrix.md`.

**Users:**
- **Primary:** solo founders and two-person teams shipping apps built with Cursor, Lovable, Bolt or v0.
- **Secondary:** agencies handing sites to clients.

**Product rules:**
- **Every plan gets the same page checks and the same honesty rules.** Code runs every SEO, GEO, security, accessibility and email check that reads public pages on every plan, and grounding applies to all. Paid plans add depth: more pages, read-only probes on verified domains, code scans, real search data, citation tracking, where a test can go and what happens over time. Every report says which models ran. (Founder decisions 2026-09-24 and 2026-09-25.)
- **Free tier only, deterministic first.** Every plan runs on the free model chain and free API quotas. Claude Haiku 4.5 is wired and stays off until revenue pays for it within payment.md's caps. A model call is used only where judgement or writing is the product. (Founder decision 2026-09-25.)
- **Open source before scratch.** Checks are ported from permissively licensed projects after a licence check (docs/decisions.md 2026-09-25), with notices kept in `apps/api/THIRD_PARTY.md`.
- **Every claim is grounded.** Findings cite a step, a URL, a header or a snippet. Walkthru never blames the site for its own stops.
- **GEO claims are honest.** Walkthru measures readiness (can AI search fetch and understand you). It does not promise citations or rankings, and it labels low-evidence checks such as `llms.txt` as low impact.

## Plans

Prices confirmed by the founder on 2026-09-24. Shown as list price, with the founding price in brackets for the first 50 customers, locked for 12 months. V1 paid access follows [payment.md](payment.md): founder-approved 30-day passes through Dodo, no auto-renewal until the V2 gate.

| | Free | Launch Pack | Pro | Plus |
|---|---|---|---|---|
| Price | $0 | $9 once | $19/mo ($15 founding) | $49/mo ($39 founding) |
| Test user and report writer | Free models (gpt-oss-120b and backups) | Free models; Claude Haiku 4.5 once revenue allows | Same as Launch Pack | Same as Launch Pack |
| Instant Scan (no install) | 5 an hour per address, 10 pages | Included | Included | Included |
| **AI readiness score (GEO)** | Homepage score and top 3 fixes | Full site | Full site, up to 50 pages | Full site, up to 50 pages, every site |
| **"What AI search sees"** | Yes | Yes | Yes | Yes |
| **GEO fix pack** (robots.txt rules, JSON-LD, llms.txt draft, rendering fix for your framework) | Preview of 1 fix | Yes | Yes | Yes |
| **Agent fix plan**: batches for Cursor, Claude Code, Lovable or Bolt, with a recipe for the detected stack, a risk note and a local check per finding (P1.3); file and line with a connected repo (P2.3) | Locked, shows how many fixes it holds | Yes | Yes | Yes |
| **Agent readiness score**: can AI agents complete your flows (P1.7) | Yes | Yes | Yes | Yes |
| **Launch Ready score**: UX, GEO, SEO, security and speed in one number, with a live badge for your site | Yes | Yes | Yes | Yes |
| **Signup email check**: SPF, DMARC and MX records, plus auth-mailer limits spotted in journeys | SPF and DMARC | Full | Full | Full |
| **Ignore a finding** ("won't fix", with a reason) | No | Yes | Yes | Yes |
| **First impression**: screenshot-based checklist with quoted evidence (P0.3) | Yes (text only on Instant Scan) | Yes | Yes | Yes |
| **Signup funnel numbers**: steps, fields, errors and time to the first useful screen, across reruns (coming, P0.2) | No | Yes | Yes | Yes |
| **Landing copy review**: headline, subheadline and CTA rewrites quoting the text they replace (coming, P0.3) | No | Yes | Yes | Yes |
| **Competitor side by side** (passive scans) | No | 3 competitors | 3 competitors | 3 competitors per site |
| **Backend exposure** (Supabase, Firebase; P1.1) | Detects a public backend key and explains the risk | + read-only probe on verified domains: tables readable without login (row counts only), public buckets | Same as Launch Pack | Same as Launch Pack |
| **Code scan** of a connected GitHub repository: secrets, vulnerable packages, open database policies, risky code (P2, proposed) | No | 1 scan | 1 repo, on every paid run | 5 repos, on every push |
| **Search Console and Bing Webmaster data** joined to findings (P3.1, proposed) | No | No | Yes | Yes |
| **AI citation tracking** on free engines (Gemini with Google Search, Groq Compound): mentions, citations, share of voice, sources, accuracy (P3.2, proposed) | No | One snapshot of 10 prompts | 10 prompts weekly | 25 prompts per site weekly |
| **Opt-in active scan of a staging URL** (P4.1, revenue-gated) | No | No | No | Yes |
| **Walkthru MCP server**: Claude Code, Cursor and other agents scan, read the fix prompt and rerun from the editor | No | No | No | Yes |
| **GEO and SEO watch** (weekly, email only on change, deploy webhook) | No | No | No | Yes |
| Test runs | 3 a month | 20 within 30 days | 40 a month | 150 a month |
| Pages the test user may enter | Public pages | Public and logged-in | Public and logged-in | Public and logged-in |
| Test users | First-time visitor | All 4 | All 4 | All 4 + custom test users |
| Steps per run | 12 | 30 | 30 | 30 |
| Rerun and compare (fixed, still broken, new) | No | Yes | Yes | Yes |
| SEO | 10 pages | 50 pages | 50 pages | 50 pages |
| Security hygiene | Header quality (CSP weaknesses, HSTS max-age and preload, CORS, SRI on public CDN scripts), cookies and cookie prefixes, https, TLS version and certificate expiry, CAA, vulnerable JavaScript libraries loaded from public CDNs | + exposed files, backups and dumps, source maps, leaked keys (gitleaks rules), library versions inside bundles and subdomain takeover, on verified domains | Same, + safe Nuclei templates on verified domains (P2.4) | Same as Pro |
| One real form send on a verified domain, after you confirm | No | Yes | Yes | Yes |
| Evidence report with screenshots, PDF | Web report | PDF | PDF | PDF with your own logo, no Walkthru branding |
| Sites tested per month or pass (local dev servers do not count) | 1 | 1 | 2 | 5 |
| Shareable public report with AI readiness badge | Yes | Yes | Yes | Yes |

**GEO in every plan.** GEO checks are deterministic, so they cost nothing in model calls:
- **Free:** the hook. "Can ChatGPT read your site?"
- **Pro:** full-site readiness plus the fix pack.
- **Plus:** keeps it working, with alerts when a deploy blocks an AI crawler, drops structured data or empties the HTML sent before JavaScript runs.

**Agent fix prompt (paid).** Built in code from the report, with no model call, so it costs nothing and cannot invent findings.
- **What it contains:** the detected stack. Then each finding in priority order: security, UX blockers, GEO, SEO, accessibility, performance. For each: what is wrong, where (URL, element text, header), the evidence, the required change and an acceptance check.
- **Rules for the coding agent:** keep existing behavior, ask before adding dependencies, never paste secrets.
- **Last step:** "rerun Walkthru to verify", with the list of findings expected to flip to fixed.
- **Formats:** a full Markdown version (Cursor, Claude Code, Codex), a short chat version for Lovable and Bolt, and a `walkthru-fixes.md` download.
- **Privacy:** leaked key values are masked. Journey text never includes personal data. The API serves it only to paid plans; it is not stored in the report, so the free tier cannot read it through the report row.

**Plan allocation of the new rows is proposed** (2026-09-25) until the founder confirms it. Prices do not change.

**Next versions, not in v1.2:** the preview-deploy check (GitHub Action with a PR comment) and exporting findings to GitHub Issues or Linear.

**AI citation tracking (Phase 3)** runs only on free engines (Gemini with Google Search grounding, Groq Compound) under a database-counted daily cap. ChatGPT and Perplexity are labelled "not measured" until revenue pays for their APIs (Phase 4). It reports what those engines said; it never promises citations or rankings.

**Plus launches as a waitlist** until weekly watch, citation tracking and branded PDFs ship (ROADMAP Phase 3). Nothing is sold before it exists.

## How it works

```
Chrome extension (client)                    Walkthru API (FastAPI + LangGraph)
side panel: goal + test user     ── start ─▶ entitlement check (plan, runs left, steps, logged-in, site)
content script: snapshot page    ── observe ▶ persona agent decides the next action
executes the action in the tab   ◀─ action ── click | type | scroll | done | give_up
                                  ... loop until done / give_up / safe stop / budget ...
                                              report: journey + SEO + GEO + security + a11y + performance
                                              compare with the previous run of the same site and goal

Server only (no browser): Instant Scan, site audit, GEO readiness, security hygiene, backend exposure,
weekly watch, citation tracking, Search Console data, deploy webhook.
Worker on the VM (Phase 2): repository code scans and safe Nuclei templates, one job at a time.
```

The step loop, safety model, redaction, evidence and grounding are unchanged from v1. See ARCHITECTURE.md.

## SEO depth (P1.6)

`apps/api/app/scans/seo_depth.py` extends the bounded site crawl with conservative checks for invalid or nonreciprocal hreflang, required Google rich-result fields on Product, SoftwareApplication and BreadcrumbList markup, generic content anchors, lazy images without HTML dimensions, large image responses and large older-format images, a page with only one observed incoming link when the crawl is complete, pagination links and canonicals, and canonicals pointing at a known or safely fetched noindex or redirect target. The crawler keeps numeric `?page=` URLs up to page 100 while dropping tracking and other query variants. Checks use fetched pages where possible; image HEADs and unseen canonical reads are same-origin, robots-aware where applicable, bounded by time and count. An unmeasured image size or canonical target is never called healthy. The check inventory was reviewed against MIT [Open SEO Crawler](https://github.com/puneetindersingh/open-seo-crawler), [LibreCrawl](https://github.com/PhialsBasement/LibreCrawl) and [FreeCrawl](https://github.com/kemalai/FreeCrawl-SEO-Tool); required schema fields and pagination advice follow Google Search Central's current documentation. Licence notices are in `apps/api/THIRD_PARTY.md`.

Paid reports send at most the first five audited URLs to the existing PageSpeed Insights integration with `strategy=mobile` and `PAGESPEED_API_KEY`. Requests run with three workers and a 15-second request timeout. The report shows URL-level real-user LCP, CLS and INP when PageSpeed supplies them, alongside the separate Lighthouse lab score. Missing field data and failed API calls are labelled unavailable. Free reports retain the homepage-only check. The PageSpeed scan follows the site crawl so it can use the exact audited URLs.

## GEO readiness (new)

Deterministic scanner in `apps/api/app/scans/geo.py` and `geo_depth.py`. It reuses the pages, `robots.txt` and homepage the site audit already fetched. Extra reads are `GET /llms.txt`, two optional discovery files, and one homepage GET with a citation-bot user agent. A full nonlocal report also looks up the site name and official domain in Wikidata, and Google Knowledge Graph only when a free API key is configured. An unavailable check is excluded from the measured-point denominator. Scored 0 to 100:

| Category | Points | Checks |
|---|---|---|
| AI crawler access | 25 | `robots.txt` allows the citation bots (OAI-SearchBot, ChatGPT-User, Claude-SearchBot, ClaudeBot, PerplexityBot, Googlebot, Bingbot, Applebot) (15). The homepage answers a citation-bot user agent with 200 rather than 403 or a challenge page (10). Blocking training-only bots (GPTBot, Google-Extended, CCBot) is reported as a choice, not a fault. |
| Content without JavaScript | 20 | Homepage HTML contains the main text before JavaScript runs (15). Key pages (pricing, about, docs, features) are not empty shells (5). Most AI crawlers do not run JavaScript, and many AI-built apps are single-page apps. |
| Structured data | 15 | Valid JSON-LD (5). Organization or WebSite (4). A page-type schema: SoftwareApplication, Product, FAQPage or Article (4). Schema with 5 or more useful properties (2). |
| Answerability | 15 | One H1 (3). Descriptive H2s (3). A plain paragraph early on the page (3). Lists or tables (3). Concrete numbers (3). |
| Entity and trust | 10 | Same name in title, og:site_name, schema and H1 (4). About, contact and privacy or pricing pages linked (4). sameAs links to public profiles (2). |
| Meta | 10 | Title, description, canonical, Open Graph. The score reuses SEO signals; findings stay in the SEO section so nothing is reported twice. |
| llms.txt | 3 | Present and well formed. Labeled "low measured impact" ([Otterly study](https://otterly.ai/blog/the-llms-txt-experiment/)). |
| AI discovery files | 2 | Plain-text `/.well-known/ai.txt` and `/llms-full.txt`. These are optional, and their effect on AI search is not established. Missing files receive low-severity guidance. |

- **Score bands:** 0 to 35 critical, 36 to 67 foundation, 68 to 85 good, 86 to 100 excellent.
- **Reference:** the category model adapts [geo-optimizer-skill](https://github.com/Auriti-Labs/geo-optimizer-skill) (MIT), whose citability guidance draws on [Princeton's GEO research](https://collaborate.princeton.edu/en/publications/geo-generative-engine-optimization/). It is re-weighted toward checks with evidence, and implemented on Walkthru's SSRF-safe fetcher rather than added as a dependency.
- **"What AI search sees":** the report quotes the homepage text a crawler gets before JavaScript runs, with its word count. It is deterministic, so it is true for scans and test runs alike (a run's first impression reads the page after JavaScript, so it is not relabelled). On a JavaScript shell it says plainly that AI search sees nothing.
- **Fix pack:** deterministic templates filled from the audited pages. They cover robots.txt rules, JSON-LD blocks, an llms.txt draft, a rendering fix for the detected framework (Vite single-page app, Next.js, Lovable, Astro), and, on full reports, an optional IndexNow key file and manual Bing Webmaster sitemap submission note. Neither step submits anything automatically.
- **Depth pass (P1.5):** a separate, advisory 0 to 100 citability checklist for each fetched page counts statistics with sources, attributed quotations, definitions and comparison tables at 25 points each. It also reports visible or structured dates and sitemap `lastmod`; CTA overload, boilerplate, repeated keywords and hidden instructions to AI; identity, social proof, external citations and name consistency; and section, question-heading and answer-first signals for retrieval. A citation-bot challenge is reported even when robots.txt permits the bot. Wikidata and optional Knowledge Graph checks require an entity whose official URL matches the scanned domain; absence does not lower the score. This adapts the MIT geo-optimizer-skill taxonomy, with its notice in `apps/api/THIRD_PARTY.md`. Citability is content evidence, not a citation prediction.
- **Measurement (Phase 3):** citation tracking on free engines, the sources AI cites for the category, accuracy of what AI says, AI crawler hits and AI referral visits.

## Agent design, safety, tech stack

Unchanged from v1: `persona_session` graph (decide, interrupt, check); destructive actions never run; sends only on verified domains after the owner confirms, once per run; same-origin; CAPTCHA stop; redaction before upload; deep security checks and read-only probes only on verified domains; fake test identity. Stack: Chrome MV3 + WXT + React; React 19 + Vite + Tailwind v4 web; FastAPI + LangGraph API; Supabase; free model chain (Groq, OpenRouter writer, Gemini); Dodo; Resend. See ARCHITECTURE.md.

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
- **Ask first:** new dependencies (permissive open source approved in principle 2026-09-25; still named per task), switching on any paid model or API, schema changes after launch, price changes after this spec.
- **Never:** attack payloads, fuzzing, denial of service or writes to a site's backend; probes on unverified domains; active scans of production URLs (Phase 4 scans only an owner-entered staging URL); CAPTCHA solving; payment submission; promising AI citations or rankings; a weaker free report; storing repository code after a scan; code or data from AGPL, Commons Clause, Elastic or unlicensed projects; committing secrets.

## Success criteria
- Instant Scan returns SEO, GEO score, "what AI search sees" and security headers in 20 s or less for a 10-page site.
- GEO scanner flags every GEO trap on the hard fixture; overall trap recall is 80% or more (Checkpoint B).
- A free account cannot start a logged-in run, a 13th step or a 4th monthly run, whatever the client sends.
- A rerun marks every prior finding fixed, still broken or new, and matches a hand check on 3 fixture reruns.
- Paid run cost is $0.20 or less; free run is $0.02 or less. While every plan runs on free tiers, model cost is $0 and the limit is free-quota capacity, guarded by database-counted daily caps.
- Checkpoint P1: recall 85% or more on the hard fixture including backend, security and GEO traps, with no false alarms on the easy fixture and 3 real sites.
- Validation (founder/validate-idea.md): 5 of the first 100 Instant Scans convert to a $9 Launch Pack, and 25% of beta users who click "Run a test" finish a run.
- Chrome Web Store listing approved before launch (Oct 20). 50 community sites tested and 5 paying by 2026-11-30.

## Open questions
- Keep the exact list prices ($19 and $49) or adjust after experiment 1?
- Cloud runner (public journeys without installing the extension): build only if experiment 2 shows fewer than 25% of beta users finish a run after clicking "Run a test".
