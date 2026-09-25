<!-- /founder:validate-idea · 2026-09-24 · input: Walkthru as built, AI test users in the owner's own Chrome plus Instant Scan (SEO, security, first impression); indie devs, small startups, agencies; pre-launch, launch Oct 20 2026, no paying users, solo founder, free LLM providers. -->

# Idea validation: Walkthru

Assumption: the product works as in commit 9db7e24: real-browser journeys, grounded reports, Instant Scan, and no billing yet.

## 1. The 30-second assessment

The problem is real. People who ship apps they built with AI really don't know where strangers get stuck, and UserTesting proved companies pay to find out ([$1.3B acquisition, 2022](https://www.thomabravo.com/press-releases/usertesting-to-be-acquired-by-thoma-bravo-and-sunstone-partners-for-1.3bn)). But in 2026 "AI users test your site" is a crowded category, not a new one. As built, Walkthru is a well-made version of what CanaryUsers sells for $9 and Meerkat gives away free. The technology is not the risk. Distribution and a sharper reason to pay are.

## 2. The five fatal questions

**Q1: Who is the customer, and would they pay today?**
- **The person:** a solo founder or two-person team, 0 to 3 months from launch, with a signup and onboarding flow they built with Cursor or Lovable. No designer and no QA. Lovable alone was near 8 million users by November 2025 ([Wikipedia](https://en.wikipedia.org/wiki/Lovable_(company))).
- **Willingness to pay:** Estimate: $9 to $19 a month. That's what CanaryUsers charges this exact buyer ([site](https://www.canaryusers.ai/)), and indie founders already pay similar amounts for single-purpose tools.
- **Would they pay today?** Once, around launch: likely. Every month: only if something brings them back (reruns after deploys, alerts). Walkthru has not built any of those yet. So today it's "maybe", which by this skill's rule is a no for the subscription.

**Q2: Why hasn't someone built this already?**
- They have: [Meerkat](https://runmeerkat.com/), [CanaryUsers](https://www.canaryusers.ai/), [Swarm](https://www.useswarm.co/) (backed by Afore Capital), [Uxia](https://www.uxia.app/), and at the high end [Synthetic Users](https://www.syntheticusers.com/pricing) from $12,500 a year.
- **What changed:** browser agents became cheap and reliable in 2025 and 2026, so the category opened for everyone at once. None of these tools has won yet. That's the opening, and also the danger.
- **Walkthru's real differences** (see `founder/competitor-matrix.md`):
  - It runs in the owner's own signed-in browser, so no password is shared.
  - The report also covers SEO and security.
  - Findings are grounded and never blame the site for the agent's own stops.
  - The first two are real. The third is invisible until a buyer has been burned by another tool.

**Q3: What's the distribution advantage?**
- **The first 100 users:** Instant Scan needs no install. Post free scans for other people's launches on Indie Hackers, r/SaaS, r/SideProject and Product Hunt launch days. Each shared report is an ad.
- **Growth loop:** the loop exists but is weak today. It becomes a real loop if public reports carry "Tested by Walkthru" with a backlink (CanaryUsers already gives a dofollow backlink at $9) and if the Instant Scan result is fun to share.
- **Red flag:** the paid product needs a Chrome extension. Every competitor starts from a URL. Expect a large drop between "scanned" and "installed and ran a test". Measure it before anything else (experiment 2).

**Q4: Can this be a big business, or is it a feature?**
- **Feature risk: high.** Vercel, Lovable or a testing platform could add "AI users try your preview deploy" as a button. Meerkat and CanaryUsers already treat it as a whole product.
- **Natural ceiling as a solo indie product:** Estimate: 2,000 paying users × $25 blended ARPU × 12 months = $600K ARR. That's a strong one-person business, not a venture-scale one.
- **For $1M ARR:** about 3,300 customers at $25/mo, or an agency plan at $99+/mo. Agencies are the most likely route, because white-label reports get resold to their clients.

**Q5: Can the founder build it?**
- It is already built. The hard parts work: agent safety, grounding, extension, database over HTTPS, and free-model failover.
- **Hardest remaining challenge: operations, not code.**
  - Free-provider capacity is about 110 full runs a day across all users (estimate in `founder/pricing-strategy.md`).
  - Chrome Web Store review.
  - Billing without a credit card (payment.md).
- **No first-hire problem.** The gap is sales and distribution experience, which the founder has said they lack.

## 3. Idea scorecard

| Dimension | Score | Notes |
|---|---|---|
| Problem severity | 3 | Real, but it hurts around launch, then fades |
| Market size | 4 | Millions of people building with AI; agencies too |
| Willingness to pay | 2 | Indie buyers are price-sensitive; competitors anchor at $9 with free tiers of about 170 runs |
| Competition gap | 2 | At least 4 direct competitors; gap only in the combined report and running without credentials |
| Distribution | 3 | Instant Scan is a good hook; the extension step is friction |
| Timing | 4 | AI-built apps plus the move from search to AI answers (GEO) both peak now |
| Founder fit | 3 | Proven builder who ships fast; little industry or sales experience, no budget |
| **Total** | **21/35** | Promising, with gaps. Fix willingness to pay before building more features. |

## 4. Validation experiments

These test demand for what's already built. No new code is needed.

**1. Will anyone pay once?**
- **Test:** 5% of people who get a free Instant Scan will pay $9 for the Launch Pack.
- **How:**
  1. Post 30 free scans of real launches in Indie Hackers, r/SaaS and r/SideProject threads over 10 days.
  2. Under each report, add one line: "Want AI users to test your signup and dashboard? Founding Launch Pack, $9."
  3. Take payment through a manual Dodo payment link or UPI.
- **Success:** at least 5 paid out of the first 100 scans.
- **Time and cost:** 10 days, $0.

**2. Does the extension kill the funnel?**
- **Test:** at least 25% of people who click "Run a real test" install the extension and finish a run.
- **How:**
  1. Load the extension unpacked for 20 beta users from experiment 1.
  2. Send each the same 3-line install guide.
  3. Count each stage from the run table in Supabase: clicked, installed, first run finished.
- **Success:** 5 or more of the 20 finish a run within 48 hours.
- **Time and cost:** 7 days, $5 (Chrome Web Store fee).

**3. Is GEO the stronger hook?**
- **Test:** "Can ChatGPT read your site?" gets 1.5x more Instant Scan starts than "Find where users get stuck".
- **How:**
  1. Post the same free-scan offer twice in two comparable communities, one headline each.
  2. Or run a $100 split on Reddit ads.
  3. Count scan starts per headline using a query parameter.
- **Success:** the GEO headline gets 1.5x or more scan starts.
- **Time and cost:** 7 days, $0 to $100.

## 5. The honest verdict

**Pivot it: not the code, the angle.**

Stop selling "AI test users". Four funded or cheaper tools already say that. Sell **"the launch check for apps built with AI: can a stranger sign up, can Google and ChatGPT read you, and are you leaking anything. It runs in your own browser, so your logged-in pages get tested without sharing a password."** The journey testing stays the core. GEO and security make the story different, and reruns and alerts make it a subscription.

**This week:** run experiment 1 using the Instant Scan you already have. If fewer than 5 of 100 scans convert at $9, no feature list will save the paid plans, and you'll know before building billing.

Saved to `founder/validate-idea.md`. Next: `/go-to-market`, `/landing-page`.
