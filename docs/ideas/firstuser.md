# FirstUser (working name)

## Problem Statement
How might we show a small team, before launch, exactly where a real first-time visitor gets confused, stuck, or leaves — without recruiting testers or paying $99+/mo for research tools?

## Recommended Direction
Paste your URL and a goal ("sign up and create a project"). AI personas ("non-technical shop owner", "impatient mobile user", "skeptical buyer checking pricing") open your site in a real browser, try to do the goal, think aloud, and get stuck where real users would. You get a shareable report: did they succeed, where they hesitated (with screenshots), what confused them, a 5-second first-impression test, basic accessibility issues, and a prioritized fix list. Re-run after every deploy and compare.

Why this one (after rejecting StudioOS, pipeline, and TrustDraft):
- **Cheap to run, even with zero paying users.** Tests public pages; free tier runs on a free/cheap model; browser runs on a free or $5 VM. No per-seat enterprise sales.
- **Your community can use it for free and it helps them immediately.** Every student/indie project has a signup or landing page. Shared report links spread the product.
- **Genuinely agentic.** A browser agent must observe, plan, act, recover from dead ends, and reflect in character. Personas run in parallel; a synthesizer agent merges findings. Not a cron job, not a template.
- **Not a Claude Code one-liner.** Real browser, personas, screenshots, scoring, re-test diffs, and a shareable report — a product, not a prompt.
- **Proven willingness to pay, low price anchor.** Existing tools charge ~$3 per persona (Evelance), $8–20 per study (Articos), $99+/mo (Maze). Indie devs have nothing cheap and dev-friendly.

## Key Assumptions to Validate
- [ ] Reports find real, non-obvious issues on real projects — test: run on 20 community projects in week 3; ask owners "did this find something you fixed?" (target ≥ 50% yes).
- [ ] Cheap models are good enough for the free tier — test: compare free vs paid model reports on the same 10 sites.
- [ ] Some teams pay $9–39 — test: launch-week conversion from free; founding offer.
- [ ] Browser runs stay under ~$0.25 each on paid tier — test: token + minute logging per run.

## MVP Scope
In: auth, site ownership verification, test setup (URL + goal + personas), browser persona agent, synthesizer report, shareable report page, 5-second test, axe-core accessibility scan, email summary, CSV/Google Sheet issue export, re-run + compare, Dodo credits/subscriptions.

## Not Doing (and Why)
- Figma prototype testing — v2, different input pipeline.
- Logged-in areas needing 2FA/SSO — v2; v1 supports a test email/password only.
- Solving CAPTCHAs — never; the agent stops and reports it.
- Testing sites the user doesn't own — blocked by domain verification (abuse/legal).
- Native mobile apps — out of scope; v1 uses mobile viewport emulation.
- Heatmaps / session replay of real users — that's Hotjar's game.

## Open Questions
- Name/domain. Paid model choice (Haiku 4.5 vs Sonnet 5) after week-2 comparison.
