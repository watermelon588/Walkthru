# Report v2 contract (R-S5)

Completed 2026-10-05. This is an additive JSON contract in `runs.report`; no relational migration, new dependency or additional model call is required. Saved reports are not regenerated. [Task completion](task-completion-contract.md) supplies the recorded checkpoint evidence; report code does not promote model thoughts into proof.

## Version and compatibility

A missing `version` or integer `1` means the existing report contract. Integer `2` requires a valid `assessment`. Unknown versions, string/boolean versions and contradictory version/assessment pairs fail clearly. API detail reads return 409 for unsupported reports after access checks; MCP returns a tool error after owner checks. Supabase web detail reads retain RLS and validate the report before rendering or export. Private reports still return 404 to non-owners through the API; public and team reads retain their existing policies.

All existing summary, findings, kind/rule IDs, top fixes, scores, comparison, page mapping, GEO, stack and funnel fields remain available. Finding IDs follow the existing MCP rule/fingerprint identity and duplicate `#2` suffix. Each v2 issue links to one exact legacy finding index, so identical findings retain distinct records. Site comparison aggregates keep their existing `compare` envelope; their underlying scan reports use v2. Missing-version legacy aggregates remain readable.

## Assessment fields and invariants

| Record | Meaning |
|---|---|
| `objective`, `outcome`, `stop_reason` | Retained owner objective, conservative scoped outcome and recorded termination status. Outcomes are `completed`, `unconfirmed`, `blocked` or `not_tested`. |
| `coverage` | Measured/unavailable technical checks, actions with recorded outcomes, declared/confirmed checkpoint counts, bounded audited URLs and crawl truncation. Counts must agree with retained evidence and checkpoints. |
| `limitations` | Public UI versus backend limitations, missing expectations, subjective interpretations, bounded reproduction/crawl scope and existing check notes. |
| `checkpoints` | Declared description/expected result, recorded actual result, status and milestone reference. Missing expectations and missing outcomes are null. A passed checkpoint requires its own numbered milestone and matching retained actual evidence. |
| `issues` | One detailed record per legacy finding: source type, observed facts, expected/actual result, interpretation, nullable cause hypothesis, proposed change, recorded reproduction, acceptance test and evidence references. |
| `evidence_index` | Unique scanner, browser step, milestone or subjective first-impression records. Browser records can include a masked URL and step ordinal; scanner records bind to the exact finding index. |

Observed facts and actual results must equal referenced evidence. TypeScript bounds actual results in Unicode code points, matching Python serialization. Scanner, browser-observation and subjective issues require matching source types. Referencing an unrelated step cannot support a scanner finding. An issue expectation must come from retained declared checkpoints; unknown business expectations remain null. `completed` requires nonempty, fully evidenced checkpoints and an actual `done` termination when constructed. A scan's journey is `not_tested`, irrespective of legacy run status `done`.

Generation excludes interrupted, controller-loss, safety-limited and terminal records from browser outcome evidence. Reproduction uses recorded public action labels, never typed values or thoughts, and retains at most 20 recent actions. Scanner reproduction repeats the same check in the recorded scope. First impressions are labeled subjective, with no verified functional defect claim. Cause hypotheses remain null because this slice has no causal proof. Existing URL/value/key/PII masking runs before new text truncation; raw DOM, backend state and screenshot credentials are not embedded.

There is no minimum issue count. Clean and stopped zero-action reports keep zero issues. The structured fields prevent missing references and obvious source/result contradictions; they do not prove every interpretation's semantic correctness or establish causation. Model-written summary/detail and legacy score heuristics retain their existing limits. Public phrase proof does not establish backend persistence, email delivery, authorization or dataset correctness. R-S6 adds an owner-defined assertion path.

## Consumer migration matrix

| Consumer | Legacy behavior | Version 2 behavior |
|---|---|---|
| Private, public and team web reports | Existing saved body, stop coverage and access policies | Same shared body; tested scope/outcome/limitations before prose, explicit outcome labels and keyboard-accessible detailed issue disclosure. |
| Owner/public/team CSV | Original six columns exactly | Same six columns first, followed by ID, source, detailed issue fields, references, outcome and limitations. Uses the same serializer; spreadsheet formulas stay inert. |
| Browser PDF/print | Existing page print and evidence expansion | Includes scope and detailed facts/reproduction/acceptance. `printPage` opens closed disclosures, then restores them after printing. |
| Account JSON export | Existing saved JSON | Preserves additive version/assessment without reconstruction. |
| Full fix prompt / GitHub fix-plan recipe | Existing recipes, ordering and ignored findings | Scope first; complete structured issue fields, evidence and acceptance, including manual-only fixes. No new inference call. |
| Chat fix prompt | Existing bounded 4,000-character parts | Scope plus issue evidence and acceptance, including manual-only fixes. Detailed reproduction stays in the full prompt/report; later chapter prompt parity is R-S5a. |
| MCP report/finding | Existing IDs and owner-scoped access | Validates before reading; report includes scope, full report/finding includes structured facts and reproduction. Bounded summaries point to full tools. |
| Rerun comparison | Existing fingerprints, ignored rules and audited-page semantics | Validates both chosen reports; an unsupported prior report yields an explicit comparison limitation, rather than silently reading it as legacy. |

CSV remains an issue table: a zero-issue report exports the header only, with no fabricated finding row. Full scope remains in web/PDF, JSON and MCP/fix-prompt output. Chapter navigation and section prompts were added by R-S5a (below). The report contract does not alter owner verification, passive probing, send/payment boundaries, screenshot retention, financial admission or pricing.

## Verification and handoff

- Shared Python-generated JSON fixture roundtrips in Python and TypeScript. Tests cover clean/missing-expectation/controller-stop reports, evidence/source/result violations, malformed/future versions, private access ordering, public-value masking and MCP/full/chat/manual-only prompt compatibility.
- Full offline API suite: **915 passed, 19 existing PostgREST-dependent skipped**, one existing Starlette/AnyIO deprecation warning, exit 0 in 695.56 seconds. Final affected report/compare/MCP/prompt suites, including manual-only, privacy, clean and multi-step reproduction additions: **78 focused tests passed**; whole API Ruff passed.
- Web: **42 tests passed**, TypeScript and Vite production build passed, zero-warning lint. Existing Vite chunk-size/dynamic-import warnings remain. The host npm shim is broken, so checks used the already installed package entry points directly without installing packages.
- Actual isolated Edge: **15/15 checks passed**, no runtime errors/warnings. Owned loopback fixtures covered scope ordering, keyboard detail expansion, print expansion/restoration, desktop/mobile overflow, owner/public controls, legacy/future versions, clean and stopped reports. Screenshots were inspected. The sandbox reset Edge's debug connection; approved offline execution completed verification. This does not establish hosted PostgREST, installed-extension, live model quality or deployed acceptance.
- Local artifacts are ignored under `evals/results/restructure-session-5/`: API/web logs, fixture harness, `browser-qa.json`, desktop/mobile/expanded screenshots and disposable test data. Graphify code-only traversal informed consumer discovery; no LLM enrichment, new paid provider, migration or deployment was activated.

**R-S5a followed (below). Next: R-S6** owner assertions. R-S5 and R-S5a edits are local; the separate publication agent owns GitHub commits and pushes.

## Chapters (R-S5a)

Completed 2026-10-06. Chapters are derived in code from the saved report on every read, by `apps/api/app/agent/report_chapters.py` and its mirror `apps/web/src/lib/reportChapters.ts`. No stored field, schema version, migration or model call is added, so legacy and v2 reports both get chapters. Both implementations must match `apps/web/tests/fixtures/report-chapters.json`; regenerate it with `WALKTHRU_WRITE_FIXTURES=1` only after a deliberate contract change.

| Key | Chapter | Primary findings | Status when it has no open finding |
|---|---|---|---|
| `journey` | Journey and UX | `ux` | `not_tested` for scans; `clear` only when declared checkpoints were confirmed (legacy: run `done`), else `unconfirmed` |
| `accessibility` | Accessibility | `accessibility` | `clear` if the check ran, else `not_measured` with the saved reason |
| `performance` | Performance | `performance` | same |
| `seo` | SEO foundations | `seo` | same (legacy reports: SEO always ran) |
| `keywords` | Keywords and content | none yet | `not_measured`: no search demand data, no keyword direction given |
| `authority` | Authority and backlinks | none yet | `not_measured`: no backlink data, nothing invented |
| `geo` | GEO readiness | `geo` | as measured checks (legacy: measured when the GEO block exists) |
| `citations` | AI citations | none | `separate`: sampled on the AI answers page with their own dates, engines and sources |
| `security` | Security and email hygiene | `security` | as measured checks (legacy: always ran) |
| `evidence` | Evidence and coverage | none | `reference`: counts of evidence records, audited pages and limitations |

- **One primary chapter per finding**, from its kind. **Cross-links** come from rule IDs only: GEO JavaScript-rendering rules also affect SEO; `seo.image.alt_missing` and `a11y.image.alt_missing` cross-link each other. Legacy rows without a rule ID get none.
- **Issue IDs** are the existing MCP IDs (`finding_ids`: rule or fingerprint, repeats `#2`). Web anchors are `issue-` plus the lowercased ID with other characters as hyphens.
- **Next actions:** up to three open findings, ordered by severity, then chapter, then report order. Ignored findings stay listed in their chapter but do not count as open and are not next actions.
- **Summaries** are fixed sentences filled with counts; they never claim a pass for unmeasured data.

| Consumer | Chapter behavior |
|---|---|
| Web report (private, public, team) | Scope, summary, Start here (next actions), Contents, then ten numbered chapters. Findings keep their evidence and v2 disclosure, show their ID and cross-links. Timeline, first impression, GEO/agent readiness and audit coverage sit in their chapters. Paid owners get a per-chapter fix prompt button; public and team views do not. |
| Print/PDF | Contents and all chapters print; v2 details expand for print and restore afterwards. |
| CSV | v2 appends `chapter` and `also_affects` after the existing columns. v1 keeps exactly six columns. |
| Fix prompt API | `GET /runs/{id}/fix-prompt?section=<key>` builds the existing deterministic plan for one chapter, headed by the chapter name. Unknown key 422; a chapter with no open findings 409. Without `section` the prompt is unchanged. |
| MCP | `get_report` adds next actions and the chapter index. New optional `get_report(section, cursor)` reads one chapter, ten issues per call, with `next cursor` for the rest. New optional `get_fix_prompt(section)` matches the API route. Owner checks run first, as before. |

