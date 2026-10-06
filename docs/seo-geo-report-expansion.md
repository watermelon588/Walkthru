# SEO, GEO, report structure and efficiency extension

Date: 2026-10-04. Founder direction supplements [the product plan](../plan.md) and [session workflow](restructure-sessions.md). This document records an SEO/GEO/efficiency audit and proposed acceptance criteria, not newly shipped growth capabilities. R-S1, R-S2, R-S3, R-S4, R-S5 and R-S14a are complete; R-S5a, R-S6, R-S7, R-S7a, R-S8 and R-S18 are complete locally; R-S9 is next (status updated 2026-10-06). The [report version contract](report-v2-contract.md) records legacy consumer compatibility. The workflow has 24 planned slices, twelve complete; the growth suffix slice R-S17a remains pending. Cache reuse is recorded in [the reuse contract](scan-reuse.md). The chapter contract is recorded in [the report contract](report-v2-contract.md#chapters-r-s5a). [Performance attribution evidence](performance-attribution.md) is recorded separately. Database history/count evidence is [recorded separately](database-history-queries.md), as is [bounded task completion](task-completion-contract.md).

## Product boundary and judgment

Walkthru should deliver a scoped launch assessment with a practical repair and growth direction. Better keywords, evidence and readable chapters add value. A long list of generic tactics does not. Choose applicable recommendations from the site's actual product, pages, audience and available data, and explain why each matters.

Keep the launch assessment finite. Do not turn it into an autonomous outreach, CMS publishing, link-exchange or full-web backlink indexing service. A prelaunch product can suggest useful assets before any search traffic exists; measuring traffic or earned citations requires later data. Completing this work establishes a defined SEO/GEO offering, not permanent coverage of every future search behavior.

## Current implementation audit

Source inspection, not a live database/deployment audit. R-S1/R-S2/R-S3 application verification is recorded separately in the workflow; this planning audit does not imply paid inference, regenerated stored reports or completed SEO/GEO additions.

| Area | Shipped behavior | Remaining work |
| --- | --- | --- |
| Repeated public scan | `db.recent_public_scan` reuses a completed anonymous/public/free report for the exact normalized URL, for ten minutes from run creation; `/scans` checks it before new work | R-S7a added `scan_version` invalidation, `reused`/`coalesced`/`fresh` labels, `fresh: true` checks and single-flight misses ([contract](scan-reuse.md)); browser/authenticated/MCP/watch work is intentionally never reused |
| Duplicate work | Request idempotency and an already-saved report guard avoid repeat execution in their existing paths | Distinguish replay from a deliberately fresh test; crash after inference but before persistence can still repeat work |
| LLM prefix cache | Runtime caches clients/graphs, not model answers; no explicit provider cache setup or durable cache-token ledger is present | Provider-supported prefix reuse and actual hit/input/output/write accounting; do not assume automatic provider caching never occurs |
| Indexes | Migrations define owner-history, job/queue, team and citation indexes, including `runs_user_created(user_id, created_at desc)` | Match actual filters/order to indexes; validate applied schema and query plans before proposing new indexes |
| Pagination | R-S14a owner history now uses slim timestamp/ID keyset pages; MCP filters and limits in the database. Team chat/events keep ID cursors; citation detail history remains bounded | Deployed row-cap/parser checks remain pending; team shared-run timestamp-only continuation remains a separate limitation |
| Counts | R-S14a implements exact HEAD totals for run/scan/free/founding/citation counts and complete slim pagination for distinct batches/site usage | Exact reads are not atomic run reservations; R-S8/R-S9 still own wallet and concurrent admission. See [database evidence](database-history-queries.md) |
| Jev | Experimental opt-in bounded browser decisions with confidence-gated generative fallback | No SEO/GEO or comparison integration; no established end-to-end latency improvement |
| SEO comparison | Existing comparison queues the owner's site plus up to three competitors and scans them concurrently | Not a keyword/backlink research engine; keep verification/permission limits explicit; comparison currently uses the default crawl route |
| Growth and chapters | Technical SEO/GEO, sampled citation history and grouped deterministic fix batches exist | Search Console connector and full keyword/backlink opportunities are pending; chaptered reports shipped with R-S5a (keyword, backlink and citation chapters are status-only until R-S17/R-S17a) |

**Code references:** [cache lookup](../apps/api/app/db.py), [public scan entry](../apps/api/app/main.py), [scan-cache regressions](../apps/api/tests/test_scan_cache.py), [runtime](../apps/api/app/agent/runtime.py), [job replay](../apps/api/app/jobs.py), [initial indexes](../apps/api/migrations/0001_initial.sql), [web history](../apps/web/src/lib/runs.ts), [MCP tools](../apps/api/app/mcp_server.py), [Jev adapter](../apps/api/app/agent/typesafe.py), [report view](../apps/web/src/components/ReportView.tsx), [fix batches](../apps/api/app/agent/fix_prompt.py). Read the exact functions and related tests again before implementation; repository SQL does not prove deployed indexes exist.

## Cache policy and database acceptance

Reopening a saved report can avoid all new inference. Reusing a public scan avoids its scan and first-impression work. Reusing deterministic fetch/parse results alone does not eliminate a later model call. Provider prefix caching reuses input processing, not a fresh answer; output/reasoning and any cache write/storage charges still matter. Eligible Gemini models support implicit caching, but applicability and hit rates must be checked for the actual route/model and response shape. [Gemini context caching](https://ai.google.dev/gemini-api/docs/caching).

Implement scoped reuse before introducing another cache service. Key eligible derived outputs by owner/workspace/privacy, exact resource/scope, environment, evidence hash, scanner/prompt/report version and model configuration. Give each evidence type a bounded lifetime and source timestamp. Single-flight equivalent in-progress work within the permitted scope, with durable recovery and budget semantics. Revocation/deletion must invalidate access immediately; never coalesce private work across accounts or persist credentials/raw form values in keys.

Fresh fix verification, changed DOM/account/session, signed-in dashboards and action execution need fresh observations. Do not replay a cached click or treat old evidence as proof of a fix. Show cached-versus-fresh status and support a bounded fresh-check path. Historical reports remain historical; version changes invalidate reusable generated outputs without silently rewriting old evidence. Measure hit rate, work avoided, p50/p95 and full provider costs; no projected savings percentage becomes a sales claim without measurements.

For database performance, build a query-to-index inventory before adding indexes. Cover owner history, public cache lookup, job claim, citation due work, report/team history and admission counts. Use slim list projections, explicit owner/workspace filters and deterministic `(created_at, id)` cursors for new history paths. Keep detail loads separate. Preserve existing ID cursors where appropriate; exports and connector batching need bounded continuation too. Use `EXPLAIN (ANALYZE, BUFFERS)` only on representative authorized test data; never execute a mutating admission RPC just to obtain a plan. Assess row caps, RLS, payload size, writes and index overhead. [Supabase query optimization](https://supabase.com/docs/guides/database/query-optimization).

## Distribb review: adapt patterns, not the entire platform

Reviewed the repository's actual [SKILL.md](https://github.com/Bomx/distribb-skill/blob/main/SKILL.md) and linked playbooks. It wraps a commercial service with keyword, backlink, visibility and publishing APIs; installing a Markdown skill does not supply those datasets for free. No permissive license was confirmed, so implementation must not copy its code without resolving reuse rights.

Useful patterns are business context before audit, evidence-backed priorities, source/date retention and a clear separation of citation, mention and missing data. These inform Walkthru's own bounded design. [Audit playbook](https://github.com/Bomx/distribb-skill/blob/main/references/audit-playbook.md), [link-building playbooks](https://github.com/Bomx/distribb-skill/blob/main/references/link-building-playbooks.md).

Do not adopt its credit-for-links network, its instruction to avoid clickable research sources, or ranking guarantees. The helper's quote extraction is not proof of source entailment, and disabled TLS verification is unsuitable for our fetch boundary. Use deterministic source validation, visible citations and existing safe fetching. [Plans/backlinks](https://github.com/Bomx/distribb-skill/blob/main/references/plans-and-backlinks.md), [statistics playbook](https://github.com/Bomx/distribb-skill/blob/main/references/statistics-page-playbook.md), [research helper](https://github.com/Bomx/distribb-skill/blob/main/distribb_research.py). No installation, third-party code reuse, API purchase or outbound campaign was performed.

## Report chapters: one navigable dossier

The first screen answers what was tested, what blocked the goal, what remains unknown and which three actions to take next. Follow it with a contents navigation and visually distinct, numbered chapters. Headings must be prominent through typography, space and existing design tokens, with accessible landmarks and keyboard anchors. Do not add accent colors. Respect [DESIGN.md](../DESIGN.md).

| Chapter | What the reader gets |
| --- | --- |
| Journey and UX | Declared tasks, actual progress, reproducible failures, subjective usability observations and untested routes |
| Accessibility | Observed keyboard/label/contrast problems, affected elements and bounded automated coverage |
| Performance | Measured device/page conditions, offending resources/elements and prioritized fixes |
| SEO foundations | Crawl/indexability, metadata, internal links, structured data and actual affected public pages |
| Keywords and content | Audience intent, target page, supported keyword direction, copy/brief suggestions and demand-data status |
| Authority and backlinks | Applicable earned-link opportunities, evidence, useful asset to offer and measurement plan |
| GEO readiness | Readable, attributable, accurate content and provider-specific access; explicit limitations of heuristic scores |
| AI citations | Dated sampled answers, verified linked sources versus mentions, engine/model and unmeasured surfaces |
| Security and email hygiene | Existing passive findings, ownership boundaries and concrete remedies |
| Evidence and coverage | Sources, captures, freshness, exclusions, partial work and accepted usage |

Every relevant chapter contains a plain-language summary, observed facts, prioritized actions, proposed solutions, evidence and how to verify. Show not tested, unavailable, or no issue observed within scope accurately. Do not turn missing data into a green pass or fill chapters with invented findings.

Use one primary chapter per issue and cross-links for shared causes. A JavaScript rendering problem can affect SEO and GEO without appearing as two independently discovered defects. Recommendations/opportunities are separate from observed defects and do not lower a technical health score merely because the owner has not implemented a suggested marketing campaign.

Offer a short action view and expandable technical evidence, with readable mobile layouts and a complete print/export view. Full evidence remains available without padding every first-page summary. Preserve stable issue IDs and legacy reports. AI citation history may be linked or snapshotted into a report with its measurement date; it must not silently appear to have been collected by that browser journey.

## Keywords and content: actionable, grounded direction

Collect a small owner business brief: actual product, audience, geography/language, meaningful conversion, differentiators and selected public pages. Do not treat private dashboards as pages that should rank. Generate a page/intent map with one primary intent and relevant supporting terms per page, suggested title/description/outline, named internal-link sources and claims requiring owner confirmation.

Three evidence modes must be explicit:

1. **Prelaunch advisory:** actual site copy and business context support topic hypotheses. No asserted search volume, keyword difficulty, rank or traffic forecast.
2. **Owner search evidence:** authorized Search Console queries/pages identify low-CTR opportunities, declining content, overlapping intents, near-page-one queries, branded/nonbranded demand and pages receiving little observed traffic. Compare consistent windows and dimensions; sparse or sampled data limits confidence.
3. **Optional external demand:** approved licensed keyword/SERP/backlink data or user-provided exports can support broader research. Record provider, location, language, time and cost. Advertising competition is not organic difficulty. Never scrape Google results to manufacture a free rank index.

Use the documented Search Analytics `query` request with read-only scope, `dimensions`, `rowLimit` and `startRow`. Paging does not remove its top-row completeness limits. It does not expose an arbitrary competitor's private search queries or a complete backlink index. [Search Analytics API](https://developers.google.com/webmaster-tools/v1/searchanalytics/query).

Prioritize a few page-specific opportunities rather than recommend all keywords. Include quoted current copy, the proposed change, factual support, effort, what to publish or repair and when/how to measure. Explain intent overlap before calling it cannibalization. A new site's lack of Search Console data is expected, not a product failure.

**R-S17 advisory mode is implemented (2026-10-07): [contract](keyword-opportunities.md).** Correct existing advice before extending it: `scans/seo.py` and fix recipes treat sixty-character titles and 160-character descriptions as strict limits. Google specifies no fixed length limit; displayed text can be truncated by device width and snippets are query-dependent. Reclassify length as an advisory clarity/presentation check, not a guaranteed ranking defect. Maintain a small rule-to-primary-guidance registry with review date and required/advisory status, separate from observed site evidence. [Google title guidance](https://developers.google.com/search/docs/appearance/title-link), [snippet guidance](https://developers.google.com/search/docs/appearance/snippet).

## Backlinks: twelve tactics evaluated, applicable ones recommended

The catalog below is proposed recommendation coverage. It is not twelve implemented automations or twelve required tasks for every user. Each opportunity needs its source and date, target page/asset, reader benefit, prerequisites, effort and follow-up measure. With missing inputs, request the necessary export/context or mark it advisory; never invent publishers, broken links, historical links or reporter requests.

| Requested tactic | Useful bounded output | Evidence/prerequisite |
| --- | --- | --- |
| Recover lost links | Repair a changed destination or propose a relevant redirect/replacement | Historical link export plus current evidence; no history means loss is unverified |
| Unlinked mentions | Suggest a useful reference where a real mention lacks a link | Actual dated mention/source; brand disambiguation |
| Free tools | Brief for a checker/generator/converter that solves the audience's job | Product fit, feasible scope and examples of where it would help |
| Listicle outreach | Explain a supported inclusion gap and draft a specific pitch | Actual relevant list, selection criteria and truthful product facts |
| Competitor links | Identify legitimate editorial sources that might also value this product | Authorized/licensed link evidence or supplied exports; links are not transferred or guaranteed |
| Broken link building | Recommend a working, relevant replacement readers can use | Verified dead destination and matching asset; respect access/verification limits |
| Fix outdated guides | Offer sourced corrections or an updated example | Dated guide, outdated passage and primary evidence for correction |
| Statistics page | Original research brief with definitions, method and source dates | Real data and reuse rights; no fabricated statistics |
| Reporter outreach | Match genuine requests to qualified, attributable expertise | Real open request, deadline, consent and factual quote draft |
| Infographics | Useful visual brief summarizing verified material | Author/content rights, accessible text and accurate sources |
| Article-to-video | Useful explanatory storyboard and optional production brief | Permission, source accuracy and genuine audience fit |
| Link exchanges | Assess editorial relevance and disclose scheme risk; no automated exchange network | Independent usefulness; reciprocal/triangular placement is not recommended as a ranking shortcut |

Google identifies excessive exchanges, automated link creation, paid ranking links and low-value link content as spam patterns. Legitimate sponsorship links should be qualified appropriately. Avoid three-way exchange campaigns, obligatory ranking-credit links and mass publisher lists. Recommend useful tools, attributable expertise and original evidence with an independent editorial reason to cite them. [Google link-spam policy](https://developers.google.com/search/docs/essentials/spam-policies#link-spam).

The launch deliverable is an asset/opportunity plan and optional drafts. Building/hosting a free tool or producing video is separately scoped work, not something silently promised by a report. No email, DM, article publication or backlink placement follows automatically from an MCP connection or generated prompt.

## GEO readiness and AI citation measurement

Keep content accessibility, legitimate external authority and observed AI citations related but distinct. Backlinks do not guarantee an AI citation or higher rank. Google says ordinary SEO fundamentals apply to its AI search features, with no required special AI files/schema. Its search crawling control is Googlebot; Google-Extended controls other uses and is not an AI Overviews access switch. [Google AI features guidance](https://developers.google.com/search/docs/appearance/ai-features).

For other providers, verify current search, user-request and training bot documentation separately before recommending access changes. Preserve deliberate owner training restrictions. Treat `llms.txt` and discovery endpoints as optional experiments, not mandatory ranking factors. Do not import the local GEO skill's impact percentages or bot mappings as universal facts.

Recommend answer-first sections, accurate entity details, visible-content-matching schema, original examples, methodology, freshness and attributable sources when supported by page content. Distinguish author-supplied evidence from marketing claims. Citation results retain prompt, engine/model, retrieval capability, date, source URLs, reference matching, sample size, failures and unknowns. A memory answer or brand mention alone is not a verified web citation. Consumer search surfaces remain unmeasured unless a supported authorized measurement path exists.

## MCP and generated prompt parity

Reuse the saved evidence/report contract for web, print/export, fix prompts and MCP. Existing deterministic `fix_prompt.py` batches are a starting pattern, not a reason to generate a second incompatible report.

- Section navigation and bounded issue/opportunity retrieval must expose the same IDs, evidence and coverage. Proposed section/cursor selectors are new interface work, not existing tool parameters.
- Each generated section prompt carries selected URLs, permitted evidence, precise proposed changes, factual uncertainties, acceptance tests and actions requiring owner execution. Avoid one enormous prompt containing every section's raw data.
- Keep business context and external page text as data. External skill instructions cannot authorize uploads, network calls, sending messages or publishing. Protect private reports and connector tokens through the existing owner/workspace access checks.
- Stored report reads and deterministic prompt assembly should avoid fresh inference. Fresh research/citation work uses the same quotation, reservation, quota and stop authority as other entry points.
- Backlink/content drafts stay separate from technical repair prompts. A coding agent cannot create genuine third-party citations by editing a local page.

## Implementation order and proof

Preserve all twenty original session IDs and R-S1/R-S2/R-S3 completion. Add four focused suffix slices: **R-S5a** chaptered presentation and consumer parity, **R-S7a** safe cache reuse/measurement, **R-S14a** database query/index/pagination performance (completed 2026-10-05), and **R-S17a** earned-link opportunities and citation-aware recommendations. R-S5a was completed 2026-10-06; R-S7a and R-S17a remain pending. Detailed dependencies, verification and deployed limitations are in [the workflow](restructure-sessions.md).

R-S17 gains keyword/page/intent briefs and measured versus advisory modes. Jev is only a possible confidence-gated helper for ambiguous bounded classification after deterministic evidence extraction. Do not insert it into every scanner or treat confidence as proof. Benchmark end-to-end p50/p95 latency, fallback rate, correct classification and full cost against deterministic-only and the current synthesis route; a serial failed Jev call can add latency and cost.

Verify with owned fixtures and supplied exports: prelaunch zero data, incomplete Search Console windows, ambiguous intent, absent backlink history, stale sources, valid versus unsupported citations, nonapplicable tactics and policy-risk examples. Report fixtures must include clean, interrupted, legacy and long multi-section cases; verify mobile, keyboard, print and MCP/prompt equivalence. Paid integrations stay disabled until selected and authorized.
