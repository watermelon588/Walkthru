import { fieldCoverage, metricValue, type PerformanceMeasurement } from '../lib/performance'

/** The same bounded PSI evidence for private, public, team and printed reports. */
export function PerformanceEvidence({ measurements }: { measurements?: PerformanceMeasurement[] }) {
  if (!measurements?.length) return <p className="mt-5 text-sm text-muted">No PageSpeed measurement details were retained. Browser observations, when available, appear on their recorded journey steps.</p>
  return (
    <div className="mt-6 space-y-6 [overflow-wrap:anywhere]">
      {measurements.slice(0, 5).map((row, i) => (
        <section key={`${row.url}-${i}`} aria-label={`Performance measurements for ${row.url}`} className="min-w-0 rounded-2xl border border-line p-5">
          <h3 className="font-mono text-xs">{row.url}</h3>
          <p className="mt-2 text-xs text-muted">PageSpeed Insights · {row.device ?? 'mobile'} · retrieved {row.retrieved_at ?? 'time not retained'}</p>
          <h4 className="mt-5 text-sm font-medium">Lighthouse lab run</h4>
          <p className="mt-1 text-xs text-muted">One synthetic run. Performance score: {row.lab_score == null ? 'unavailable' : `${row.lab_score}/100`}. Lab LCP: {metricValue(row.lab?.metrics.lcp_ms)}. Lab CLS: {metricValue(row.lab?.metrics.cls, 'score')}.</p>
          {row.lab && (
            <>
              <p className="mt-2 text-xs text-muted">Measured {row.lab.measured_at ?? 'time not reported'} · Lighthouse {row.lab.version ?? 'version not reported'} · emulated device {row.lab.device ?? 'not reported'} · throttling {row.lab.throttling_method ?? 'not reported'}</p>
              <p className="mt-1 text-xs text-muted">Final URL: {row.lab.final_url ?? 'not reported'}. Lab duration: {metricValue(row.lab.duration_ms)}.</p>
              <p className="mt-1 text-xs text-muted">Lab FCP: {metricValue(row.lab.metrics.fcp_ms)} · TBT: {metricValue(row.lab.metrics.tbt_ms)} · Speed Index: {metricValue(row.lab.metrics.speed_index_ms)}</p>
              {Object.keys(row.lab.throttling).length > 0 && <p className="mt-1 font-mono text-[10px] text-muted">{Object.entries(row.lab.throttling).map(([k, v]) => `${k}: ${v}`).join(' · ')}</p>}
              {row.lab.error && <p className="mt-2 text-xs text-danger">Lab unavailable: {row.lab.error}</p>}
              {row.lab.warnings?.slice(0, 5).map((warning, n) => <p key={n} className="mt-2 text-xs text-muted">Lab warning: {warning}</p>)}
            </>
          )}
          <h4 className="mt-5 text-sm font-medium">CrUX field p75</h4>
          <p className="mt-1 text-xs text-muted">Mobile population over a trailing 28-day period, {row.field_scope ?? 'URL'} scope: {row.field_url ?? row.url}. These values are separate from the lab run and this journey's browser observations.</p>
          <p className="mt-2 text-xs">LCP: {metricValue(row.lcp_ms)} · CLS: {metricValue(row.cls, 'score')} · INP: {metricValue(row.inp_ms)}</p>
          <p className="mt-1 text-xs text-muted">{fieldCoverage(row)}</p>
          {(row.lab?.audits.length ?? 0) > 0 && (
            <details className="mt-5 text-xs">
              <summary className="w-fit cursor-pointer py-1">Inspect {row.lab!.audits.length} retained lab audits</summary>
              <p className="mt-3 text-muted">Opportunity savings are Lighthouse estimates. They are not measured speed or conversion gains and should not be added together.</p>
              <ul className="mt-3 space-y-4">
                {row.lab!.audits.slice(0, 12).map((audit) => (
                  <li key={audit.id} className="min-w-0 border-t border-line pt-3">
                    <p className="font-medium">{audit.title}</p>
                    <p className="mt-1 font-mono text-[10px] text-muted">{audit.id} · {audit.mode ?? 'mode not reported'}</p>
                    {audit.description && <p className="mt-1 text-muted">{audit.description}</p>}
                    {audit.display_value && <p className="mt-1">{audit.display_value}</p>}
                    {audit.value != null && <p className="mt-1">Recorded audit value: {audit.value} {audit.unit ?? '(unit not reported)'}</p>}
                    {audit.error && <p className="mt-1 text-danger">Audit unavailable: {audit.error}</p>}
                    {audit.estimated_savings_ms != null && <p className="mt-1">Estimated opportunity savings: {metricValue(audit.estimated_savings_ms)}</p>}
                    {audit.estimated_savings_bytes != null && <p className="mt-1">Estimated transfer savings: {metricValue(audit.estimated_savings_bytes, 'bytes')}</p>}
                    {Object.entries(audit.metric_savings_ms).map(([metric, value]) => <p key={metric} className="mt-1">Estimated {metric} savings: {metricValue(value)}</p>)}
                    {audit.resources.length > 0 ? (
                      <ul aria-label="Measured resources and elements" className="mt-2 space-y-2 font-mono text-[10px]">
                        {audit.resources.slice(0, 5).map((resource, n) => <li key={n}>{resource.url && <p>Resource: {resource.url}</p>}{resource.selector && <p>Element: {resource.selector}</p>}{resource.wastedBytes != null && <p>Estimated wasted transfer: {resource.wastedBytes} bytes</p>}{resource.wastedMs != null && <p>Estimated wasted time: {resource.wastedMs} ms</p>}</li>)}
                      </ul>
                    ) : <p className="mt-2 text-muted">No resource or element locator retained for this audit.</p>}
                    {audit.resources_truncated && <p className="mt-2 text-muted">Resource details were truncated by the capture limit.</p>}
                  </li>
                ))}
              </ul>
              {row.lab!.audits_omitted > 0 && <p className="mt-3 text-muted">{row.lab!.audits_omitted} additional relevant audits omitted by the capture limit.</p>}
            </details>
          )}
        </section>
      ))}
    </div>
  )
}
