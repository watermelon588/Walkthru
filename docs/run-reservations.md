# Run reservations and settlement (R-S8)

Implemented locally 2026-10-06. Code: `apps/api/app/reservations.py`, reservation wrappers in `app/db.py`, the hooks in `_start_run` (`app/main.py`) and the `finish_run` job (`app/jobs.py`). Proposed storage: `apps/api/migrations/0005_run_reservations.sql` with a reversible `.down.sql`. This follows the T14 run-reservation protocol in [payment.md](../payment.md#run-reservation-protocol).

Nothing here charges a customer, changes a price, creates a grant, routes to a paid model or activates a migration.

## Activation status

`RESERVATIONS=off` is the default. It makes no reservation requests, and today's count-based admission (`plans.check_start`) is unchanged.

Migration 0005 is **proposed**. It was tested only on disposable local PostgreSQL. No configured or hosted database was inspected or migrated. Activation needs separate founder authorization, in this order:

1. Apply 0005 with the migration runner.
2. Insert both `spend_budgets` rows (`platform_daily`, `platform_monthly`) with the approved limits in micro-USD. Zero is allowed while every plan's cap is zero.
3. Set the approved per-run caps `RUN_MAX_COST_MICROUSD_LAUNCH`, `_PRO` and `_PLUS`. They default to 0 until approved; free runs use free models at 0.
4. Set `RESERVATIONS=postgres` on the API **and** the standalone worker, then restart both.

Activate at a counting-window boundary. Runs made before activation are not counted by the ledger (see Limits).

## Authority

The database is the authority for admission. One `reserve_run` transaction does all of this:

- Takes a per-user advisory lock, then locks both funded budget rows. That serializes admissions platform-wide, which is simple and exact at V1 volume.
- Replays an existing reservation for the same `(user, operation key)`. The key is the accepted run ID, so request replays reuse it. Conflicting terms return `conflict`.
- Refuses with `unfunded` unless both budget rows exist.
- Counts the user's credits in use for the exact plan or pass window: open reservations, plus settled runs whose outcome used the credit. Refuses with `no_credits` at the allowance.
- Adds the run's maximum cost to each window's liability (UTC day, UTC month) and refuses with `budget` if it would exceed the funded limit.
- Inserts the reservation.

Liability counts open, settled and refunded work at its actual cost, or at its reserved maximum while the actual cost is unknown. Released work counts nothing. Money is integer micro-USD with a `price_version` (`run-caps-2026-10-06`). The Python layer fails closed: no confirmation means no run and no model call.

## State machine

```text
reserve_run ──> reserved ──mark_reservation_dispatched──> reserved + dispatched
   reserved (never dispatched) ──finish: released / not_dispatched──> released     (credit and budget return)
   reserved (any)              ──finish: settled / reason, credit──>   settled      (cost: actual, or the max if unknown)
   settled (credit 1)          ──refund_reservation (founder only)──> refunded     (credit returns, cost stays counted)
```

- **Dispatch before work.** `mark_reservation_dispatched` runs immediately before the first model call (the goal planner). If it cannot be confirmed, the reservation is released and the run returns 503 without calling a model.
- **No release after dispatch.** A dispatched reservation can only be settled. Nothing releases on a lease, timeout or timer. A worker that dies after dispatch leaves the reservation open, and it counts its credit and maximum cost until a settlement records the outcome. Settlement reasons are `completed`, `stopped`, `failed`, `refused` and `reconciled`.
- **Credit and cost are separate.** `credit` (0 or 1) records whether the customer's run was used:
  - A goal refused by the planner settles `refused` with credit 0. As before, it does not use a run, but its provider cost stays counted.
  - A start that fails after dispatch settles `failed` with credit 0.
  - A finished report job settles `completed` with credit 1.
- **Idempotent and order-safe.** An identical terminal payload replays as true; a conflicting one returns false. A late dispatch mark on a settled reservation acknowledges without reopening it. A dispatch mark on a released reservation is refused. The report job settles on every attempt, so a crash between saving the report and settling is fixed by the retry.
- **Refunds have an owner.** `refund_reservation` requires actor `founder` and a reason, only applies to a settled run that used its credit, and is executable only by the database owner (founder SQL or the local admin). Grants stay `entitlements` rows with their existing `source`.

## Storage and permissions

`run_reservations` and `spend_budgets` have row-level security and revoked grants. `anon` and `authenticated` can neither read them nor call the functions. `service_role` can read both tables and call `reserve_run`, `mark_reservation_dispatched` and `finish_reservation`. It cannot insert, update or delete rows directly, change budgets or refund; refund and the internal liability function are explicitly revoked from it, because Supabase default privileges would otherwise grant execute. Rows hold opaque user UUIDs, run keys and amounts only. Rollback deletes reservation history and budget configuration.

## Verification

- Disposable PostgreSQL, 13 tests in `tests/test_run_reservations_sql.py`:
  - 20 concurrent starts for one user with 3 credits admit exactly 3.
  - 10 concurrent users against a 1,000 micro-USD daily budget at 300 each admit exactly 3.
  - Unfunded budgets fail closed.
  - 8 concurrent replays produce one reservation, and conflicting terms are refused.
  - Release is refused after dispatch; settlement is idempotent and conflicting payloads are refused.
  - A refused goal returns the credit but keeps its cost.
  - A crash after dispatch, in a separate process that exits: the reservation stays counted and is not releasable, and reconciliation settles the actual cost.
  - Out-of-order marks.
  - Founder-only refunds.
  - Public and customer roles are denied; the service role cannot write rows, change budgets or refund.
  - Rollback and reapply.
- Python wiring, 14 tests in `tests/test_reservations.py`:
  - Off mode makes no requests.
  - Reserve and the dispatch mark precede the planner.
  - Every refusal or unconfirmed reservation fails closed before any model call (402/409/503).
  - An unrecorded dispatch releases and starts nothing.
  - A refusal or a failure after dispatch gives the credit back.
  - The report job settles on every attempt; a settlement failure leaves the reservation counted.
  - Configuration is validated.
- The R-S7 rollback test was made order-aware now that 0005 follows 0004.
- Final full offline API: 1,063 passed, 19 existing PostgREST-dependent skips. API Ruff passed.

## Limits and pending decisions

- **Pre-activation runs are not in the ledger.** They are not counted toward a pass that is already running. Activate at a window boundary, or reconcile existing runs first.
- **Admission is serialized platform-wide** while budgets are locked. That is fine at V1 volume but would need sharded budgets at scale.
- **Actual costs are unknown by default.** Settlements send `actual_cost_microusd = null`, so the reserved maximum stays counted, which is conservative. Feeding R-S7 receipt totals or provider statements into settlement is reconciliation work, and the R-S7 estimates are partial token baselines, not bills.
- **Every entry point reserves since R-S9.** Instant Scans, MCP scans and checks, comparisons, watch checks, AI answer batches and Scout use the same ledger and budget through `reserve_work` (proposed migration 0006). See [shared work admission](work-admission.md).
- **Not yet decided by the founder:** the funded platform budgets, the per-run caps, the refund policy wording, and whether a run that delivered nothing meaningful should settle with credit 0 (today a finished report uses the credit, matching current counting).
