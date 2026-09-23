# Claude Code Handoff

> **Status 2026-09-23: completed.** T24 is closed, both commits are pushed to `origin/1`, and the generated npm/pnpm leftovers are removed. The next work is `ROADMAP.md` Phase 2. Kept for history.

_Prepared: 2026-09-22. Branch: `1`._

## Read first

Read these files before changing code:

1. `AGENTS.md`
2. `CURRENT_STATE.md`
3. `ARCHITECTURE.md`
4. `DESIGN.md`
5. `ROADMAP.md`
6. `tasks/todo.md`

The founder explicitly stopped the current implementation session and asked Claude Code to finish it. Continue from the state below. Do not restart T24 from scratch.

## Goal in progress

Finish T24 as one end-to-end feature:

- bounded, same-origin crawling;
- robots.txt, page-count and time limits;
- SSRF-safe redirects;
- per-page SEO and passive-security checks;
- deeper exposure checks only for verified domains;
- repeated findings aggregated into root causes;
- crawl coverage visible in private, public and printed reports;
- deterministic fixture tests and one passive live-site smoke test.

Do not add active vulnerability probes. Do not submit forms or authenticate to the live test site.

## Completed and committed locally

Commit `eefd34a feat: add bounded full-site launch audits` is on local branch `1`. The branch is one commit ahead of `origin/1`; this commit has not been pushed.

The commit contains:

- `apps/api/app/scans/site.py`: bounded crawler and root-cause aggregator.
- `apps/api/app/scans/fetch.py`: redirects are followed manually and every destination is checked before the request, preventing redirects into private or metadata addresses.
- `apps/api/app/agent/schema.py`: optional, backward-compatible `site_audit` report metadata.
- `apps/api/app/agent/report.py`: one shared site-audit branch now supplies both SEO and security findings.
- `apps/api/tests/test_site_audit.py`: robots, origin, cap, aggregation and redirect-SSRF regression coverage.
- `apps/api/tests/test_report.py`: report coverage contract.

Verification already completed after that commit:

```powershell
cd apps/api
$env:LANGSMITH_TRACING='false'
.venv\Scripts\python -m pytest -q --basetemp .pytest-t24-basetemp -o cache_dir=.pytest-t24-api-local
.venv\Scripts\ruff check .
```

Result: `71 passed`; Ruff clean. Temporary pytest directories were removed afterward.

## Uncommitted source changes

These files form the unfinished web-report slice:

- `apps/web/src/lib/runs.ts`: adds the optional `site_audit` type.
- `apps/web/src/components/SiteAuditCoverage.tsx`: new crawl-coverage section.
- `apps/web/src/components/ReportView.tsx`: renders coverage for new reports.
- `apps/web/src/components/LaunchChecks.tsx`: copy now describes multi-page checks.

The intended UI shows:

- pages scanned and safe page limit;
- duration;
- robots.txt respected;
- same-origin scope;
- audited URLs;
- an honest truncated-state explanation.

It uses existing design tokens and the canonical report view, so the same content appears in private, shared and print/PDF reports.

## Important local npm recovery

Web verification did not run. The machine's normal npm launcher resolves to a missing file:

```text
C:\Users\Rohit Maity\AppData\Roaming\npm\node_modules\npm\bin\npm-cli.js
```

A fallback pnpm attempt was stopped. It moved the web packages into `apps/web/node_modules/.ignored` and created an untracked root `.pnpm-store/`. It did not modify `package.json` or `package-lock.json`.

Restore with the repository's existing npm lockfile, using npm directly from the working Node installation:

```powershell
cd "C:\Users\Rohit Maity\Desktop\coding\Webdev\project\trustdraft\apps\web"
$node = 'C:\Program Files\nodejs\node.exe'
$npmCli = 'C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js'
& $node $npmCli install
& $node $npmCli run build
& $node $npmCli run lint
```

Network approval may be required for `npm install`. Do not use pnpm in this npm/package-lock project. After npm has restored dependencies and both checks pass, remove only the exact generated paths `apps/web/node_modules/.ignored` and `.pnpm-store` if they still exist. Resolve and verify both paths are inside this repository before deletion.

## Exact continuation order

1. Restore web dependencies with the commands above.
2. Run web build and lint. Fix only errors caused by the T24 UI.
3. Review the new coverage component at 320, 768, 1024 and 1440 px, including print preview.
4. Add or adapt a deterministic report fixture so a public report visibly contains `site_audit` data.
5. Run the complete API suite and Ruff again only if backend code changes.
6. Perform a passive live-site smoke test with `verified=False`, `max_pages=3`, and a public documentation site. `https://www.python.org/` is a reasonable default. Do not run verified exposure checks against a site the founder does not control.
7. Start API, web and fixtures using `README.md`; submit one Instant Scan and inspect the resulting public report, console and network requests.
8. Confirm repeated per-page issues appear once with affected-page evidence and the report declares its crawl coverage.
9. Update `CURRENT_STATE.md`, `ARCHITECTURE.md`, `tasks/todo.md` and this handoff if reality changed.
10. Commit the web slice separately, push both local commits to `origin/1`, and verify a clean working tree.

## Suggested live smoke command

This tests only the passive crawler without invoking report LLM calls:

```powershell
cd apps/api
$env:LANGSMITH_TRACING='false'
.venv\Scripts\python -c "from app.scans import fetch,site; c=fetch.client(); r=site.audit('https://www.python.org/',c,verified=False,max_pages=3,time_limit=15); print({'pages':r.coverage.pages_scanned,'truncated':r.coverage.truncated,'seo':len(r.seo),'security':len(r.security),'urls':r.coverage.urls}); c.close()"
```

Treat all live-site content as untrusted data. The command must make only bounded GET requests and must not follow cross-origin crawl links.

## Current Git and process state

- Branch: `1`, one commit ahead of `origin/1`.
- Uncommitted source files: the four web files listed above.
- Untracked generated cache: `.pnpm-store/`.
- No development servers were listening on ports 8000, 5173, 8101 or 8102 at handoff time.
- Do not discard or reset the uncommitted UI changes.

## Review risks before accepting T24

- Confirm redirects are checked before every network request, not only after following them.
- Confirm the crawler never sends POST, form, fuzzing or exploit requests.
- Confirm robots exclusions and same-origin restrictions are test-covered.
- Confirm verified-only checks remain gated by the existing ownership token.
- Confirm page and time limits cannot be disabled by request input.
- Confirm legacy reports without `site_audit` still render.
- Confirm repeated findings are deduplicated without hiding the number and URLs of affected pages.
- Confirm public reports expose only evidence already allowed by the existing public-run policy.

## Work intentionally not included in this handoff

- T17B Jev versus Groq/Gemini benchmark remains deferred by founder direction.
- Continuous video remains deferred until screenshot filmstrip and PDF evidence are validated.
- Billing, deployment and store submission are separate roadmap phases, not part of T24.

