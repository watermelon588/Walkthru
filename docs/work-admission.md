# Shared work admission (R-S9)

Implemented locally 2026-10-07. Code: `app/reservations.py` (`work`, `reserve_work`, `settle_work`), `db.reserve_work`, and one hook at each entry point listed below. Proposed storage: `apps/api/migrations/0006_work_admission.sql` with a reversible `.down.sql`. It extends the [R-S8 ledger](run-reservations.md).

Nothing here charges a customer, changes a price, creates a grant, routes to a paid model or activates a migration.

## Activation status

`RESERVATIONS=off` is still the default. It makes no reservation requests, and every existing count check is unchanged.

Migration 0006 is **proposed** and follows 0005. It was tested only on disposable local PostgreSQL. No configured or hosted database was inspected or migrated. Activation follows the [R-S8 order](run-reservations.md#activation-status): apply 0005 and 0006, fund both budget rows, set the approved caps, then set `RESERVATIONS=postgres` on the API and the worker.

## One authority

Every operation reserves in `run_reservations` through `reserve_work(owner, operation, key, window, allowed, units, max_cost, price_version)`. That is one transaction under the owner's advisory lock and the funded budget rows:

- **Allowance.** Units in use for the same owner, operation and exact window: open reservations, plus settled work that used its credit. `used + units > allowed` refuses with `no_credits`.
- **Budget.** The work's maximum cost is added to the same daily and monthly platform liability as journey runs. No operation has its own pool. An unfunded platform refuses everything.
- **Replay.** The same key returns the existing reservation. A released key (never dispatched) is re-admitted under the same checks. A settled key answers `replayed`/`settled`, and the caller refuses with 409 instead of executing again. Different terms answer `conflict`.

`reserve_run` (R-S8) is now the `run` operation of the same function, and keeps its R-S8 replay answer.

The server always picks the owner, the allowance and the price. The client never sends a wallet, owner or price. Costs are integer micro-USD per unit from `WORK_MAX_COST_MICROUSD_<OPERATION>`, default 0, because every route uses free models today. Windows are UTC days, except journey runs, which use the plan or pass window.

## Exits

`reservations.work(...)` wraps one synchronous piece of work and yields `dispatch`. The caller calls `dispatch` once, right before the first provider call.

| Exit | Ledger outcome |
| --- | --- |
| Refused or unconfirmed reservation | Nothing runs; 429/503/409. The database being unreachable fails closed with 503. |
| Never dispatched (the site did not answer, the per-host limit, a refused URL) | `released`: credit and budget return |
| Dispatched and finished | `settled` / `completed`, credit used |
| Dispatched and failed | `settled` / `failed`, credit returned, cost counted at its maximum |
| Dispatch mark not confirmed | Released; 503; no provider call |

Asynchronous work (comparisons, AI answer batches) uses `reserve_work` → `dispatched` → `settle_work`. Nothing releases on a timer or a lease.

## Entry-point inventory

Every route and job that can call a model, a paid data API or a media service, as of 2026-10-07:

| Entry point | Who / scope | Operation, owner | Allowance | Dispatch | Settlement |
| --- | --- | --- | --- | --- | --- |
| `POST /runs` (web, extension) | signed-in owner | `run`, user | plan or pass runs (R-S8) | before the goal planner | report job: `completed`; refused goal or start failure: credit 0 |
| `POST /runs/{id}/observe` (steps) | run owner | covered by the run's reservation | n/a | n/a | n/a |
| `finish_run` job (report) | run owner | covered by the run's reservation | n/a | n/a | settles every attempt |
| `POST /scans` (anonymous Instant Scan) | anyone; per-address and per-host limits first | `public_scan`, all-zero UUID | `FREE_SCANS_PER_DAY` platform-wide | after the page answers, before the report model | `work` exits |
| `POST /scans` reused report (R-S7a) | anyone | **none**: no regeneration and no debit | n/a | n/a | n/a |
| MCP `scan_site`, `rerun` | Plus API key's owner | `scan`, key owner | `mcp_server.SCANS_PER_DAY` | before the report model | `work` exits |
| MCP `verify_finding` | Plus API key's owner | `scan`, key owner | same daily allowance | before the re-check (PageSpeed may be called) | `work` exits |
| `POST /compare`, MCP `compare_sites` | paid owner | `scan`, user, **units = sites** | same daily allowance | job start, before the part scans | job end: `completed` |
| Comparison part scans | inside the comparison | covered by the comparison | n/a | n/a | n/a |
| Watch: weekly job, `POST /watch` baseline, manual check, deploy hook, MCP `watch_site` / `check_watched_site_now` | site owner (the hook token resolves the owner) | `watch`, site owner | `WATCH_CHECKS_PER_DAY` (20) | before the report model | `work` exits; a refusal on the weekly job reschedules in 6 h |
| AI answers: `POST /citations/{id}/check`, the weekly schedule, MCP `check_ai_answers_now` | paid owner | `citations`, user, **units = answers** | the plan's sites × prompts × engines a day | before the queue accepts the batch | the batch's last answer settles it (credit used when any answer came back); a queue refusal settles `failed` |
| Scout (`@Scout` in team chat) | workspace member | `scout`, **workspace** | `SCOUT_DAILY` (50) a workspace | after context is built, before Gemini | `work` exits; a refusal answers in the thread |

**Reviewed and not admitted.** These make no model, paid-data or media call:

- `POST /citations` (track a site): one homepage fetch and deterministic prompt suggestions.
- `POST /runs/{id}/fix-pr` and MCP `open_fix_pull_request`: GitHub API with config-only fixes from the saved report.
- `GET /runs/{id}/fix-prompt`, MCP `get_fix_prompt`, `get_report` and `get_finding`: built from the saved report.
- `POST /runs/{id}/email`, the `/scans` email copy and watch emails: send a stored report and never regenerate it.
- Verification, sharing, badges, team triage and notifications.
- Billing webhooks and the admin panel.

Request replay: `POST /runs` goes through the request idempotency layer (`app/idempotency.py`, migration 0003), and its reservation key is the accepted run ID, so a replay cannot debit or start twice. All other entry points take a fresh key per execution. Each execution that may spend is counted once.

## Scheduled work caps

Every scheduled entry point has a cap in the same ledger:

- Weekly watch: `WATCH_CHECKS_PER_DAY` per owner. The plan's site limit and the 10-minute hook cooldown still apply first.
- Weekly AI answers: the plan's day of answers.
- Scout: per workspace.

The existing quota, concurrency and stop rules still run first and give the quick plain-language answer. These are the per-address and per-host limits, `free_runs_today`, `user_scans_today`, the in-process MCP verify count, the citation queue's engine quotas and the Scout count. When reservations are on, the reservation is the authority: those reads can race, and the reservation cannot.

## Verification

- Disposable PostgreSQL, 10 tests in `tests/test_work_admission_sql.py`:
  - 16 anonymous scans against a capacity of 4 admit exactly 4.
  - 4 concurrent 3-site comparisons against a 10-scan day admit 3.
  - Each operation has its own allowance but one budget, which journey runs share.
  - A scan in exactly a journey run's window does not use the run credit.
  - A released key is re-admitted; settled work answers `replayed`/`settled`.
  - A released journey-run replay keeps the R-S8 answer.
  - Invalid input is refused.
  - Public and customer roles are denied; the service role can reserve.
  - Rollback restores R-S8 (non-run rows are deleted) and reapplies.
- The R-S8 SQL suite (13) and the R-S7 SQL suite (7) pass on top of 0006. The R-S8 rollback test was made order-aware.
- Python wiring, 21 tests in `tests/test_work_admission.py`. They run fully offline; they also pass with the database address pointed at a closed port.
  - Off mode makes no requests.
  - Each entry point reserves as the right owner (anonymous pool, key owner, site owner, workspace), with the right allowance and units, before its model call.
  - A reused scan reserves nothing.
  - Every refusal or unconfirmed reservation fails closed before any fetch or model call (429/503/409), and no run row is created.
  - A settled replay is not executed again.
  - No answer from the site releases; a failure after dispatch returns the credit and keeps the cost.
  - Comparisons reserve every site once; answer batches dispatch before queueing and settle when done.
  - Scout answers its limit in the thread.
  - Cost configuration is validated.

## Limits and pending decisions

- **The founder has not decided** the funded budgets, the per-unit caps (`WORK_MAX_COST_MICROUSD_*`), `WATCH_CHECKS_PER_DAY` (20 is a proposal) or whether anonymous scans should keep one platform-wide pool.
- **A comparison job retried after a late failure** re-runs its parts under the same reservation, so the second execution's cost is not counted twice. It only happens when saving the comparison fails after every part ran. If the dispatch mark fails inside the job, the reservation is released and the comparison stays without a report (fail closed).
- **A refused Instant Scan holds the page's coalescing claim** (R-S7a) for up to 60 s, so other visitors of the same page wait, then get 503. That is the existing behavior for any scan that fails before saving.
- **An AI answer batch whose last answer never finishes** stays open and counted at its maximum until reconciliation.
- **Admission is serialized per owner and platform-wide on the budget rows**, as in R-S8, and so are anonymous scans under one owner. That is fine at V1 volume.
- **Customer paid adoption stays off.** The inventory above is complete for 2026-10-07. A new model, data or media route must add a row here and a reservation before it ships. R-S10 (quote and cap UI) is next.
