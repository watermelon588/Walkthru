<!-- /founder:pricing-strategy · 2026-09-24 · input: Free / Launch Pack $9 / Pro $15 / Team $39 as in SPEC.md; founder wants GEO in Pro; free LLM providers only; paid run cost ceiling $0.20; Dodo 4% + $0.40. Would a buyer pay, and what should Pro and a Plus tier include beyond volume? -->

# Pricing strategy: Walkthru

Assumption: paid runs use the free model chain unless a paid model is added. $0.20 is the worst-case cost of a paid run (payment.md), not a measured average.
Assumption: payment.md's V1 rule stands. "Monthly" plans are sold as 30-day passes, approved by the founder, with no auto-renewal until the V2 gate.

## 1. Pricing model analysis

| Model | Fit | Pros | Cons |
|---|---|---|---|
| Flat subscription | 4 | Simple, predictable revenue, matches "keep my site working" | Heavy users can cost more than they pay unless runs are capped |
| Usage-based | 2 | Cost tracks revenue | Indie buyers fear surprise bills; Dodo's $0.40 fee per charge punishes small top-ups |
| Per-seat | 1 | Standard for teams | Buyers are solo founders; seats don't match value |
| Freemium | 5 | The report is the demo; Instant Scan needs no install | Free runs use up free-provider capacity (section 4) |
| Credits | 3 | Meerkat and CanaryUsers use them, so buyers know them | Two competitors disagree on what a credit buys; confusing for a first-time buyer |
| One-time purchase | 3 | Suits "I launch Tuesday" | Nothing brings the buyer back |

**Recommendation: freemium with flat plans that include a run allowance, plus the one-time Launch Pack.** Because the buyer is a solo founder who wants a fixed price, a run count is easier to understand than credits, and the one-time pack captures people who ship once.

## 2. Tier design

The rule for every tier: **free reports are exactly as good as paid ones.** Paid plans unlock *where* the test can go and *what happens over time*, not a better answer. A weaker free report would destroy the trust that sells the paid plans.

### Free: $0
- Instant Scan, no install: first impression, SEO basics, security headers, and **GEO basics**: are AI crawlers (GPTBot, ClaudeBot, PerplexityBot) allowed, is there structured data, is the text readable without JavaScript
- 3 test runs a month, public pages, 1 persona, 12 steps
- Full report quality, share link
- **Upgrade trigger:** "the test stopped at my login screen" or "I fixed it, did it work?"

### Pro: $19/mo, or $190/yr (17% off, "2 months free")
- **Logged-in flows in your own browser**: onboarding, dashboard, settings, checkout up to payment. No password is shared with Walkthru.
- **Rerun and compare**: every finding marked fixed, still broken or new
- All 4 personas, 30 steps a run, 40 runs a month
- Full-site SEO **and GEO readiness** up to 50 pages: AI crawler rules, JSON-LD per page type, answer-ready headings, content visible before JavaScript, an llms.txt check (reported as low impact)
- Security hygiene on verified domains, including exposed files and leaked keys
- One real form send on your verified domain, after you confirm it
- PDF report with step screenshots
- **Upgrade trigger:** a second site, a client, or forgetting to rerun after deploys

### Plus (replaces Team): $49/mo, or $490/yr (17% off). Self-serve.
- **Weekly automatic reruns** with an email only when something breaks or gets fixed
- **GEO and SEO watch**: a weekly alert when a deploy blocks an AI crawler, drops structured data or empties the pre-JavaScript HTML
- 5 sites, 150 runs a month, 3 seats sharing reports
- **White-label PDF** (agency logo, no Walkthru branding)
- Custom personas ("a 60-year-old first-time buyer on a phone")
- **Upgrade trigger:** more than 5 sites, CI or API access, or SSO. That is an enterprise conversation, not a fourth self-serve tier.

**Launch Pack: $9 once.** Everything in Pro for 30 days, 20 runs. Keep it as the risk-free way to try Pro.

### Where the founder's current plans are wrong
- **Pro at $15 as a list price is too low.** It already sits above CanaryUsers' $9 Starter, so being cheap doesn't win. And it leaves $14.00 after Dodo's fee against a worst case of $12.00 in model cost for 60 runs (payment.md). Use $15 only as the founding price (section 6).
- **Team at $39 with 250 runs loses money** if runs cost $0.20: $37.04 net against $50.00 in cost. Fewer runs and more automation (weekly reruns) gives buyers more value at lower cost.
- **"GEO in Pro" is right, but a GEO taste belongs in Free.** GEO checks need no LLM calls, so they cost nothing to run, and "Can ChatGPT read your site?" is a stronger reason to try Instant Scan than anything SEO says in 2026. Keep full-site GEO in Pro and GEO monitoring in Plus.
- **Don't sell AI citation tracking yet** ("does ChatGPT mention you for these prompts"). It costs model and search calls on every check, and Otterly already sells it from $29/mo ([Frase, 2026](https://www.frase.io/blog/the-10-best-ai-visibility-tools-in-2026)). Readiness is the Walkthru job; tracking can come later as a Plus add-on.

## 3. Competitive pricing context

Prices from `founder/competitor-matrix.md`, checked 2026-09-24.

| Competitor | Price | Includes | Walkthru position |
|---|---|---|---|
| [CanaryUsers](https://www.canaryusers.ai/) | $9 Starter, $19 Pro, $49 Team | Logged-in flows and runs on every push from $9 | **Same price at $19**, because Walkthru adds SEO, GEO and security that CanaryUsers doesn't list, and needs no credentials |
| [Meerkat](https://runmeerkat.com/pricing) | Free (large), $49 Pro, $199 Team | Personas, findings carried across releases | **Below**, because the buyer is a solo founder, not a product team |
| [Swarm](https://www.useswarm.co/) | $150 Startup | 20 live runs, 10 personas, code fixes | **Well below**, different buyer |
| [Otterly.AI](https://www.frase.io/blog/the-10-best-ai-visibility-tools-in-2026) | From $29 | GEO audit and AI visibility tracking | **Plus at $49 replaces a $29 GEO tool plus a $19 persona tool**. That's the bundle pitch. |

## 4. Unit economics

**Costs**
- Estimate: $5/mo for a VPS if Oracle Always Free doesn't work, plus about $1.25/mo for a domain ($15/yr). Supabase, Vercel and Resend at $0 on free plans. Fixed cost is about $6.25/mo.
- Model cost on free providers is $0, but capacity is capped. Estimate: 3 Groq models × 1,000 requests a day ÷ about 27 calls per 25-step run = about 110 runs a day for all users combined. That's about 3,300 runs a month. Free capacity, not money, is the first limit.
- Dodo fee: price × 4% + $0.40.

**Margin by tier.** The "likely" column assumes Estimate: $0.05 average per run, mostly free chain with occasional paid escalation.

| Tier | Price | Net after Dodo | Worst case (runs × $0.20) | Margin, worst | Likely model cost | Margin, likely |
|---|---|---|---|---|---|---|
| Launch Pack | $9 | $8.24 | $4.00 | 47% | $1.00 | 80% |
| Pro | $19 | $17.84 | $8.00 | 52% | $2.00 | 83% |
| Plus | $49 | $46.64 | $30.00 | 34% | $7.50 | 80% |

(Margin = (net − model cost) ÷ price. Hosting is ignored per customer because it is fixed.)

**Break-even**
- Hosting: 1 Pro customer covers $6.25.
- A $1,000/mo founder income needs $1,000 ÷ $15.84 (Pro net minus likely model cost) = **64 Pro customers**, or 26 Plus customers.
- **Target blended ARPU:** 80% Pro and 20% Plus gives 0.8 × $19 + 0.2 × $49 = **$25/mo**.

## 5. Pricing psychology

- **Anchor:** show Plus at $49 to the right of Pro, with "replaces a GEO tool and a UX test tool". That makes $19 look small. Because buyers compare against the most expensive visible option.
- **Decoy:** the $9 Launch Pack. It is 20 runs once, with no weekly reruns and no reruns next month. A buyer who expects to deploy again sees that $19 a month is the better deal. Because the pack's missing "over time" features are exactly what Pro sells.
- **Annual framing:** "2 months free" instead of "17% off". Because a concrete count is easier to value than a percentage. Only offer annual after V2 self-serve billing exists, since V1 passes don't auto-renew.

## 6. Launch vs. scale pricing

- **Launch price (first 90 days):** Pro at **$15**, as a "founding price, locked for 12 months", for the first 50 approved customers. Plus at $39 on the same terms. Because early buyers take a risk on an unproven tool and give feedback, and 50 is a small enough cost exposure for the founder-approved V1.
- **Grandfathering:** founding customers keep their price for 12 months from purchase while their pass stays active. Give 30 days' email notice before it ends.
- **Raise prices to the list price ($19 and $49) when all three are true:**
  1. 20 paying customers with monthly churn under 8%.
  2. Instant Scan to paid conversion above 3%.
  3. Weekly reruns and GEO watch have shipped.

  **Then consider Pro at $24 when** 30% or more of Pro customers use 30+ runs a month. That means they value volume and the price is below what the product is worth to them.

Saved to `founder/pricing-strategy.md`. Next: `/validate-idea`, `/landing-page`.
