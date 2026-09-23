# Walkthru Completion Roadmap

_Updated: 2026-09-22. Detailed task state lives in `tasks/todo.md`._

## Product finish line

Walkthru is ready to launch when a stranger can install the extension, sign in, test a public or authenticated flow safely, receive a truthful evidence-backed launch-readiness report, share or export it, understand its limits, and pay for another run in production without founder intervention.

## Dependency order

```text
Development environment recovery
        |
        v
T24 full-site audit completion
        |
        v
Evidence, retention and report QA
        |
        +------------------+
        v                  v
Store/legal readiness   Production infrastructure
        |                  |
        +---------+--------+
                  v
          Billing and limits
                  |
                  v
        Launch onboarding and GTM
                  |
                  v
       Post-launch retention features
```

## Phase 0: Stabilize the handoff (done 2026-09-23)

**Outcome:** Claude Code can build and verify the current branch without losing partial work.

- Restore `apps/web/node_modules` from `package-lock.json` using npm.
- Remove the generated `.pnpm-store` only after npm recovery succeeds.
- Finish and verify the uncommitted T24 report UI.
- Push local commit `eefd34a` and the final T24 UI commit to branch `1`.

**Gate:** clean working tree; API, web and extension verification commands are green.

## Phase 1: Complete T24 full-site launch audit (done 2026-09-23)

**Outcome:** one bounded crawl produces a deduplicated, evidence-backed SEO and passive-security section.

- Preserve robots, same-origin, SSRF, page-cap and time-limit guarantees.
- Show page coverage and truncation honestly in private, public and PDF views.
- Test easy/hard fixtures plus one passive public live site.
- Verify that unverified scans never request exposed-file or bundle-secret paths.
- Document crawl limits and verification behavior in architecture and user-facing copy.

**Gate:** launch-readiness checkpoint passes for UX, accessibility, performance, SEO and passive security in one report.

## Phase 2: Close evidence and privacy gaps

**Outcome:** screenshot evidence is reliable, reviewable and automatically expires.

- Run one fresh real-browser easy-fixture journey with screenshots, axe and Web Vitals.
- Verify owner-only evidence, public-share evidence and multi-page PDF output.
- Link normalized findings to exact journey steps where evidence exists.
- Define screenshot retention, implement automated cleanup and show the policy to users.
- Add account data export and deletion paths for runs, reports and evidence before production launch.
- Complete desktop, phone and print visual QA.

**Gate:** every meaningful captured step has reproducible visual proof, and retained personal data has a deletion path.

## Phase 3: Provider quality decision

**Outcome:** the default decision provider is chosen using evidence, not speed claims.

- Keep the current LLM default until T17B is intentionally resumed.
- Run identical easy and hard sessions through Groq/Gemini and Jev-hybrid.
- Compare recall, median latency, fallback rate, cost and persona fidelity.
- Publish the comparable LangSmith experiment and update `docs/decisions.md`.
- Enable Jev by default only if it clears the agreed quality gate.

**Gate:** provider decision is recorded and reversible. This phase is deferred until the founder resumes it.

## Phase 4: Distribution, trust and Chrome Store

**Outcome:** the extension can be reviewed and installed by strangers.

- Build real Privacy, Terms and Security pages; remove footer placeholder links.
- Document data collection, screenshot masking, retention, subprocessors and deletion.
- Audit extension permissions and production `externally_connectable` origins.
- Create store listing copy, screenshots, demo video and support contact.
- Submit early because review can take days.
- Enable and verify Google and GitHub OAuth production redirect URLs.

**Gate:** a fresh Chrome profile can install, authenticate and complete a fixture run using the store build.

## Phase 5: Billing and product limits

**Outcome:** paid usage is enforceable and retry-safe.

- Finalize plans and credits with founder approval before changing pricing.
- Add Dodo checkout, signed webhook verification and atomic idempotency handling.
- Add a credit ledger, run reservation/refund rules and clear insufficient-credit UI.
- Test duplicate webhooks, delayed webhooks, failed checkout and refund behavior.
- Keep free report quality intact; paid value comes from volume, authenticated flows and collaboration.

**Gate:** test-mode purchase grants exactly the intended credits once, and one completed run consumes the intended amount once.

## Phase 6: Production reliability and deployment

**Outcome:** web, API, database and extension operate reliably outside localhost.

- Buy/configure the production domain and HTTPS.
- Deploy web with SPA rewrites and API with persistent process supervision.
- Configure production CORS, extension origin, Supabase redirects, Resend and PageSpeed.
- Replace per-process scan limiting with a shared production limiter.
- Add structured error logging, health checks, uptime alerts and a run/report failure dashboard.
- Add database backup, restore and migration runbooks.
- Split oversized web and extension bundles before store submission if warnings remain.
- Rotate every secret shared during development before launch.

**Gate:** a clean production browser can complete signup, extension handoff, run, report, share, email and payment without local services.

## Phase 7: Launch surface and validation

**Outcome:** visitors understand the product and can reach value quickly.

- Wire pricing buttons to real checkout.
- Replace placeholder product images with current real captures.
- Publish a representative public demo report.
- Add onboarding for extension install, permissions, safe mode and domain verification.
- Test at least 20 community sites and classify failures before public launch.
- Verify analytics are privacy-minimized and contain no DOM snapshots, credentials or report evidence.
- Finish Product Hunt, Show HN, community and agency launch assets.

**Gate:** a stranger installs, tests, understands the report, shares it and pays without founder help.

## Phase 8: Post-launch retention and team value

Build only after launch gates are stable:

1. rerun comparison;
2. multi-persona synthesis;
3. scheduled audits;
4. Slack, Linear and GitHub delivery;
5. optional continuous video, only if filmstrip research proves incremental value;
6. safe browser-session resume, only with tab, origin, checkpoint and pending-action revalidation.

## Definition of done for every phase

- Acceptance criteria have deterministic tests.
- API pytest and Ruff are green when backend code changes.
- Web/extension type checks, lint, tests and production builds are green when those surfaces change.
- Browser-facing work is inspected at phone and desktop widths with a clean console.
- Security-sensitive changes include an abuse-case review.
- No secrets, `.env`, build output or generated caches are committed.
- `CURRENT_STATE.md`, `tasks/todo.md` and relevant architecture/design docs match reality.
- Changes are committed atomically and pushed to branch `1` unless the founder chooses another branch.

