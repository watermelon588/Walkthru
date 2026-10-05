# Database history reads and count evidence

R-S14a, 2026-10-05. This document distinguishes repository query contracts and isolated local measurements from deployed Supabase behavior. No production connection, migration, new index, paid call or dependency was activated.

## Query and index inventory

The inventory follows migrations `0001_initial.sql` through `0003_run_idempotency.sql`, not a claim about the live database. API reads use the secret-key Data API and therefore retain explicit owner filters; browser reads also use RLS. The baseline RLS permits owner, public and team-shared reports, so RLS alone does not mean a history row belongs to the current owner.

| Surface | Query and bound | Existing repository index/policy | Assessment |
| --- | --- | --- | --- |
| Dashboard owner history | Metadata only, owner equality, excludes comparison parts; descending `(created_at,id)`, page size 50 | `runs_user_created(user_id,created_at desc)`; owner/public/team RLS | Deterministic tie continuation preserves stored timestamp precision. Report and step JSON stay in detail loads. |
| MCP owner history | Explicit owner equality; literal case-insensitive site substring in database; descending `(created_at,id)`, maximum 50 | Same owner index; API owner filter remains authoritative | Metadata plus scalar launch score, no full report or evidence payload. Cursor is scoped to owner and site. |
| Detail and account export | Detail selects one ID; account export retains its existing separate full-row contract | Run primary key; API ownership checks | History pagination does not silently turn a list into an export. Export limits and streaming are a separate concern. |
| Anonymous public cache | Exact URL, scan/free, anonymous, public, completed, non-null report, creation within ten minutes; one row | No dedicated matching partial/composite cache index | Strict reuse scope is retained. Local empty-result plan alone is insufficient evidence to add an index. |
| Owner run admission usage | `HEAD`, `Prefer: count=exact`, owner/kind/time filters | Owner index | Counts no longer depend on response row limits. Missing/malformed exact-count headers fail closed. |
| Complete owner site usage | Slim `id,site`, test/time/owner filters, ascending ID keyset batches | Run primary key plus owner index | Continue through short server-capped pages until empty; reject nonadvancing IDs. Avoid carrying reports/steps through plan calculation. |
| Global free daily usage | Exact `HEAD` count, kind/free/UTC-day filters | No dedicated free-daily partial index | Exact read is not an atomic reservation. Paid run reserves and concurrent quota admission remain R-S8/R-S9. |
| Founding paid offers | Exact `HEAD` count, founding/paid filters | No dedicated founding/paid count index | Preserve the financial cap semantics independently of response limits; no speculative index added. |
| Jobs | Oldest queued/due projection of ID/kind/run-after, limit 1; claim through existing RPC | `jobs_ready(run_after)` partial queued/running; `jobs_finished(updated_at)` partial terminal; unique dedupe key | Read-only monitoring plan inspected. Mutating claim/admission RPCs were not benchmarked. |
| Citation scheduling | Due sites, next-check ascending, limit 20 | Unique `(user_id,site)`; no next-check scheduling index | Empty local ancillary table plan is structural evidence only. Measure a representative populated deployed workload before changing schema. |
| Citation history/queue | Site history descending timestamp/ID; queue ascending timestamp/ID; bounded batch reads | `citation_checks_site(site_id,created_at desc)`, partial queue `(status,created_at)`, engine/checked-time index | Existing bounded reads retained. Offset-based batched detail history remains a bounded snapshot-style view, not a concurrent streaming history guarantee. |
| Citation counts/admission | Exact completed-check and engine backlog counts; site batch IDs read with advancing ID pages; queue/claim RPC already serializes counts with advisory/site/quota locks | Existing citation indexes and quota engine primary key | Distinct batch counts use complete slim pagination because ordinary exact row counts are not distinct counts. Repository atomic citation admission remains intact. |
| Team shared-run history | Team filter, shared-time descending, bounded board/history read | `team_runs_team_shared(team_id,shared_at desc)`; member-only RLS | Existing timestamp-only continuation can skip equal-time shares. Changing team UI/routes is outside this owner-history slice and remains documented work. |
| Team messages/events | Team/thread filters; bounded ID keysets | `team_messages_thread(team_id,thread,id)`, `team_events_team(team_id,id desc)`; membership policies | Existing ID cursor behavior preserved. Member revocation continues to govern visibility. |

## Continuation and account privacy

Run IDs are the application's 32-character lowercase hexadecimal IDs, not hyphenated UUIDs. Stored ISO timestamps retain up to six fractional digits; converting a continuation boundary through JavaScript `Date` would lose microseconds. Timestamp and ID validation happens before assembling PostgREST predicates.

Every owner query includes an owner equality filter even when the viewer can read public or team-shared rows. A continuation token grants no access. New rows newer than the current boundary appear on refresh; inserts behind a boundary may appear in a later page, so this is a stable keyset traversal, not a transaction snapshot. Row IDs deduplicate repeated UI replies. Page errors retain loaded rows and a retry path; account/session changes clear visible rows and discard stale replies. Plan-display reuse is scoped to account/session with finite lifetime; balances and permission decisions still come from the server.

An empty page proves exhaustion. A short nonempty response cannot prove it because PostgREST can impose a row cap. The web therefore keeps a continuation after every nonempty page, with one final empty read. The API fills at most `limit + 1` slim rows using advancing keyset subqueries through short caps; its extra row proves continuation. Both preserve complete history under configured response caps.

## Isolated performance evidence

The reproducible script is ignored `evals/results/history-pagination/query-benchmark.py`; its JSON output records actual `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` plans and repository indexes. It initializes and stops a disposable PostgreSQL 18 cluster, installs the repository migrations with Supabase role/auth/storage stubs, and creates 10,000 synthetic runs, including 2,500 owner runs. Ancillary tables are empty; their plans do not establish production performance.

Thirty measured warmed samples follow two warmups for each shape. Times include local SQL execution, fetch and JSON serialization, excluding HTTP, network, rendering and production load. Synthetic report and step contents are deliberately large and contain no user data. Before/after list projections select the same 50 rows.

| Shape | Returned rows | JSON bytes | Local p50 ms | Local p95 ms |
| --- | ---: | ---: | ---: | ---: |
| Previous web list with report/steps | 50 | 1,347,041 | 13.558 | 15.310 |
| Metadata web list | 50 | 12,542 | 2.139 | 2.404 |
| Metadata plus one lookahead | 51 | 12,792 | 3.499 | 5.111 |
| API metadata plus scalar score, 20 + lookahead | 21 | 5,983 | 1.677 | 2.128 |
| Exact owner count | 1 scalar | 16 | 2.435 | 2.985 |

The same-size web payload dropped 99.07%; local median fetch/serialization dropped 84.22%. These are synthetic local measurements, not promised end-user or deployed API p50/p95. The final web empty-page continuation contract does not require lookahead; that sample documents the investigated alternative. The API retains bounded lookahead.

The existing owner index serves the filter and timestamp order; PostgreSQL used incremental sorting for the ID tie break. On this fixture it remained sub-millisecond at the SQL plan level. A new `(user_id,created_at desc,id desc)` index is therefore deferred: no demonstrated bottleneck justifies its write/storage cost yet. Cache, citation-due and team plans were inspected structurally, but adding indexes based on empty tables would be speculative. No migration is required by this implementation.

The SQL traversal collected all 2,500 owner rows across 100 pages, including 100 timestamp groups. A concurrent newest insert did not cause duplication or gaps in the remaining traversal. Actual baseline RLS was exercised as `authenticated`: the owner saw all their rows, while only explicitly public rows from another owner were readable. The list owner filter excludes those public rows. These SQL checks complement application cursor/filter tests; they do not replace a deployed PostgREST contract test.

## Verification and remaining deployment checks

Final source review covered correctness, readability, architecture, privacy and performance. Affected API suites passed 136 tests; a subsequent exact-count adaptation of the legacy citation-capacity fixture passed 89 affected tests, and whole API Ruff passed. Web passed 34 tests, TypeScript/Vite build and zero-warning lint. Actual installed Edge passed 20 component checks: twelve real history panel/hook/pager/pipeline checks and eight real dashboard/sidebar plan-meter checks using real plan-cache/read/invalidation code with fixture auth and intercepted fetch. These cover loaded-row retry, duplicate dispatch, 107 tied-time rows, account clearing, notification coalescing, account switching after retry and late old responses. An actual browser review found the retained retry-intent race; the implementation now invalidates in the retry handler and shares ordinary reads after identity changes.

Ignored artifacts are `browser-qa.json`, `plan-browser-qa.json`, `query-benchmark.json` and `regex-qa.json` under `evals/results/history-pagination/`, with fixture scripts beside them. Five PostgreSQL regex fixtures passed for literal wildcard/punctuation/quote/backslash/Unicode/newline values. Browser stubs do not establish installed auth or deployed transport acceptance. Initial shared API verification with R-S4 reported 895 passed, 19 skipped and two failures, both repaired with focused regressions passing. Broad sandbox verification then passed 862 tests with 19 existing PostgREST-dependent skips, exit 0 in 132.52 seconds. Final combined full API verification passed **902 tests, with 19 existing PostgREST-dependent skips**, one existing Starlette/AnyIO warning and exit 0 in 526.71 seconds. This includes all disposable PostgreSQL suites; the unrelated concurrency fixture now keeps its burst within one fixed window while separately testing rollover, without changing production SQL. Final ignored evidence is `evals/results/restructure-session-4/api-full-final-c.log` and fresh `api-full-final-20261005c` basetemp. The earlier approval-review capacity failure is resolved.

Deployed indexes, runtime query plans, production latency and actual hosted PostgREST parsing have not been inspected. Before deployment, compare applied migration checksums and indexes, verify exact-count response headers and literal special-character site filters against the configured PostgREST version, and measure representative owner/cache/scheduling queries with authorized read-only access.

Reference behavior: [PostgREST pagination and count](https://docs.postgrest.org/en/v12/references/api/pagination_count.html), [Supabase query optimization](https://supabase.com/docs/guides/database/query-optimization), and [PostgreSQL EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html). Exact counts are authoritative reads at their statement time; they are not reservations or a concurrency guarantee.
