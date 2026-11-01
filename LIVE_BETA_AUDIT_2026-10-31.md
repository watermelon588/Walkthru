# Walkthru live beta-readiness audit

Date: 31 October 2026. Target: https://tripverse-0.vercel.app/. Environment: current local web/API/worker and the founder's signed-in Plus account. Dodo payments and paid LLM activation/calls are excluded.

## Final artifact review, 1 November 2026

The completed journey was re-read in recent history as **Ended early**, 47 loaded records, with **149/150 runs left, 1 used and 1/5 sites**. Its full report remains available at the linked run ID. This clears genuine journey persistence and one-run accounting for this case, not successful task completion.

**PDF export also produced a real artifact:** `evals/results/live-beta-audit-2026-10-31/new-run-report.pdf`, 15 pages, 2,765,304 bytes, eight evidence images on pages 5/6. The actual UI opened print preview and saved through Microsoft Print to PDF. Rendered pages 1 and 11 were visually inspected; outcome/scope limitations and GEO/report content are present.

**L8, medium: PDF usability needs another correction.** Page 11 prints the structured-data code in a bounded scrolling box, clipping the rest of the JSON. Print styles must expand code blocks and retain the full copy-paste fix. The tested Microsoft Print to PDF artifact yields only 14 extracted text characters through PyMuPDF despite visually readable pages; do not count this output as searchable/accessibility-verified. Retest the browser's built-in Save as PDF destination separately before assigning the text-layer limitation to all exports. Evidence: `new-run-pdf-check.json`, `new-run-pdf-page-1.png`, `new-run-pdf-page-11.png`.

**Release decision remains no public-beta sign-off.** Basic pipeline/integrations work in the verified scope, but L1/L2/L5/L6, incomplete difficult-task performance and report/PDF consistency issues require correction and rerun. Cross-account permissions, suite/recheck/compare/watch/helper/persona/branding and recovery cases are not certified by this audit. The pending second-account request is for role/isolation testing; no password or secret needs to be pasted into chat. GitHub App and mail delivery checks need their respective deliberately configured integrations. No payments or paid-model service was activated.

## Retry results, 31 October evening

This section supersedes the first pass's unverified labels where explicitly stated below. The founder requested a retry, authorized a temporary MCP key and opened the extension in Chrome.

- **MCP read path passed live.** Real Streamable HTTP initialization negotiated `2025-06-18`; discovery returned 26 tools. Actual authenticated `get_plan`, unfiltered `list_runs` with a next cursor, `get_report(section=journey)`, `get_fix_prompt(section=seo)`, `get_ai_answers`, `get_usage` and `list_watched_sites` returned real account data. The public scan was correctly denied as not belonging to the account, corroborating L1. No mutating MCP tool or paid model was called. The temporary key was revoked through the UI; an actual subsequent MCP handshake returned **401**. The existing `test api` key was preserved. Evidence: `mcp-readonly-result.json`, `mcp-history-unfiltered.json`, `mcp-revocation.json`.
- **Fresh citations completed and exports/filters passed.** The 31 October batch has 22 done, 0 queued, 0 failed; 10 named mentions and only 1 answer with resolved citation evidence (0 own-site citations). Groq plus unbranded prompts filters to 6 answers, 0 named mentions and citation N/A. The downloaded CSV has 22 rows and separate Named/Cited/Source columns. Retrieved source URLs are now visible in expanded answers; most attribution remains incomplete.
- **New high-priority citation defect L6: brand identity collision.** The fresh “What is TripVerse?” Groq answer, timestamp 20:40:51 IST, claims an iOS travel app and cites/retrieves other TripVerse domains (`tripverse.app`, `tripverse.co.uk`, a LinkedIn company and other organizations), not the supplied target. It is nevertheless credited as **Named you**. That is lexical brand matching without established entity identity. Keep raw lexical mentions separate from verified own-brand attribution, show ambiguity and avoid crediting unsupported product claims as visibility success. Evidence: `citation-brand-answer.txt`, `citation-brand-answer.png`, `citation-results.csv`. This is a fresh result, not merely the old dataset.
- **Owner team writes passed live.** Created the private owner-only workspace [TripVerse beta audit 31 Oct](http://localhost:5173/app/team/44f512a5-f1da-4202-b0d0-f46b01cdd38f), 1/3 seats. Shared the existing genuine 7 October report `6d426751f2034ad994cf0ab7add2c8f6` into it, producing 18 findings. Assigned the LCP finding to the owner, verified Assigned to me filters to 1/18, changed it to In progress and verified both values after reload. Restored it to **Open / No one**. No invite/message or second-member access was created. The workspace and shared historical report remain as audit artifacts; they are not a newly executed journey. Evidence: `team-created.txt`, `team-assignment-status.txt`, `team-persisted-triage.json`, `team-reload.txt`, `team-restored.png`.
- **Owner report delivery passed for the genuine historical report.** CSV and `walkthru-fixes.md` downloads succeeded. CSV contains chapter and evidence/acceptance columns; the prompt retains the unconfirmed outcome and scope limitations. Stored journey screenshots loaded with nonzero image dimensions. These checks do not establish a newly captured screenshot upload or an exported PDF. Historical F2 findings remain historical; their presence does not revert the new F2 scanner fix.
- **Ownership verification passed live.** Settings returned `Verified https://tripverse-0.vercel.app/`. No DNS, source or deployment changes were needed for this check.
- **Chrome access and connection recovered.** Native accessible-value entry and normal UI navigation worked after initial input/geometry problems. The signed-in Chrome dashboard connected the extension, which displayed the real Plus quote: one run, up to 30 steps/4 minutes, free models, 150 before/149 after. No card charge per run. In-app toolbar side-panel support remains a separate limitation.
- **New release-blocking extension defect L5: optional suite fields block ordinary Start test.** Clicking the actual Start test button while not saving a suite triggered browser validation on the empty **New suite name**. `SuitePanel.tsx:109` marks that field `required` while `App.tsx:305` wraps both suite controls and Start test in the same form. The run starts only after filling that unrelated field. Required fix: isolate scenario-save validation from journey-start validation, retaining a valid nonempty goal requirement. Verify actual installed-browser Start with empty optional suite fields and Save scenario's own invalid-name behavior. Evidence: `extension-start-blocked-by-suite.png`. No source patch was made; for this audit only, the unused field was filled and Save scenario was not clicked.
- **Real difficult journey completed its bounded execution and saved a partial report.** Run [aefe880d6c4f49ecaa6f867e2de97eb1](http://localhost:5173/app/runs/aefe880d6c4f49ecaa6f867e2de97eb1), started at 21:20:14 IST, ended early with 14 recorded steps, 13 actions with recorded outcomes in the scope box, 8 captured frames and Launch Ready 58. It navigated via signup to the guest flow, waited for preparation, entered the trip request and budget, and stopped on brief step 3/4 before confirming the final interest-field action. **No generated itinerary, Trip Studio, map or completed budget inspection was reached.** This run exists in actual account history; no row or observation was manufactured. The extension's next quote shows 149/150 remaining. A generic Ended early label is shown; the exact internal stop reason is not surfaced clearly enough to distinguish cap/owner stop from that label alone.
- **New Plus report confirms L2 beyond the anonymous scan.** Its Keywords and Authority chapters are still Not measured despite usable rendered product context in its first-impression section. The technical crawl covers three visited routes (home, signup, create), paid page limit 50. `site.py:335` builds advisory input from response HTML; carrying relevant sanitized rendered/owner context into this path needs attention for SPA targets. No backlink/keyword data or demand metrics should be invented to fill the gap.
- **Report consistency issues L7 require follow-up.** This fresh scope box says 13 actions with outcomes while its summary says 11 browser actions; the source excludes waits from the latter count. Explain/reconcile the definitions. The extension retained three understood-goal checklist items, but the report declares zero checkpoints and cannot validate completion against them. A fresh step without a screenshot says evidence is available on “new runs” and refers to older runs even though this is a new run that already has eight frames. Surface actual missing-frame reasons. Its browser LCP is 272.8 seconds from an already-open tab; preserve the single-browser label, review measurement age/interaction/SPA context and reproduce on a fresh navigation before presenting that as normal page-load performance.
- **Fresh artifact delivery passed.** New-run CSV, full fix prompt and SEO-only prompt copied/downloaded successfully; all eight saved frame images loaded with nonzero dimensions. Evidence: `new-run-report.txt`, `new-run-report.csv`, `new-run-fixes.md`, `new-run-seo-prompt.md`, `new-run-overview.png`, `extension-final.txt`. Earlier historical-report export tests remain separately labelled. A transient dashboard plan read timed out and a page navigation briefly timed out under this workload; later state reads recovered. These are observations requiring latency/recovery investigation, not proof of a specific infrastructure root cause.

## Verdict and completion boundary

**Do not mark beta acceptance complete yet.** The real extension journey, persistence/report pipeline, fresh citation batch, read-only MCP, owner team writes and exports were exercised on retry. The difficult task did not reach its goal, ordinary Start test has an unrelated required-field blocker, citation identity is unreliable and new Plus recommendation chapters remain empty. Cross-account collaboration and the remaining matrix still need acceptance.

This is a detailed record of a **partially completed live audit**, not a claim that every feature passed or failed. There is enough evidence to identify a concrete signed-in scan/history defect and report-value gaps, but insufficient evidence to approve an unrestricted production beta. A supervised founder pilot could resume after the browser blocker is resolved.

The first pass stopped because Computer Use could not establish the active Windows Chrome URL with sufficient confidence. The retry recovered browser access and completed the live checks above. Initial input/geometry problems were tool issues; L5's native required-field validation and the failed difficult mission are actual product observations. The API, web app, fixtures and admin processes were left running.

Earlier automated tests and historical reports are supporting context only. No mocked browser session, seeded run, fabricated observation, rewritten historical report, source fix, schema change or cloud operation was used to replace live acceptance.

## What actually ran

| Artifact or action | Observed result |
| --- | --- |
| Signed-in workspace | Plus grant visible; 150/150 runs remaining, 0 used, pass ends 30 November; 0/5 sites in the plan meter. |
| Existing history | 46 loaded records, including 37 browser journeys. Latest displayed journey was about 23 days old. These are not new acceptance results. |
| Extension handoff | Connect extension displayed “Extension connected. Open a site and click the bird.” |
| Installed extension | Walkthru appeared in the in-app browser toolbar and its Extensions menu. Both opening routes were attempted; neither visibly opened a side panel. |
| New Instant Scan | `d97cd1aa8b6c444180caf548f46b658c`, completed at 20:29 IST. [Public report](http://localhost:5173/r/d97cd1aa8b6c444180caf548f46b658c). |
| History after the scan | Returning to the dashboard still showed the old 46 records and old latest journey; the new scan was absent. |
| TripVerse AI answers | Existing tracker loaded with 11 prompts against Mindtrip, Wanderlog and Layla. A real Check now action queued a new 22-answer batch. |
| New citation batch | Retry verified 22 complete, 0 queued, 0 failed; CSV, filters, sources and identity-attribution defect reviewed. |
| Existing team | Owner workspace `700c4f31-84b1-4cdd-b06a-a8f148bec540` loaded: 2/3 seats, 1 person present, live updates indicated, 1 shared report, 18 open findings. Findings board and its status/owner controls rendered. |
| New difficult agent journey | `aefe880d6c4f49ecaa6f867e2de97eb1`: actual extension execution, 14 steps/eight frames, saved partial report; **requested trip/map/budget goal not completed**. |

Local evidence: `evals/results/live-beta-audit-2026-10-31/` (ignored). Saved files: `instant-scan.ax.txt`, `instant-scan.png`, `citation-before.ax.txt`, `citation-queued.ax.txt`. The last citation file is an accessibility-tree diff. No session tokens, passwords or API key values were copied into these artifacts.

![Fresh real Instant Scan](evals/results/live-beta-audit-2026-10-31/instant-scan.png)

## Confirmed issue L1: signed-in dashboard scans lose account context

**Priority: high.** From the signed-in Plus dashboard, enter TripVerse and click Scan my site. The app opens a public/free report at `/r/d97cd1aa8b6c444180caf548f46b658c`. Returning to the dashboard does not add the scan to recent history. The report also shows one GEO fix and “3 more ready-made fixes for this site on Pro,” although the entry account is Plus.

Source evidence agrees with the UI:

- `apps/web/src/components/Shared.tsx:191` calls the shared `instantScan(site)` and navigates to `/r/{run_id}`.
- `apps/web/src/lib/runs.ts:291` explicitly calls `/scans` with authentication disabled.
- The dashboard reuses this public ScanForm.

**Required change:** give signed-in dashboard scans an authenticated owner path, persist their ownership/appropriate plan scope and navigate to the owner's report. Preserve the intentionally anonymous homepage scan. Account ownership must come from verified authentication on the server.

**Acceptance:** a new Plus scan appears at the top of that account's history after reload, has the correct entitlements and owner controls, and is inaccessible to an unrelated account unless deliberately shared. Check plan/site usage and cache isolation. Do not “fix” this by inserting a fake history row or automatically making private reports public.

The present Plus meter staying at 150 does not independently prove a quota bug: this path currently behaves as a public Instant Scan, not a paid browser journey.

## Fresh report review

### What is improved and visible

The report now has ten clearly separated chapters:

1. Journey and UX.
2. Accessibility.
3. Performance.
4. SEO foundations.
5. Keywords and content.
6. Authority and backlinks.
7. GEO readiness.
8. AI citations.
9. Security and email hygiene.
10. Evidence and coverage.

It includes three Start here actions, a prioritized fix list, stable issue IDs, evidence/inspection disclosures and coverage limitations. The report explicitly says **Journey not tested**, zero recorded actions and zero declared checkpoints. It does not use the scan as proof of signup or dashboard success. This separation and honesty are meaningful improvements over a mixed list of findings.

Observed measurements:

| Item | Value | Interpretation |
| --- | --- | --- |
| Launch Ready | 63/100, “Almost ready on what was checked” | Partial technical score, not application approval. |
| SEO | 75 | Server-HTML checks only. |
| GEO | 42 | Readiness signals, not AI search ranking. |
| Security | 74 | Headers-only scope for this unverified shared-host domain. |
| Findings | 15: 1 high, 4 medium, 10 low | No browser-journey findings were collected. |
| Crawl | 1 page, 2.8 seconds, limit 10, same origin | Server HTML exposed no navigation links. Rendered site actually has more routes. |
| First impression | Not judged | No readable text before JavaScript runs. |
| Accessibility | Unavailable | JavaScript-rendered page was not checked in a real journey. |
| Performance | Unavailable | PageSpeed not configured. |

The UI states that 45% of the normal score weight was unmeasured and redistributes that weight. Preserve this disclosure. Consider making coverage as prominent as the headline score so a partial 63 cannot be mistaken for an end-to-end pass.

### What still falls short of the promised value

**L2, high for product positioning: this delivered report still provides no keyword direction or contextual backlink plan.** Its Keywords chapter says there is no search-demand data and gives no direction. Authority says backlinks and earned-link opportunities were not measured. AI citations are a separate sample workflow and are not included here.

The retry's authenticated Plus journey report confirms these sections are also empty there. Implementation files exist, but the customer-visible result does not deliver the promised direction on this SPA target. Static HTML supplies little content while rendered browser context is available. Fix the owner scan path and the advice input/coverage path; do not call R-S17/R-S17a accepted from source presence alone.

Required checks after that fix:

- Identify the actual product/audience from rendered or owner-supplied evidence when static HTML is empty.
- Offer explicitly labelled keyword hypotheses, intent/page mapping, content briefs and next actions without inventing volume, difficulty or rank.
- Where Search Console or licensed demand data is absent, explain what is advisory and how the user can validate it.
- Show the relevant twelve-tactic authority plan with concrete prerequisites and useful-asset ideas, distinguishing unmeasured opportunities from sourced ones. Do not invent backlinks or perform outreach.
- Keep GEO readiness, backlink advice and sampled AI citations distinct; do not promise rankings or guaranteed citations.

**L3, medium: several recommendations need more precise claims and applicability.** Examples in this fresh report:

- “Full URLs, including query strings, leak to every site you link to” from a missing Referrer-Policy header is too categorical; effective browser policy and defaults matter. State the observed missing header separately from demonstrated leakage.
- The agent-readiness component deducts for missing `WebSite SearchAction` without establishing that TripVerse has a site-search feature. Check applicability before prescribing a capability.
- The writer's top-fix list says to add a CSP starting with `default-src 'self'`, while the detailed finding sensibly says use report-only first. Preserve the rollout/context warning in concise prompts too; a restrictive policy can break legitimate assets or integrations.
- Static HTML is empty, but “ChatGPT, Claude and Perplexity see an empty page” is stronger than the observation. Say which fetch/browser mode was actually measured and avoid claiming every engine's behavior was tested.

**Acceptance:** each recommendation separates observed facts, inferred risk, applicable remediation and verification. These examples require wording/applicability review; this audit did not perform an exploit or benchmark every crawler/browser.

## AI citation review

The current UI is more honest about measurement boundaries than a generic visibility score:

- It distinguishes Groq with web search from Gemini from memory.
- It explicitly says Google AI Overviews, AI Mode, ChatGPT, Perplexity and Claude are not measured.
- It warns that API answers differ from consumer products, one sample is not a stable ranking, brand-naming prompts bias mentions, and mention/source order is not ranking.

Existing TripVerse data, observed **before** the new batch:

- 22 completed answers, 10 naming TripVerse.
- Citation summary: 0 of 1 answers with resolved citation evidence.
- 21 completed answers excluded from citation measurement.
- Share of tracked-brand mentions: TripVerse 29%, Layla 35%, Mindtrip/Wanderlog 18% each.

**L4, confirmed remaining acceptance risk: usable citation coverage is very low in both the existing and fresh datasets.** Naming a brand is not evidence that its actual domain was cited, and neither proves that product claims are accurate. The retry inspected completed fresh answers and found L6's identity collision. Retrieved source capture now works for the expanded Groq answer, but resolved attribution/own-brand accuracy remain inadequate.

An additional historical Opzami view showed aggregate Cited you N/A while one row said Cited your site. This needs version/evidence inspection before declaring a current aggregation defect; it is historical data, not a fresh reproduced engine result.

Required next acceptance:

1. Wait for the fresh TripVerse batch to finish, retaining failed/delayed states honestly.
2. Expand a branded answer and an unbranded category answer per available engine.
3. Verify source URLs, matched answer references, timestamps, engine labels and exact own-domain attribution. Retrieved pages alone are not resolved citations.
4. Compare factual statements with the real TripVerse site. Flag unsupported claims; do not count flattering invented features as product success.
5. Export CSV/PDF and reconcile denominators with the filtered UI. A missing source must remain N/A, not become a confirmed negative or positive citation.

Groq capacity showed 20 attempts/day and a queue of 11 web plus 11 memory answers after submission. The source intentionally spaces web attempts by 60 seconds and allows retries. A batch can take many minutes; instant batch completion should not be promised.

## Extension and difficult-task acceptance

The acknowledged Connect extension response is real, but **session connection is not browser execution**. The installed in-app browser action did not visibly open the side panel. Standard Chrome acceptance remains unresolved because Computer Use stopped while attempting to inspect that environment.

The source uses `chrome.action.onClicked` to call `chrome.sidePanel.open({tabId})`; the built manifest declares `sidepanel.html`. The package is built, but this audit did not establish which build the in-app browser has loaded or whether its side-panel API behaves like standard Chrome. Do not label the extension globally broken from this observation alone.

The following real mission was attempted on retry, without manually substituting the auditor's actions for the agent. It needs to succeed after the controller/flow issues are addressed:

> From the TripVerse homepage, use guest planning to plan three days in Kyoto, departing from Delhi, for two people with a ₹150,000 total budget and an interest in food and temples. Open the generated trip studio, inspect the map and budget, and identify whether the itinerary actually reflects the requested constraints. Do not sign in, create an account, book, pay or delete anything. Stop once the stated evidence is visible; if guest generation is unavailable, record the exact blocker instead of claiming completion.

Use the normal bounded Plus run, with dry-run disabled, free configured providers and a suitable declared step cap. If a provider fails or the cap is reached, report that as an agent/provider limit unless an independent site failure was observed. Leave the genuine saved run in recent history.

Required evidence: actual click/type/scroll outcomes, no stale-target clicks, bounded waits, honest stop reason, checkpoint evidence tied to the correct page, masked screenshots uploaded and readable, report generated, history survives reload, rerun/compare recognizes unchanged scope. A second run after an actual fix is required to prove a fix, not merely to generate another report.

## Team workflow

Observed owner workspace loads its overview, counts, existing shared report, member list summary and findings board. The board exposes severity/status filters, Assigned to me, per-finding owner/status, How to fix, Comment and export controls. Presence says 1 here now and Live updates on.

**Not verified:** creating a workspace, persisting a new assignment/status/comment, a second member seeing it, role restrictions, report sharing/revocation, invitations, member removal, reconnect/realtime delivery, team exports and deleted-workspace handling. Rendered controls and a presence label are not proof of those operations.

No invitation or chat message was sent, no membership changed and no existing issue was falsely marked fixed. Finish in a private audit workspace with the genuine new report and an explicitly participating second account. The previous feature audit's 19 PostgREST-dependent team-test skips remain an acceptance gap; this read-only owner check does not clear them.

## MCP workflow

**Read-only connection and tools verified on retry**, as detailed above. The founder explicitly authorized a temporary key, which was used for local MCP checks and revoked, with HTTP 401 verified afterward. Mutation tools, an external editor's saved configuration and cross-account access cases remain unexercised. Source implementation is `apps/api/app/mcp_server.py`; setup is `apps/web/src/components/ApiKeys.tsx` and `apps/web/src/pages/Mcp.tsx`.

Source inspection shows personal-key authentication, Plus gating, chapter selection and paged `get_report(section, cursor)`, section fix prompts and paged run history. This is implementation evidence, not proof that the founder's client can connect.

Remaining real checks: initialize a client using a deliberately authorized key without putting it in the audit/logs; list tools; call `get_plan` and `list_runs`; fetch the genuine new owner report and a chapter-specific prompt; verify an unrelated report is inaccessible; confirm that server-side rerun does not claim a browser journey was rerun. Public sharing, GitHub PR creation and deployment hooks require explicit deliberate use because they change access or external state. Revoke a dedicated temporary key after the check.

## Full feature coverage matrix

“Not exercised” is not a failure verdict. It means this audit cannot approve that feature yet.

| Feature | Current live evidence | Remaining acceptance |
| --- | --- | --- |
| Existing sign-in / Plus entitlement | Passed account display | Real fresh login, expiry, refresh, logout and account switch not exercised. |
| Dashboard / history | Existing and new actual journey load; MCP returns next cursor | Anonymous dashboard scan still missing; UI Load more not exercised; transient plan timeout observed. |
| Instant Scan | Real target scan completed | L1 ownership/entitlements/history correction; error/retry paths. |
| Scan caching | No repeat scan performed | Real fresh/reused label, scope/owner isolation and invalidation. |
| Multi-page crawl | Honest one-page static coverage | Rendered SPA discovery/paid scope not established. |
| Extension connection | Standard Chrome connection and real execution passed on retry | In-app side panel limitation; ordinary Start test L5 blocker; logout/disconnect repeat pending. |
| Agent decisions / complex tasks | Genuine 14-step mission saved with partial report | Task did not complete; unnecessary navigation/scrolls, clearer checkpoints/stop explanation and successful rerun needed. |
| Custom personas | Not exercised | Save/select/use in a real journey; task must remain authoritative. |
| Count assertions | Not exercised | Owner-provided dataset/check and real observed count. |
| Saved suites | Not exercised | Serial runs, distinct saved IDs, stop/resume, recovery and coverage. |
| Report chapter separation | Passed in fresh scan | Owner journey/report/export/MCP parity live check. |
| Fix prompts / per-section prompts | New owner report full download and SEO-only copy passed | Recipe applicability and actual fix acceptance remain. |
| Screenshot evidence / annotations / replay | Eight new frames uploaded/read; step details and unconfirmed final action inspected | Full visual redaction/annotation/replay/expiry acceptance remains; missing-frame wording needs correction. |
| PDF / CSV / branding | Actual CSVs and 15-page PDF saved; PDF cover/GEO pages visually inspected | L8 clipped code and tested-driver text-layer issue; branded/built-in-PDF variants remain unverified. |
| Ignore / accept / reopen findings | Not exercised | Persist state without hiding real failed evidence. |
| Targeted recheck / previous-run comparison | Not exercised | Real before/after fix under identical scope; unknown stays unknown. |
| Public sharing / badge | New scan public report renders | Deliberate owner sharing, revoke, badge and evidence privacy. |
| SEO technical checks | Fresh static findings visible | Evidence disclosures not individually expanded; SPA/owner scope. |
| Keyword direction | Empty in both public scan and new authenticated Plus report | L2: deliver applicable advisory output; keep measured/advisory distinction. |
| Authority / twelve backlink tactics | Empty in both public scan and new authenticated Plus report | L2: contextual plan, sources/prerequisites, no invented links. |
| GEO readiness / fix pack | Score, breakdown, one fix visible | Correct owner entitlement, relevant structured-data advice. |
| AI citations | Fresh batch completed; sources, filters and CSV work | L6 entity identity and sparse resolved citation coverage remain. |
| Accessibility | Explicitly unavailable | Run axe/browser diagnostics in actual journey. |
| Performance | Explicitly unavailable | Configure an approved available measurement and inspect attribution. |
| Passive security | Header findings visible | Verified-owner controls, applicable risk wording, new F2/F3 evidence. |
| Email DNS / SMTP integration | Not exercised | Authorized domain checks; delivery not established. |
| Team owner view | New private workspace, report share, assignment/filter/status/reload passed | Second-account roles, realtime/revocation, invitations/chat and exports remain. |
| Compare sites | Not exercised | New real comparison, truthful missing metrics and saved history. |
| Weekly Watch / notifications | Not exercised | Create/schedule/change detection/notification delivery. |
| MCP | Actual initialization/26 tools/read operations/key lifecycle passed | Mutation tools, editor-specific setup and cross-account cases remain. |
| GitHub fix PR / deploy hook | Not exercised | Deliberate authorized integration and safe reviewable result. |
| Billing usage | Real free-route quote; one run used, next quote 149/150 | Ledger explicitly inactive; full cap/retry/settlement acceptance and plan timeout recovery remain. No Dodo activity. |
| Scout helper | Button visible | Actual grounded response, error/limit behavior. |
| Settings / feedback / onboarding | Not exercised | Save/read behavior and relevant privacy handling. |
| Account export / deletion | Not exercised | Review export safely; irreversible deletion is not an audit prerequisite. |
| API health / worker durability | Prior startup check only | This audit did not repeat restart/checkpoint/queue recovery drills. |
| Responsive UI / keyboard access | Narrow report/dashboard rendered | Full keyboard and mobile acceptance not performed here. |

## F1-F6: fixed in code versus accepted live

The implementation record is [docs/prelaunch-fixes-2026-10-31.md](docs/prelaunch-fixes-2026-10-31.md). The earlier full offline API result was 1,267 passed/19 skipped after F3; later F4/F5 affected tests passed and F6 web tests/audits passed. These suites were **not rerun in this live audit**.

| Fix | Existing implementation status | What this live audit establishes |
| --- | --- | --- |
| F1 evidence-based completion/readiness | Corrected locally for new calculations | Fresh static report does not claim a journey succeeded. Difficult actual completion/stop scoring remains untested. |
| F2 public Supabase configuration | Informational, unscored locally | Headers-only scan does not exercise verified backend checks. No fresh live acceptance claim. |
| F3 cookie-purpose remediation | Corrected locally with redaction | No relevant new cookie evidence examined. No fresh live acceptance claim. |
| F4 variant font failure | Blocking remote imports removed | No fresh variant/offline-font pass in this audit; prior browser verification remains recorded. |
| F5 `/ready` | Bounded DB/queue readiness added | Prior startup readiness was 200; no durability/restart drill here. |
| F6 dependency advisories | Web lockfile patched and prior audits clean | No dependency change or vulnerability-scan repeat here. |

These fixes are not reverted by the remaining gaps. They also do not make the full restructure or release acceptance complete. Older saved report scores/evidence were not rewritten.

## Configuration and cost boundary

Presence-only inspection of local `.env` found no configured Claude Vertex project or controller candidate, no PageSpeed key and no Resend key. Groq, OpenRouter, Google and TypeSafe keys are present; their values were not read into audit output. Gemini grounding was not enabled in that file. The fresh scan labels its models as free gpt-oss-120b and backups.

Reservation/provider-receipt flags were absent in the inspected file; source defaults for `RESERVATIONS` and `PROVIDER_USAGE` are off. This is not a full process-environment or live database activation audit. Do not market the planned funded wallet, exact cost settlement or stronger paid routing as active based on source presence. No Dodo flow, paid-model switch or cloud resource change was made.

## Required next actions, in order

1. **Fix L5 and complete the real agent mission successfully.** Standard Chrome now connects, TripVerse is verified and the failed actual run persists. Isolate optional suite validation from Start test, then improve current-state decisions/waiting and outcome checks. A saved partial run is not success. Diagnose in-app side-panel support separately.
2. **Fix L1 before evaluating Plus report value.** Preserve anonymous homepage scans while making the signed-in dashboard produce owner-associated reports with correct entitlements and history.
3. **Correct citation identity/attribution.** The fresh review is complete enough to confirm L6; resolve it or narrow the feature promise to clearly labelled lexical mentions with N/A/ambiguous identity where appropriate.
4. **Evaluate one fresh authenticated report end to end.** Check keyword/authority applicability, actionable page-specific fixes, screenshots, prompts, PDF/CSV and chapter parity. Correct L3 wording and applicability.
5. **Finish the remaining team and MCP acceptance.** Owner team writes and read-only MCP passed. Use an explicitly participating second account for role/access/realtime checks and deliberate approval for access-expanding integration/mutation tests. No further key is needed merely to repeat the already-passed read checks.
6. **Exercise the remaining matrix deliberately.** Suites/recheck/compare/watch/helper/settings need real artifacts and clear failure states. Email delivery requires an actual configured sender; absent configuration cannot pass as delivered.
7. **Close operational beta gates.** Actual checkpoint/worker recovery, user-specific access control and permission/privacy acceptance remain needed even when payments and paid models are excluded. Keep the founder admin loopback-only.

The next audit should append the genuine run IDs and measured results here, and change individual matrix rows only when their evidence exists. Do not replace “not exercised” with “passed” because an offline test exists or a source file implements the route.
