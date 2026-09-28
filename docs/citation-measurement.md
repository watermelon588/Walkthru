# Citation measurement v2

Implemented 2026-09-27. This is sampled API visibility, not a reproduction of consumer search results. No paid provider was added or enabled.

## What counts

- Groq: a returned source counts only when an explicit provider ID matches an answer marker, or the answer contains that exact source URL. Result array positions are never treated as citation IDs. Retrieved-only pages remain visible but do not count as citations.
- Gemini: memory mode measures mentions only. The existing optional Google Search mode uses `groundingSupports` and its chunk indices; the supporting quote must occur in the answer. Redirect destinations are unresolved, never inferred from titles. No redirects are fetched.
- Brand domains match an actual URL host or subdomain, not a path, query, user-info field or a longer unrelated hostname. Names are matched in prose with boundaries.
- Citation rate divides cited answers by completed, resolved measurements only. Memory, legacy, unavailable and incomplete evidence are excluded and labelled. A partially resolved answer can display a proven citation while remaining excluded from the rate.
- Raw answers, evidence references/quotes, provider, model, mode, prompt version and the tracked brands are retained. Queued context survives later edits. Historical labels do not change when today's grounding setting changes.
- Existing measurements with discarded reference markers cannot be repaired reliably. Their mention counts are recomputed; citations become unknown until a fresh check.
- Google AI Overviews, Google AI Mode, ChatGPT, Perplexity and Claude remain explicitly unmeasured. Gemini search grounding is not coverage of Google's consumer AI surfaces.

## Queue and quotas

`queue_citation_batch` atomically checks pending batches, the 20-hour manual interval and a global backlog bounded to seven daily quotas per engine. A rejected batch inserts no partial work. The same batch ID is replay-safe.

`claim_citation_job` serializes quota reservation and claims a ten-minute lease. Attempts, including failures and quota responses, use the UTC daily allowance. A replay with the same active token does not consume quota twice. Expired leases can be reclaimed, and stale workers cannot save an answer. Global spacing and provider cooldowns survive worker restarts.

HTTP 429 defers that engine for an hour without marking the answer permanently failed. Other provider failures back off and become terminal after four failures. Gemini makes one request per quota reservation using the first configured citation model. Weekly admission failures retry scheduling after six hours rather than adding overlapping batches. Queue/history reads paginate past PostgREST's per-response cap, with a 5,000-check display bound.

Defaults remain 20 web and 300 memory attempts per UTC day. These are shared across customers. The UI reports remaining quota, queue size, retries and approximate quota windows; it does not promise completion in minutes. Capacity and real provider availability still constrain launch allocations.

## Schema and operations

The additive citation v2 block in `apps/api/schema.sql` creates `citation_quota`, lease/retry columns and service-role-only RPCs. Apply it before starting the updated worker. `python scripts/migrate_citations.py` applies only this block transactionally and reloads PostgREST. The shared schema was already applied with founder approval by the parallel local agent on 2026-09-27 (see CURRENT_STATE.md); this session did not reapply it.

No keys, grounding flag, provider limits, pricing or paid integrations were changed. The initial live showcase check tracked twice is still outstanding. Missing provider credentials yield visible failed checks after bounded retries; capacity also shows that the provider is not configured.

## Verification

- Recorded and synthetic provider responses: reference attribution, host boundaries, duplicate names, unsafe links, grounding redirects, old records and citation denominators.
- API fixtures: admission rejection, immutable batch context, quota retries, bounded failures, plan limits, weekly scheduling and completion notices.
- Disposable PostgreSQL: idempotent schema/application and admission, concurrent last-slot claims, lease expiry/replay fencing, UTC reset/cooldown and anonymous RPC denial.
- Web tests and browser fixtures: citation denominators, saved labels, engine/prompt filters, expanded sources, empty state and 375px layout.
- Live provider behavior and sustained week-over-week showcase coverage are not verified by these fixtures. Unmapped references remain unknown rather than being guessed.

Provider references: [Groq browser search](https://console.groq.com/docs/tool-use/built-in-tools/browser-search), [Gemini grounding data](https://ai.google.dev/api/generate-content#GroundingSupport), [Gemini Google Search](https://ai.google.dev/gemini-api/docs/google-search).
