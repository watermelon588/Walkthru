# One synthetic filtered-count assertion (R-S6)

The extension can check one owner-declared filtered count on a verified site. The owner supplies a path, filter value, count label, expected count, synthetic dataset identity/time, maximum age and count tolerance. The browser reuses its executed, masked public snapshot. This adds no connector, database query, model call, dependency or relational migration.

The mission checkpoint is reaching the declared filter state. Count correctness is a separate verdict. A browser can reach Active successfully while the count assertion fails. The report shows both, and the journey chapter explicitly names failed, blocked or inconclusive assertions rather than showing a clear journey. Assertions do not create invented UX findings.

## Golden mission

Owned fixture: `evals/fixtures/easy/dashboard.html` and `dashboard.js`, served by `./dev` on `http://localhost:8101/dashboard.html`. It has three synthetic records: Alpha and Beta are Active, Gamma is archived. Filtering is entirely local to the page: no requests, form submissions, storage or backend mutation.

1. Open the fixture and read its visible `Dataset time` value. It is generated once per page load. Keep that tab loaded while checking it.
2. Use goal **Filter Active records** and enable **Check a synthetic filtered count** in the extension.
3. Supply this definition, replacing `dataset_at` with the exact displayed timestamp:

```json
{
  "path": "/dashboard.html",
  "filter_value": "Active",
  "count_label": "Filtered records",
  "expected_count": 2,
  "dataset_id": "synthetic-sales-v1",
  "dataset_at": "2026-10-06T05:00:00.123Z",
  "max_age_seconds": 3600,
  "tolerance": 0
}
```

That timestamp is an example, not a reusable fresh expectation. A page reload changes the fixture timestamp and requires a new declaration. `case=mismatch` intentionally keeps all three rows after selecting Active; `case=stale` dates the dataset two hours earlier; `case=blocked` presents a recognizable CAPTCHA boundary and disables Active. Expected results are passed, failed, inconclusive and blocked respectively. The real-browser harness captures exact definitions, actual snapshots and report assessments in ignored `evals/results/restructure-session-6/golden-missions.json`.

Local fixture verification drives the graph with a scripted model and the compiled extension injection through a runtime shim. It does not relax the API's public-address policy to allow localhost targets. For a normal extension/API run, host the synthetic fixture on your own verified public/staging domain. Prepare any login yourself and select the existing logged-in option when your plan permits it. CAPTCHA resolution remains a human handoff; the agent never solves it.

## Evidence and outcomes

The page must expose exactly one matching `Filter: Active`, a delimiter or the count label immediately after the filter value, a unique `Filtered records: N`, `Dataset: synthetic-sales-v1` and an ISO timestamp with timezone as `Dataset time: ...`. The path must match exactly and remain on the start origin. Ambiguous filters, missing or multiple count labels, missing/changed dataset identity/time, stale/future data, truncated snapshots or page errors cannot produce a pass. Expected count or dataset fields may be omitted; they remain unknown rather than inferred.

| Result | Meaning |
|---|---|
| passed | Recorded count differs from the supplied fresh expectation by at most the declared tolerance. |
| failed | The filter state was reached with matching fresh dataset context, but the count is outside tolerance. |
| blocked | A genuine site or safety boundary prevented checking the declared state. |
| inconclusive | Expected data or usable evidence is missing, stale, inaccessible, ambiguous, or the controller did not reach the state. |

`POST /runs` accepts an optional `assertion` object. Unknown properties and key-like/private marker identifiers are rejected. Ownership, plan admission, human-prepared authentication, confirmation, destructive-action and payment boundaries remain in force before and during the run. The declaration/outcome travels in the existing checkpointed graph state and report job; no separate data fetch occurs.

Additive report v2 stores at most one `assessment.assertions` entry. It includes expected context, observed count/dataset/time, evaluation time, reached state, reason and an `assertion:1` reference bound to an executed `step:N` on the same URL. Readers reject conflicting verdict arithmetic, freshness, source/step binding and recorded facts. Old v2 reports without this field remain readable. Freshness is judged at recorded evaluation time, so an old saved pass does not change merely because it is read later.

The shared owner/public/team report body, print/PDF and JSON retain the result. Full/chat fix prompts and MCP summaries retain assertion identity, verdict, path/filter, count/tolerance, dataset/time and evidence reference; chapter summaries agree between Python and web. CSV remains a findings export and does not manufacture a finding row for a count result. Existing finding comparison/verify tools do not recheck assertion identities; targeted assertion comparison belongs to R-S13.

This is a visible synthetic UI check. It does not certify backend persistence, authorization, all records, a broader multi-step goal or overall application correctness. Native installed-extension, real account and deployed/live-model acceptance are separate from the isolated browser evidence.

## Dashboard/account plan under `./dev`

A stale API `.env` value set `WEB_URL` to port 5174 while the dev app uses 5173. The API rejected the browser's plan/billing preflight with `Disallowed CORS origin`, so authenticated content requests could not reach their handlers.

`dev.py` now pins child-process URLs to its fixed ports: API `WEB_URL=http://localhost:5173`, web/extension `VITE_API_URL=http://localhost:8010` and `VITE_WEB_URL=http://localhost:5173`. It changes neither `.env` nor production CORS. Regression tests verify parent environment isolation; API test setup uses a deterministic dev origin independent of local `.env`.

The corrected stack is running. Reload the dashboard/account tab. After rebuilding, reload the unpacked extension and its tested website tab to use the new assertion controls. Live API plan and billing preflights return 200 with the correct allowed origin; isolated Edge can read an anonymous 401 plan response from the actual app origin. This proves browser/API connectivity, not a paid entitlement grant or a signed-in account read.
