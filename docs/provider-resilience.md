# Provider resilience (SD-6.3)

Completed locally 2026-09-28. No new dependency, credentials, paid provider activation or database migration.

`app/providers.py` shares health per provider within one API/worker process. Groq and Gemini health is shared by
journey/report models and citation requests. OpenRouter, Claude Vertex, direct Anthropic and TypeSafe have separate
circuits. Existing provider ordering and activation rules remain in force.

- Three consecutive failed calls open a circuit for 60 seconds. A success resets the failure count. Failed structured
  output counts as a failed call in the LangChain wrapper and falls through to the next configured provider.
- During cooldown, calls fail immediately with `CircuitOpen`; no sleep or outbound request. Other providers continue.
- After cooldown, one caller probes recovery. Others skip until it finishes. Success closes the circuit; failure
  restarts the cooldown. A generation counter prevents older in-flight results from closing a newer circuit.
- Only admission/state changes hold a lock. Already-running requests are not cancelled. State uses a monotonic clock,
  resets on process restart, and is not shared across machines/processes. This is an availability guard, not a quota
  or spend limiter. Existing database quota/rate controls remain authoritative.
- TypeSafe wraps transport/HTTP/JSON decoding only; a valid response with low confidence is normal abstention and
  does not trip its circuit. The usual LLM fallback handles both abstention and temporary unavailability.

## Timeouts and retries

| Path | Configured timeout | In-call retries |
|---|---:|---|
| Groq structured models | 8 seconds | 0 |
| Gemini structured models | 20 seconds | 0 |
| OpenRouter writer | 90 seconds, 5-second connect | 0 |
| Claude Vertex | 30 seconds | 0 |
| Existing direct Anthropic path | 30 seconds | 0; now falls back to the free pool |
| TypeSafe | 10 seconds | 0 |
| Groq citation requests | 60 seconds, 5-second connect | 0 |
| Gemini citation requests | 45 seconds, 5-second connect | 0 |

These are SDK/transport timeouts, not a total deadline across an entire fallback chain. No graph mutation or browser
action is retried by the circuit breaker. Job retries already use the durable queue's bounded attempts and exponential
backoff with jitter: 15-30 seconds initially, capped at 30-60 minutes. That queue behavior was verified, not rewritten.

Citation workers check availability before reserving quota. Checks remain queued when the circuit is already open.
If another thread opens it between the check and invocation, the reserved attempt remains conservatively counted;
the lease is released and the check is rescheduled for 60 seconds without increasing its terminal failure counter.
Actual quota responses retain the existing one-hour deferral. Circuit state never manufactures a citation result.

## Verification

116 affected tests passed across provider, runtime, TypeSafe, citation, job, persona, report, goal, MCP-tool and stop
reason suites. Includes a real local HTTP start/observe journey through the real graph/fallback chain with scripted
models, concurrency tests for one recovery probe and stale results, and queue preservation tests. External providers,
application database rows and browser observations are faked; no live or paid model calls were made. API Ruff passed.
This is focused verification, not a claim that the full repository/production acceptance suite ran in this task.
