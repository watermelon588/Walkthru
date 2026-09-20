import type { Run } from '../lib/runs'

const stages = [
  { label: 'AI journey testing', detail: 'real browser steps' },
  { label: 'Visual evidence', detail: 'private screenshots' },
  { label: 'Technical checks', detail: 'SEO and security' },
  { label: 'Prioritized fixes', detail: 'shareable report' },
] as const

export function ReadinessPipeline({ runs }: { runs: Run[] }) {
  const values = [
    runs.filter((run) => run.kind === 'test').length,
    runs.reduce((sum, run) => sum + run.steps.filter((step) => step.evidence).length, 0),
    runs.reduce((sum, run) => sum + (run.report?.findings.filter((finding) => finding.kind !== 'ux').length ?? 0), 0),
    runs.filter((run) => run.report).length,
  ]

  return (
    <section aria-labelledby="pipeline-title" className="mt-10">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Launch-readiness pipeline</p>
          <h2 id="pipeline-title" className="mt-2 text-2xl font-light tracking-tight">One run, four layers of proof</h2>
        </div>
        <span className="hidden text-xs text-muted sm:block">Updated from your latest 50 runs</span>
      </div>
      <ol className="mt-5 grid gap-px overflow-hidden rounded-2xl bg-line sm:grid-cols-2 lg:grid-cols-4">
        {stages.map((stage, index) => (
          <li key={stage.label} className="bg-bg px-5 py-5">
            <div className="flex items-center justify-between gap-3">
              <span className="font-mono text-[10px] text-muted">0{index + 1}</span>
              <span className="font-mono text-lg tabular-nums">{values[index]}</span>
            </div>
            <h3 className="mt-7 text-sm font-medium">{stage.label}</h3>
            <p className="mt-1 text-xs text-muted">{stage.detail}</p>
          </li>
        ))}
      </ol>
    </section>
  )
}
