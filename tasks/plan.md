# Implementation Plan: Walkthru v1

_2026-09-24: the plan, plans and build order are superseded by [SPEC.md](../SPEC.md) v1.1 and [ROADMAP.md](../ROADMAP.md) v1.1. Cost notes and risks below still apply._

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

## Competitive quality roadmap: Swarm-level evidence plus launch readiness

This roadmap extends v1 without replacing unfinished launch work. The product wedge is one polished launch-readiness report that combines synthetic journey testing with visual evidence, UX findings, accessibility, SEO, performance, and passive security. Free limits quantity, not report quality. Paid plans add authenticated flows, volume, comparison, collaboration, scheduling, and integrations.

### Architecture decisions

- Keep LangGraph as the run state machine. Decision providers are replaceable inside `persona_session`.
- Add Jev as an opt-in hot-path decision provider. Keep the existing LLM as fallback for low confidence, service errors, and open-ended text generation.
- Keep code in control of safety, freshness, execution, arithmetic, and exact checks. A typed model response is not permission to act.
- Build an evidence record before redesigning reports: every step eventually carries timestamp, action result, screenshot reference, confusion, provider, and decision confidence.
- Build an interactive screenshot filmstrip before continuous video. It provides replay, searchability, lower storage, and fewer Chrome permissions. True video remains a later opt-in feature.
- Render PDF from the same report data and print layout. Do not create a separate report pipeline.
- Add accessibility, SEO, performance, and passive-security checks as evidence-producing modules. No active vulnerability probes.

### Phase 0: Prove the decision engine

#### T17A: Opt-in TypeSafe decision adapter

**Description:** Add a server-side Jev adapter for bounded operation and target decisions while preserving the current LLM path and safety executor.

**Acceptance criteria:**
- [x] `PERSONA_DECISION_MODEL=jev` enables Jev only when `TYPESAFE_API_KEY` exists; default behavior is unchanged.
- [x] One TypeSafe request asks operation, compatible click/type targets, goal completion, and confusion in parallel.
- [x] Confidence below the configured floor, API errors, and unsupported free-text fields fall back to the existing LLM.
- [x] Email, password, and name fields use deterministic test identity values without a generative call.
- [x] Stored steps record the decision provider and confidence without exposing credentials or raw page input.

**Verification:** focused unit tests for request construction, response mapping, deterministic identity, and fallback; then the full API pytest and Ruff suites.

**Dependencies:** Existing persona graph and TypeSafe API key.

**Files likely touched:** `apps/api/app/agent/typesafe.py`, `apps/api/app/agent/persona.py`, `apps/api/app/agent/runtime.py`, `apps/api/tests/test_typesafe.py`.

**Estimated scope:** Medium.

#### T17B: Real browser provider benchmark

**Description:** Run the easy and hard fixtures through Groq/Gemini and Jev-hybrid using identical goals and personas.

**Acceptance criteria:**
- [ ] Easy signup closes as `done` in three consecutive runs.
- [ ] Hard fixture is scored with `evals/runner.py`; provider, latency, tokens, confidence, and fallback reason are retained.
- [ ] Jev becomes a default only if it clears the 80% recall gate and materially improves median decision latency or paid cost.

**Verification:** saved run JSON, LangSmith experiment, and final decision in `docs/decisions.md`.

**Dependencies:** T17A and Checkpoint A.

**Estimated scope:** Small.

### Phase 1: Evidence foundation

#### T18: Step evidence contract

**Description:** Extend each run step with timestamps, executor outcome, page transition, screenshot reference, and decision metadata.

**Acceptance criteria:**
- [ ] Old runs still render.
- [ ] Each new step distinguishes observation, decision, execution result, and resulting page.
- [ ] Redacted evidence is retained only as long as required for the report.
- [x] Old runs render through the legacy evidence-empty state; new evidence paths are validated against the run id.
- [x] Decision metadata, executor note, capture time and resulting page are available in the selected-step inspector.

**Verification:** API contract tests, extension tests, and one real easy-fixture run.

**Dependencies:** T17A.

**Estimated scope:** Medium.

#### T19: Screenshot capture and storage

**Description:** Capture the visible tab at the first observation, after meaningful navigation, on errors, and when confusion is high.

**Acceptance criteria:**
- [ ] Capture frequency is bounded and configurable.
- [ ] Screenshots are associated with exact steps and never included in Jev requests.
- [ ] Logged-in capture requires clear disclosure; sensitive values remain masked where technically possible.
- [x] Capture is capped at eight frames and attached to the exact completed step.
- [x] Form controls are masked for the captured paint, Scout is hidden and screenshots never enter the Jev/LLM request.

**Verification:** extension permission/build tests and manual public plus logged-in safe-mode checks.

**Dependencies:** T18 and Supabase Storage policy.

**Estimated scope:** Medium.

### Phase 2: Report experience

#### T20: Interactive evidence timeline

**Description:** Replace the plain step list with a three-pane workspace: runs, chronological screenshot timeline, and selected-step evidence inspector.

**Acceptance criteria:**
- [ ] Keyboard-accessible step navigation and responsive mobile layout.
- [ ] Each step shows screenshot, action, page, confusion, outcome, and finding links.
- [ ] Loading, empty, failed-capture, and legacy-run states are handled.
- [x] Three-pane responsive workspace, signed-image loading states and keyboard-operable step controls are implemented.

**Verification:** web build/lint, component tests, and browser inspection at phone and desktop widths.

**Dependencies:** T18 and T19.

**Estimated scope:** Medium.

#### T21: Filmstrip replay and shareable PDF

**Description:** Add timed screenshot replay and a print-perfect PDF export from the canonical report view.

**Acceptance criteria:**
- [ ] Replay supports play, pause, previous, next, and reduced motion.
- [ ] PDF includes summary, prioritized fixes, findings, and step evidence without clipped content.
- [ ] Shared reports respect existing public/private access rules.
- [x] Timed play/pause/previous/next controls and a canonical print action are implemented.

**Verification:** browser replay check plus rendered PDF visual inspection.

**Dependencies:** T20.

**Estimated scope:** Medium.

#### T22: Optional continuous video

**Description:** Evaluate tab capture only after the filmstrip is validated with users.

**Acceptance criteria:**
- [ ] Explicit opt-in, bounded recording, retention policy, and Chrome Store permission review.
- [ ] Product research proves video adds value beyond filmstrip replay.

**Dependencies:** T21 and privacy/legal review.

**Estimated scope:** Deferred.

### Phase 3: Broader launch-readiness checks

#### T23: Accessibility and performance evidence

**Description:** Add automated accessibility findings and performance measurements, normalized into the existing finding contract.

**Acceptance criteria:**
- [ ] Findings cite page, rule, affected element, severity, and fix.
- [ ] No dependency is added until its license, bundle boundary, and execution environment are approved.
- [ ] Results are deduplicated against persona UX findings.

**Dependencies:** T18.

**Estimated scope:** Medium.

#### T24: Full-site SEO and verified passive security

**Description:** Crawl a bounded verified site, aggregate repeated issues, and preserve passive-only security behavior.

**Acceptance criteria:**
- [ ] Crawl respects robots, same-origin boundaries, page caps, timeouts, and SSRF protection.
- [ ] Security checks remain passive and deeper checks require ownership verification.
- [ ] Report prioritizes unique root causes rather than repeating per-page findings.

**Dependencies:** T18.

**Estimated scope:** Medium.

### Phase 4: Retention and team value

#### T25: Comparison, personas, schedules, and integrations

Order these as separate vertical slices: rerun comparison, multi-persona synthesis, scheduled audits, then Slack/Linear/GitHub delivery. Paid value comes from repetition and collaboration, not withholding the quality of the free report.

### Checkpoints

- **Decision checkpoint:** T17A and T17B complete; model choice backed by fixture evidence.
- **Evidence checkpoint:** T18 and T19 complete; a run has trustworthy visual proof.
- **Experience checkpoint:** T20 and T21 complete; a shared report feels complete without continuous video.
- **Launch-readiness checkpoint:** T23 and T24 complete; UX, accessibility, SEO, performance, and passive security use one prioritized finding model.

### Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Fast decisions behave like an optimizer rather than a human persona | High | Add prominence and viewport evidence, benchmark persona-specific choices, retain LLM fallback |
| Screenshot capture exposes private information | High | Explicit disclosure, bounded capture, masking, private-by-default storage, retention controls |
| Report UI is polished but evidence is incomplete | High | Build T18 and T19 before T20 |
| Video delays the core product | Medium | Ship filmstrip replay first; require evidence before T22 |
| More scanners create noisy reports | Medium | Normalize, deduplicate, and rank root causes before display |
| Vendor behavior changes | Medium | Pin `jev-1.13.0` during evaluation and keep provider fallback |
