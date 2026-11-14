<!-- /founder:competitor-matrix · 2026-11-13 · input: Diagnose Walkthru AI answers, compare competitors and design useful evidence-backed AI citation measurement. -->

# Competitor matrix: AI answer visibility

Checked 13 November 2026. This narrows the comparison to the AI answers feature. The [September journey-testing comparison](competitor-matrix-2026-09-24.md) is preserved. [Full diagnosis, formulas, costs and implementation plan](../docs/ai-citation-research-2026-11-13.md).

Assumption: Walkthru serves indie SaaS founders and small agencies. Its existing Groq search/Gemini memory tracker is Building; consumer-surface tracking is Planned. Competitor features below are documented vendor claims, not independently tested performance. Unknown means not established by the sources reviewed.

## Market landscape

| Product | Segment and differentiation | Published pricing checked today | Company context |
|---|---|---|---|
| [Peec AI](https://peec.ai/) | Marketing teams/agencies; prompt-level chats, source analysis and action workflows | Starter $95/month: 50 prompts, three models, daily collection, one project. [Pricing](https://peec.ai/pricing) | Founded date not independently established here. Announced $21M Series A in November 2025. [Company announcement](https://peec.ai/blog/we-raised-21m-series-a-to-help-brands-win-in-ai-search) |
| [Profound](https://www.tryprofound.com/) | Enterprise AEO/content teams; citation categorization, watched pages and marketing agents | Current page lists a free seven-day trial with 50 daily prompts and custom enterprise pricing. Do not reuse older $99/$399 quotes without confirmation. [Pricing](https://www.tryprofound.com/pricing) | Founded date not independently established here. September 2026 $180M Series D at $1.8B valuation. [Announcement](https://www.tryprofound.com/blog/series-d) |
| [OtterlyAI](https://otterly.ai/) | Solo marketers/small teams/agencies; accessible multi-engine prompt monitoring and GEO audits | Pricing page rendered €29/month Lite, 16 prompts/2,000 monthly credits/four engines. November 10 announcement quotes $29/$189/$489. Currency and engine allocation must be confirmed in checkout. [Pricing](https://otterly.ai/pricing/), [new packaging](https://otterly.ai/blog/new-pricing-choose-your-ai-search-engines/) | Product launched October 2024; December 2024 release described it as bootstrapped. Current funding not established. [About](https://otterly.ai/about), [launch](https://otterly.ai/blog/ai-search-monitoring-software/) |
| [Ahrefs Brand Radar](https://ahrefs.com/brand-radar) | SEO teams/agencies; combines custom question panels with a broad search-derived AI index | Custom tracking starts $50/month; individual AI index $199/month; all indexes $699/month. Products/allowances differ. [Product pricing](https://ahrefs.com/brand-radar) | Ahrefs media kit says founded 2010; about page describes it as bootstrapped. [Media kit](https://ahrefs.com/media-kit), [about](https://ahrefs.com/about) |
| [Semrush AI Visibility](https://www.semrush.com/solutions/ai-visibility/) | Existing SEO teams and agencies; prompt/source research connected to audit and content workflows | Current page shows Base $99/month/domain billed annually. Monthly checkout price not established here. [Pricing](https://www.semrush.com/pricing/ai/) | Founded 2008; current company page identifies it as an Adobe company. [Company](https://www.semrush.com/company/) |
| [Scrunch](https://scrunch.com/) | Midmarket/enterprise; prompt monitoring, page audits and agent-traffic/experience tooling | Starter $300 month-to-month or $250/month billed annually; 350 custom prompts. [Pricing](https://scrunch.com/pricing/) | Emerged from stealth in 2024; announced $15M Series A in 2025; company page records Sitecore acquisition in 2026. [About](https://scrunch.com/about/) |

## What each gets right

**Peec:** explicitly separates retrieved URLs from visibly cited URLs and brand visibility from source visibility. It documents UI collection for most engines, with separate API-based options. Its March 2026 changelog describes URL-level history and corrected source metrics. Copy the evidence drill-down and collection labels. Do not adopt marketing statements that retrieval proves authority or influence. [Method](https://peec.ai/ai-instructions), [changelog](https://peec.ai/changelog).

**Profound:** categorizes sources into owned, competitor and external types, tracks individual pages, and connects source gaps to content work. Its documentation reveals a consequential denominator: brand visibility is conditioned on responses containing at least one brand. Walkthru should state its own denominator instead of treating vendors' percentages as interchangeable. [Citation workflow](https://www.tryprofound.com/features/answer-engine-insights/citations), [definitions](https://help.tryprofound.com/articles/3443229936-answer-engine-insights-overview).

**Otterly:** makes recurring collection and link analysis accessible to smaller teams. Its November 2026 change makes engine selection and prompt credits explicit. Copy budget transparency and restrained setup; a broad logo list alone does not validate measurement quality. [Current packaging](https://otterly.ai/blog/new-pricing-choose-your-ai-search-engines/), [included features](https://otterly.ai/pricing/).

**Ahrefs:** distinguishes its existing index from a customer's chosen questions and explains refresh frequency/location. This is especially relevant to new products whose niche may barely appear in a broad index. Copy custom panels and demand provenance, not the implication that modeled prompt volume equals actual AI users reached. [Custom tracking](https://help.ahrefs.com/en/articles/13192745-how-to-set-up-custom-prompts-to-track-brand-visibility-in-ai-assistants), [product](https://ahrefs.com/brand-radar).

**Semrush:** brings questions, source opportunities and suggested actions into a workflow alongside established SEO data. That helps a user decide what to change. Copy the question-to-source-to-action connection. [Prompt tracking](https://www.semrush.com/kb/1503-prompt-tracking), [feature overview](https://www.semrush.com/kb/1626-ai-visibility-features).

**Scrunch:** exposes exact prompt answers and cited URLs, with branded/nonbranded, persona, funnel, country and ownership filters. This is much closer to answering an actual customer's buying question than a single name counter. [Citation guide](https://scrunch.com/how-tos/how-to-track-citations-in-ai-search/).

## Feature matrix

Yes means documented; Partial means narrower or conditional. A vendor's statistical treatment or collection method is Unknown when not verified, even when its marketing offers a visibility score.

| Capability | Peec | Profound | Otterly | Ahrefs | Semrush | Scrunch | Walkthru |
|---|---|---|---|---|---|---|---|
| Owner-selected prompts | Yes | Yes | Yes | Yes | Yes | Yes | Building |
| Recurring observations | Yes | Yes | Yes | Yes | Yes | Yes | Building, weekly snapshot |
| Explicit UI/API collection distinction in reviewed docs | Yes | Unknown | Unknown | Unknown | Unknown | Unknown | Building, API-only labels |
| Individual cited URL drill-down | Yes | Yes | Yes | Yes | Yes | Yes | Building, sparse resolved evidence |
| Own/competitor/external source analysis | Yes | Yes | Partial | Yes | Yes | Yes | Building, limited brands/raw sources |
| Source-to-content action workflow | Yes | Yes | Yes | Partial | Yes | Yes | Planned |
| Country selection | Yes | Yes | Yes | Yes | Yes | Yes | Planned, locale unspecified |
| Source history over time | Yes | Yes | Yes | Yes | Yes | Yes | Building, batch totals only |
| Published uncertainty interval in reviewed product docs | Unknown | Unknown | Unknown | Unknown | Unknown | Unknown | Planned |
| Fix handoff connected to actual signup-journey testing | Unknown | Unknown | Unknown | Unknown | Unknown | Unknown | Planned integration, journey capability exists |

Sources: vendor methods/guides linked immediately above; Peec [pricing](https://peec.ai/pricing), Profound [filters](https://help.tryprofound.com/articles/5194011335-interpret-answer-engine-insights-v2), Otterly [plan details](https://otterly.ai/pricing/), and Walkthru's [measurement contract](../docs/citation-measurement.md). Unknown is not a claim competitors lack the capability.

## Positioning opportunities

These are product opportunities inferred from the reviewed material, not proven exclusive market gaps.

1. **Decision-quality evidence for tiny brands.** Treat same-name ambiguity, collection failure and one-off citations as first-class states; provide understandable repeatability. Difficulty medium. Estimated differentiation lead one to three months, because established vendors can add presentation changes quickly. Data quality and trust are the advantage.
2. **A developer-ready repair loop.** Link the buying question to cited pages, a verifiable edit and a code-agent handoff; measure again with the same panel. Difficulty medium with existing fix-prompt infrastructure. Estimated integration lead two to four months, not a defensible monopoly.
3. **Discovery plus working conversion.** After identifying the cited landing page, test whether a stranger can complete its signup/onboarding. Difficulty high because reliable browser testing remains unresolved. Estimated lead several months, conditional on fixing Walkthru's agent evidence problems. Do not position an unfinished journey capability as certified conversion validation.

## Threat assessment

1. **Otterly: high for this feature's budget buyer.** Close segment overlap and low entry pricing; the November 10 packaging release demonstrates current iteration. Its last verified bootstrapped disclosure is dated, so present resource advantage as its established product breadth, not an invented funding figure.
2. **Peec: high for agencies and expanding SMB teams.** Funded, explicit collection methodology, daily prompts and a continuing changelog. It already covers much of a generic citation dashboard.
3. **Scrunch: medium for current indie buyers, high for the longer workflow.** More expensive, but page/agent analysis overlaps our proposed discovery-to-conversion direction; Sitecore ownership expands distribution resources. Acquisition and product breadth are not proof of a specific future roadmap.

Profound is a strong enterprise reference but a less immediate price/segment rival. Ahrefs and Semrush have distribution and data advantages; replacing their full suites is not a credible first goal.

## Recommendation

Own **“AI discovery evidence and fixes for small web products”**, connected to Walkthru's launch/journey workflow. First ship trustworthy entity and citation evidence, then a small validated consumer-surface panel. The first differentiated deliverable should be one useful, source-backed page fix with a predeclared recheck, not another composite score.

Watch Otterly for packaging and Peec for collection/source workflows. Compare with their actual products during a later pilot; this desk research does not certify their parser precision or customer outcomes.

Saved to `founder/competitor-matrix.md`.
