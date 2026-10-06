# Safe reuse and measured savings (R-S7a)

Completed locally 2026-10-06. Code: `apps/api/app/scan_reuse.py`, `db.recent_public_scan`/`db.latest_public_scan_id`, `POST /scans` in `app/main.py`, the reuse note in `apps/web/src/pages/Public.tsx`. No new cache service, dependency, migration, model call or provider request.

## Five kinds of reuse, kept apart

| Kind | Where | What it reuses | Fresh observation? | Status |
|---|---|---|---|---|
| Saved-report read | Report pages, exports, fix prompts, MCP `get_report` | A stored report, read again | No new observation and none claimed; the report shows its own date | Existing. Deterministic prompts/chapters add no inference (R-S5a) |
| Exact request replay | Idempotency keys on journey/run routes, receipt RPC retries (R-S7) | The answer to the same accepted request | No; it is the same request | Existing; never re-executes model or browser work |
| Eligible result reuse | Anonymous Instant Scan only (`POST /scans`) | A saved public scan of the exact URL, under ten minutes old, written by the current code and model configuration | No. Labelled `reused` or `coalesced` with `observed_at`; `fresh=true` forces a new scan | **R-S7a** |
| Deterministic artifact reuse | None | (Parsed pages, scan packets) | n/a | Not implemented. Reusing artifacts alone would not avoid the model calls |
| Provider prefix cache | Provider side, implicit | Repeated prompt prefixes | Not a cached answer; output and reasoning are still generated | Recorded, not assumed: R-S7 receipts keep cache read/write channels when supplied, unknown when not |

Never reused: owner and MCP scans (`scan_site`, `rerun`, `verify_finding`), weekly watch, comparisons and their parts, journeys and any browser action, signed-in pages and paid crawls. They always observe fresh. A reused or awaited result is never presented as a new test.

## Eligibility and invalidation

A saved scan is reused only when every rule holds:

- **Scope.** Anonymous, public, free-tier `scan` row of the exact normalized URL (path and query preserved), status done with a report (`db.recent_public_scan`). Owner rows can never match (`user_id is null`), so private data is never served to another caller.
- **Age.** Created within the last ten minutes. Reuse never extends the window.
- **Version.** `report.scan_version` equals the current `scan_reuse.version()`: a hash of the scanner, report, contract, schema, scoring and comparison source plus the configured Groq, Gemini, OpenRouter and Claude model lists. Any deploy that changes them, or a model configuration change, stops reuse of older scans. Reports saved before this field never match. Over-invalidation (a comment change) only costs a scan.
- **Revocation and deletion.** Every lookup reads the database; there is no process cache. A row that is unshared or deleted stops matching on the next request.
- **Current safety rules.** The owner opt-out, pause list and public-address check run before any lookup, and the per-address limit counts reused answers too.

## Fresh checks

`POST /scans {"fresh": true}` skips reuse, for re-checking a fix. It still pays the per-address limit, the daily free capacity and the per-host politeness limit. The public report shows a note for reused or coalesced answers: what happened, when the evidence was observed, that pages are reused for ten minutes, and a **Scan again now** button that sends `fresh: true`. While a fresh check waits on another request's scan, it accepts only a report that started after it asked.

## Simultaneous misses

Requests that miss for the same page start one scan:

1. A striped lock (64 stripes) inside each API process serializes requests for the page. The waiter re-checks and gets the winner's report, labelled `coalesced`.
2. Across processes, an atomic claim on the existing Postgres fixed-window counter, key `scanflight:` plus a hash of version, URL and the newest scan row ID of that page. A finished scan adds a row and frees the next claim at once. A request that loses the claim polls for the winner's report for up to 30 seconds. If none appears, it answers 503 with `Retry-After: 30` instead of starting a second scan.

Limits: a scan that fails before saving a row holds its claim for up to 60 seconds. When the counter's database is unreachable, `limits.hit` fails open, so cross-process coalescing becomes best effort and two processes can each scan once. Rare unrelated pages that share a lock stripe wait for each other. A request waiting on the claim holds one API worker thread for at most 30 seconds.

Keys hold hashes only: no URL, query string, credential or typed value. The response label is `{status: fresh|reused|coalesced, source_run_id, observed_at, age_seconds, reused_until, scan_version}`.

## Measured on owned fixtures

`apps/api/.venv/Scripts/python evals/scan_reuse_bench.py` uses the real `/scans` route, real scanners and report graph against the loopback fixtures. The two model calls per scan are scripted, every non-loopback DNS lookup is refused, and storage is in memory with fixed-window limits. Results are in ignored `evals/results/scan-reuse/bench.json`.

| Workload | Requests | Scans run | Reuse rate | Model calls avoided | Latency p50 / p95 |
|---|---:|---:|---:|---:|---|
| 60 repeat visitors over 4 exact URLs | 60 | 4 | 93.3% | 112 | reused 5.6 / 6.4 ms; fresh 2,894 / 4,527 ms |
| After a deploy (new version), 8 simultaneous visitors, 1 page | 8 | 1 | 87.5% | 14 | coalesced 2,407 / 2,413 ms; the scan 2,416 ms |
| Owner re-checks a fix with `fresh=true`, 3 times | 3 | 3 | 0% | 0 | fresh 2,215 / 2,404 ms |

These are local measurements of Walkthru's own work. They exclude network, model and production database latency, and they show avoided work, not a savings percentage for real traffic, which depends on how often the same page is scanned within ten minutes. No savings claim should be made from them. Provider-side cache hits are recorded per attempt by R-S7 receipts when providers supply them; their economics stay estimates until R-S8/R-S15 statements.

## Verification

- `tests/test_scan_reuse.py` (14) and the updated `tests/test_scan_cache.py` (20) cover: labelled reuse, stale and pre-versioning reports, version changes, `run_scan` stamping, fresh bypass under every limit, single-process and cross-process coalescing, the retry answer when the winner never lands, fresh waiters rejecting older evidence, hash-only keys, unsharing and the exact database queries.
- Reuse note in isolated headless Edge: 12/12 checks, no page errors (reused and coalesced wording, hidden for fresh/no state, sends `fresh: true` for the same site, error recovery, 320/768 px).
- Final full offline API: 1,036 passed, 19 existing PostgREST-dependent skips. Web 51 passed, TypeScript/Vite build and lint; API Ruff.
