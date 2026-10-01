# Website and extension sessions

Implemented during V0-S3, 2026-10-01. This is engineering acceptance; installed Chrome repetition and founder legal review remain open in `tasks/todo.md`.

## Connection and logout

Only the configured web origin can begin, complete or disconnect a connection. Both Chrome-reported sender origin and URL origin must match; other extensions are refused. The website first obtains a 30-second one-use challenge bound to the user and Auth session, rereads its session and transfers allowlisted credentials to the named extension. It checks identity again after the final acknowledgment before claiming success. The background worker creates a new connection ID for each handoff.

The background worker serializes credential changes. Internal refresh and 401 cleanup require the previous connection and access token to match; page content scripts cannot use this channel. A refresh finishing after disconnect cannot restore credentials; an old account's disconnect cannot clear a newer account or login. Concurrent requests share one refresh per panel, and another panel's already-refreshed credentials can be reused only on that same connection. Supabase validates token authenticity; decoding the session ID is only an identity fence.

Website sign-out waits up to three seconds for an identity-qualified disconnect, warns if it cannot be confirmed, then rereads the current login before SDK logout. A switched account is not deliberately signed out. Other-tab auth changes also request qualified disconnect. A disconnected sidepanel clears prior account state and aborts its batch. Every new browser action, batch navigation, API retry and evidence send checks its original connection. An action or request already dispatched may finish. Unfinished server runs stay recoverable from their original account's dashboard.

Rebuild and reload the extension together with the website: the challenge protocol deliberately rejects legacy one-message handoffs. This change adds no browser permission or dependency.

## Server validation and sharing

The API keeps hashed validation entries for at most 300 seconds and never beyond token expiry. It refuses a known expired token before consulting its cache or Auth. This bounds how long an upstream rejection may be hidden by a warm cache, not how soon logout universally revokes an access JWT. Supabase documents that revoked-session access tokens can remain valid until expiry; default SDK sign-out revokes refresh sessions globally. [Supabase sign-out contract](https://supabase.com/docs/guides/auth/signout).

Public links and team sharing are separate access controls. Logout does not erase reports or revoke those permissions. Team membership is read on each request and by RLS. Report email addresses are not stored in the report database; the delivery provider has its own retention. Privacy, Security and Settings now describe these behaviors consistently.

## Verification and review

- Full API: 706 passed / 19 existing PostgREST skips. Added real-schema SQL RLS test: one passed, proving private/public/team report and screenshot reads, denied membership writes and immediate access loss after removal. Focused auth/retention/citation SQL: 19 passed.
- Extension: 83 passed / one opt-in skip. Web: 13 passed. Type/lint/build passed. The citation rollover test now uses UTC like production, avoiding a local-timezone false failure.
- Live existing QA tester: owner/anonymous private/public RLS reads passed. Own-session logout returned 204; warm validation returned 200, cold validation 401, and refresh 400. This is observed project behavior, not a guarantee for every Supabase session configuration.
- Real website QA on temporary isolated origin 5175: existing tester sign-in, absent-extension error, Settings data guidance, sign-out and private-route redirect passed. API-only Settings widgets correctly rejected the temporary origin via CORS. Normal origin remains 5174. Fixture/bridge/server removed after testing; no credentials were saved in evidence.
- Fresh-context adversarial review identified handoff/logout/refresh races, stale UI and dispatch gaps; each was reconciled and corrected. Tests cover challenge expiry/replay, exact sender rejection, account switching, stale refresh/401, disconnect before dispatch and late connection acknowledgment.
- Native Chrome was unavailable to automation. Background handler tests use actual registered code with mocked Chrome messaging; they do not replace installed-extension acceptance in S5.
- Automatic approval review rejected creating and granting a new live viewer access to the existing QA workspace. That action never ran. Owner/anonymous reads and disposable local SQL tests supplied safe verification; prior live viewer/removal baseline evidence is preserved. A new live cross-account repeat needs explicit approval for that account/resource/scope.
- Founder legal review remains required by `docs/agent-safety-plan.md`: "the founder reviews the legal pages." Domain/inbox and provider callback acceptance belong to S4/S7.

Ignored local evidence: `evals/results/v0-session-3/`. No deployment, pricing change, paid service, migration, dependency or new issue was created.

## Sign-in and founder recovery, V0-S4 (2026-10-01)

Provider callbacks continue to use `/app`, preserving the configured callback contract. Callback failure redirects contain only allowlisted error codes; the login page removes the callback query/fragment and displays an actionable message rather than provider-supplied text or tokens. An invitation retained in this browser sends a successful sign-in back to `/join`; malformed percent-encoding cannot crash the page. Successful magic-link request acceptance does not prove email receipt or callback completion.

If an access-request response is lost, the client makes one saved-state read and validates the current account before and after it. A matching pending request or newly decided matching request is shown as saved; unrelated or historical decided requests do not establish success. If the read fails, the user is told to reload Plan & billing before resubmitting. No mutation is automatically retried. The existing server pending-request uniqueness remains authoritative. Once persisted, a request remains successful even if queuing its optional founder email fails; the admin panel is the fallback.

Admin failures hide internal exception detail and warn that a write may already be saved. A request-linked grant checks the recipient before granting, and reports a saved grant with a changed request status explicitly. The grant, notification, request decision and audit are separate writes; recovery guidance does not claim they are atomic. Check the current plan and request status before repeating an ambiguous action.

Focused API tests: 57 passed; web tests: 19 passed. Ruff, web TypeScript/lint/build passed. Browser expired-link recovery and Google back-navigation passed; both real OAuth login pages reached. Authorized magic-link request accepted. Successful live callbacks, invited return and founder fresh-TOTP grant/revoke remain open, as do actual inbox delivery and final domain/inbox acceptance. Resend app mail is currently unconfigured. No credentials, session tokens or live grants were captured or created in this session. Evidence: ignored `evals/results/v0-session-4/`.

Malformed invitation browser QA found another unsafe decode in the global scroll handler. It now ignores undecodable anchors. Reloading the same link rendered “No invitation here.” and anonymous Team navigation redirected to login. Final web verification passed after this fix.
