# H6 report grounding and accounting

Implemented locally, 2026-11-14. This supplements the harness rebuild plan; production rollout remains a separate gate.

## Changes and reasons

The earlier report accepted model-written summaries and top fixes even after rejecting unsupported UX findings. A writer could therefore claim lost revenue, failed signup, crawler exclusion or citation impact in the summary without a retained finding supporting it.

`report.grounded_summary` now composes the executive summary from the validated assessment outcome, recorded problem-step count, measured page coverage and retained finding count. A `done` status alone cannot supply a completion claim. Top fixes are selected from retained findings in severity order, deduplicated, with no independent free-form recommendation channel. The writer still proposes UX findings through the existing grounding filter; those proposed fixes are advice, not experimentally proven remedies. First-impression interpretation also remains model-generated and separately labelled.

This trades some narrative variety for enforceable scope. No phrase classifier or second LLM is asked to certify another model's summary. Existing model-call token accounting is preserved; the synthesis call still produces candidate UX findings. The model's summary and top-fix strings are deliberately ignored.

## Scanner scope

- SEO: missing alt attributes no longer imply images are invisible to search engines; missing Open Graph tags do not prove a missing actual preview; missing robots.txt does not prove sitemap discovery failure. Robots blocking records crawl instructions rather than actual indexing.
- GEO: static HTML and a user-agent-string probe do not establish what ChatGPT, Claude or Perplexity sees. Findings distinguish static-shell detection, JSON-LD parse errors and robots instructions from actual access, indexing and citation behavior. Training opt-out is not treated as measured answer behavior.
- Email DNS: absence at the queried SPF/DMARC/MX names does not prove spam rejection, successful impersonation or bounced replies. Unknown resolver responses such as SERVFAIL/refused are no longer promoted into absent-record findings.
- CAA: no record at the checked host/parent names does not prove certificate misissuance. Resolver errors do not produce a missing-CAA finding. This remains a bounded passive DNS check, not a complete certificate-authority validation simulation.

Primary-source basis: Google explicitly distinguishes robots access rules from keeping pages out of search in [its robots introduction](https://developers.google.com/search/docs/crawling-indexing/robots/intro). SMTP defines address-record fallback when no MX exists in [RFC 5321 section 5.1](https://www.rfc-editor.org/rfc/rfc5321#section-5.1). CAA adds issuance constraints; it is not itself a demonstration of misissuance, as described in [RFC 8659](https://www.rfc-editor.org/rfc/rfc8659).

## Token and cost accounting

The report graph already sums first-impression and synthesis token counts with its reducer. `finish_run` adds the journey total once. The missing contribution was the initial planner call: the graph owner now retains `plan.planner_tokens`, and `_start_run` initializes the journey token counter with it. A regression verifies 11 planner tokens plus 17 decision tokens yields 28, while existing report tests verify 100 impression plus 200 synthesis yields 300.

Provider receipts remain the authority for monetary costs and attempt-level usage. This change does not invent prices, turn missing usage into zero cost, enable receipt storage, or activate paid providers. Failed attempts with unknown usage remain an accounting limitation of the display total; retained provider receipts are separate. Expected graph interrupts are control flow, not failed browser actions; the persistence trial verifies resume without another model call.

## Verification

- Report/scanner/accounting and related contract/provider tests: **139 passed**, one existing dependency deprecation warning; log `tmp/h6-report-tests.log`.
- Changed report/scanner/accounting files passed Ruff.
- Local auth, queue leasing, restart/idempotency and persisted legacy-act compatibility results are recorded after the integration run. Tests use throwaway local PostgreSQL clusters and mocked identity/provider boundaries, never the production database.

No measured live-site reliability increase, installed-extension acceptance or production rollout is asserted by this work.
