# Run quotes, hard caps and usage history (R-S10)

Implemented locally 2026-10-07. Code: `apps/api/app/quotes.py`, `POST /runs/quote`, `GET /me/usage` and `GET /runs/{run_id}/usage` in `app/main.py`, the quote binding in `_start_run`, MCP `get_run_quote`/`get_usage`, the side panel quote box (`apps/extension/entrypoints/sidepanel/App.tsx`), Billing "Usage history" and the Report usage note (`apps/web/src/pages/Billing.tsx`, `Report.tsx`).

No migration and no new flag that changes default behaviour. A quote describes the terms; it is not a credit. The reservation ledger (R-S8/R-S9) remains the only thing that admits work.

## What a quote pins

`POST /runs/quote` takes `{site, personas (1 to 5), logged_in, max_steps, assertion}`. It returns `{token, terms, summary, rules}`. It refuses with the same 402/403 a start would give, for example signed-in pages on Free or more test users than runs left.

| Term | Value |
|---|---|
| Scope | site origin, public or signed-in pages, the test users, whether a count check is attached |
| Caps | `max_steps` (the request, clamped to the plan) and `max_minutes` = 4 (the extension's hard limit, `lib/safety.ts`) |
| Credits | plan, plan window, runs this uses, runs left before |
| Money | `price_version` and `max_cost_microusd_per_run` from R-S8, plus `ledger`: `active` when reservations are on, `plan_count` otherwise |
| Route | `model_route`, the plan's model label |
| Expiry | `exp`, 10 minutes |

The token is stateless: base64 JSON plus an HMAC-SHA256 signature. The key is `QUOTE_SIGNING_KEY`, else `SUPABASE_SECRET_KEY`, domain-separated. Set `QUOTE_SIGNING_KEY` in production so rotating one secret does not affect the other.

`summary` is one plain-language paragraph shared by the API, MCP and the side panel. `rules` are the four cap rules:

- A run stops at its caps with a partial report.
- Nothing is topped up or charged automatically.
- The route is fixed.
- A stopped run keeps its partial evidence.

## Acceptance

`POST /runs` with `quote` checks, in order:

1. **Signature, version and account.** Otherwise 409 "belongs to a different account" or "not valid".
2. **Expiry.** Otherwise 409 "expired".
3. **Scope.** The request may not exceed the quote: same origin, same pages, a test user in the quote, the same count-check choice. Otherwise 409 "asks for more than its quote".
4. **Current terms.** The server recomputes its terms. If the plan, window, price version, per-run maximum, model route, time cap or ledger mode changed, it answers 409 `STALE`: "The terms changed since this quote. Review the new quote and start again." It never silently applies new terms.

The run's `max_steps` is then clamped to the quoted cap, so a client can never ask for more steps than it was shown.

A start without a quote still works (older extensions) unless `RUN_QUOTES=required`; then it gets 428. Flip it once the updated extension is published.

The side panel requests a quote for exactly the current form (debounced 300 ms) and shows its summary and rules. Start stays disabled until a quote is present. A quote that expires within 60 s is refreshed before starting. A 409 shows the server's message, and the refreshed quote is shown for the next attempt.

## Usage history

`GET /me/usage` returns up to 50 of the account's reservations, newest first, each explained by `quotes.explain`:

| State | Text |
|---|---|
| released | Returned: the work never started, so 1 test run and the reserved $X were released. |
| settled, credit 1 | Used 1 test run (completed). |
| settled, credit 0 | Not counted: the goal was refused before the test started / it failed after starting, so 1 test run returned. |
| reserved, dispatched | In progress or awaiting its result: ... counted until it settles. |
| reserved, not dispatched | Admitted, not started yet: ... held. |
| refunded | Refunded by Walkthru (reason): ... returned. |

Each item also has a cost line:

- "Provider cost $X." when an actual cost is known.
- "No provider cost reserved." on a $0 route.
- Otherwise: "Provider cost not measured yet; counted at the reserved maximum of $X."

Anonymous Instant Scans are not this account's usage and are left out. With `RESERVATIONS=off` (the default) the answer is `{ledger: "off", items: [], note}`, and the web shows the note.

`GET /runs/{run_id}/usage` (owner only; a foreign id gets 404) returns the run's stop status, the number of steps it recorded and, when the ledger is active, its explained settlement. The Report page shows this as a small "Usage" box under a finished test run. It is not printed.

MCP `get_run_quote(site, test_users, logged_in)` returns the same summary and rules. It adds the prerequisite that the run starts from the extension side panel, in a tab on that site. MCP `get_usage()` returns the same lines.

## Verification (2026-10-07)

- **API** (`tests/test_quotes.py`, 15 tests):
  - pinned terms and plan refusals;
  - accepted start;
  - refusals by site, test user, signed-in pages and count check;
  - the step-cap clamp seen by the runtime;
  - expired, tampered, garbage and foreign tokens;
  - stale price version, per-run maximum and plan;
  - `RUN_QUOTES=required`;
  - every usage outcome;
  - owner-only run usage;
  - MCP parity.

  The ownership matrix covers all three routes.
- **Extension** (`tests/quote.test.ts`, 3 tests): the quote is requested for exactly the run's scope, the accepted token is sent with the start, and no token is sent when none was accepted.
- **Web, headless Edge:** the actual `UsageHistory` and `RunUsage` components with a stubbed API, loopback only. 11/11 checks, no console errors: active, ledger off, empty, error, loading, the no-print run note, no em dashes, and no overflow at 320 and 768 px. Artifacts are in ignored `evals/results/run-quotes/`.

## Not built, decisions pending

- **Customer terms.** The wording of the rules and the summary is a draft for the founder to approve before paid runs. Paid per-run maximums are still 0 pending approval (R-S8).
- **Resume.** A stopped run is continued by starting a new run. Its credit and evidence are shown, but there is no "continue from step N".
- **Route enforcement mid-run.** The model route is pinned at acceptance. Fallbacks inside the route are named in the report; a mid-run route change is not separately refused.
- **Side panel QA.** The quote box was not checked visually in a loaded extension. Unit tests, tsc and lint cover it.
- **Usage history paging.** It stops at 50 rows.
