# Saved suites and honest coverage (R-S14)

Implemented locally 2026-10-07. Code:

- `apps/extension/lib/suite.ts` (model, storage, orchestrator, coverage);
- `entrypoints/sidepanel/SuitePanel.tsx` and `runSavedSuite` in `App.tsx`;
- the `.suites` styles in `panel.css`;
- `apps/api/tests/test_unattended.py`.

No migration, dependency, model call, plan change or new server route.

## What a suite is

A named list of up to **6 scenarios** on **one site**. Each scenario is the side panel's current setup, saved: start page, goal, test user, signed-in choice, step cap and an optional R-S6 count check. A suite runs them one after another in the owner's own browser.

It covers only those scenarios. The side panel says so: "It covers only these scenarios, not your whole app."

Suites are saved in **this browser only** (`chrome.storage.local`, at most 20). Syncing across devices or a web view would need a server table with RLS, which means a reviewed migration.

## Budgets: one phase, one run

Each scenario is an ordinary run:

- its own R-S10 quote, step cap and run credit;
- the R-S8/R-S9 reservation;
- the extension's 4-minute limit.

There is no shared pool that one scenario could drain for the next. If a quote is refused (no runs left, plan limits, an expired session), the suite stops there: that scenario is not tested and the rest stay pending.

## Stop, resume and recovery

Progress is saved before and after every scenario (`walkthru_suite_run`):

| Situation | Result |
|---|---|
| Owner presses Stop | That scenario is "Stopped by you", not tested and resumable; the rest stay pending |
| Side panel closed mid-scenario | On the next run it is "Interrupted", not tested and resumable |
| Step cap (`budget`) or Walkthru lost its way (`agent_lost`, `looping`) | Not tested, **not** resumable: rerunning would spend another credit on the same limit, so the owner decides |
| Suite edited after a partial run | The old progress is not resumed against the new list; it starts afresh |
| Another account connects | The suite stops and records nothing more. That account's progress is dropped, never shown or resumed under another account |

**Resume (n left)** runs only the pending and resumable scenarios. Finished ones never run again. An interrupted or stopped scenario reruns as a new run (a new credit); the earlier partial run keeps its own report.

## Sign-in handoff

A signed-in scenario does not request a quote or spend a credit until the owner confirms: "Sign in to the site in this tab yourself, then continue. Walkthru never signs in for you."

**Not now** leaves it not tested and resumable. Plan rules still apply: a plan without signed-in pages gets the quote's 403 as the reason.

## Coverage

Coverage is shown in the side panel after or during a run:

- **Tested:** the test user reached the goal (`done`), or got genuinely stuck (`gave_up`, `stuck`). The report says where.
- **Blocked:** a human check (`captcha`, `bot_wall`) or a safety stop (`safe_stop`).
- **Not tested:** not started, stopped, interrupted, step cap, Walkthru's own loss, refused terms, waiting for sign-in, or an open error.
- **Declared checks:** each scenario's count check with a link to its report. The verdict lives in the report (R-S6, R-S13); the panel never guesses it.
- **Pages visited:** paths on the suite's site that the test users reached. They are "found along the way. Visiting a page is not a promise it was checked." Other origins never count.

## Nothing unattended

- A journey needs the owner's browser: `POST /runs` requires an executed observation (422 without one), and every step comes from the extension.
- There is no schedule, MCP tool or API route that starts or resumes a suite.
- MCP has no journey entry point.
- Watch checks (weekly, manual, deploy hook) are server scans.

Tests enforce these. A suite only runs while its side panel is open and the account is connected.

## Example

On your verified site, run each of these and press **Save scenario** with suite name "Launch checks":

1. Goal "Find the pricing page", 12 steps.
2. Goal "Start a free trial", 12 steps.
3. Signed-in goal "Filter Active records" with the R-S6 count check.

Then press **Run suite**:

- Scenarios 1 and 2 run with their own quotes.
- Scenario 3 asks you to sign in. Press **Not now** and coverage shows "Not tested (1): Waiting for you to sign in".
- Sign in, press **Resume (1 left)**, and only scenario 3 runs.

Close the side panel during a scenario and reopen it: that scenario shows "Interrupted" and Resume offers it again.

## Verification (2026-10-07)

- **Extension:** `tests/suite.test.ts`, 10 tests:
  - own quote per scenario, with step cap, captcha and done outcomes;
  - stop then resume without rerunning finished scenarios;
  - a closed panel recovered as not tested and resumable;
  - a refused quote stops the suite and keeps the rest pending;
  - an account change records nothing more;
  - sign-in handoff, declined then resumed, with no quote before consent;
  - coverage separation, with routes apart from declared checks and other origins excluded;
  - edited-suite progress refused;
  - one-site and size bounds;
  - storage, with another account's progress dropped.

  Full extension suite 174 passed/1 opt-in skip; tsc, lint and the WXT build pass.
- **API:** `tests/test_unattended.py`, 3 tests: no journey without an observation, no MCP journey entry point, and watch checks are scans that never invoke the agent. Run with outbound HTTP pointed at a closed local proxy.
- **Browser:** the actual `SuitePanel` in isolated headless Edge with an in-memory storage stub passed 15/15 checks with no console errors:
  - empty state, then save and list;
  - run fresh;
  - labelled inputs;
  - the three coverage lists;
  - declared checks shown apart from visited pages;
  - other origins excluded;
  - resume with what is left;
  - the sign-in alert and declining it;
  - no em dashes;
  - no overflow at 320 and 768 px.

  Artifacts are in ignored `evals/results/saved-suites/`.

A first draft of the watch test sent one request to the configured Supabase (`PATCH sites?id=eq.w1`). It was rejected with 400 because the id is not a UUID, and nothing changed. The test now fakes the sites table, and the R-S14 runs use the closed-proxy guard.

## Not built

- **Capacity and latency evidence** from real suite runs: no signed-in extension run was performed. Expect roughly the sum of each scenario's run time, at most 4 minutes each, run one at a time.
- **Server-side suites** (sync, a web view, team sharing).
- **Scheduled suites:** excluded by design. Unattended runs could not prepare a login or keep the owner's browser.
- **Parallel scenarios.**
- **Resuming inside a single run.**
