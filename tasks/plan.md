# Implementation Plan: Walkthru v1

Task-level detail lives in [todo.md](todo.md). This file holds decisions, costs, and risks.

## Overview
Four build weeks (Sep 21 – Oct 18, 2026), launch Tue Oct 20. Week 1 proves the hardest part: the extension ↔ server agent loop on fixture sites. Nothing else matters if that loop is flaky.

## Architecture Decisions
- **Browser runs on the user's machine (Chrome extension), brain runs on our server (LangGraph).** No Chromium on our server: hosting stays $0–5, and logged-in pages work without sharing passwords.
- **Loop lives in the side panel page**, not the MV3 service worker (Chrome kills idle workers after ~30 s).
- **One HTTP call per step**, LangGraph `interrupt` + `Command(resume=observation)`, Postgres checkpointer. Server is stateless between calls, so it survives restarts and scales horizontally later.
- **Text snapshot first, screenshots rarely.** Tokens are the main cost.
- **SEO and security scans are server-side plain code + one LLM explanation call each.** No browser, no agent needed there. Honest: these parts are automation, the persona run is the agent.
- **Passive security only**, on verified domains. Legal safety and no broken customer sites.
- **Free tier on a free-tier model; paid on Claude** (Haiku 4.5 or Sonnet 5 after the week-2 eval; founder confirms).

## Cost
| Item | Pre-launch | Monthly after launch |
|---|---|---|
| LLM (dev + evals) | ~$10–20 | free runs ≈ $0 (free-tier model); paid ≈ $0.05–0.20 per run, covered by the payment |
| Server | $0 (local) | $0 Oracle Always Free, or ~$5 VPS |
| Chrome Web Store | $5 one-time | $0 |
| Supabase, Vercel, Resend, LangSmith, PageSpeed API | $0 | $0 on free tiers |
| Dodo | $0 | fee per sale |
| **Total** | **~$15–25** | **$0–5 with zero paying users** |

## Launch & GTM (Oct 20 → Nov 30)
- Community first: free runs for college/dev groups, hackathon teams; ask for shared report links.
- Viral loop: public report links with a "Tested with Walkthru" badge.
- Launch posts: Product Hunt, Show HN ("I let AI users try to sign up to 50 indie apps"), r/SideProject, r/webdev, r/SaaS, Indie Hackers, LinkedIn/X build-in-public.
- Paying segment: small agencies (test client sites before handoff), seed startups before launches.
- Target: 50 sites tested, 5 paying by Nov 30.

## Risks and Mitigations
| Risk | Impact | Mitigation |
|---|---|---|
| Agent gives shallow, generic feedback | High | Fixture traps + evals from week 1; findings must cite a step/screenshot |
| Agent breaks something on a logged-in page | High | Safe mode, confirm before submits, recommend a test account |
| Customer data in dashboard DOM sent to LLM | High | Client-side redaction, disclosure, no retention beyond report |
| SPA quirks (shadow DOM, iframes, canvas, virtual lists) | Med | Snapshot handles open shadow roots; report "couldn't interact" instead of guessing |
| Chrome Web Store review delay/rejection | Med | Submit in week 3; minimal permissions (activeTab, sidePanel, scripting) |
| Free-tier model rate limits | Med | Queue + per-user caps; paid model fallback for paid users |
| Competitors (Evelance, Uxia, Swarm, Meerkat, Simuser) | Med | Dev-first, logged-in flows via own browser, SEO + security in one report, cheap |
| Dodo payout KYC | Med | Check now; Lemon Squeezy / Polar fallback |

## Session plan
One session = one focused sitting with the agent. Each ends with build, lint and tests green and CURRENT_STATE.md updated. "Needs" = what the founder must provide before that session can finish.

| # | Session | Tasks | Deliverable / verify | Needs from founder |
|---|---|---|---|---|
| 1 | Agent core (done 2026-09-18) | T5 | `persona_session` graph (decide → interrupt → check), `POST /runs`, `POST /runs/{id}/observe`, `GET /runs/{id}`, safe mode + loop + budget + captcha enforced in code, 9 pytest with a scripted fake model | nothing |
| 2 | Fixture sites | T2 | `evals/fixtures/easy` and `evals/fixtures/hard` static sites with seeded UX, SEO and security traps; `evals/traps.json`; served with `python -m http.server` | nothing |
| 3 | Extension snapshot | T3 | WXT MV3 skeleton, side panel UI (site, goal, persona), content script snapshot (numbered elements, text, errors, open shadow roots) + PII redaction; vitest on snapshot and redaction | nothing (Chrome only) |
| 4 | Extension loop + executor | T4 | click/type/scroll/back executor, same-origin guard, danger-word filter, confirm-before-submit on logged-in pages, step loop in the side panel calling `/runs`. **Checkpoint A:** easy fixture flow completes end to end with the free model | `GOOGLE_API_KEY` (free Gemini), `LANGSMITH_API_KEY` |
| 5 | First impression + report | T6 | `first_impression` node (screenshot + page text), `synthesize` (dedupe, severity, evidence, top fixes), report JSON schema + one pytest per node with fake model | nothing |
| 6 | SEO scan | T7 | plain checks (title, meta, h1, canonical, robots, sitemap, alt text, links) + PageSpeed Insights + one LLM content review; pytest against fixtures | `PAGESPEED_API_KEY` |
| 7 | Security hygiene scan | T8 | headers, TLS, cookies, exposed files, JS secret patterns, domain verification (meta / DNS TXT / well-known); pytest against fixtures | nothing |
| 8A | Eval tooling | T9 | Score saved run/report JSON against `evals/traps.json`, report recall by kind and cost per run, optionally publish code-evaluator results to LangSmith | nothing |
| 8B | Model benchmark | T9 | Capture real hard-fixture runs from the free and paid candidates, publish comparable LangSmith experiments, record the choice in `docs/decisions.md`. **Checkpoint B:** ≥ 80% traps found | `ANTHROPIC_API_KEY` (~$10 credit), founder Chrome for the full extension loop |
| 9 | Data + auth | T10 | Supabase schema (users, sites, runs, reports, credits) + RLS, JWT verification on every API route, extension token handoff, session handling in web | Supabase project, keys in `.env`, Google + GitHub providers enabled |
| 10 | Dashboard | T11 | react-router, `/app` shell, sites and runs lists, Instant Scan (no install), loading / empty / error states | nothing |
| 11 | Report page | T12 | `/report/:id`, share link, CSV / Google Sheet export, email via Resend. **Checkpoint C:** 20 community sites tested | `RESEND_API_KEY`, 20 sites lined up |
| 12 | Store submission + legal | T13 | privacy, terms, security pages; store listing, screenshots, minimal permissions; submit | Chrome Web Store dev account ($5), domain bought |
| 13 | Billing | T14 | plans, credits, Dodo checkout + signed webhook + limits; pytest on webhook signature and limits | Dodo test-mode keys, KYC checked |
| 14 | Deploy | T15 | Vercel (web, rewrites) + VM (API, Postgres checkpointer, rate limits, error logging) | Vercel account, VM or VPS, `DATABASE_URL` |
| 15 | Launch | T16 | landing wired to signup, pricing, demo report; launch checklist. **Checkpoint D:** stranger installs → tests → pays in production | go / no-go |

Sessions 2, 3 and 5 to 7 need no keys and can run in any order after session 1. Session 4 is the first that needs a real model key.
