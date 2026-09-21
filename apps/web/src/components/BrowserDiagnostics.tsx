import type { BrowserDiagnostics as BrowserDiagnosticsData } from '../lib/runs'

export function BrowserDiagnostics({ diagnostics }: { diagnostics: BrowserDiagnosticsData }) {
  const { accessibility, web_vitals: vitals } = diagnostics
  const metrics = [
    vitals.lcp_ms != null ? { label: 'LCP', value: formatMs(vitals.lcp_ms), rating: rate(vitals.lcp_ms, 2500, 4000) } : null,
    vitals.cls != null ? { label: 'CLS', value: vitals.cls.toFixed(3), rating: rate(vitals.cls, 0.1, 0.25) } : null,
    vitals.inp_ms != null ? { label: 'INP', value: formatMs(vitals.inp_ms), rating: rate(vitals.inp_ms, 200, 500) } : null,
  ].filter((metric): metric is NonNullable<typeof metric> => Boolean(metric))

  return (
    <section aria-labelledby="browser-evidence-title" className="mt-6 border-t border-line pt-5">
      <p id="browser-evidence-title" className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted">Browser evidence</p>

      {metrics.length > 0 ? (
        <dl className="mt-3 grid grid-cols-3 gap-px overflow-hidden rounded-xl border border-line bg-line">
          {metrics.map((metric) => (
            <div key={metric.label} className="bg-surface px-3 py-3">
              <dt className="font-mono text-[10px] text-muted">{metric.label}</dt>
              <dd className="mt-1 text-sm font-medium">{metric.value}</dd>
              <dd className={`mt-0.5 text-[10px] ${metric.rating === 'poor' ? 'text-danger' : 'text-muted'}`}>{metric.rating}</dd>
            </div>
          ))}
        </dl>
      ) : (
        <p className="mt-3 text-xs leading-relaxed text-muted">Core Web Vitals were not available yet on this page.</p>
      )}

      <div className="mt-4 flex items-baseline justify-between gap-3">
        <p className="text-sm">Accessibility</p>
        <p className={`font-mono text-xs ${accessibility.total > 0 ? 'text-danger' : 'text-muted'}`}>
          {accessibility.status === 'complete' ? `${accessibility.total} ${accessibility.total === 1 ? 'issue' : 'issues'}` : 'unavailable'}
        </p>
      </div>
      {accessibility.issues.length > 0 && (
        <ul className="mt-3 space-y-2" aria-label="Accessibility issues on this step">
          {accessibility.issues.slice(0, 3).map((issue) => (
            <li key={`${issue.rule}-${issue.target ?? ''}`} className="rounded-xl border border-line bg-surface px-3 py-3">
              <div className="flex items-center justify-between gap-3">
                <span className="font-mono text-[10px] text-muted">{issue.rule}</span>
                <span className={issue.severity === 'high' ? 'text-[10px] text-danger' : 'text-[10px] text-muted'}>{issue.severity}</span>
              </div>
              <p className="mt-1.5 text-xs leading-relaxed">{issue.message}</p>
              {issue.target && <p className="mt-1.5 truncate font-mono text-[10px] text-muted">{issue.target}</p>}
            </li>
          ))}
        </ul>
      )}
      {accessibility.issues.length > 3 && <p className="mt-2 text-xs text-muted">+{accessibility.issues.length - 3} more issues in this step</p>}
    </section>
  )
}

export function BrowserDiagnosticsSummary({ diagnostics }: { diagnostics: BrowserDiagnosticsData }) {
  const parts = [`${diagnostics.accessibility.total} a11y`]
  if (diagnostics.web_vitals.lcp_ms != null) parts.push(`LCP ${formatMs(diagnostics.web_vitals.lcp_ms)}`)
  if (diagnostics.web_vitals.cls != null) parts.push(`CLS ${diagnostics.web_vitals.cls.toFixed(3)}`)
  if (diagnostics.web_vitals.inp_ms != null) parts.push(`INP ${formatMs(diagnostics.web_vitals.inp_ms)}`)
  return <>{parts.join(' · ')}</>
}

function formatMs(value: number): string {
  return value >= 1000 ? `${(value / 1000).toFixed(1)} s` : `${Math.round(value)} ms`
}

function rate(value: number, good: number, poor: number): 'good' | 'needs work' | 'poor' {
  if (value <= good) return 'good'
  if (value <= poor) return 'needs work'
  return 'poor'
}
