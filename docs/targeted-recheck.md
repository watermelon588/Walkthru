# Targeted recheck of a chosen fix (R-S13)

Implemented locally 2026-10-07. Code:

- `recheck_assertion`, `assertion_of`, `_unique` and `journey_finished` in `apps/api/app/agent/compare.py`;
- `AssertionRecheck` and `Comparison.assertion` in `app/agent/schema.py`;
- `GET /me/recheck` in `app/main.py`;
- `RerunComparison.tsx` and `lib/comparison.ts` in the web app;
- the "Recheck my last count check" button and `getRecheck` in the extension.

No migration, dependency, model call or new flag. A recheck is an ordinary run, so it goes through the R-S10 quote and the R-S8/R-S9 reservation like any other run.

## What it answers

After a paid run, the existing "Since your last run" comparison (same goal, same site) now also compares the R-S6 count check, like for like.

| Verdict | When |
|---|---|
| Fixed | It failed before and passes now under the same declared conditions |
| Still failing | Failed both times |
| Regressed | Passed before, fails now |
| Still passing | Passed both times |
| First result | The earlier check was inconclusive or blocked, so this pass or fail is a first answer, not a fix |
| Not re-checked | This run did not declare the check, or its check was inconclusive or blocked |
| Not comparable | A different path, filter or count label, or changed conditions: expected count, tolerance, dataset, maximum age, test user, or signed-in pages |

Only a failed-then-passed pair under identical declared conditions says Fixed. The dataset timestamp is fresh on every run by design (R-S6 freshness), so a new timestamp is not a changed condition.

The check's identity is `assertion:<path>|<filter>|<count label>`. It sits beside the finding fingerprints and never mixes with findings: a count result is never a finding row, and a missing finding never stands for a passed check.

Two finding-comparison fixes ship with this:

- **A UX finding that vanished from a journey that did not finish** (any status but `done`) is "not re-checked", not fixed. The test user may simply not have reached that step. Scan findings keep their page-based rule.
- **A finding reported twice counts once** on both sides of the comparison.

Callers that pass no journey status, and old saved comparisons without `assertion`, behave exactly as before.

## Repeating the check

The side panel button **Recheck my last count check** calls `GET /me/recheck?site=<origin>`. The request sends the origin only, never the tab's full URL. The endpoint returns the owner's latest declared check on that site from their latest 20 test runs: goal, test user, signed-in choice, status and the declaration.

The declaration comes back with `dataset_at: null`. The owner must enter the timestamp the page shows now; a stale one is inconclusive by R-S6 rules. The note warns that changing anything else makes the result not comparable, and whether the plan no longer includes signed-in pages. Starting the run then follows the normal quote, admission and confirmation path.

## Example to reproduce, repair and recheck

Use the R-S6 golden fixture (`evals/fixtures/easy/dashboard.html`), hosted on your own verified public or staging domain. The API refuses localhost targets for real runs.

1. **Broken.** Serve the page in its `case=mismatch` behaviour: Active still shows all three rows. Run goal **Filter Active records** with the count check: path `/dashboard.html`, filter `Active`, label `Filtered records`, expected 2, dataset `synthetic-sales-v1`, the page's displayed dataset time, tolerance 0. The report shows the check **failed** (3 against 2).
2. **Repair.** Serve the normal page, where filtering leaves Alpha and Beta, then reload it.
3. **Recheck.** In the side panel press **Recheck my last count check**, enter the newly displayed dataset time and start. The new report's "Since your last run" shows **Count check: Fixed**, with "Before: failed (3). Now: passed (2), expected 2."
4. **Counter-checks.**
   - Change the expected count to 3 and run again: **Not comparable (expected count)**.
   - Leave the dataset time stale: **Not re-checked** (inconclusive).
   - Use `case=blocked`: **Not re-checked** (blocked).

None of these can read as Fixed.

`tests/test_recheck.py` runs the same scenarios against the real report contract (`assessment(3)` then `assessment(2)` from the R-S6 tests) through the actual report job.

## Verification (2026-10-07)

- **API** (`tests/test_recheck.py`, 20 tests):
  - six verdict pairs, each validated against the schema;
  - inconclusive, blocked and undeclared reruns;
  - six changed-condition cases, plus a fresh timestamp that is not a change;
  - the same-condition fix through `attach` and through the real report job;
  - old comparisons still readable;
  - duplicate findings;
  - UX findings from an unfinished journey;
  - `/me/recheck` returns the latest own declaration only, with no timestamp and none from another account or site.

  The ownership matrix covers the new route. Neighbouring compare, assertion, contract, chapter, funnel and MCP suites: 126 passed.
- **Web:** 52 node tests passed, including the new recheck label and count wording, plus TypeScript, build and lint. The actual `RerunComparison` in isolated headless Edge passed 9/9 checks with no console errors: fixed, not re-checked, not comparable, an old comparison without a recheck, the unfinished-journey UX note, the accent token on Fixed, no em dashes, and no overflow at 320 and 768 px. Artifacts are in ignored `evals/results/targeted-recheck/`.
- **Extension:** 164 passed, including a new test that only the origin is sent and the timestamp comes back empty; tsc and lint clean.

## Not built

- **Viewport.** Snapshots do not record the viewport, so a recheck at a different window size cannot be detected. To add it, record viewport width and height in the observation and compare breakpoints.
- **Older checks.** Rechecks of any but the latest declared check, and lookups past the latest 20 test runs.
- **A live recheck.** No signed-in, owner-authorized rerun on a deployed site was performed, and the side panel button was not checked in a loaded extension.
- **MCP.** MCP reports do not yet print the recheck verdict; the saved report JSON carries it.
