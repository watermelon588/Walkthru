import { KIND_LABEL, PERSONA_LABEL, STATUS_LABEL, type Finding, type Run } from '../lib/runs'

/** The report body. Shared by the signed-in report page and the public share page. */
export function ReportView({ run }: { run: Run }) {
  const r = run.report
  const steps = run.steps ?? []
  const peak = Math.max(0, ...steps.map((s) => s.confusion))
  const stuckAt = steps.findIndex((s) => s.confusion >= 2)
  const isScan = run.kind === 'scan'
  const counts = { high: 0, medium: 0, low: 0 }
  for (const f of r?.findings ?? []) counts[f.severity]++

  return (
    <article>
      <header>
        <p className="font-mono text-xs text-muted">{run.site}</p>
        <h1 className="mt-2 text-3xl font-extralight tracking-tight md:text-5xl">{isScan ? 'Instant Scan' : run.goal}</h1>
        <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted">
          <span>{PERSONA_LABEL[run.persona] ?? run.persona}</span>
          {!isScan && <StatusPill status={run.status} />}
          <time dateTime={run.created_at}>{new Date(run.created_at).toLocaleString()}</time>
        </div>
      </header>

      {r ? (
        <>
          <p className="mt-8 max-w-[64ch] text-lg leading-relaxed">{r.summary}</p>

          <section aria-label="Summary" className="mt-8 grid gap-px overflow-hidden rounded-2xl bg-line sm:grid-cols-3">
            <Stat label="Findings" value={String(r.findings.length)} note={`${counts.high} high · ${counts.medium} medium · ${counts.low} low`} />
            {isScan ? (
              <Stat label="First impression clarity" value={r.first_impression ? `${3 - r.first_impression.clarity} of 3` : '?'} note="3 = instantly clear" />
            ) : (
              <Stat label="Outcome" value={STATUS_LABEL[run.status]} note={`${steps.length} steps`} />
            )}
            <Stat label={isScan ? 'Security scan' : 'Peak confusion'} value={isScan ? (r.verified ? 'Full' : 'Headers only') : `${peak} of 3`} note={isScan ? (r.verified ? 'domain verified' : 'verify your domain for exposed files and secrets') : stuckAt >= 0 ? `first at step ${stuckAt + 1}` : 'never confused'} />
          </section>

          {r.first_impression && (
            <section aria-label="First impression" className="mt-12">
              <h2 className="text-xl font-light tracking-tight">First impression, five seconds in</h2>
              <dl className="mt-4 grid gap-4 sm:grid-cols-2">
                <Item term="What this site does" desc={r.first_impression.what} />
                <Item term="Who it is for" desc={r.first_impression.who} />
                <Item term="What they would click first" desc={r.first_impression.first_click} />
                <Item term="Trust signals" desc={r.first_impression.trust.join(' · ') || 'none noticed'} />
              </dl>
            </section>
          )}

          {r.top_fixes.length > 0 && (
            <section aria-label="Top fixes" className="mt-12 rounded-2xl bg-surface px-6 py-6">
              <h2 className="text-xl font-light tracking-tight">Fix these first</h2>
              <ol className="mt-4 grid gap-3">
                {r.top_fixes.map((f, i) => (
                  <li key={i} className="grid grid-cols-[2rem_1fr] gap-2 leading-relaxed">
                    <span className="font-mono text-xs text-muted pt-1">{i + 1}</span>
                    <span>{f}</span>
                  </li>
                ))}
              </ol>
            </section>
          )}

          <section aria-label="All findings" className="mt-12">
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
        <p role="status" className="mt-8 text-muted">
          {run.status === 'running' ? 'The test user is still working through the site.' : 'Writing the report. This takes about half a minute.'}
        </p>
      )}

      {steps.length > 0 && (
        <section aria-label="Think-aloud log" className="mt-12">
          <h2 className="text-xl font-light tracking-tight">What the test user did</h2>
          <ol className="mt-4 border-t border-line">
            {steps.map((s, i) => (
              <li key={i} className={`grid grid-cols-[2rem_1fr] gap-3 border-b border-line py-4 ${s.confusion >= 2 ? '-mx-3 rounded-xl bg-surface/60 px-3' : ''}`}>
                <span className="pt-0.5 font-mono text-xs text-muted">{i + 1}</span>
                <div className="min-w-0">
                  <p className="leading-relaxed">{s.thought}</p>
                  <p className="mt-1 truncate font-mono text-xs text-muted">
                    {s.action}{s.target_id != null ? ` #${s.target_id}` : ''}{s.text ? ` "${s.text}"` : ''} · {s.url}
                    {s.confusion >= 2 && <span className="ml-2 text-danger">confused ({s.confusion})</span>}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        </section>
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
