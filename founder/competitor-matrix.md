<!-- /founder:competitor-matrix · 2026-09-24 · input: Walkthru, AI test users run real flows (signup, onboarding, dashboard, checkout up to payment) in the owner's own Chrome, report where they got stuck, plus SEO and passive security. Indie devs, small startups, agencies. -->

# Competitor matrix: Walkthru

Prices checked on 2026-09-24 unless noted.

Assumption: "Walkthru" features are taken from the repo as of commit 9db7e24. "Building" means implemented but not launched. "Planned" means not built.

## 1. Market landscape

| Name | Funding | Pricing (checked 2026-09-24) | Segment | Differentiator |
|---|---|---|---|---|
| [Meerkat](https://runmeerkat.com/) | Not found | Free: 10,000 signup credits + 3,000 a month. Pro $49/mo (25,000 credits). Team $199/mo (125,000). Extra 10,000 credits $20. [Pricing](https://runmeerkat.com/pricing). A run costs 30 to 75 credits per the pricing page but "about 1,000" per [its docs](https://runmeerkat.com/docs); the two pages disagree. | Startups, SMB | "AI personas try your sign-up, onboarding or checkout in a real browser"; findings carry across releases. |
| [CanaryUsers](https://www.canaryusers.ai/) | Not found | Free: 100 credits (about 2 deep scans). Starter $9/mo (logged-in flows, runs on every push). Pro $19/mo. Team $49/mo, 5 seats, session replays. [Site](https://www.canaryusers.ai/) | Indie devs, prosumer | "Find the bugs before your users do": a flock of AI users on every deploy. |
| [Swarm](https://www.useswarm.co/) | Backed by Afore Capital, KPMG, Leap Year per [its site](https://www.useswarm.co/); amount not found | Free: 5 lifetime runs. Startup $150/mo (20 live runs, 10 personas). Enterprise custom. | Startups, product teams | "Feedback in 10 minutes", with code fixes and drop-off analytics. |
| [Uxia](https://www.uxia.app/) | Not found | 1 free test, then custom plans (price not published). | Product and UX teams | Tests prototypes, live sites and logged-in flows with AI testers. |
| [Octomind](https://www.test-lab.ai/blog/ai-testing-pricing) (indirect: QA automation) | Not found | Basic $89/mo, Pro $589/mo (verified June 2026 by [test-lab.ai](https://www.test-lab.ai/blog/ai-testing-pricing)) | Engineering teams | Discovers flows, writes Playwright tests, fixes them when they break. |
| [Otterly.AI](https://www.frase.io/blog/the-10-best-ai-visibility-tools-in-2026) (indirect: GEO) | Not found | From $29/mo; with add-ons about $200 to $489/mo per [Frase](https://www.frase.io/blog/the-10-best-ai-visibility-tools-in-2026) | Marketers, agencies | Tracks and audits brand visibility in ChatGPT, Perplexity, Gemini, AI Overviews. |

## 2. Feature comparison

| Feature | Meerkat | CanaryUsers | Swarm | Uxia | Octomind | Otterly | Walkthru |
|---|---|---|---|---|---|---|---|
| AI users on a live site in a real browser | Yes | Yes | Yes | Yes | Partial (scripted tests) | No | Building |
| Logged-in flows | Yes | Yes (from $9) | Yes | Yes | Yes | No | Building |
| Uses the owner's own signed-in browser, no credentials shared | Unknown | Unknown | Unknown | Unknown | No | No | Building |
| Several personas per run | Yes | Yes | Yes (up to 10) | Yes | No | No | Partial (1 per run) |
| Step evidence (screenshots, transcript) | Yes | Yes | Yes | Yes | Yes | No | Building |
| Compare across releases | Yes | Partial (runs each push) | Unknown | Unknown | Yes | No | Planned |
| Runs on deploy or CI | Yes (per [Meerkat's own comparison](https://runmeerkat.com/ai-usability-testing-tools)) | Yes | Unknown | Unknown | Yes | No | Planned |
| Scheduled runs | Unknown | Unknown | Unknown | Unknown | Yes | Yes | Planned |
| SEO checks | Unknown | Unknown | Unknown | Unknown | No | Partial | Building (up to 50 pages) |
| Passive security hygiene | Unknown | Unknown | Unknown | Unknown | No | No | Building |
| GEO / AI search readiness | Unknown | Unknown | Unknown | Unknown | No | Yes | Planned |
| Free tier size | About 173 runs first month | About 2 deep scans a month | 5 runs, lifetime | 1 test | Not found | Not found | Instant Scan + 3 runs a month |

Meerkat's comparison article (2026-09-23) states that none of the persona tools it reviewed list SEO or security. It is Meerkat's own content, so treat it as a claim.

## 3. Positioning gaps

**Gap 1: one launch-readiness report that covers journeys, SEO, security and GEO.**
- Missing: persona tools report journey friction only. GEO tools audit content only and never try a flow.
- Why it matters: an indie founder before launch wants one answer to "is my site ready?", not four tools at $9 to $49 each.
- Build difficulty: low for GEO. The checks are deterministic: AI crawler rules in robots.txt, JSON-LD, llms.txt, answer-ready headings, server-rendered text. Walkthru already fetches all of this for SEO.
- Head start: Estimate: 2 to 4 months. A persona tool could bolt on a Lighthouse-style pass quickly, so the lead comes from shipping first and owning the "launch readiness" message, not from the technology.

**Gap 2: logged-in testing without handing over a password.**
- Missing: every competitor that confirms logged-in support runs in its own cloud browser. None of the pages checked say how they sign in. That usually means test credentials or session cookies given to the vendor.
- Why it matters: apps with magic links, SSO, 2FA or real customer data are painful or not allowed to test that way. Agencies cannot share client admin logins.
- Build difficulty: high, and already built (extension, redaction, safety model).
- Head start: Estimate: 6+ months. A competitor needs an extension, a Chrome Web Store review and a safety model for acting inside a real user session.
- Cost of this gap: an install step. Every competitor starts with a URL; Walkthru asks for an extension.

**Gap 3 (candidate): reports that never blame the site for the agent's own failure.**
- Walkthru grounds every UX finding in a step where something went wrong and marks its own safety stops. No competitor page makes a comparable claim. Unknown whether they need to. Treat it as a quality bar, not a headline.

## 4. Threat assessment

1. **CanaryUsers: high.** Same buyer (indie devs), price below ours ($9 Starter already includes logged-in flows and runs on every push), $19 Pro. Changelog not checked.
2. **Meerkat: high.** Its free tier is far larger than ours (about 173 runs in month one against 3), it carries findings across releases, and it publishes comparison content aimed at search traffic dated 2026-09-23, a sign of active iteration.
3. **Swarm: medium.** Funded, but priced at $150/mo for product teams, above our buyer. It would become high if it launched a sub-$20 plan.

## 5. Strategic recommendations

- **Position to own:** "The launch check for indie SaaS: one report on whether a stranger can sign up, whether Google and AI search can read you, and whether you leak anything, run in your own browser so logged-in flows work without sharing a password."
- **Feature to ship first:** GEO readiness inside the existing report. It is cheap, deterministic, fits the free-model budget, and no persona tool offers it.
- **Competitor to watch:** CanaryUsers. Same price band, same buyer. Adding SEO or GEO to its roast card would take it only weeks.

Saved to `founder/competitor-matrix.md`. Next: `/pricing-strategy`, `/validate-idea`.
