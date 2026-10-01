# Remaining work, 2026-09-28

Snapshot after SD-8.1, the local SD-6.2 implementation and the SD-6.5 run retry work. This batch is finished; no next batch has been claimed. The authoritative acceptance criteria remain in [system design](system-design.md) and [product tasks](../tasks/todo.md). Open means acceptance is unfinished; some code may already exist.

**Completed locally:** request logging/support references (SD-8.1), durable checkpoint implementation and restart tests (SD-6.2), and run retry idempotency with safe extension retries and partial-report recovery (SD-6.5 run scope). **Still open:** migration 0002, VM configuration/live restart check; migration 0003 and deployed retry acceptance; SD-6.5's separate payment acceptance. No production migration, deployment or paid integration was performed.

## System tasks, ascending difficulty

| Difficulty | Task | Remaining area | Prerequisite |
|---|---|---|---|
| 1/5 | SD-1.2 | CAA record and certificate monitoring | Needs setup/approval |
| 1/5 | SD-1.5 | `security.txt` | Code work; check task prerequisites |
| 1/5 | SD-2.5 | Kill switches | Code work; check task prerequisites |
| 1/5 | SD-4.1 | XSS stays impossible by construction | Code work; check task prerequisites |
| 1/5 | SD-4.2 | Security headers on the API too | Code work; check task prerequisites |
| 1/5 | SD-4.4 | CSRF: document why it does not apply | Code work; check task prerequisites |
| 1/5 | SD-4.8 | Rotate everything that was ever shared or committed | Needs setup/approval |
| 1/5 | SD-6.7 | Health and readiness | Code work; check task prerequisites |
| 1/5 | SD-7.3 | Put the VM next to the database | Needs setup/approval |
| 1/5 | SD-8.3 | Uptime and alerting | Needs setup/approval |
| 1/5 | SD-9.6 | Remove dev-only code from production | Code work; check task prerequisites |
| 1/5 | SD-10.4 | Incident and breach process | Needs setup/approval |
| 2/5 | SD-1.1 | Put the domain behind Cloudflare | Needs setup/approval |
| 2/5 | SD-1.3 | Cloudflare WAF and bot rules (free tier) | Needs setup/approval |
| 2/5 | SD-1.4 | Email DNS for our own domain | Needs setup/approval |
| 2/5 | SD-2.4 | Sign-up and sign-in abuse | Needs setup/approval |
| 2/5 | SD-3.4 | Session storage in the extension | Code work; check task prerequisites |
| 2/5 | SD-3.6 | Enable Google and GitHub sign-in with production redirect URLs | Needs setup/approval |
| 2/5 | SD-4.3 | No internal details in errors | Code work; check task prerequisites |
| 2/5 | SD-4.6 | Prompt-injection hygiene | Code work; check task prerequisites |
| 2/5 | SD-4.9 | Extension hardening for the store | Needs setup/approval |
| 2/5 | SD-5.3 | Indexes for every hot query | Code work; check task prerequisites |
| 2/5 | SD-5.4 | RLS regression tests | Code work; check task prerequisites |
| 2/5 | SD-5.5 | Personal data inventory | Code work; check task prerequisites |
| 2/5 | SD-6.2 (partial) | Postgres checkpointer on the VM | Needs setup/approval |
| 2/5 | SD-6.4 | Graceful shutdown | Code work; check task prerequisites |
| 2/5 | SD-6.6 | Process supervision on the VM | Needs setup/approval |
| 2/5 | SD-7.1 | Set latency budgets and measure them | Code work; check task prerequisites |
| 2/5 | SD-7.5 | Load test before launch | Code work; check task prerequisites |
| 2/5 | SD-8.2 | Error tracking and metrics | Needs setup/approval |
| 2/5 | SD-8.5 | Runbooks | Code work; check task prerequisites |
| 2/5 | SD-9.1 | CI on every push and pull request | Needs setup/approval |
| 2/5 | SD-9.4 | API versioning for the extension | Code work; check task prerequisites |
| 2/5 | SD-10.2 | Spend guards for paid models | Code work; check task prerequisites |
| 2/5 | SD-10.3 | Legal review | Needs setup/approval |
| 3/5 | SD-3.5 | Founder admin tools behind a separate role | Needs setup/approval |
| 3/5 | SD-5.2 | Backups and a restore drill | Needs setup/approval |
| 3/5 | SD-6.5 (partial) | Activate tested run idempotency; separate payment idempotency acceptance | Production migration/deployment and payment setup |
| 3/5 | SD-7.4 | Prerender the marketing pages | Needs setup/approval |
| 3/5 | SD-7.6 | Horizontal scaling (only when SD-6.1, 6.2 and 2.1 are done and one VM is not enough) | Deferred until after launch; needs spend approval |
| 3/5 | SD-8.4 | Security audit log | Code work; check task prerequisites |
| 3/5 | SD-9.3 | Staging environment | Needs setup/approval |
| 3/5 | SD-9.5 | One-command deploy and rollback | Code work; check task prerequisites |
| 4/5 | SD-10.1 | Dodo webhooks done right (V10) | Needs setup/approval |

## Product backlog with open acceptance criteria

These items are separate from system hardening and include later-phase expansion. Do not treat every later-phase feature as a launch blocker. See each phase checkpoint and launch gate in the task list.

- P0.3: First impression v2 and landing copy review (V19).
- P1.2: Security parity (partially completed; see remaining validation).
- P2.1: GitHub App connect.
- P2.2: Code scans on the worker.
- P2.3: File and line in the fix plan.
- P2.4: Nuclei with safe templates on verified domains.
- P3.1: Search Console and Bing Webmaster connect.
- P3.3: Sources and accuracy.
- P3.4: Weekly watch and deploy webhook (V12).
- P3.5: AI traffic.
- P3.6: Citability rewrites.
- P4.1: Opt-in active scan of a staging URL.
- P4.5: Paid engines and Claude Haiku.
- P4.6: Cloud runner (V14).

Also open: the live citation showcase checked twice, security false-positive checks on verified sites, fixture recall and evidence/PDF close-out, final copy/onboarding, beta-user validation, store submission, and the complete production stranger journey. Payment work includes Dodo test-mode verification, credit reservation/refund rules, live verification, and the deferred offer notice/coupons; it remains outside this batch.

SD-3.2 (bounded LRU auth cache), SD-3.3 (extension sender/session validation), SD-6.3 (provider resilience) and SD-7.2 (public scan caching, parallel task) are complete locally. Next choices, ascending difficulty: **SD-4.2** (API security headers), **SD-5.5** (personal-data inventory and deletion coverage), **SD-6.4** (graceful shutdown), or **SD-8.4** (owner-visible security audit log). Read current task claims again before starting to avoid overlap with another agent. The founder chooses the next batch. Production activation and the full-suite environment limitations remain recorded in CURRENT_STATE.md.
