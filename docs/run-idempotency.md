# Run request idempotency (SD-6.5)

Implementation contract, 2026-09-28. Scope: POST /runs, /runs/{id}/observe and /runs/{id}/stop. Payment handling is separate.

- A client creates one UUID `Idempotency-Key` per intent and reuses it with the same body on transport retries.
- Claims are durable, unique per authenticated user and key, and bind the operation plus a canonical validated body hash.
  Cross-user requests never share responses. Changing the operation or body for an existing key returns 409.
- A completed claim replays its original status, body and safe application headers, before plan limits or agent work run again.
  Request support IDs are new on every HTTP attempt. Authentication and request-rate limits still run on every attempt.
- An in-flight duplicate returns 409 with Retry-After. Different keyed mutations of the same run are also serialized.
  There is no timeout-based takeover: an interrupted operation with an unknown outcome must not run again automatically.
- Unexpected errors preserve an uncertain claim. The user can inspect the saved run; operators investigate the reference.
  A stopped/crashed worker cannot be replaced by a retry that silently repeats its action. Automatic recovery of uncertain
  operations is not claimed by this feature.
- A running reply identifies its pending action. New clients send that ID with the next observation; a stale ID is rejected.
- Cached replies cannot be replayed after 24 hours. The next six-hour retention pass erases their payloads (normally
  24 to 30 hours after completion); a request after expiry erases its own payload immediately. Run deletion also erases
  payloads and fences late completions. Minimal key/hash tombstones remain until account
  deletion so delayed retries cannot recreate a deleted run. Raw request bodies are never stored by the idempotency layer.
- Legacy requests without a key retain their existing behavior and do not receive retry guarantees. Deploy the API and
  migration before the new extension. The extension enables automatic retries only after the policy endpoint advertises
  the new contract; it never retries a browser action, only the HTTP request carrying the already captured observation.

## Implementation and deployment

`app/idempotency.py` wraps the three run mutations. Migration `0003_run_idempotency.sql` creates `run_requests` and
service-only claim/completion/expiry functions. A short per-account advisory transaction lock serializes admission;
no database transaction stays open while the model runs. The unique account/key constraint stores one intent.
The server creates an attempt-owner UUID before calling the claim RPC, so a database transport retry can confirm its
own claim or completion without starting the application work again.

Apply migrations 0002 and 0003 before deploying the API and updated clients. Migration 0002 has its own maintenance
requirements in [the checkpoint guide](checkpoints-and-request-logs.md). **Neither migration was applied to production
by this work.** Check `python -m app.migrate status` using the intended environment, then follow the approved deployment
procedure. Run the API and a job worker so the six-hour retention pass executes. Rolling the API back must preserve
the ledger: there is deliberately no destructive down migration that forgets old keys.

The extension freezes the body and key for each intent. After `/runs/policy` advertises `idempotency: "v1"`, it permits
at most three attempts, each with a 90-second HTTP timeout. It retries transport failures, interrupted successful
response bodies, HTTP 408/502/503/504 and `409 request_in_progress`. Backoff is 250/500 ms, or the positive `Retry-After`
delay capped at five seconds. Authentication failures, other 4xx replies and explicit `request_outcome_unknown` are
terminal. No snapshot, screenshot or browser action is repeated by this loop. Action IDs also stop the browser loop
if the API returns an action it already executed. This protection lasts for that live side-panel journey; automatic
resumption after closing the side panel is outside this feature.

Web dashboard stops also carry keys. Legacy requests without keys still work but can race with keyed requests; they
do not get serialization or replay guarantees. Enforcing a minimum extension version belongs to SD-9.4.

Report jobs use the existing queue's `report:<run_id>` deduplication key. A repeated stop or a lost database stop
acknowledgement can queue a missing partial report without adding another queued job. This uses SD-6.1's queue and
does not change its worker/retry behavior. Graph mutations themselves are never blindly retried after a database
error; safe checkpoint reads may retry.

## Unknown outcomes and support

A pending claim after process death remains pending. An application failure after admission records `uncertain` when
possible. Neither state expires into permission to run again; another keyed mutation of the same run is blocked too.
This favors avoiding repeated work over automatic recovery. An acknowledgement lost after a successful completion
write can still replay the committed response on a later retry.

Use the request reference to find safe diagnostic logs. A database operator can inspect metadata, without loading
cached action text or snapshots, using a parameterized query:

```sql
select key, operation, run_id, state, status, created_at, finished_at
from public.run_requests
where user_id = $1
order by created_at desc
limit 50;
```

Correlate the run with its stored steps, checkpoint and `report:<run_id>` job. Do not delete/reset a pending or uncertain
claim merely because it is old, or resend the operation under a new key: neither proves the original work did not
commit. There is no automated reconciliation tool in this change. A run can still be inspected or deliberately
deleted by its owner; deletion erases cached results, and account deletion removes its ledger rows.

## Verification scope

`tests/test_run_idempotency.py` exercises HTTP start/observe/stop with real PostgreSQL claim functions, constraints,
role permissions and deletion triggers. Application run rows and model calls use fixtures. It covers duplicate and
simultaneous requests, ownership, body/operation mismatch, stale/missing actions, lost completion acknowledgements,
expired caches, stuck claims, late completion after deletion and CORS. `test_persona.py` covers the lost stop
acknowledgement; `test_jobs.py` checks the stable report job key. No live model calls are required.

Extension tests exercise the real step loop and API client with a mocked browser and HTTP transport, including lost
observation replies, one browser click, repeat-action rejection, bounded retries and terminal errors. These are
automated local integration tests, not a deployed browser/VM acceptance run. Final suite results are in CURRENT_STATE.md.

## Session 1 local activation (2026-09-30)

The founder authorized V0-S1 implementation. The connected development database previously had only migration 0001.
With the local API and its worker paused, existing 0002 and 0003 were applied through `app.migrate`, without editing
migrations or application admission logic. The legacy checkpoint backup is a private, ignored custom-format dump in
`evals/results/v0-session-1/`; it contains user state and must never be committed or published. Backup metadata records
its checksum. All legacy counts were preserved in the private schema: 10 checkpoint migration rows, 224 checkpoints,
221 blobs and 877 writes. PostgREST schema reload was requested. All three applied checksums match; applying again
does nothing. Browser roles and the REST service role cannot read private checkpoints; only the service role may call
the run-request RPCs.

Live current-contract acceptance used the built extension snapshot/execution code in headless Chrome with stubbed
Chrome messaging, a dedicated test account, free models and the real API/database/storage. No TripBurst form was sent.

| Journey | Saved run | Actions / exact request replays | Outcome |
| --- | --- | --- | --- |
| Discover the sign-in page, homepage to signup to login | `814100f3ecf0463c8b5f078dd677784f` | 2 / 3 | done, report ready |
| Stop with the first action pending | `2e7fc3a801114f31955c88e814324a02` | 0 / 2 | stopped, pending step marked interrupted, partial report ready |

Each run consumed exactly one quota unit, has one saved run, one completed ledger entry per unique mutation and one
completed report job with one attempt. Replays returned the exact original JSON/status and `Idempotency-Replayed: true`.
A guarded synthetic request was aged past 24 hours: expiry erased its payload/headers, preserved `gone`, and a new
claim could not execute it. The guard locked the table and required that only that synthetic intent was eligible.
A broad live retention purge was rejected by automatic approval review; isolated tests verified the remaining cleanup
parts without deleting shared evidence. The strengthened retention regression confirms audit/job/rate-limit/request
cleanup still runs after screenshot cleanup fails.

Focused API migration/checkpoint/idempotency/persona/jobs/retention tests: 72 passed; after strengthening the retention
assertions its six tests passed again. Extension tests: 64 passed, one opt-in live-provider test skipped. API/eval Ruff
and extension type check/lint/build passed. Logs, migration/backup metadata, privilege/expiry checks and live acceptance
metadata are under `evals/results/v0-session-1/` (ignored local artifacts); reports are in `evals/results/e2e-<run_id>.json`.

To repeat the successful read-only acceptance from the repository root with the development API running on 8010:

```powershell
$env:WEB_URL = 'http://localhost:5174'
$env:WALKTHRU_API = 'http://127.0.0.1:8010'
$env:REQUIRE_IDEMPOTENCY = '1'
$env:VERIFY_REPLAYS = '1'
$env:PERSONA = 'skeptic'
Remove-Item Env:STOP_AFTER_STEPS -ErrorAction SilentlyContinue
& apps/api/.venv/Scripts/python evals/e2e_extension.py http://127.0.0.1:5173/ 'Find the sign in page without submitting any forms'
# Separate stop acceptance; creates another run and consumes another quota unit:
$env:STOP_AFTER_STEPS = '0'
$env:PERSONA = 'first_timer'
& apps/api/.venv/Scripts/python evals/e2e_extension.py http://127.0.0.1:5173/ 'Read the explore page and then the guide'
Remove-Item Env:STOP_AFTER_STEPS -ErrorAction SilentlyContinue
```

Use only an owned target/test account. Model-driven outcomes can vary: a separate planning attempt ended `gave_up`,
so it is not counted as a successful goal. The stop report also falsely interpreted a custom stop reason as navigation
trouble despite zero actions. That confirmed report-grounding defect is tracked under V0-S5; report generation here
proves the operational path, not correctness of that finding. Native sidepanel/permission/session-handoff acceptance
remains V0-S5. The local API still uses memory checkpoints; live durable restart/readiness remains V0-S2.

For a separate production database in Session 7, use this order:

1. Stop new run admission, resolve/drain active journeys, then stop **all** API/checkpoint writers and workers. Back up
   the database/checkpoint state and confirm a recovery path; compare migration checksums before maintenance.
2. Apply pending migrations through `python -m app.migrate` in numerical order, 0002 before 0003. Verify preserved
   checkpoint rows and private role permissions; reload the PostgREST schema and verify service-only RPC availability.
3. Start the API and worker with the Session 2-verified production configuration (`APP_ENV=production`,
   `CHECKPOINTER=postgres`, private checkpoint connection). Pass readiness and the restart drill before admission.
4. Deploy matching web/extension clients only after the API contract is usable; run keyed start/observe/stop/replay
   acceptance and verify quota/report counts. Native and deployed checks must pass before widening access.

Rollback must retain the ledger/tombstones and private checkpoint schema. Do not move checkpoints back to a public
schema or delete uncertain requests to make retries succeed. No production deployment was performed in Session 1.
