# Decisions

## T9: Free and paid model selection

**Status:** Pending real browser benchmark

### Measurement contract

- Dataset: 18 seeded traps in `evals/traps.json`, split evenly across UX, SEO, and passive security.
- Recall: a trap counts as found only when a conservative phrase appears in the captured report or browser-run steps.
- Cost: use provider or LangSmith `cost_usd` when available. Otherwise calculate from separate input and output token counts using the rates current on the experiment date.
- Gates: at least 80% overall recall, free run at most $0.02, paid run at most $0.20.

### 2026-09-19 deterministic baseline

| Candidate | Overall | UX | SEO | Security | Cost / run |
|---|---:|---:|---:|---:|---:|
| Deterministic homepage scans | 11/18 (61%) | 0/6 (0%) | 6/6 (100%) | 5/6 (83%) | unknown |

This is a boundary check, not a model result. The homepage scanners correctly find every SEO trap and five security traps. The insecure signup form and all UX traps require the extension to traverse the flow.

### Decision still needed

Capture the same hard-fixture goal with the free pool and each paid candidate through the real extension. Score and publish those captured runs with `evals/runner.py`, then choose the least expensive candidate that clears the recall gate. Do not change `PAID_MODEL` before that comparison.

## T9: Jev as the browser decision layer

**Status:** Benchmark candidate, not adopted

### Finding

Jev 1.13 is a TypeSafe System One model. It consumes text or structured text state and returns typed `Choice`, `Score`, and `Noul` decisions with probabilities. It does not generate prose, explanations, code, images, audio, or video. The official model card lists a price of $0.042 per million input tokens, free output tokens, a 64k request context, and a 32k state-plus-longest-question limit.

This matches part of Walkthru's browser loop unusually well. The extension already converts the page into at most 120 indexed controls, below Jev Choice's documented 255-option maximum. A single Jev call could choose the operation and compatible target while also scoring goal completion, stuck probability, and confusion. LangGraph can remain the orchestrator because its nodes can call Jev, an LLM, or plain code.

Jev cannot replace every current LLM call. Free-text form values that are not known test identity fields still need deterministic generation or a small generative model. Persona think-aloud, first impressions, summaries, findings, and fixes also require generation. A post-run LLM can turn the structured trace into human-readable evidence without putting prose generation on every browser step.

### Candidate architecture

1. Keep the extension snapshot, redaction, safety executor, LangGraph state, checkpointer, and reports.
2. Replace only the persona graph's hot-path action selection with one Jev request containing speculative parallel questions for operation, target, goal completion, stuck state, and confusion.
3. Use deterministic test identity values first. Call a small text model only for genuinely open-ended input.
4. Generate persona narration and report prose after the run from the structured trace.
5. Gate low-confidence decisions to the existing LLM or stop safely.

### Risks

- Jev 1.13 is newly released and its public browser-agent evidence is narrow. Browser Use reports three successful repeats of one Google Flights task, not a general reliability benchmark.
- TypeSafe documents weaker performance on indirection, numeric precision, long irrelevant state, adversarial content, and non-English inputs.
- Jev accepts text only, so screenshot understanding still needs a vision-capable model if Walkthru later tests canvas-heavy or visually ambiguous interfaces.
- TypeSafe offers zero data retention only on enterprise plans. Authenticated page data still needs the existing client-side redaction and a vendor/privacy review.

### Decision gate

Add Jev as a third candidate in Session 8B, using the same easy and hard fixture captures and the existing 18-trap scorer. Do not replace the free pool unless the hybrid clears the same recall gate, completes the easy flow reliably, and materially improves median step latency and cost.

Sources: [TypeSafe introduction](https://docs.typesafe.ai/introduction), [model and pricing](https://docs.typesafe.ai/models), [Jev 1.13 limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13), and [Browser Use Jev Ultrafast](https://github.com/browser-use/jev-ultrafast).

### 2026-09-20 live API experiments

The official TypeSafe skill was installed globally and Jev `jev-1.13.0` was called through the documented HTTP API. The key is stored only in ignored `apps/api/.env`.

| Design | Easy decisions | Median latency | Mean input tokens | Mean operation confidence |
|---|---:|---:|---:|---:|
| One combined action-target Choice | 5/5 | 625 ms | 938 | 0.896 |
| Speculative operation and compatible targets | 5/5 | 382 ms | 1,044 | 0.966 |

The speculative fan-out shape is the implementation candidate. It completed homepage CTA selection, email, password, submit, and goal detection correctly. On the ambiguous hard homepage it selected the exact footer `Create account` link five times with confidence 1.0. That is efficient but may under-represent how a person reacts to the more prominent vague `Continue` and `Proceed` buttons, so persona fidelity remains unproven.

Risk probes supported conservative fallback:

- After a misleading action opened a newsletter modal, operation confidence fell to 0.38 and target confidence to 0.44.
- Adversarial page text did not cause a destructive selection, but TypeSafe's documented adversarial-content limitation means code safety remains mandatory.
- With 120 visible controls, Jev selected element 120 correctly in 638 ms using 6,809 input tokens.

**Decision:** build an opt-in hybrid adapter with a 0.50 starting confidence floor, deterministic values for known identity fields, and LLM fallback for low confidence, provider errors, and open-ended typing. Keep the existing LLM as the default until the real hard-fixture benchmark clears the product recall gate. Pin `jev-1.13.0` during evaluation.

Additional sources: [HTTP API](https://docs.typesafe.ai/api), [structured state](https://docs.typesafe.ai/concepts/state), [confidence routing](https://docs.typesafe.ai/confidence), and [speculative fan-out](https://docs.typesafe.ai/patterns/fan-out).

## 2026-09-24 Report writer model

**Question:** would a stronger free model stop the report inventing problems?

**Method:** `evals/model_bakeoff.py` replays the exact production report prompt for five saved runs: three where nothing went wrong (portfolio contact twice, verified fixture send) and two Tripverse signups that hit a real "email rate limit exceeded" error. "Invented" means a UX finding the production filter (`grounded_ux`) would drop. "Summary invents" means problem words in the summary of a run with no problem.

| Model | Answered | Invented (filtered) | Caught the real error | Summary invents | Median |
|---|---:|---:|---:|---:|---:|
| Groq gpt-oss-120b | 2/5 (rest 429) | 0 | not reached | 0/2 | 2.9 s |
| Groq gpt-oss-20b | 4/5 (one schema 400) | 0 | 2/2 | 1/2 | 2.4 s |
| OpenRouter Nemotron 3 Ultra (free) | 4/5 (one empty reply) | 1 | 2/2 | 0/2 | 58 s |
| OpenRouter Nemotron 3 Super (free) | 5/5 | 2 | 1/2 | 1/3 | 6 to 53 s |
| OpenRouter Gemma 4 31B (free) | 0/5, rate-limited upstream | | | | |
| Gemini 3.5 Flash | 0/5, 503 | | | | |
| OpenRouter Nex N2.5 Pro (free) | cut off after 355 s | | | | |

gpt-oss-20b's flagged summary said the portfolio form "cannot be submitted because the domain is not verified", blaming the site for Walkthru's own safety stop. Nemotron Ultra wrote "the walkthrough stopped at the submit button by design" for the same run.

**Finding:** the grounding code already removes invented findings from every model. The model mostly changes the summary and the fixes, and there Nemotron Ultra and gpt-oss-120b were the most careful.

**Decision:** report writing goes Groq gpt-oss-120b, then Nemotron 3 Ultra through OpenRouter (90 s budget), then the fast chain. Persona steps stay on the fast chain, because a step cannot wait 60 s. The persona steps usually use up 120b's per-minute budget, so in practice Ultra writes most reports. That adds about a minute to report time and costs nothing. A 503 or 429 from OpenRouter falls through in under a second.

**Revisit when:** a paid tier exists (the T9 eval decides the paid writer), or OpenRouter's free Ultra becomes unreliable. Rerun the bakeoff with `MODELS=... python evals/model_bakeoff.py`.

## 2026-09-24 Positioning, plans and GEO (v1.1)

**Context:**
- A sourced review (`founder/competitor-matrix.md`, `founder/pricing-strategy.md`, `founder/validate-idea.md`) found that "AI users test your site" is crowded. Meerkat, CanaryUsers, Swarm and Uxia all sell it, CanaryUsers from $9.
- Our paid plans mostly sold volume.
- Plan limits were not enforced by the server.
- The idea scored 21 out of 35.

**Decision:**
- Walkthru is "the launch check for apps built with AI": journeys, SEO, GEO and passive security in one report, with logged-in pages tested in the owner's own browser.
- GEO readiness is in every plan: a free score, a paid fix pack, and a watch in Plus.
- Plans:
  - Free.
  - Launch Pack $9 once.
  - Pro $19 (founding $15, 40 runs).
  - Plus $49 (founding $39, 150 runs), replacing Team and launched as a waitlist until watch ships.
- Free report quality always equals paid.
- The server owns every limit.

**Alternatives rejected:**
- Competing on run volume: capacity is capped by free providers at about 110 runs a day.
- Selling a better model: grounding, not the model, removes invented findings (2026-09-24 bakeoff).
- AI citation tracking in V1: recurring model and search cost, and Otterly already sells it.
- Adding `geo-optimizer-skill` as a runtime dependency: it uses its own HTTP client, outside our SSRF guard, and weights low-evidence checks such as llms.txt at 18 of 100.

**Revisit when:**
- Experiment A1 (5 of 100 scans convert at $9) fails.
- A2 shows fewer than 25% of beta users finish a run. That triggers the cloud runner.

## 2026-09-24 Scope, dates and dev testing of paid plans

**Scope accepted by the founder:**
- Agent fix prompt.
- Ignore a finding.
- Launch Ready score and badge.
- Signup email check.
- Signup funnel numbers.
- Landing copy review.
- Competitor side by side.
- Walkthru MCP server (Plus).

This approves the official `mcp` Python SDK when V20 is built.

**Deferred to next versions:** the preview-deploy check, and exporting findings to GitHub Issues or Linear.

**Dates:**
- Launch target 2026-10-20, 2026-10-27 at the latest. The two outside waits are Chrome Web Store review and Dodo live-mode verification.
- Plus opens by 2026-11-22.

**Dev testing:** paid plans are tested at no cost.
- Plans are `entitlements` rows granted by `scripts/grant_plan.py`.
- No plan uses a paid model.
- Payments run in Dodo test mode.

## 2026-09-24 Goal intent before execution; no matplotlib charts

**Context:**
- A real run on the founder's portfolio reached its goal at step 2, then circled four "NEXT CASE" pages until the owner stopped it at step 11.
- The report then blamed the site for the loop, and counted the owner's Stop as "user confusion".

**Decisions:**
- **Goal planner.** Every run starts with a goal planner (one fast model call): an intent plus a checklist, with the finish checked in code. A goal that asks to pay, delete or attack is refused before a run is used.
- **Looping guard.** It stops circles as `looping`, Walkthru's own limit.
- **Owner Stop.** It is never evidence against the site.
- **Suggested goals.** They come from the page's own links, in plain code.
- **Charts: no matplotlib charts for now.**
  - Single reports hold too little data for a chart to add insight.
  - matplotlib is a heavy server dependency producing static, theme-blind images.
  - The PDF is the printed web page.
  - Charts come back for trends over time (score and fixed/new findings across reruns) once rerun-compare (V4) and watch (V12) produce that data, drawn as inline SVG in React.

## 2026-09-24 Checkpoint B: trap recall 82%

**Setup:**
- Two real journeys on the hard fixture through `evals/e2e_extension.py`: headless Chrome, the built extension script, the real API and the free models.
- The test account was on a Pro dev pass, on an owner-verified domain.
- Goals: "Sign up for an account" and "Find the pricing plans".
- Scored with `evals/runner.py --combine` against 22 traps (18 original plus 4 GEO traps the hard site already had).

| Run | Overall | UX | SEO | Security | GEO |
|---|---:|---:|---:|---:|---:|
| Sign up | 17/22 (77%) | 1/6 | 6/6 | 6/6 | 4/4 |
| Find pricing | 17/22 (77%) | 2/6 | 6/6 | 5/6 | 4/4 |
| **Both (one site evaluation)** | **18/22 (82%)** | 2/6 | 6/6 | 6/6 | 4/4 |

**What made the difference:**
1. **Visited pages audited.** Pages the test user visited are audited even when robots.txt blocks crawlers, on owner-verified domains only. This found the signup form posting over plain http (X5).
2. **Signup placement check.** A plain-code check reports a homepage whose only sign-up link is in the footer (U1).

**Misses:**
- **U2:** the report did describe the silent submit ("an unchecked required checkbox with no validation feedback"), but not in the scorer's exact phrases. It is counted as missed; the scorer was not changed to fit.
- **U4:** the ambiguous CTAs were never needed by either goal.
- **U5:** the pricing page is not linked from anywhere.
- **U6:** the test password already met the hidden rule.

**Also fixed on the way:**
- "Done" right after a click or typing that changed nothing is questioned once, then ends as gave up. A run had declared signup complete without submitting.
- A click that changes nothing is evidence for the report.
- Em and en dashes are stripped from model-written report text.
- Cost per run is logged in tokens (about 9,000 to 12,000 for a report), all on free models.

## 2026-09-24 Claude Haiku 4.5 for Pro and Plus

**Decision (founder):** Pro and Plus use Claude Haiku 4.5 as the goal planner, test user and report writer, through Google Cloud Vertex AI. Free stays on the free chain.

**Why Google Cloud:** the founder has no credit card. Google Cloud accepts a UPI prepayment and lists Claude Haiku 4.5; OpenRouter needs an international card, AliPay or USDC. GPT-5 mini is not on Google Cloud.

**Cost, from measured runs:**
- Runs of 4 to 6 steps used 6,400 to 11,800 tokens.
- At an estimated Google Cloud rate of $1.10 input and $5.50 output per million tokens (about 10% over Anthropic's list price; confirm at setup), a typical run costs about $0.02 to $0.04 and a 30-step run about $0.08.
- Pro at full use costs about $1.40 a month (worst case $3.08) against $17.84 net.
- Plus about $5.43 (worst $11.73) against $46.64 net.
- Both stay within payment.md's 25% allowance, with the cost ledger as the guard.

**Product rule changed:** "free reports are exactly as good as paid" became "same checks and honesty rules on every plan; Pro and Plus add Claude's judgment". Every report states which models ran.

**Built on 2026-09-24:** off until `CLAUDE_VERTEX_PROJECT` is set. The free chain always sits behind Claude.

**Before marketing specific gains:** a measured comparison on the hard and showcase journeys (session 6).

## 2026-09-24 Jev stays off; first-step latency fixed in our own code

**Question (founder):** Jev calls never show in the usage dashboard. Is Jev still part of the system, and would it make Walkthru fast?

**Finding:** Jev is wired but off. `runtime.make_model` only builds the hybrid when `PERSONA_DECISION_MODEL=jev`, and nothing sets it, so every step uses the free LLM chain.

**Measured** (same easy-fixture signup journey through the real API, test account on a Pro pass):

| | Free LLM chain | Jev hybrid |
|---|---:|---:|
| Server time per step after the first | 1.4 to 2.0 s | 1.8 s when Jev answered; 12.3 and 14.7 s when Jev timed out and fell back |
| Whole journey | 30.8 s | 64.0 s |
| Step narration | Written by the model | Template ("I will use Email because it looks like the clearest next step") |

Steps arrive about 5 s apart even when the server answers in 1.5 s: the rest is the browser acting, the page settling and the screenshot upload. A 0.4 s decision model would save at most about 1 s of that, and only when it is reliable.

**Decision:** keep Jev off. Its timeouts doubled the journey, and templated narration weakens the think-aloud that reports quote. Revisit if TypeSafe latency from this region is stable and it can return real narration, using the same A/B.

**What made the first step slow, and the fix** (timed with the new `start_run` log line):
- Before: plan check 0.7 to 1.8 s, goal planner 2.0 to 7.2 s, domain verification 4.4 to 6.0 s, first step 1.1 to 3.8 s, all one after another: 13 to 19 s.
- Domain verification now runs in a background thread while the plan check and planner work (it needs only the site and the user).
- Startup now warms both agent graphs and the planner's model clients, not just the free graph.
- After: 7.6 to 8.8 s for the first call on the same machine. What remains is the database plan check and one planner model call.

## 2026-09-24 OpenSEO's audit checks adopted; its paid data features not

**Reviewed:** [every-app/open-seo](https://github.com/every-app/open-seo) (MIT, TypeScript). Keyword research, rank tracking, backlinks, competitor data and AI visibility all come from DataForSEO (paid, $50 minimum top-up; the hosted plan is $10 a month plus usage). Only its site audit is its own code.

**Adopted** (rewritten in Python in `app/scans/site.py` `_site_checks`, no code copied): broken internal links, server errors, pages blocked by bot protection or rate limits (reported as "not checked" instead of silently skipped), duplicate titles, descriptions and content, thin content, dead-end pages, redirect chains, conflicting canonicals, slow HTML (production only), pages 5+ clicks deep, orphan pages from the sitemap (only when the crawl finished), and short meta descriptions. All plain code, every plan.

**Not adopted:** anything that needs DataForSEO. It costs per call, needs a card, and OpenSEO already sells that data at cost plus 28%. Revisit: Google Search Console (free, the owner's real queries and indexing) after launch.

## 2026-09-25 Friends beta hosting and the audit before it

**Hosting (free, no card):** web on Vercel, API on Render's free web service (`render.yaml`). Hugging Face Spaces was ruled out: Docker Spaces now need a paid plan. The API used 147 MB, inside Render's free limits. Trade-offs accepted for a beta: sleeps after 15 idle minutes (about a minute to wake) and a restart ends any test mid-run. Production still moves to an always-on VM with `CHECKPOINTER=postgres`.

**Fixed before deploy:**
- Public reports leaked contact emails: the `anon` role can read every column of a public run, and `runs.email` held Instant Scan and owner addresses (5 readable live). Emails are no longer stored; report emails look the owner up in Supabase Auth when sending. Column grants were not used because the screenshot storage policy reads `runs.user_id` as `anon`.
- The public repo held test account passwords (code defaults and CURRENT_STATE.md). Removed; the accounts must be rotated or deleted (docs/deploy.md step 0).
- `langchain-groq`, `python-dotenv` and `email-validator` were imported but undeclared; a clean install crashed. Declared, and a clean install was verified.
- The extension only accepted sessions from localhost and had a machine-specific id. A committed public key fixes the id; the allowed page comes from `VITE_WEB_URL` (`npm run zip:beta`).
- Behind a proxy every visitor shared one address, so 5 scans an hour would have been the limit for everyone. uvicorn trusts the proxy's forwarded address. A spoofed header only bypasses the per-address limit; the database-counted daily cap still holds.
- Vercel gets SPA routing and security headers, including a strict CSP (`script-src 'self'`), tested against the production build.
