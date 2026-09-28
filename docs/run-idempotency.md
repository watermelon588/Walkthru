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
