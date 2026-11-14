import { worklogRows } from '../lib/harness'

export function HarnessWorklog({ events }: { events: unknown }) {
  const rows = worklogRows(events)
  if (!rows.length) return null
  return (
    <section aria-labelledby="harness-worklog-title" className="mt-10">
      <h3 id="harness-worklog-title" className="text-xl font-light tracking-tight">How Walkthru decided</h3>
      <p className="mt-2 max-w-[64ch] text-sm leading-relaxed text-muted">
        Execution checks, observed evidence and recovery decisions, recorded as the journey ran.
        These explain what the test established and where Walkthru reached its limits.
      </p>
      <ol className="mt-4 divide-y divide-line rounded-2xl border border-line">
        {rows.map((e, i) => (
          <li key={`${e.sequence}-${i}`} className="grid gap-2 px-4 py-3 text-sm sm:grid-cols-[8rem_1fr] break-inside-avoid">
            <span className="font-mono text-xs text-muted">Step {e.step}<br />{e.node}{e.action ? ` / ${e.action}` : ''}</span>
            <div>
              <p>{e.explanation}</p>
              {e.reason === 'contract_revised' && <p className="mt-1 text-xs text-muted">
                {e.before_kind}: {e.before_target || 'unknown destination'} → {e.after_kind}: {e.after_target || 'observed target'}
              </p>}
              <p className="mt-1 text-xs text-muted">
                {e.checkpoint ? `Checkpoint ${e.checkpoint}. ` : ''}{e.progress} checkpoints confirmed at this decision.
              </p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  )
}
