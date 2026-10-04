<!-- /founder:pricing-strategy · 2026-10-04 · input: Founder proposes subscription plus pay-as-you-go usage and safeguards for every integration. -->
# Pricing proposal: workspace plus capped usage

Assumption: current actual catalog remains $19 Pro/$49 Plus with founding prices, fixed runs and founder-approved 30-day passes. This is a draft replacement to validate, not activation.

## Model comparison

| Model | Fit / 5 | Benefit | Risk |
| --- | ---: | --- | --- |
| Flat subscription | 2 | Predictable bill | Variable-depth missions have unequal cost |
| Usage based | 4 | Funds deeper work | Surprise bills unless prepaid/capped |
| Per seat | 2 | Helps agencies | Solo buyers do not buy seats as value |
| Freemium | 3 | Lets evidence demonstrate value | Premium trial needs funded abuse limits |
| Credits | 4 | Caps liability and supports multiple workloads | Confusing if raw tokens or dozens of units |
| One-time purchase | 4 | Matches occasional launches | Does not prove retention |

**Recommend workspace access plus prepaid service usage, with a no-subscription PAYG route.** Every job shows scope, expected charge and hard maximum. Basic evidence and acceptance tests are included. Do not make the user buy an add-on to understand a finding.

## Draft tiers

| Tier | Price | Usage | Concrete access |
| --- | ---: | ---: | --- |
| Explore | $0 | Bounded trial, actual cap from measured cost | 1 project; technical inventory; sample dossier; no unlimited premium use |
| Pro | $29/30 days | $10 service balance per period | 2 projects; saved missions; comparisons; manual reruns; 30-day evidence target; scoped API/MCP; 1 active mission |
| Plus | $79/30 days | $35 service balance per period | 5 projects; up to 3 seats; shared suites/board; branded exports; 90-day evidence target; per-key caps; public monitoring; at most 2 active missions after capacity tests |

PAYG: minimum proposed $10 top-up, one project and one active job; users can buy more usage without subscription. Higher-tier upgrade triggers are collaboration, project count, retention and repeated release coordination. Depth consumes prepaid balance on either tier.

Potential later annual Pro $290/Plus $790: 16.7% discount, grants issued monthly. Do not sell annually before measured costs and retention. Start reviewed 30-day access; recurring opt-in is a separate launch decision. Preserve existing entitlements and verified founding commitments.

Included grants expire at the period end as a proposed policy. Purchased grants remain usable during the pilot without subscription. Publish eventual expiry/refund terms before purchase; no automatic top-up/overage initially. API keys authorize wallets, they are not money or provider-token credits.

## Current competitive context

Checked 2026-10-04, provider-published terms:
- [Checkly](https://www.checklyhq.com/pricing/): Starter displayed $24/month billed annually; free browser monitoring exists.
- [BrowserStack pricing](https://www.browserstack.com/pricing/): Test Companion Individual $25/Pro $99 monthly billed annually. Different from Low Code agentic-test pricing.
- [Screaming Frog](https://www.screamingfrog.co.uk/seo-spider/pricing/): paid £199/$279 USD annually per user; 500-URL free crawl.
- [PostHog replay](https://posthog.com/session-replay): 5,000 recordings free monthly, then starts $0.005/recording.

These are different products/units. They anchor substitute pressure, not a proven Walkthru price. A $19 mission pilot should precede $29 recurring sales.

## Economics

Estimate: usage catalog charges 5 times fully loaded variable cost, including models, retries, storage/egress and compute. One service dollar is not one provider dollar. No deep-mission invoice has been measured.

Illustrations: $0.25 variable cost -> $1.25 job; $1 -> $5; $2.50 -> $12.50. The accepted quote caps charges and pins a catalog version. Sonnet pricing is $2/$10 per million input/output on Google global, but billed reasoning and context vary. [Google pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing).

Using historical payment.md fee assumption 4%+$0.40, not a current verified fee:
- $10 top-up: $0.80 fee, $2 work, $7.20 contribution before shared fixed costs.
- Pro: $29 - $1.56 fee - $2 included work - assumed $2 allocated infrastructure - $6 support = $17.44 contribution, 60.1%.
- Plus: $79 - $3.56 - $7 - $6 - $12 = $50.44, 63.8%.

At assumed $100 remaining shared monthly overhead: 6 Pro or 2 Plus customers cover it. Hypothetical 70/30 mix: $44 subscription ARPU and $27.34 contribution. Do not double count infrastructure allocations. Human review, refunds, tax/account-specific fees and expensive workloads can erode margins. Actual current values unknown. Thirty minutes concierge review at assumed $20/hour adds $10/job.

## Presentation and rollout

1. Show the mission's outcome and maximum price, with settled usage afterward. Avoid raw token shopping.
2. Plus is an honest capability anchor, not a fabricated decoy; PAYG is the trial for infrequent buyers.
3. Keep annual framing dormant until recurring value is proven.

First 90 days: reviewed pilots, then optional access passes/top-ups after atomic ledger and paid-model gates. Later subscription price increases require measured cost/value and explicit terms. Existing purchased/founding commitments must be audited and honored, never silently converted. Dodo credit billing is asynchronous and does not enforce service blocking; our local reservations do. [Credit docs](https://docs.dodopayments.com/features/credit-based-billing).

Full schema/settlement and migration plan: [plan.md](../plan.md). Saved to founder/pricing-strategy.md. Next: mvp-scope, metrics-dashboard.