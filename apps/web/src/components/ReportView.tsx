import { KIND_LABEL, PERSONA_LABEL, STATUS_LABEL, type Finding, type Run } from '../lib/runs'
import { AgentPresence, type AgentPresenceState } from './AgentPresence'
import { EvidenceTimeline } from './EvidenceTimeline'
import { LaunchChecks } from './LaunchChecks'
import { SiteAuditCoverage } from './SiteAuditCoverage'

/** The report body. Shared by the signed-in report page and the public share page. */
export function ReportView({ run }: { run: Run }) {
  const r = run.report
  const steps = run.steps ?? []
  const peak = Math.max(0, ...steps.map((s) => s.confusion))
  const stuckAt = steps.findIndex((s) => s.confusion >= 2)
  const isScan = run.kind === 'scan'
  const counts = { high: 0, medium: 0, low: 0 }
  for (const f of r?.findings ?? []) counts[f.severity]++
  const stopped = ['gave_up', 'budget', 'stuck', 'captcha', 'stopped'].includes(run.status)
  const agentState: AgentPresenceState = stopped ? 'stopped' : r ? 'complete' : 'observing'
  const agentActivity = stopped
    ? STATUS_LABEL[run.status]
    : r
      ? 'Report ready'
      : isScan
        ? 'Scanning this homepage'
        : 'Testing this flow'

  return (
    <article className="report-root">
      <header className="report-cover grid gap-6 sm:grid-cols-[1fr_auto] sm:items-end">
        <div>
          <p className="report-kicker font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Launch readiness report</p>
          <p className="mt-3 font-mono text-xs text-muted">{run.site}</p>
          <h1 className="mt-2 text-3xl font-extralight tracking-tight md:text-5xl">{isScan ? 'Instant Scan' : run.goal}</h1>
          <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted">
            <span>{PERSONA_LABEL[run.persona] ?? run.persona}</span>
            {!isScan && <StatusPill status={run.status} />}
            <time dateTime={run.created_at}>{new Date(run.created_at).toLocaleString()}</time>
          </div>
        </div>
        <AgentPresence activity={agentActivity} state={agentState} phase={0.32} />
      </header>

      {r ? (
        <>
          <p className="mt-8 max-w-[64ch] text-lg leading-relaxed">{r.summary}</p>

          <section aria-label="Summary" className="report-summary mt-8 grid gap-px overflow-hidden rounded-2xl bg-line sm:grid-cols-3">
            <Stat label="Findings" value={String(r.findings.length)} note={`${counts.high} high / ${counts.medium} medium / ${counts.low} low`} />
            {isScan ? (
              <Stat label="First impression clarity" value={r.first_impression ? `${3 - r.first_impression.clarity} of 3` : '?'} note="3 = instantly clear" />
            ) : (
              <Stat label="Outcome" value={STATUS_LABEL[run.status]} note={`${steps.length} steps`} />
            )}
            <Stat label={isScan ? 'Security scan' : 'Peak confusion'} value={isScan ? (r.verified ? 'Full' : 'Headers only') : `${peak} of 3`} note={isScan ? (r.verified ? 'domain verified' : 'verify your domain for exposed files and secrets') : stuckAt >= 0 ? `first at step ${stuckAt + 1}` : 'never confused'} />
          </section>

          {!isScan && steps.length > 0 && <EvidenceTimeline steps={steps} />}

          {r.first_impression && (
            <section aria-label="First impression" className="report-print-section mt-12">
              <h2 className="text-xl font-light tracking-tight">First impression, five seconds in</h2>
              <dl className="mt-4 grid gap-4 sm:grid-cols-2">
                <Item term="What this site does" desc={r.first_impression.what} />
                <Item term="Who it is for" desc={r.first_impression.who} />
                <Item term="What they would click first" desc={r.first_impression.first_click} />
                <Item term="Trust signals" desc={r.first_impression.trust.join(', ') || 'none noticed'} />
              </dl>
            </section>
          )}

          {r.site_audit && <SiteAuditCoverage audit={r.site_audit} />}

          <LaunchChecks findings={r.findings} verified={r.verified} states={r.checks} />

          {r.top_fixes.length > 0 && (
            <section aria-label="Top fixes" className="report-print-section print-break-before mt-14">
              <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Prioritized fixes</p>
              <h2 className="mt-2 text-2xl font-light tracking-tight">Fix these first</h2>
              <ol className="mt-5 overflow-hidden rounded-2xl border border-line bg-line">
                {r.top_fixes.map((f, i) => (
                  <li key={i} className="grid grid-cols-[3rem_1fr] gap-3 border-b border-line bg-bg px-5 py-4 leading-relaxed last:border-b-0">
                    <span className="font-mono text-xs text-muted pt-1">P{String(i + 1).padStart(2, '0')}</span>
                    <span>{f}</span>
                  </li>
                ))}
              </ol>
            </section>
          )}

          <section aria-label="All findings" className="report-print-section mt-12">
            <h2 className="text-xl font-light tracking-tight">All findings</h2>
            {r.findings.length === 0 ? (
              <p role="status" className="mt-4 text-sm text-muted">Nothing to report. Nice.</p>
            ) : (
              <ul className="mt-4 border-t border-line">
                {r.findings.map((f, i) => <FindingRow key={i} f={f} />)}
              </ul>
            )}
          </section>
        </>
      ) : (
        <>
          <p role="status" className="mt-8 text-muted">
            {run.status === 'running' ? 'The test user is still working through the site.' : 'Writing the report. This takes about half a minute.'}
          </p>
          {!isScan && steps.length > 0 && <EvidenceTimeline steps={steps} />}
        </>
      )}
    </article>
  )
}

function FindingRow({ f }: { f: Finding }) {
  const tone = f.severity === 'high' ? 'text-danger' : f.severity === 'medium' ? 'text-ink' : 'text-muted'
  return (
    <li className="grid gap-2 border-b border-line py-5 sm:grid-cols-[7rem_1fr]">
      <div className="flex gap-2 text-xs sm:flex-col sm:gap-1">
        <span className={`font-medium ${tone}`}>{f.severity}</span>
        <span className="text-muted">{KIND_LABEL[f.kind]}</span>
      </div>
      <div className="min-w-0">
        <h3 className="font-medium">{f.title}</h3>
        <p className="mt-1 leading-relaxed text-muted">{f.detail}</p>
        <p className="mt-2 leading-relaxed"><span className="text-muted">Fix: </span>{f.fix}</p>
        {f.evidence && <p className="mt-2 truncate font-mono text-xs text-muted">{f.evidence}</p>}
      </div>
    </li>
  )
}

export function StatusPill({ status }: { status: Run['status'] }) {
  const tone = status === 'done' ? 'text-accent' : status === 'running' ? 'text-muted' : 'text-danger'
  return <span className={`rounded-full border border-line px-2.5 py-0.5 ${tone}`}>{STATUS_LABEL[status]}</span>
}

function Stat({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="bg-bg px-5 py-4">
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-1 text-lg font-light">{value}</p>
      {note && <p className="text-xs text-muted">{note}</p>}
    </div>
  )
}

function Item({ term, desc }: { term: string; desc: string }) {
  return (
    <div className="rounded-2xl border border-line px-5 py-4">
      <dt className="text-xs text-muted">{term}</dt>
      <dd className="mt-1 leading-relaxed">{desc}</dd>
    </div>
  )
}
