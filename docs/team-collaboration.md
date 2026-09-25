# Team collaboration (Plus): team workspaces

Built 2026-09-25 by Claude Code (cloud). Backend, database, API, tests and working web pages are done and verified end to end. This file is the reference for the feature and the brief for the local agent that polishes the UI.

## 1. What it is

A Plus owner creates a **workspace** for their team or for a client. The workspace is one persistent place for:

- **Shared reports.** Share any of your runs, scans or watch checks into the workspace. You can also turn on auto-share so every new report lands there.
- **Findings board.** Every finding across the shared reports gets one row per problem and site, with a status (open, in progress, fixed, won't fix) and an owner. A finding marked fixed that shows up again in a later report is flagged **Found again after a fix**.
- **Chat.** One persistent channel per workspace, with @mentions, unread counts, edit and delete. It stays for everyone who joins later.
- **Comment threads** on every shared report and every finding.
- **Activity log.** Who joined, shared, triaged, invited or changed a role. It doubles as the audit trail.
- **Presence.** Shows who is here now.
- **Members and roles:** owner, admin, member, viewer. Viewers suit clients: they read, chat and comment.
- **Invitations.** The "connection string" is either an email invite for one verified address, or an invite link with a join code people can type (`ABCD-EFGH-2345-JKLM-NPQR-STUV`). A link can be limited to your company's email domain, a number of uses and an end date.

Members do not need a plan of their own. Everything is enforced on the server.

Inspiration:
- Linear: triage states and owners.
- Vercel: team invites, roles and the join link.
- Figma and Google Workspace: viewer seats for clients.
- Slack: persistent channel, mentions, unread counts.

## 2. How a team uses it

1. The owner (on Plus) opens **Team** in the sidebar, creates "Acme launch", and lands on Members.
2. They invite `bo@acme.io` as a member. Bo gets an email when Resend is set up, and the owner can also copy the link. For the client, they make a viewer link limited to `@client.io`.
3. Bo opens the link. `/join` shows the workspace, who invited him and his role, and he joins. If Bo was signed out, the browser keeps the invitation for an hour and brings him back after sign-in.
4. The owner opens a report and clicks **Share to workspace**, or turns on auto-share in the workspace settings.
5. Bo opens **Findings**, sets "Missing Content-Security-Policy" to *In progress* and assigns it to himself. The activity log records it and the owner's overview shows "Assigned to you" counts.
6. The team talks in **Chat** and in the comment thread under each report and finding ("@Bo Member can you take the CSP one?").
7. After a fix, a rerun is shared. If the finding is still there, the board flags it **Found again after a fix**.
8. If the owner's Plus plan ends, the workspace becomes read-only (everything readable, nothing new) until they renew or hand it to a member who is on Plus.

## 3. Architecture

```
Browser (React)                          Walkthru API (FastAPI, app/teams.py)           Supabase Postgres
──────────────                           ──────────────────────────────────────         ─────────────────
/app/team, /app/team/:id/:tab  ── GET/POST/DELETE /teams/... (bearer JWT) ──▶ membership + role read    teams, team_members,
/join#CODE                                                                  on every request,          team_invites, team_runs,
                                                                           plan of the owner,          team_findings,
                                                                           writes with the secret key  team_messages, team_events
report page: getRun(id) ─────────── Supabase REST under RLS ───────────────────────────────────────▶ runs policy: owner, public,
screenshots: signed URLs ────────── Supabase Storage under RLS ────────────────────────────────────▶ or shared_with_me(run)
live updates ◀─────────── Supabase Realtime postgres_changes (RLS: members only) ◀───── publication supabase_realtime
             (falls back to polling: chat every 5 s, page every 30 s)
```

Decisions:
- **All writes, and the business rules, go through the API.** Membership and role are read from the database on every request (never cached, never from the client). Non-members get **404**, so a workspace id reveals nothing.
- **Row-level security is the second wall.** Browsers get `select` only, and only on rows of workspaces they belong to (`public.is_team_member`). Invitations are never readable from a browser. No team table grants insert, update or delete to a browser role.
- **Realtime is a nudge, not a data path.** A change event makes the page refetch through the API. If the socket is down, pages poll.
- **Shared reports reuse the existing report view.** A member reads a shared run and its screenshots straight from Supabase, because the new policies on `runs` and `storage.objects` allow it through `public.shared_with_me(run_id)`.
- **Seats are counted in one locked transaction** (`public.team_join`), so two people can never take the last seat at once.
- **Ownership moves in one transaction** (`public.team_transfer`).
- **No new dependencies.** Python stdlib and the libraries already in the repo; supabase-js already ships Realtime.

Code map:

| Piece | File |
|---|---|
| Tables, RLS, functions, realtime publication | `apps/api/schema.sql` (section "Plus: team workspaces") |
| Data access (PostgREST) | `apps/api/app/db.py` (section "Plus team workspaces") |
| Routes and rules | `apps/api/app/teams.py` |
| Auth profile (verified email, name) | `apps/api/app/auth.py` |
| Invitation email | `apps/api/app/deliver.py::send_team_invite` |
| Auto-share hooks | `apps/api/app/main.py` (`start_run`, `run_scan`) |
| Account export and deletion rules | `apps/api/app/main.py`, `teams.before_account_delete`, `teams.forget_user` |
| Web data layer and realtime hook | `apps/web/src/lib/teams.ts` |
| Pages | `apps/web/src/pages/Teams.tsx`, `Team.tsx`, `TeamReport.tsx`, `Join.tsx` |
| Tab components | `apps/web/src/components/team/{Overview,Chat,Findings,Reports,Members,Settings}.tsx` |
| Share button on the owner's report | `apps/web/src/components/ShareToTeam.tsx` |
| Tests | `apps/api/tests/test_teams.py` (always), `tests/test_teams_live.py` (real Postgres + PostgREST), `tests/live_stack.py` |

## 4. Data model

| Table | Key columns | Notes |
|---|---|---|
| `teams` | `id`, `name` (1-60), `owner_id` | Deleting the owner's account deletes the team (the API refuses while others are in it). |
| `team_members` | `(team_id, user_id)`, `role`, `name`, `email`, `auto_share`, `last_read_message_id`, `last_seen_at` | One owner per team (partial unique index). `name` and `email` are a display copy, refreshed when the member opens the workspace. |
| `team_invites` | `id`, `kind` (`email` or `link`), `token_hash` (SHA-256), `email`, `email_domain`, `role`, `max_uses`, `uses`, `expires_at`, `revoked_at` | Links never grant admin. Email invites are single use. API only. |
| `team_runs` | `(team_id, run_id)`, `shared_by`, `shared_at` | Deleting a run removes it from every workspace. |
| `team_findings` | `(team_id, origin, fingerprint)`, `status`, `assignee_id`, `updated_by`, `updated_at` | Keyed like ignored findings: site origin plus `compare.fingerprint`. |
| `team_messages` | `id` (bigint), `thread`, `author_id`, `author_name`, `body` (4,000), `mentions uuid[]`, `client_id`, `edited_at`, `deleted_at` | `thread` is `general`, `run:<run id>` or `finding:<32 hex>`. `(team_id, client_id)` is unique, so a retried send lands once. Deleted messages keep the row with an empty body. |
| `team_events` | `id`, `actor_id`, `actor_name`, `type`, `detail` jsonb | The activity feed and audit trail. Invitee emails are masked here, because viewers read it too. |

Functions:
- `is_team_member(team)` and `shared_with_me(run)` are SECURITY DEFINER. They answer only for `auth.uid()`, and `authenticated` may execute them.
- `team_join(...)` and `team_transfer(...)` can be executed by the service role only.

## 5. Permissions

| Action | Viewer | Member | Admin | Owner |
|---|---|---|---|---|
| Read reports, findings, chat, activity, members | yes | yes | yes | yes |
| Chat and comment, edit and delete own messages | yes | yes | yes | yes |
| Share own reports, auto-share | no | yes | yes | yes |
| Triage findings (status, owner) | no | yes | yes | yes |
| Remove a report from the workspace | own runs | shared by them or their run | any | any |
| Delete anyone's message (logged) | no | no | yes | yes |
| Invite by email, make invite links, withdraw | no | no | member and viewer | any role |
| Change roles, remove people | no | no | members and viewers | anyone but themselves |
| Rename the workspace | no | no | yes | yes |
| Hand over, delete the workspace | no | no | no | yes |
| Leave | yes | yes | yes | no (hand over first) |

**While the workspace is read-only** (the owner is not on Plus):
- Paused: chat, sharing, triage, invitations and renaming all answer 402.
- Still allowed: reading, leaving, removing people, withdrawing invitations, deleting your own messages, handing over and deleting the workspace.

Limits:

| Limit | Value |
|---|---|
| Seats per workspace (`TEAM_SEATS`), open email invitations included | 3 |
| Workspaces one Plus account can own | 3 |
| Workspaces one account can be in | 20 |
| Open invite links per workspace | 5 |
| Invitations per workspace per day | 30 |
| Messages per person per minute | 30 |
| Invitation-code attempts per person per 10 minutes | 30 |

## 6. API reference

All routes need `Authorization: Bearer <Supabase access token>`, and every body forbids extra fields. Errors are `{"detail": "<plain sentence>"}`.

| Method and path | Who | What |
|---|---|---|
| `GET /teams` | anyone | Your workspaces (role, active, unread, mentions), invitations sent to your verified email, `can_create`, `seats` |
| `POST /teams {name}` | Plus | Create; you become the owner |
| `GET /teams/{id}` | member | Overview: team, `me.can` (what you may do), members with presence, sites, finding totals, 15 latest events, unread |
| `POST /teams/{id} {name}` | admin | Rename |
| `POST /teams/{id}/delete {confirm}` | owner | Delete (confirm = the exact name) |
| `POST /teams/{id}/transfer {user_id}` | owner | Hand over to a member or admin |
| `POST /teams/{id}/me {auto_share}` | member | Your auto-share |
| `GET /teams/{id}/members` | member | Members; admins also get open invitations and `seats_used` |
| `POST /teams/{id}/members/{user_id}/role {role}` | admin | Change a role |
| `DELETE /teams/{id}/members/{user_id}` | admin, or yourself | Remove, or leave |
| `POST /teams/{id}/invites {email, role}` | admin | Email invitation; returns `link`, `code` (once) and `emailed` |
| `POST /teams/{id}/links {role, days, max_uses, email_domain?}` | admin | Invite link; returns `link` and `code` (once) |
| `DELETE /teams/{id}/invites/{invite_id}` | admin | Withdraw |
| `POST /invites/preview {code}` | anyone | Workspace name, inviter, role, `problem` (why you cannot join, if so) |
| `POST /invites/accept {code}` | anyone | Join. The code can be the full link or the code with or without dashes |
| `POST /invites/{id}/accept`, `/decline` | the addressee | Accept or decline an email invitation listed in `GET /teams` |
| `GET /teams/{id}/runs?before=` | member | Shared reports, 50 a page |
| `POST /teams/{id}/runs {run_id}` | member, own runs | Share (not competitor comparisons) |
| `DELETE /teams/{id}/runs/{run_id}` | see matrix | Remove from the workspace |
| `GET /runs/{run_id}/teams` | run owner | Workspaces this run can go to, with `shared` |
| `GET /teams/{id}/findings` | member | Board, assignable members, `can_triage` |
| `POST /teams/{id}/findings {origin, fingerprint, status?, assignee_id?}` | member | Triage (only findings in this workspace's reports) |
| `GET /teams/{id}/messages?thread=&after=&before=&limit=` | member | Oldest first; `after` for new messages, `before` for history |
| `POST /teams/{id}/messages {body, thread, mentions, client_id}` | member | Send (mentions are filtered to members) |
| `POST /teams/{id}/messages/{mid} {body}` | author | Edit |
| `DELETE /teams/{id}/messages/{mid}` | author or admin | Delete |
| `POST /teams/{id}/read {message_id}` | member | Mark the channel read, and presence |
| `GET /teams/{id}/activity?before=` | member | Events, 50 a page |

## 7. Security model (what was checked)

**Authorization**
- Membership and role come from the database on every call. `_member()` in `teams.py` returns 404, 403 or 402. Every id in a path is typed: team, member and invite ids are UUIDs, run ids are 32 hex characters, message ids are bounded integers. Nothing the client sends reaches a PostgREST filter unvalidated.
- Every write targets rows scoped by the team id as well as the object id, so an id from another workspace does nothing.

**Invitations**
- Codes carry 120 random bits, are shown once and stored as SHA-256.
- The link carries the code in the URL fragment (`/join#CODE`), which browsers never send to a server or in a Referer. The join page then removes it from the address bar.
- An email invitation works only for its **verified** address.
- Code attempts are rate limited.

**Seats and races**
- Joining re-checks the invitation, membership, the account's workspace limit and the seats inside a locked transaction. It was tested with 6 people racing for one seat: exactly one got in.

**Row-level security**
- Tested on a real PostgREST with Supabase's roles:
  - Members read their workspace rows. Strangers read nothing.
  - Browsers cannot insert, update or delete team rows, read invitations, or call `team_join`.
  - Members read a shared run and its screenshot objects, and lose that access the moment they leave or the report is removed.

**Privacy**
- The Runs list now filters to the signed-in owner. Before this change, RLS let it list every public report, and now workspace reports as well.
- Invitee emails are masked in the activity log.
- A deleted account's name becomes "Former member" in other people's workspaces.
- The account export includes memberships and your own messages.
- An account that owns a workspace with other people in it cannot be deleted until it is handed over or deleted.

**Content**
- Names and messages lose control characters and bidirectional overrides.
- Workspace names cannot contain links, because they appear in emails.
- React escapes all text, and chat links are http(s) only with `rel="noopener noreferrer nofollow"`.
- The invitation email escapes every value.

**Auth changes**
- `require_user` now also returns `email_verified` (from `email_confirmed_at`), a display name and an avatar.
- The token cache is keyed by SHA-256, is bounded, and never trusts a token past its own `exp`.

**Founder must keep:**
- In Supabase Auth, keep **Confirm email ON**, or turn the email and password provider off. Email invitations rely on `email_confirmed_at` meaning the person owns the address. The app signs in with magic links and OAuth, which prove it, but Supabase's email and password signup is on by default at the API level, and with confirmation off anyone could create an unconfirmed-but-trusted account for someone else's address.

## 8. Setup on the founder's machine

1. Apply the schema: `cd apps/api && .venv/Scripts/python -m app.db` (use the IPv4 pooler `DATABASE_URL` override from CURRENT_STATE.md). `setup()` now splits statements outside `$$` bodies, so the new functions apply cleanly. Re-running is safe.
2. Realtime: nothing to switch on. The schema adds the team tables to the `supabase_realtime` publication. Check Database > Publications in the dashboard if live updates do not arrive. The pages poll anyway.
3. Email invitations need `RESEND_API_KEY`, and a verified sending domain to reach anyone other than the Resend account owner. Without them, the invite response says `emailed: false` and the page shows the link to send yourself.
4. Give a test account Plus: `scripts/grant_plan.py EMAIL plus`. Invite a second account (any plan).
5. Optional: `TEAM_SEATS` changes the seat count (default 3, from founder/pricing-strategy.md).

Manual test, about 10 minutes:
1. Account A (Plus): Team > create > Members > invite B by email, and make a viewer link.
2. Account B, in a private window: open the link > Join > Chat > say hi.
3. Account A: open a report > Share to workspace > tick the workspace.
4. Account B: Reports > open it > comment > Findings > set a status and an owner.
5. Account A: Overview (totals and activity) > Settings > hand over and back.

## 9. Tests

- `tests/test_teams.py` (always runs): codes, name, message and domain cleaning, threads, the permission map, the 402 for non-Plus, and the schema splitter.
- `tests/test_auth.py`: verified email and name, hashed and bounded cache, never past `exp`.
- `tests/test_teams_live.py` (19 tests, real Postgres 16 + PostgREST 12 with Supabase's roles): idempotent schema, Plus gate and owned limit, 404 for strangers, email invitation for its verified address only, in-app invitations, seats counting open invitations, the 6-way race for the last seat, domain-limited links, roles, hand over and delete, RLS on shared runs and evidence, browser write denial, findings board with triage and "found again", chat with mentions, unread, idempotent sends, edit, moderation, threads and RLS, message rate limit, read-only mode and recovery by handing over, auto-share, and account deletion rules. They skip when the binaries are missing. To run them, set `PG_BIN` (the folder with `initdb`) and `POSTGREST_BIN`.
- A browser end-to-end test (cloud session, not committed) ran the production web build, the real API and a Supabase-shaped gateway over the same Postgres. An owner, a member and a client viewer each had their own browser. It covered create, invite by email and by domain-limited link, join, share two reports, a member reading a shared report through RLS and commenting, triage, chat both ways, a viewer who can chat but not triage, the Runs list showing only your own runs, the signed-out invitee flow, and every tab at 390 px with no page overflow. It ran with no console errors.

## 10. Brief for the local Claude Code agent (UI polish)

The pages work and follow the existing patterns: PageHeader-like header, the Settings two-column sections, tokens only, pills and `rounded-2xl`. They were kept deliberately plain because the founder reverted two redesign passes before. Your job is to polish, not rebuild.

**Load first:** `frontend-ui-engineering` + [DESIGN.md](../DESIGN.md) for any change. Then `impeccable` for the critique and polish pass, and `emil-design-eng` for motion details. `ponytail` stays on.

**Hard rules:**
- Tokens only: `bg-bg`, `bg-surface`, `text-ink`, `text-muted`, `border-line`, `text-accent`, `text-danger`. No new colours.
- No em dashes in copy.
- Label every input.
- Keep the loading, error, empty, locked and read-only states.
- Honour `prefers-reduced-motion`.
- Do not move rules into the client: the API decides, and `me.can` only hides controls.
- Keep `npm run build` and `npx oxlint` at 0 warnings. Watch the `react(set-state-in-effect)` rule: reset state by keying a component, not with a synchronous `setState` in an effect.

**Pages and what to polish:**

| Route | File | Polish ideas (keep them small) |
|---|---|---|
| `/app/team` | `pages/Teams.tsx` | Workspace rows could show member avatars and the latest activity line. The invitation banner is fine as is. |
| `/app/team/:id` Overview | `components/team/Overview.tsx` | The stat strip uses the hairline grid; consider a small severity bar per site. Keep the setup checklist until all 3 steps are done. |
| `/app/team/:id/chat` | `components/team/Chat.tsx` | Day separators, a "new messages" divider at `last_read_message_id`, grouping consecutive messages by the same author, an @ autocomplete listbox (accessible combobox) in place of the mention chips. Keep `role="log"`. |
| `/app/team/:id/findings` | `components/team/Findings.tsx` | Group by site or by status (columns on desktop, list on phones). "Found again after a fix" deserves a clearer mark. Keyboard: the selects already work. |
| `/app/team/:id/reports` | `components/team/Reports.tsx` | Score as a small ring like the report's Launch Ready. Filter by site. |
| `/app/team/:id/members` | `components/team/Members.tsx` | After creating a link, show the code large and typeable next to the link. Group invites and links. |
| `/app/team/:id/settings` | `components/team/Settings.tsx` | Fine; maybe a warning line when handing over to someone not on Plus (the API response says `active`). |
| `/app/team/:id/runs/:runId` | `pages/TeamReport.tsx` | A sticky "Comments (n)" jump, or comments in a side column on wide screens. |
| `/join` | `pages/Join.tsx` | Use `AgentPresence` like Login and NotFound. |
| Report page | `components/ShareToTeam.tsx` | The popover needs Escape and click-outside to close, and focus return. |
| Sidebar | `components/AppShell.tsx` | An unread dot on "Team" (sum of `unread` from `GET /teams`, refreshed on focus). It adds one request per page, so debounce it. |

**Do not change without asking the founder:**
- Seat count, which plan gets teams, and free viewer seats (pricing).
- Letting members' runs use the owner's quota (billing).
- Where the rules live.

## 11. Open decisions for the founder

1. **Seats.** The pricing doc says Plus is "3 seats sharing reports", so `TEAM_SEATS=3`, with viewers counted. Two options that would sell well to agencies:
   - Free viewer seats, so clients do not count.
   - A Team tier (for example $99/mo, 10 seats) above Plus.
   Both are pricing changes, so they are yours to decide.
2. **Shared run quota.** Today each member runs tests on their own plan and shares the reports. A team plan could let members spend the owner's runs. That touches billing, so it has not been built.
3. **Plus waitlist copy.** The pricing card still says waitlist, per the earlier rule (citation tracking not shipped). Team workspaces are not yet in the pricing copy.
4. **Email notifications** for mentions and assignments (Resend) are not built. In-app unread and mention counts are.
