# Checkpoints and request logs (SD-6.2, SD-8.1)

Implemented 2026-09-28. Local restart and migration tests use disposable PostgreSQL databases and scripted models.
No provider calls or paid dependencies are needed. **Production migration and VM restart verification remain open.**

## Durable agent state

Development can use `CHECKPOINTER=memory`. Production must set `APP_ENV=production` and `CHECKPOINTER=postgres`.
An absent database URL, unsupported mode, missing migration, unreachable database or incompatible checkpoint schema
refuses startup; none falls back to memory. API lifespan initializes persistence before serving requests and closes
the pool on shutdown. The cache is protected against concurrent warmup/first requests.

Use `CHECKPOINT_DATABASE_URL` for checkpoints, or leave it empty to reuse `DATABASE_URL`. Point it at the same database
as the application. Choose a direct connection or the Supabase **session** pooler on port 5432, with `sslmode=require`.
Do not use the Supabase transaction pooler on port 6543: the saver uses connection/pipeline semantics that require a
direct or session connection. Session pooling works from an IPv4-only VM without buying the IPv4 add-on.
See [Supabase connection guidance](https://supabase.com/docs/guides/database/connecting-to-postgres) and
[LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/add-memory).

Each API process opens at most four checkpoint connections. Connections have bounded acquisition, connect, statement,
lock and reconnect timeouts, keepalives, and health checks before reuse. Keep API/worker process counts within the
database's connection allowance. Every resume uses the same run ID as LangGraph's `thread_id`.

`0002_agent_checkpoints.sql` owns the private `walkthru_checkpoints` schema. It installs the schema for the pinned
checkpoint-postgres 3.1.2 dependency and moves existing public checkpoint tables without discarding their contents.
Browser roles and the REST service role get no access; the server uses the database owner connection.
The schema must not be added to Supabase's exposed API schemas. Startup checks compatibility instead of running DDL.
Changing the checkpoint library's schema requires another numbered migration, tested on a scratch database first.

Before applying 0002, take a backup and stop API and worker processes. The runner applies the file atomically, including
its indexes. If both schemas already hold checkpoint tables, or the existing library schema is newer, migration stops
and rolls back for investigation. No automatic down migration is supplied: returning private customer snapshots to a
REST-exposed schema is unsafe. Do not roll back to the old public-schema runtime after moving populated checkpoints.
Use a compatible code release or a reviewed forward migration.

### VM activation and restart checklist

1. Set the environment above in the server's private environment file; never paste credentials into logs or this file.
2. From `apps/api` with its venv active, run `python -m app.migrate status`, then `python -m app.migrate` against the
   intended database during the stopped-service maintenance window. The migration command uses `DATABASE_URL`.
3. Disable tracing for the synthetic drill: `LANGSMITH_TRACING=false` and `LANGCHAIN_TRACING_V2=false`.
4. Generate a random ID with `python -c "import uuid; print('smoke-' + uuid.uuid4().hex)"`. Run
   `python -m scripts.checkpoint_smoke start smoke-YOUR_UUID_HEX`. It prints `running` and one saved step.
5. Start/restart the API service. Run `python -m scripts.checkpoint_smoke resume smoke-YOUR_UUID_HEX` in a fresh process.
   It must print `done` and two steps, with the first action preserved. It deletes only that smoke thread's state.
   Both phases use synthetic page text and a scripted model: they do not scan a site or call a provider.
6. Finally run an extension journey on a controlled fixture, restart the API while an action is pending, and submit the
   next observation. Confirm that it completes rather than returning an early-stop report, and save the timestamp,
   release, run ID and result in CURRENT_STATE.md. Mark SD-6.2 complete only after this VM check passes.

Persistence protects acknowledged checkpoints, not exactly-once browser actions across a lost HTTP response.
Retry idempotency is implemented separately in [SD-6.5's run contract](run-idempotency.md), with migration 0003 required
before activation. Graph/state changes must remain compatible with pending runs.
An HTTP lifespan restart is tested locally with real checkpoints and fake application rows; a separate two-process
test exits without shutdown hooks before resuming. These complement, but do not replace, the deployed extension test.

## Request correlation and safe logs

The API and standalone job worker configure JSON logs on stderr. A new server-generated, 32-character hex
`X-Request-Id` accompanies every HTTP response, including validation, body-limit and unhandled errors. CORS exposes it.
The shared web and extension API clients add `Reference: <id>.` to errors. Caller-supplied IDs are ignored.

Each completed request records its ID, authenticated UUID when available, method, **route template**, status and total
duration in milliseconds. No raw path or query is recorded for unmatched routes. The completion event is
`request_finished`, or `request_failed` for an uncaught exception. The correlated `server_error` event includes the
exception class and traceback locations (file basename, function, line); the founder's error record retains the same ID.
Startup emits `checkpoint_ready` or `checkpoint_unavailable`. Background jobs and pre-auth failures can have null user
and request IDs. This change does not add distributed tracing or propagate IDs into queued payloads.

The formatter allowlists fields and event names. It never formats arbitrary messages, arguments, exception text,
headers, access tokens, emails, snapshots, typed values or arbitrary extras. Existing free-form logs keep their source
location and severity, with event `log`; their message is deliberately omitted. Uvicorn's raw URL access log is disabled.
A broken log sink does not fall back to Python logging's unsanitized error diagnostic. Do not add another raw handler.
External tracing is a separate pipeline: these guarantees do not scrub LangSmith captures or reverse-proxy logs.

Questions these logs answer:

- **Which request failed?** Search the user's reference ID; compare route/status and the correlated error frame list.
- **Was the failure shared or isolated?** Count failed requests by route and status over the incident window.
- **Was it slow or unavailable?** Compare request `duration_ms`; `database_unavailable` identifies handled DB failures.
- **Did durable storage initialize?** Look for `checkpoint_ready` before accepting production traffic.

For example, after replacing the ID and saving API stderr as `api.jsonl`:

```powershell
Get-Content api.jsonl | ConvertFrom-Json | Where-Object request_id -EQ 'THE_32_CHARACTER_REFERENCE'
```

Limit log access to operators and use bounded retention in the eventual process supervisor/log service. Metrics,
error-tracking SDKs, alerts and operational runbooks remain SD-8.2, SD-8.3 and SD-8.5.
