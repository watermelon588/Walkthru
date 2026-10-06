export type PerformanceAudit = {
  id: string; title: string; description: string | null; display_value: string | null
  score: number | null; mode: string | null; error: string | null; value: number | null; unit: string | null
  estimated_savings_ms: number | null; estimated_savings_bytes: number | null
  metric_savings_ms: Partial<Record<'LCP' | 'FCP' | 'TBT', number>>
  resources: { url?: string; selector?: string; totalBytes?: number; wastedBytes?: number; wastedMs?: number; duration?: number; startTime?: number }[]
  resources_truncated: boolean
}

export type PerformanceMeasurement = {
  url: string; status: 'field_data' | 'lab_only' | 'unavailable'; lab_score: number | null
  /** These legacy top-level values are CrUX field p75, never Lighthouse lab metrics. */
  lcp_ms: number | null; cls: number | null; inp_ms: number | null
  source?: 'pagespeed_insights'; device?: string; retrieved_at?: string; request_duration_ms?: number
  analysis_at?: string | null; field_status?: 'complete' | 'partial' | 'unavailable'
  field_scope?: 'url' | 'origin'; field_source?: 'crux_p75'; field_url?: string | null
  lab?: {
    source: 'lighthouse_lab'; status: 'measured' | 'unavailable'; score: number | null
    metrics: { lcp_ms: number | null; cls: number | null; fcp_ms: number | null; tbt_ms: number | null; speed_index_ms: number | null }
    requested_url: string | null; final_url: string | null; measured_at: string | null; version: string | null
    device: string | null; throttling_method: string | null; throttling: Record<string, number>
    duration_ms: number | null; error: string | null; warnings?: string[]; audits: PerformanceAudit[]; audits_omitted: number
  } | null
}

export function fieldCoverage(row: PerformanceMeasurement): string {
  const count = [row.lcp_ms, row.cls, row.inp_ms].filter((v) => v != null).length
  return count === 0 ? 'Field data unavailable. This does not establish healthy Core Web Vitals.'
    : count === 3 ? 'Three field metrics available.' : `${count} of 3 field metrics available. Missing metrics remain unknown.`
}

export function metricValue(value: number | null | undefined, unit: 'ms' | 'score' | 'bytes' = 'ms'): string {
  return value == null ? 'unavailable' : `${value}${unit === 'score' ? '' : ` ${unit}`}`
}
