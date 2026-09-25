import { Link } from 'react-router'
import { ApiKeys } from '../components/ApiKeys'
import { AppShell } from '../components/AppShell'
import { PageHeader } from '../components/PageHeader'

const tools = [
  { name: 'scan_site', body: 'Scans a public site: SEO, AI search readiness, passive security and a first impression, in about 20 seconds.' },
  { name: 'get_report', body: 'Reads any of your reports in full, with the evidence and the fix for each finding.' },
  { name: 'get_fix_prompt', body: 'Returns the fix prompt, so your agent can apply every fix in the codebase it has open.' },
  { name: 'get_finding', body: 'Everything about one finding: why it matters, every affected page, the change and ready-made code when there is some.' },
  { name: 'verify_finding', body: 'Re-runs only the check behind one finding, on its pages, and answers fixed or still broken.' },
  { name: 'rerun', body: 'Checks the site again after the fixes and says what disappeared and what is new.' },
  { name: 'list_runs', body: 'Lists your recent runs and scans with their Launch Ready scores.' },
]

/** Plus: connect Claude Code, Cursor or any MCP client to Walkthru. */
export default function Mcp() {
  return (
    <AppShell title="MCP">
      <PageHeader kicker="Plus" title="Connect your editor">
        Your coding agent can scan your site, read the report, apply the fixes and rerun, without leaving the editor. It uses the same checks, limits and honesty rules as this dashboard.
      </PageHeader>

      <ApiKeys />

      <section aria-labelledby="tools-heading" className="mt-14 border-t border-line pt-10">
        <div className="grid gap-10 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
          <div>
            <h2 id="tools-heading" className="text-xl font-light">What your agent can do</h2>
            <p className="mt-2 max-w-[48ch] text-sm leading-relaxed text-muted">
              Each key reaches only your own runs. Test journeys still run from the Chrome extension; rerun repeats the server-side checks.
            </p>
            <Link to="/docs#mcp" className="mt-4 inline-block text-sm text-ink underline decoration-line underline-offset-4 transition hover:decoration-ink">Setup guide</Link>
          </div>
          <dl className="border-t border-line">
            {tools.map((t) => (
              <div key={t.name} className="grid gap-1 border-b border-line py-3 sm:grid-cols-[9rem_1fr] sm:gap-4">
                <dt className="font-mono text-xs text-ink">{t.name}</dt>
                <dd className="text-sm leading-relaxed text-muted">{t.body}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>
    </AppShell>
  )
}
