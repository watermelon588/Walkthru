import { Link } from 'react-router'
import type { RunSummary } from '../lib/runs'

const stages = [
  { label: 'AI journey testing', detail: 'test runs in loaded history' },
  { label: 'Visual evidence', detail: 'screenshots are shown inside each run' },
  { label: 'Technical checks', detail: 'measured checks are shown in reports' },
  { label: 'Prioritized fixes', detail: 'recommendations are shown in reports' },
] as const

export function ReadinessPipeline({ runs }: { runs: RunSummary[] }) {
  const latest = runs.find((run) => run.status !== 'running' && run.kind !== 'compare')

  return (
    <section aria-labelledby="pipeline-title" className="mt-10">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Launch-readiness pipeline</p>
          <h2 id="pipeline-title" className="mt-2 text-2xl font-light tracking-tight">One run, four layers of proof</h2>
        </div>
        <span className="hidden text-xs text-muted sm:block">Based on {runs.length} loaded runs</span>
      </div>
      <ol className="mt-5 grid gap-px overflow-hidden rounded-2xl bg-line sm:grid-cols-2 lg:grid-cols-4">
        {stages.map((stage, index) => (
          <li key={stage.label} className="bg-bg px-5 py-5">
            <div className="flex items-center justify-between gap-3">
              <span className="font-mono text-[10px] text-muted">0{index + 1}</span>
              {index === 0 ? <span className="font-mono text-lg tabular-nums">{runs.filter((run) => run.kind === 'test').length}</span>
                : <span className="text-xs text-muted">Inside each run</span>}
            </div>
            <h3 className="mt-7 text-sm font-medium">{stage.label}</h3>
            <p className="mt-1 text-xs text-muted">{stage.detail}</p>
          </li>
        ))}
      </ol>
      <p className="mt-3 text-xs leading-relaxed text-muted">
        Open a run to see its captured evidence, completed checks and fixes. History does not load these details.
        {latest && <> <Link to={`/app/runs/${latest.id}`} className="text-ink underline decoration-line underline-offset-4">View recent run</Link></>}
      </p>
    </section>
  )
}
