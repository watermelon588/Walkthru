# Implementation Plan: In-app live runs (cloud runner)

_Written 2026-11-11. Status: plan only, nothing built. Founder decisions still open are listed at the end._

## Overview

Walkthru journeys today need the Chrome extension. This plan adds a second way to run the same journey: the user enters a URL and a goal inside the web app, picks or generates test users, and watches each one move through the site in a browser-style viewer with an animated cursor. The browser itself runs on our server (headless Chromium driving the already-built `inject.js`), and the viewer replays one screenshot per step. The extension stays, for logged-in and localhost journeys and for the Chrome Web Store. The report is unchanged.

This is the `cloud-runner` module already sketched in ARCHITECTURE.md, promoted from "conditional" to "build before launch", plus a live viewer and persona generation.

## Reference research (Swarm, 2026-11-11)

Sources: the founder's 83 s screen recording (`reference-swarm.mp4`, reviewed at 1 frame per second plus 5 fps on the step transitions), two reports and one live run in the founder's Swarm account, and the Swarm persona, swarm and context pages. This is reference for the experience only. Walkthru's layout, tokens and cursor are our own.

### Run page timeline (from the video)

| Time | What the user sees |
|---|---|
| 0 s | Toast "Test launched!", skeleton, then the run page: goal as the title, `Running · just now · 3 personas · 0/3 done · site link`, a red Terminate button |
| 1 to 13 s | Tabs `Results` / `Agent sessions` (sessions selected). One card per persona in a row: name, spinner, `Running · 0 steps · 9s`, ticking every second. Stage area says "Waiting for steps..." |
| 14 s | First step arrives. Step bar: `Step 1 of 1 · Landed on the page`. Left column: the persona's comment for this step ("No observations for this step." when empty). Right: the stage. Bottom: play button, scrubber with one dot per step, `1 / 1`, speed `1x 2x 4x` |
| 18 s | Screenshot of the site fades into the stage. A coloured cursor sits on it |
| 21 to 23 s | Step 2: old frame dims, stage clears, a pill "Scrolling down ..." shows on the empty stage, the new frame loads, the pill becomes "Scrolled down" and fades, the cursor glides to its new position. The comment column updates ("Projects are easy to reach, but the first card only shows an unlabeled arrow so far.") |
| 28 to 31 s | Step 3 "Clicked on the page": cursor glides to the target, a ring ripples out from it, next frame loads |
| 33 to 34 s | Persona cards flip to `Completed · 4 steps · 31s` one by one; header shows `1/3 done`. Final step "Task complete" stacks two comment cards (last thought, then the outcome summary) |
| 35 to 55 s | All done: the page switches itself to `Results` and shows a centred checklist that ticks through: All agents finished, Analyzing UX observations, Cross-referencing sessions, Identifying patterns, Composing verdict, Generating your results |
| 56 to 65 s | Results stream in: verdict first, then findings rows appear while a thin status bar says "Enriching evidence blocks 1/2", "Generating recommendations and attaching screenshots", "Report complete". Header gains Share and Rerun |
| 66 to 83 s | Back on `Agent sessions`: clicking another persona card swaps the whole player to that persona's session, from step 1 |

### What is actually happening behind it

- The stage is not a live browser. It is an `<img>` of `step-N.jpg` (one JPEG per step in their S3 bucket) with a `<canvas>` on top that draws the cursor. During a run the page polls for new steps.
- The browser runs on their servers (API paths `cua-tests`, plus an AWS Device Farm endpoint).
- "Side by side" is the row of persona cards with live status, and one shared player that switches persona. It never shows three browsers at once.
- Runs are short: 3 or 4 steps per persona, about 35 s each, all three in parallel.

### Test creation flow (from the live run)

1. Home: one prompt box ("What do you want to understand?"), mode switch `Live agent` / `Static flows`, three suggested tests personalised to the saved site.
2. Plan page, drafted by a model and editable line by line: **Start at** (URL), **Goal**, **Steps** ("a rough path, personas may wander"), **Done when** (how success is judged). A side box, "Refine the plan", rewrites it from a sentence.
3. Personas page: one text box ("recruiter"), a `- 3 personas +` stepper, a generate arrow. Output is one card per persona: initials avatar, name and age, city, job title, and a first-person paragraph on how they browse. Buttons: Regenerate, Run test.
4. Swarms page: the same generator, then "Review and name your swarm" and Save. Saved swarms are attached to any test with `@name`.
5. Paid extras we saw gated: Deep research for personas, auth profiles (logged-in pages), local setup (CLI), Ask Hive, org "Context" documents.

### What to take, what to leave

| Take | Leave |
|---|---|
| Persona cards with live status and a step count | The fake-precision checklist driven by timers; ours ticks on real job states |
| One player: stage, step label, comment column, scrubber with step dots, speed | "x/3 agents" counts presented as confidence when only one or three agents ran |
| Action pill between frames ("Scrolling down") and a cursor that glides and ripples | Padding findings with "platform strengths" |
| Auto-switch to results when everything finishes, results streaming in | Submitting real forms on unverified sites (Swarm sent a real contact message) |
| Persona generation from one audience sentence, reviewable before the run | "Clicked on the page" labels; we name the element ("Clicked 'Live site'") |

## Architecture decisions

1. **Server-side headless Chromium, driven over CDP, running the built `inject.js`.** A web page cannot embed and control a third-party site (frame blocking, cross-origin rules), so the browser must run on a server. `evals/e2e_extension.py` already does this end to end against the real API; we promote its `Tab` class and loop into `apps/api/app/runner/`. Snapshot, masking, executor and safety code are shared with the extension, byte for byte.
2. **The runner calls the same run logic as the extension** (start, observe, stop), in-process as the signed-in user's id, so quotes, reservations, idempotency, step caps and reports all behave the same. No second agent path.
3. **Replay of step frames, not a video stream.** One JPEG per step into the existing private `run-evidence` bucket, polled by the web page. Cheap, works on the free tier, and is exactly what the reference does.
4. **Cursor data is measured, not invented.** The executor returns the centre of the element it acted on as viewport fractions. The player animates from the previous point to that one. Scroll steps carry direction only.
5. **One browser at a time, everyone else queued (founder decision, 2026-11-11).** The live VM is an `e2-small` (2 GB, shared CPU) that already runs two systemd services: `walkthru-api` (`JOB_WORKERS=0`) and `walkthru-worker` (`JOB_WORKERS=1`). Cloud runs do **not** go through the general `jobs` queue, for two reasons found in the code: production has a single worker thread, so a journey of up to 4 minutes would hold up every other user's report, comparison and Scout reply; and `claim_job` cannot filter by kind. Instead:
   - The `cloud_runs` table is its own queue, with a `claim_cloud_run` function (`FOR UPDATE SKIP LOCKED`, lease and heartbeat) in the same migration.
   - A third systemd service, `walkthru-runner` (`python -m app.runner`), claims one row at a time and owns the only Chromium on the machine. Concurrency is fixed at 1 for launch; `RUNNER_CONCURRENCY` exists but stays 1 until the VM is larger.
   - The queue is global across users, oldest first. Each user may have at most 3 test users waiting or running, so one account cannot fill the queue. The page shows "Queued, N ahead of you".
   - The runner only drives the browser. When a journey ends it enqueues the normal `finish_run` job, so the report is still written by the existing worker.
   - A run whose runner died (lease expired) is marked failed with "interrupted", its reservation is released, and it is **not** replayed automatically; the user reruns it. This matches the existing rule that unknown outcomes are never re-executed.
   - Memory: the runner unit gets a systemd `MemoryMax`, Chromium starts with a small cache and one renderer, and the browser process is killed after every run. T0 measures whether a swap file is also needed.
6. **Public pages, visitor mode; no verification needed to run (founder decision, 2026-11-11).** Any signed-in user can run a live test on any public URL. Cloud runs are always `logged_in: false`. On a domain the owner has not verified, the existing visitor rules apply (no submits except search, nothing destructive). Sending forms stays limited to verified domains with the owner's confirmation. Logged-in and localhost journeys stay extension-only, and the UI says so.
7. **Network guard on the server browser.** Every request Chromium makes passes the existing SSRF check in `app/scans/fetch.py` through CDP `Fetch` interception: private, loopback, link-local and cloud-metadata addresses and non-http schemes are refused, downloads are disabled, each run gets a fresh throwaway profile, and Chromium runs as an unprivileged user with its sandbox on.
8. **Honest identity.** The cloud browser's user agent names Walkthru and links `/bot`, and the existing per-host politeness limits apply.
9. **Ships behind a flag.** `CLOUD_RUNNER=off` by default and one allowance number per plan in `plans.py`, so the free/Pro/Plus decision can be made later without code changes.
10. **New dependencies: none in Python or npm.** CDP uses the `websockets` and `httpx` packages already installed. The VM (Ubuntu 24.04, systemd, no Docker) gains one headless Chromium build installed from a `.deb` or the `chrome-headless-shell` archive, not the snap; record it in `THIRD_PARTY.md`. DEPLOYMENT_GUIDE.md currently says the VM needs no Chromium and must be corrected.

## Data and API changes

- **Migration `NNNN_cloud_runs.sql`:** table `cloud_runs` (`id`, `user_id`, `group_id`, `site`, `goal`, `persona`, `status` queued/starting/running/finished/failed/blocked/stopped, `run_id` nullable, `error`, `lease`, `locked_until`, timestamps), owner-only RLS, plus the service-only `claim_cloud_run` function. It is both the queue and the record the page reads: a run row only exists after the first snapshot, and the page must show "queued" and a queue position before that.
- **`StepEvidence` gains two optional fields:** `pointer {x, y}` (viewport fractions, the element acted on) and `label` (short action text, for example `Clicked "Live site"`, max 80 chars, built in code from the snapshot's element name, never from model output).
- **Evidence cap:** the 8-frame cap stays for the extension. Cloud runs capture every step (at most the plan's step cap, 25).
- **Endpoints:** `POST /cloud-runs` (site, goal, personas[], optional quote) returns `group_id`; `GET /cloud-runs/{group_id}` returns each persona's status, steps, thoughts and signed frame URLs; `POST /cloud-runs/{group_id}/stop`; `POST /personas/generate` (audience text, count 1 to 3) returns draft personas.

## Task list

Sizes: S = 1 to 2 files, M = 3 to 5 files. Every task keeps build, lint and tests green.

### Phase 0: Spike (fail fast)

- [ ] **T0. Chromium next to the live services, memory and bot walls.** Run `evals/e2e_extension.py` under a 2 GB memory limit with an API and a worker process running beside it (locally first, then once on the VM with the founder's go-ahead), against the easy fixture, TripVerse and the founder's portfolio. Record peak memory of each process, time per step, and whether Vercel or Cloudflare blocks the headless browser.
  - Acceptance: a written result in `docs/decisions.md` with peak RSS, the `MemoryMax` value for the runner unit, and whether a swap file is needed. Concurrency stays 1 regardless.
  - Verify: the three runs end with a report or an honest `bot_wall`.
  - Size: S. Depends on: none.

### Phase 1: Runner core (API)

- [ ] **T1. Move the CDP driver into the app.** Extract `Tab`, Chrome launch and the screenshot helper from `evals/e2e_extension.py` into `apps/api/app/runner/cdp.py`; the eval script imports it.
  - Acceptance: eval script behaves as before; Chromium path comes from `CHROME_PATH`; launch flags include a fresh profile, no downloads, sandbox on.
  - Verify: `pytest -q`, `ruff check .`, one eval run on fixture :8101.
  - Size: S. Depends on: T0.
- [ ] **T2. Callable run service.** Make the bodies of `POST /runs`, `/observe` and `/stop` callable in-process with a user id (thin functions the routes also call).
  - Acceptance: routes unchanged for the extension; quote, reservation and idempotency behaviour identical; no HTTP hop needed by the runner.
  - Verify: full API suite, with the existing run tests untouched and passing.
  - Size: M. Depends on: none.
- [ ] **T3. Network guard.** CDP `Fetch` interception that applies the `app/scans/fetch.py` address check to every browser request, including redirects and subresources.
  - Acceptance: requests to 127.0.0.1, 10.0.0.0/8, 169.254.169.254, `file:` and `chrome:` are refused; a public page loads normally; a page that redirects to a private address is stopped and the run ends as blocked with a plain reason.
  - Verify: new `tests/test_runner_guard.py` against local fixtures.
  - Size: M. Depends on: T1.
- [ ] **T4. Runner service and queue.** Migration for `cloud_runs` and `claim_cloud_run`; `python -m app.runner` loop that claims one row, launches Chromium, loads the site, and runs the snapshot, act, observe loop from T1 and T2 with the same 4-minute wall-clock limit as the extension, a lease heartbeat, origin check and browser kill in `finally`. It enqueues `finish_run` at the end.
  - Acceptance: a queued row becomes a finished run with a report; two runner processes never claim the same row; a second queued row starts only after the first ends; a killed runner leaves the row failed as "interrupted" with the reservation released and no replay; the general worker's jobs are never delayed by a journey.
  - Verify: `tests/test_cloud_run.py` on the easy fixture with a scripted model; migration `status` clean, `.down.sql` present.
  - Size: M. Depends on: T2, T3.
- [ ] **T5. Per-step frames, pointer and label.** `execute.ts` returns the acted element's centre; `StepEvidence` accepts `pointer` and `label`; the cloud runner captures a masked frame every step (using the existing `evidence_capture` message so form values are hidden).
  - Acceptance: every cloud step has a frame; click and type steps carry a pointer inside 0 to 1; typed text and form values are not readable in any frame; extension runs still validate.
  - Verify: extension `npm test`, `npx tsc --noEmit`, `npm run lint`; API schema tests; one fixture run inspected by eye.
  - Size: M. Depends on: T4.
- [ ] **T6. Endpoints.** `POST /cloud-runs`, `GET /cloud-runs/{group_id}`, `POST /cloud-runs/{group_id}/stop`, with rate limits in `limits.py`, the plan allowance in `plans.py` and the `CLOUD_RUNNER` flag.
  - Acceptance: owner-only access; flag off returns a clear 403; no domain verification required; at most 3 queued or running test users per user (clear 429 beyond that); `GET` returns statuses, queue position, steps and one-hour signed frame URLs; stop ends queued and running personas.
  - Verify: API tests for auth, flag, limits and stop.
  - Size: M. Depends on: T4, T5.

### Checkpoint A: runner works without UI

- [ ] `POST /cloud-runs` from a script produces a normal report for the easy fixture and for TripVerse.
- [ ] Guard tests pass; full API suite and Ruff green.
- [ ] Founder reviews one report and its frames before UI work starts.

### Phase 2: Live page (web)

Design per DESIGN.md tokens; load the design skills before building. Honour `prefers-reduced-motion` (no glide, frames cut instantly). Every state has loading, empty and error forms.

- [ ] **T7. Start a live run.** New page `/app/live`: URL, goal, test user picker (the four built-ins plus saved custom test users), Start. Links to the extension for logged-in or localhost sites.
  - Acceptance: labelled inputs; validation for non-public URLs; quote shown before start (reuse the quote box logic); navigates to the run page.
  - Verify: web tests, `npm run build`, `npm run lint`.
  - Size: M. Depends on: T6.
- [ ] **T8. Session cards and polling.** `/app/live/:groupId`: header (goal, site, status, Stop), one card per test user with status, step count and elapsed time, polling every 1.5 s until all finish, with backoff on errors.
  - Acceptance: queued (with "N ahead of you"), running, finished, blocked, stopped and failed states all render; a finished test user's session is watchable while later ones are still queued; polling stops when done or when the tab is hidden.
  - Verify: component tests with mocked responses; preview check in the browser.
  - Size: M. Depends on: T6.
- [ ] **T9. Step player.** One `SessionPlayer` component: stage (frame in a browser-style frame with the page URL), step label, thought column, scrubber with a dot per step, play and speed. Cursor layer animates to each step's pointer with a click ripple; an action pill shows between frames; the evidence region boxes from R-S19 still draw.
  - Acceptance: follows the newest step while live, pauses following when the user scrubs; keyboard reachable (arrow keys step, space plays); reduced motion respected; a missing frame shows a placeholder, not a broken image.
  - Verify: component tests for stepping and follow mode; screenshot proof at desktop and mobile widths.
  - Size: M. Depends on: T8.
- [ ] **T10. Finish, progress and report.** When every test user finishes, show a short checklist driven by real states (runs finished, pages checked, report written), then open the existing report. Add a "Sessions" tab to `Report.tsx` that reuses `SessionPlayer` for any run with frames.
  - Acceptance: no timer-driven fake steps; partial results when one persona is blocked; old reports without pointers still replay.
  - Verify: web tests; one full run watched end to end in the preview.
  - Size: M. Depends on: T9.

### Checkpoint B: one persona, end to end, in the app

- [ ] Founder runs a live test on their own site from `/app/live` and reaches the report.
- [ ] Web 0 lint warnings, build passes, API suite green.

### Phase 3: Personas

- [ ] **T11. Generate test users.** `POST /personas/generate`: one free-chain model call that turns an audience sentence into 1 to 3 drafts (name, age, place, role, how they browse). Output is cleaned with the existing `plus.clean_test_user` rules and admitted through `reserve_work`.
  - Acceptance: schema-validated output; prompt-injection text in the audience field cannot change the output shape; a failed model call returns a clear error and no charge.
  - Verify: API tests with a scripted model.
  - Size: S. Depends on: none.
- [ ] **T12. Persona step in the start flow.** Audience box, count stepper, generate, cards the user can edit or regenerate, "save as test user" (existing `/me/test-users`), then run.
  - Acceptance: works with zero generated personas (built-ins only); respects the plan's limit on personas per run.
  - Verify: web tests and preview check.
  - Size: M. Depends on: T7, T11.
- [ ] **T13. Several test users on one goal.** One `group_id`, one queue row per persona, cards switch the player, and the finish step opens the existing grouped report. Note: `main._group` currently limits grouped runs by plan (`MAX_GROUP` 6); the allowance for live runs follows open question 1.
  - Acceptance: extra personas show "Queued" and start in turn, one browser at a time; a finding's "seen by" count comes from real runs.
  - Verify: API test for a 3-persona group; watched run in the preview.
  - Size: M. Depends on: T10, T12.
- [ ] **T13a. Editable test plan (in version 1, founder decision 2026-11-11).** Between the goal box and the persona step: a plan page with Start at, Goal, Steps and Done when, drafted by the existing goal planner (no new model path) and editable line by line. The edited goal and milestones are what the run uses.
  - Acceptance: works when the planner fails (the user's own goal text is used); edits are validated with the same length limits as `StartRun.goal`; steps are shown as "a rough path", never as a script the test user must follow.
  - Verify: API and web tests; one run started from an edited plan.
  - Size: M. Depends on: T7.

### Phase 4: Policy, deploy, acceptance

- [ ] **T14. Policy and copy.** Privacy (new section: in live runs the page loads on our server, what a frame contains, masking, retention), Terms (test only sites you own or may test; what the test user will and will not do), Security (two modes side by side), Bot page (cloud user agent and how to block it), FAQ and landing copy in `content.ts`, Docs.
  - Acceptance: no claim that everything stays in the user's browser unless scoped to the extension; no em dashes; founder approves the wording.
  - Verify: web build and lint; read-through of all four pages.
  - Size: M. Depends on: decisions 1 to 3 below.
- [ ] **T15. Deploy on the VM.** Install headless Chromium on the Ubuntu 24.04 VM; new unit `/etc/systemd/system/walkthru-runner.service` (user `walkthru`, `NoNewPrivileges`, `MemoryMax` from T0, `Restart=always`), with `CHROME_PATH` and `CLOUD_RUNNER` in the env; swap file only if T0 says so; apply the migration; update `DEPLOYMENT_GUIDE.md` (new service, Chromium now required) and `apps/api/THIRD_PARTY.md`. The founder runs or approves each command on the live VM.
  - Acceptance: API and worker services are untouched and stay up; restarting the runner mid-run leaves no orphan browser and marks the run interrupted; the API stays responsive while a journey runs.
  - Verify: restart drill on the VM.
  - Size: M. Depends on: T0, T6.
- [ ] **T16. Live acceptance and records.** Three real runs on the deployed stack (fixture, TripVerse, portfolio), one blocked-site run, one stop mid-run. Update ARCHITECTURE.md (`cloud-runner` now built), `docs/decisions.md`, SPEC.md and CURRENT_STATE.md.
  - Acceptance: results recorded with run ids; known limits listed.
  - Size: S. Depends on: all above.

### Checkpoint C: ready to switch on

- [ ] All acceptance criteria met, flag still off in production until the founder picks the plans.

## Order and parallel work

T0 first. Then T1 to T6 in order (T2 and T11 can run alongside T1). Phase 2 needs T6. T14 can be drafted any time after the open decisions are answered. Everything in this plan ships in version 1 (founder decision). Rough size: Phase 1 about 5 to 6 days, Phase 2 about 4 days, Phase 3 about 3 days with the plan page, Phase 4 about 2 to 3 days.

## Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| The live 2 GB VM cannot hold Chromium plus the API and worker | High | T0 measures it first; one browser at a time; `MemoryMax` on the runner unit so it is the runner that gets killed, never the API; browser killed after every run |
| Long waits when several users queue (up to 4 minutes per test user ahead) | Medium | Queue position shown; 3 test users per account in the queue; typical journeys take 1 to 2 minutes; move to a larger VM when the measured wait hurts |
| Server browser used to reach internal addresses | High | T3 guard on every request, tests for redirects and metadata addresses, no credentials on the VM user |
| Sites block datacentre headless browsers | Medium | Report it honestly as `bot_wall`, never solve CAPTCHAs, point the user to the extension |
| Free model limits (Groq 8k tokens per minute) when personas run in parallel | Medium | Queue personas; concurrency is one setting; UI shows "Queued" |
| Privacy promise no longer true for cloud runs | High | T14 rewrites the copy before the flag is turned on |
| Evidence storage grows (25 frames per persona) | Medium | JPEG quality 60, existing retention job, per-plan allowance |
| Our IP does the clicking on sites the user does not own | Medium | Visitor mode on unverified domains, per-host limits, honest user agent, `/bot` page |
| Screenshots capture personal data on the tested page | Medium | Existing form masking before capture; private bucket; retention; stated in Privacy |

## Open questions for the founder

Decided on 2026-11-11:

- **Unverified sites:** yes. Anyone signed in can run a live test on a public URL without verifying it, in visitor mode.
- **Concurrency:** one test user at a time on the live 2 GB VM; the rest queue.
- **Scope:** everything in this plan ships in version 1, including the editable test plan (T13a).

Still open:

1. Which plans get live runs, how many per month, and how many test users per run on each plan? (Flag and allowance are built either way. Several test users on one goal is a Plus feature today.)
2. How long are step frames kept for cloud runs? Recommended: the same retention as extension evidence.
3. Name of the feature and page ("Live run", "Watch a test user", other).

## Not in this plan

Logged-in or localhost cloud runs, saved persona groups ("swarms") beyond the existing test users list, live video streaming, mobile device runs, scheduled journeys, an "ask about this report" chat on the run page.
