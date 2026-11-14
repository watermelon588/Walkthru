# AI answers: diagnosis and measurement proposal

Research checked 13 November 2026. Status: research and implementation specification, not a shipped change or a new live visibility study. [Competitive comparison](../founder/competitor-matrix.md).

Walkthru should sell an evidence-backed answer to: **For the buying questions relevant to my product, how often do selected AI services cite my pages, what do they say about my product, and what should I fix next?** It cannot measure every user's AI experience or guarantee inclusion. Paying for collection buys observations, not placement.

The recommended next step is a small, validated consumer-surface collection pilot. Keep the existing API experiments separately labelled. Do not add another headline score before the underlying observations are trustworthy.

## 1. What the application measures today

Inspection covers the current working tree, including pre-existing uncommitted work. No application files were edited for this research.

| Finding | Evidence | Consequence |
|---|---|---|
| It does not measure consumer ChatGPT, Perplexity, Claude or Google's AI surfaces. | `apps/api/app/citations.py:33-52`, `NOT_MEASURED`; `docs/citation-measurement.md` | An OpenAI-named model hosted by Groq is not evidence about ChatGPT. Current UI correctly discloses this. Preserve that honesty. |
| The web experiment is heavily customized. | `WEB_SYSTEM`, `citations.py:180`: one search, no opening pages, recommend products, under 150 words | This measures our constrained search assistant. Provider, retrieval policy and instructions all differ from consumer usage. |
| A matching name is credited without establishing the entity. | `citation_evidence.py:47-64,161-172` | Another product called TripVerse becomes “Named you.” Domain boundary checks are good, but cannot repair a bare-name collision. |
| Suggestions are homepage templates. | `citations.py:150-170`; `main.py:923-945` | There is no confirmed ICP, buying job, market, geography, factual product profile or query-demand provenance. “What is TripVerse?” is recognition, not discovery. Automatic scheduling can start before owner review. |
| A batch has one answer per prompt per engine. | `citations.py:256-264` | A snapshot cannot establish persistence. There is no within-prompt repeat estimate or confidence interval. |
| Aggregates default to all modes and both branded/unbranded prompts. | `CitationResults.tsx:16-53`; `citationMetrics.ts:3-19` | Branded questions and memory mentions can dominate the most visible numbers. Filters exist, but the default still answers the wrong question for acquisition. |
| Historical batches are not matched cohorts. | `citations.py:443-474` | Changed prompts, modes and completion rates can move counts without any visibility change. A UI caveat is not a comparable experiment. |
| Retrieval attribution fails too often to be useful. | Saved 31 October audit and expanded answers | The batch had 11 memory answers, correctly ineligible, and 11 Groq answers, only one with resolved citation measurement. Ten Groq answers were not measurable. Do not describe all 21 exclusions as parser failures. |
| `source_rank` follows retrieved-source order. | `citation_evidence.py:165-171`; local reproduction below | It can disagree with citation order in the answer. It must not be sold as a search rank. |
| Capacity cannot sustain broad tracking. | `DAILY` is 20 web attempts/day across the service | Theoretical maximum is 140 web attempts/week: 14 sites at 10 questions once/week, before retries and other pressure. At 20 questions daily, one site consumes the entire web allowance. These are code-default calculations, not measured provider entitlements. |
| GEO/citability scores are heuristics. | `geo_depth.py:190-210` gives 25 points each for four content patterns; `geo.py:254-267` scores discovery files | A 75/100 pattern score is not a 75% chance of citation. Keep technical checks and observed citations separate. |

The archived live audit already documented the wrong-entity result: the tracked domain was `tripverse-0.vercel.app`, but the answer described an iOS product and returned other TripVerse domains. This session reproduced the defect with the actual pure analyzer: a sentence about another TripVerse publisher returned `mentioned=true`. A separate fixture cited B before A while returning A before B in retrieval results; the analyzer assigned A `source_rank=1`.

References: [live audit](../LIVE_BETA_AUDIT_2026-10-31.md), [archived expanded answer](../evals/results/live-beta-audit-2026-10-31/citation-brand-answer.txt), [reproduction script](ai-citation-diagnostic.py). Archived evidence is from October, not a new November live test.

Retain the useful foundations: deterministic citation parsing, exact host boundaries, unresolved states, saved raw answer and historical context, bounded retries, lease fencing, quota admission, and exported source evidence. The fix is not a ground-up rewrite.

## 2. Define what is being counted

The unit is **one pre-scheduled prompt execution on one named surface, in one recorded market/language/session configuration, at one actual collection time**. It is an observation from a controlled panel, not a real customer impression.

| Observation | Count as an owned-site citation? | Separate meaning |
|---|---|---|
| The answer contains the brand's name | No | Lexical mention. Identity may be ambiguous. |
| Correct product is explicitly identified | No | Verified brand mention. May be positive, neutral, negative or mistaken about a feature. |
| The answer recommends the correct product for the buying job | No | Recommendation, requiring evidence in the answer. |
| Our URL occurs only in retrieved results | No | Retrieval observation. Even observed retrieval does not prove how much it influenced generation. |
| A visible citation marker/link is tied to our verified domain or page | Yes | Owned-site citation observed. Save the answer span and URL mapping. |
| A cited third-party page discusses us | No | Earned-source exposure; validate entity and passage separately. It is not an owned-domain citation. |
| Our link appears in an ad, navigation card or unrelated list | No, for the primary organic citation metric | Record its actual placement type. Do not relabel it as supporting evidence. |
| An AI referral arrives on our site | No | Observed visit. Useful business outcome, separately instrumented. |
| An AI crawler fetches our page | No | Bot access, not a user visit or a citation. |

Citation occurrence and citation correctness are different. A response may visibly cite a page that does not support its claim. Store `support_status=not_checked/supported/contradicted/unclear` separately; an extracted link alone never proves the claim is correct. Human review comes first for important product claims.

This distinction is supported by primary API contracts: OpenAI returns cited URL annotations separately from all consulted URLs; Gemini exposes grounding information; DataForSEO distinguishes search results from answer sources. Its description of sources includes both cited and relied-on material, so even that array needs an answer-level attribution check. [OpenAI web search](https://developers.openai.com/api/docs/guides/tools-web-search), [Gemini search](https://ai.google.dev/gemini-api/docs/google-search), [DataForSEO response contract](https://docs.dataforseo.com/v3/ai_optimization/chat_gpt/llm_scraper/live/advanced/).

## 3. Measure the intended surface

**Consumer-surface observations:** collect the actual ChatGPT website/search experience through a validated data supplier or deliberate manual captures. Record logged-in/out state, plan/model when observable, search setting, country and language. Default chat and explicitly forced Search are different panels. A supplier's claim to reproduce the UI is evidence of its advertised method, not independent validation.

**Official API observations:** OpenAI Responses with web search, Gemini grounding, or a Perplexity answer endpoint measure those API configurations. These are useful experiments with structured evidence, but must be labelled “OpenAI API web-search panel,” for example. They cannot silently replace a failed consumer collection job.

**Memory experiments:** keep outside citation reporting. They may help diagnose brand recognition or misinformation, but are a weak lead feature for newly launched companies.

No system can promise the exact experience of every user. ChatGPT documents that location and saved memories can change its search queries. Controlled sessions reduce variation but do not represent the entire user population. [ChatGPT search behavior](https://help.openai.com/en/articles/9237897-searching-the-web-with-chatgpt).

Never inject the customer's domain, homepage text, approved claims or a request to cite them into an unbranded measurement prompt. The private entity profile is for analysis after collection. A controlled “read this URL” diagnostic is useful, but belongs to a different experiment.

## 4. Calculation without false hope

For each surface, market, language, prompt version and date window, classify each scheduled slot as:

- `C`: proven owned-domain citation, even if an unrelated citation elsewhere is unresolved.
- `N`: complete, successfully parsed answer with proven absence of an owned-domain citation. A valid complete answer with no citations belongs here.
- `U`: unknown, including failure, blocking, truncation, unresolved target attribution or unobservable citation markup.

Then calculate:

```text
T = C + N + U                           # all scheduled slots
D = C + N                               # target-verifiable slots
observed citation frequency = C / D      # N/A if D = 0
measurement coverage = D / T
missing-data bounds = [C/T, (C+U)/T]
```

The bounds describe what unknown slots could contain; they are not a confidence interval. Never substitute unknown with zero, silently remove failed days, or condition the primary denominator on “answers that already cite something.” For Google AI Overviews, a successfully observed absence of the AI Overview is a valid zero for overall query-level AI citation presence; “citation share when an Overview appears” is a separate conditional metric.

Example: 10 cited, 70 confirmed not cited and 20 unknown out of 100 scheduled runs yields 12.5% among verifiable runs, 80% coverage, and missing-data bounds of 10% to 30%. Reporting just “12.5% visibility” hides material uncertainty.

Also calculate, separately:

- **Verified mention frequency:** entity-confirmed mentions divided by answers with resolved entity status. Show entity ambiguity coverage.
- **Prompt coverage:** eligible prompts with at least one citation / eligible prompts tested. Label this “observed at least once”; it does not establish repeatability.
- **Persistence:** distinct days with a citation / scheduled measurement days, accompanied by usable days and per-day sample counts. Display `1 citation on 1 of 30 days` plainly.
- **Citation share:** owned-domain appearances / all cited-domain appearances, deduplicating each domain once per answer. This is a different quantity from response frequency and is not market share.
- **Tracked-competitor mention share:** retain only with an explicit denominator and entity validation. Do not call it share of all industry conversation.
- **Referrals and conversions:** sessions arriving through observed AI referrers, then signup or other declared goals. Referrers can be missing, so this is a measurable subset, not total AI-influenced revenue.

For a fixed panel, report per-prompt results first. For a category aggregate, compute each prompt's frequency and average using fixed, declared weights. Do not let frequently retried or oversampled prompts dominate. Equal weights are acceptable when demand is unknown. Google search volume and third-party prompt-volume estimates are not actual consumer AI impression counts.

### Uncertainty and repeated sampling

An illustrative independent Bernoulli calculation gives 1 citation in 30 checks = 3.33%, with a 95% Wilson interval of approximately **0.59% to 16.67%**. Zero in 30 still has an upper Wilson bound of about **11.35%**. Neither supports “AI knows you” or “AI never cites you.” Formula and arithmetic are in the diagnostic script. [NIST proportion intervals](https://itl.nist.gov/div898/handbook/prc/section2/prc241.htm).

Those intervals assume comparable independent observations. Repeated prompts, related intents, cached responses and daily model changes violate that assumption. Do not present a pooled Wilson interval as certainty about all buyers. For a fixed panel's aggregate time trend, resample whole day blocks, keeping the prompt panel intact, and recompute the weighted metric. For comparisons, use matched prompts/configurations and day blocks in both windows. A category-generalization analysis additionally needs prompt/topic clustering and a defensible sample of prompts. With too few independent blocks, show descriptive counts and “insufficient evidence for a trend.”

A 2026 preprint studies repeated collections and finds meaningful citation variability. It supports repeated sampling and uncertainty reporting, not a universal “run N times” rule. Its three consumer categories, generated prompts, roughly nine-day observation window and API collection limit extrapolation to Walkthru's B2B customers and consumer ChatGPT. [Study and limitations](https://arxiv.org/html/2603.08924v3).

There is also an internal reporting inconsistency: its high-frequency methods/table include Gemini, while its limitations say Gemini was excluded. Treat this paper as supporting motivation for uncertainty analysis, not an independently validated sample-size prescription. The proposed panel and release gates below are our design choices, not thresholds established by that paper.

**Proposed product policy, not a validated industry threshold:** use a 28-day default report; permit a 14-day baseline view. Suppress improvement/rank badges while coverage is below 90%, the relevant panel has fewer than 14 distinct usable days, the configuration changed, or the interval of the matched difference includes zero. Predeclare a practical effect threshold per panel before testing; statistical significance alone is insufficient. Check sensitivity to missing-data bounds. These gates do not magically make a sample representative. Recalibrate after the pilot.

Do not stop collecting when the first favorable answer appears. Schedule the whole panel in advance. Run completion retries only for technical failures, record every attempt and select the first valid completion for the slot. Do not retry valid negatives. Repeated identical text from genuinely distinct uncached requests is legitimate; deduplicate delivery replays by request identity, not answer text alone.

## 5. Industry relevance and actions

Onboarding should confirm the product's canonical domain, aliases, same-name exclusions, product category, target buyer, geography/language, main buying jobs, three competitors and a few verified facts. Use already audited content as suggestions, then let the owner approve the profile and prompts before paid or scheduled collection.

Start with **20 prompts: 15 unbranded buying questions and 5 branded accuracy questions**, one relevant market and one consumer surface. These are proposed pilot numbers, not existing plan allocations. Source questions from owner/customer conversations, support questions, Search Console when connected, and actual product tasks. Record each prompt's source. Generated suggestions must be labelled as hypotheses.

For a travel-planning product such as the audited TripVerse, example hypotheses are:

- “Which trip planners combine a day-by-day itinerary, map and editable budget?”
- “What travel-planning apps help Indian couples plan a Japan trip in rupees?”
- “What are alternatives to Wanderlog for collaborative itinerary planning?”
- Branded panel only: “What does TripVerse at [verified domain] do, and can I plan before signing up?”

Verify that these are real product capabilities and customer jobs before using them. Do not turn them into factual marketing copy based on this report alone. For Walkthru itself, a relevant question is “How can a solo founder test signup and onboarding on an AI-built app before launch?” rather than “What is Walkthru?”

The useful output is a concrete work item:

> Across the selected buying-question panel, these comparison/documentation pages repeatedly receive citations. Your matching page lacks a clear answer about the required capability. Here is the cited passage, your current page evidence, a proposed factual edit, and the unchanged questions we will recheck after publication.

That example describes a workflow, not an observed competitor gap in this session. Each real recommendation must carry supporting observations, target URL, missing information, an owner-verifiable fix, and follow-up results. “It was cited” is not proof of why it was cited, and before/after association is not proof the edit caused a change.

For brand-new sites with no visibility, offer a technical and factual baseline before selling ongoing tracking: indexability, crawl access, server-delivered useful content, specific use-case/docs/pricing/comparison pages, and clear identity. Authentic independent coverage may help discovery, but paid mentions cannot guarantee organic AI citations. Google explicitly says no special AI text files or schema are required for AI features. OpenAI likewise does not guarantee placement. Treat `llms.txt` as optional tooling, not a citation remedy. [Google guidance](https://developers.google.com/search/docs/appearance/ai-features), [OpenAI search inclusion](https://help.openai.com/en/articles/9237897-searching-the-web-with-chatgpt).

Walkthru's strongest differentiated path is **buying question → cited landing page → factual fix → repeated measurement → test whether the visitor can complete signup**. This builds on its journey-testing capability. Citation tracking by itself is already crowded.

## 6. Do we need to pay upfront?

No payment can purchase a guaranteed organic citation. Collection access may require payment. Public prices below were checked on 13 November 2026; actual account availability, billing terms, data rights and endpoint behavior remain unverified.

| Route | What it measures | Advertised cost / upfront requirement | Recommendation |
|---|---|---|---|
| Manual consumer captures | The observed individual consumer session | May use an existing eligible account; labor and plan limits apply | Good for initial ground truth; not scalable monitoring. |
| Bright Data ChatGPT scraper | Vendor-collected consumer-surface responses | Product and pricing pages advertise 5,000 free records/month, no card; PAYG $1.50/1,000 records | First free candidate to validate. Verify the actual ChatGPT endpoint's allowance, freshness, output and restrictions before depending on it. [Product](https://brightdata.com/products/web-scraper/chatgpt), [pricing](https://brightdata.com/pricing/web-scraper). |
| DataForSEO LLM Scraper | Vendor-collected ChatGPT/Gemini interfaces | Standard $0.0012/result; priority $0.0024; live $0.004; $50 minimum top-up | Paid fallback candidate for asynchronous monitoring after quality validation. The top-up is a balance, not a $50 monthly subscription. [Rates](https://dataforseo.com/pricing/ai-optimization/llm-scraper), [minimum payment](https://dataforseo.com/help-center/minimum-payment). |
| OpenAI official web-search API | An API search configuration | $10/1,000 search tool calls plus model/search-content tokens. New prepaid accounts: minimum $5 purchase | Useful API research track; does not validate consumer ChatGPT visibility. [API rates](https://developers.openai.com/api/docs/pricing), [prepaid billing](https://help.openai.com/en/articles/8264644-setting-up-and-managing-prepaid-api-billing). |
| Gemini grounded API | Gemini API with Google Search | Free allowance and paid search/token pricing vary by model and billing tier | Do not infer all models' availability from the old repo comment. Inspect chosen model/account first. Does not measure AI Overviews/AI Mode. [Rates](https://ai.google.dev/gemini-api/docs/pricing). |
| Full GEO SaaS | Its own sampled panels, dashboards and workflows | See the six-vendor comparison | Useful to benchmark workflow or import licensed exports; do not assume a subscription grants data resale rights. |

DataForSEO's LLM **Responses** product is different from LLM **Scraper**: Responses calls underlying model APIs and adds their costs. Its $0.0006 base-task figure must not be mistaken for the total price of consumer ChatGPT observation. [Their billing explanation](https://dataforseo.com/help-center/how-the-price-for-using-llm-responses-endpoints-is-calculated).

### Collection-cost examples

Formula: `prompts × surfaces × markets × days × repeats`, then multiply by the exact endpoint's unit price. These estimates assume one billable result per run and that both selected surfaces use the stated price.

| Panel | Runs | DataForSEO standard | DataForSEO live | Bright Data PAYG equivalent |
|---|---:|---:|---:|---:|
| 20 prompts, 1 surface, 1 market, 14 days, 1/day | 280 | $0.336 | $1.12 | $0.42 |
| 20 prompts, 2 surfaces, 1 market, 30 days, 1/day | 1,200 | $1.44 | $4.80 | $1.80 |
| Same monthly panel, 3/day | 3,600 | $4.32 | $14.40 | $5.40 |

These are raw collection estimates before storage, retries if billable, validation, engineering, tax and support. A free tier can make the pilot collection bill zero, but is shared account capacity, not a per-customer entitlement. Ten customers on the 1,200-run panel need 12,000 results/month. Do not design margins around a temporary free allowance.

For OpenAI, 600 executions with exactly one search call each incur $6 in search-tool fees **plus tokens**. Reasoning can issue multiple calls. Capture actual usage receipts; do not quote the search fee as the total cost. A prepaid balance is not an instantaneous spending cutoff.

Recommendation: validate the advertised free consumer collector first. If it fails the evidence contract or is unavailable, the next concrete purchase to evaluate is a $50 DataForSEO balance with a bounded pilot. Do not buy a $95+ analytics subscription merely to collect the first few hundred observations. No purchase or activation was made in this session. Existing repo rules require approval to switch on paid services.

## 7. Exact implementation path

### Phase A: repair interpretation using existing data

Work in `citation_evidence.py`, `citations.py`, `citationMetrics.ts`, `CitationResults.tsx`, `Visibility.tsx`, and the MCP/export serializers.

1. Add `lexical_mention`, `entity_status=verified/ambiguous/other/absent` and evidence. A bare shared name cannot produce verified success. Exact owned-domain references establish ownership only for the corresponding reference; a domain elsewhere does not validate every product claim.
2. Default the acquisition view to unbranded prompts and one surface. Move memory and branded accuracy to separate views. Remove a blended headline percentage.
3. Use target-specific citation verdicts and coverage. A positive can be proven with one owned citation; a negative requires complete absence evidence. Preserve unknown states.
4. Add `prompt_set_version`, actual date-window filtering and comparable-panel identifiers. Prompt/profile/config changes start new cohorts; retain the old evidence.
5. Replace source-list position with actual answer citation position when observable, otherwise null.
6. Relabel heuristic citability as content checks. Remove any suggestion that discovery files or a checklist predict citation probability.

Initial additive interpretation fields can fit the existing result JSON. A durable scheduler schema should use the next unused numbered migration and reversible down migration after checking current schema state. Do not repurpose a migration already applied or collide with other work's pending cloud migration.

### Phase B: one consumer collector and a durable observation contract

Add a small provider adapter beside the existing engines, keeping collection and parsing separate. Reuse the queue, admission and usage machinery. Persist a scheduled slot key such as `(panel_id, prompt_version, surface, market, day, repeat_index)` and idempotent provider request IDs. New `surface` values must be explicit, e.g. `chatgpt_web_default`, `chatgpt_web_search`, `openai_responses_web`, `groq_browser_search`, `gemini_api_memory`.

Store:

```text
panel_id, prompt_id/version, exact_prompt, intent, brandedness, prompt_origin
entity_profile_version, owned_domains, tracked_competitor_version
surface, provider, collection_method, observed_model_or_unknown
requested_country/language, observed_country/language_or_unknown
session_mode, search_mode, configuration_hash
scheduled_at, captured_at, repeat_index, attempt_id, provider_request_id
raw_response_reference/hash, answer_text, available_html_or_capture
retrieved_urls[], citation_edges[{answer_span, raw_url, normalized_url,
  display_position, placement_type, attribution_method, entity_id_or_unknown}]
parse_version, parse_completeness, target_verdict, unknown_reason
support_status, usage_receipt, estimated_cost, actual_cost_if_supplied
```

Normalize IDNA/host case and tracking fragments without collapsing different pages. Treat customer deployments on `vercel.app`, `github.io` and similar shared hosts as separate tenants. Do not reduce ownership to the hosting provider's registrable domain. Keep raw URLs. Follow redirects only with an explicit safe, bounded, approved resolver; until resolved, preserve unknown destination. Retain historical redirect/alias mappings rather than changing old evidence when a destination changes.

For OpenAI API adapters, extract native cited-URL annotations rather than asking another LLM to invent citations. For consumer collectors, verify visible citation links/markers against supplied answer HTML or capture. A `sources` array, a generated `check_url`, or a vendor `cited=true` flag by itself is insufficient proof of a specific answer citation. A prompt URL can regenerate a different answer; save the actual returned payload.

Collector failure must not trigger a different surface under the same label. Record a gap. A challenge/block remains unavailable; Walkthru must not solve CAPTCHAs. Supplier eligibility, supported use and commercial display/retention rights are selection requirements, not assumptions established by a pricing page.

### Phase C: sampling and verification

Start with the approved 20-prompt panel, one country/language and one surface, one scheduled execution daily for 14 days; extend unchanged to 28 days. This is 280 then 560 observations, but only 14 then 28 observations **per prompt**. Do not imply 560 independent observations for every individual buying question. Add a predeclared second/third repeat on priority prompts if needed to assess within-day variability, without changing the unweighted interpretation of other prompts.

Before enabling customer-facing percentages, review at least 50 captured answers spanning positives, valid negatives, same-name cases and incomplete evidence. Manually inspect the supplier's exact captured artifacts. Separately compare a small matched set with independent consumer sessions for method differences, without expecting identical generated answers. Proposed engineering gates:

- Every positive has a clickable evidence reference, exact URL and surface/time provenance.
- Zero false positives on the labelled identity/citation edge-case fixture set. Report sample size; this is not proof of a zero population error rate.
- Demonstrate extraction precision/recall and measurement coverage against human-labelled captured answers. Set release thresholds before seeing the outcome; start with a precision-first policy and leave uncertainty visible.
- Blocked, truncated, retrieved-only, memory-only and duplicate-delivery samples pass the negative/unknown contracts.
- UI, export and MCP numerator/denominator agree for identical filters.
- Dates/cohorts, actual collection freshness, retries and model changes remain visible.
- Spending is reserved before dispatch, with per-tenant and platform caps, idempotency and a kill switch. Verify the currently inactive ledger/migration state before assuming those protections are live.

### Phase D: deliver the fix-and-recheck workflow

Add a source-gap view ranked by repeated evidence on relevant prompts. Each row connects the buying job, repeatedly cited URLs, the customer's matching page and a concrete verified content/technical action. Add claim review for incorrect pricing, capabilities and identity. Mark publication dates, retain the baseline panel, compare matched future windows, and track referrals/conversions separately. Use control topics/pages where feasible and describe causal conclusions cautiously.

Suggested UI copy:

> Your pricing page was cited in 3 of 28 checks for this question, across 3 days. ChatGPT web Search, English, India, [date range]. 28 of 28 observations were usable. This is a sampled panel, not the percentage of all ChatGPT users who see your site.

If coverage is poor:

> We could verify 1 of 11 search answers. There is not enough evidence to estimate citation frequency. Open the observations to inspect what was collected.

If there is one positive:

> One citation observed. Repeatability is not established.

## 8. Deliverable and verification limits

This research used official competitor product/help/pricing pages, provider contracts, Google/OpenAI discovery guidance, NIST methodology and an explicitly limited preprint. Public vendor capabilities are documented claims, not hands-on certification. Conflicting/localized pricing is identified in the comparison. No customer outcome, referral uplift or live provider quality was invented.

The local pure-code reproductions and numerical examples were executed successfully. The separate diagnostic file preserves them. No new provider account, paid API call, schema application, product fix, deployment or fresh multi-day panel was performed. Existing unrelated work remains intact.

The decision now is a product scope decision: build a trustworthy small panel with evidence and actions, then expand coverage only when the provider validation, demand and economics justify it. The existing constrained API snapshot can remain an explicitly experimental diagnostic; it should not be the main paid proof of AI discovery.
