import type { AssertionRecheck, CompareSite } from './runs'

/** R-S13: the recheck verdict in plain words. Only a like-for-like failed-then-passed pair says Fixed. */
export const RECHECK_LABEL: Record<AssertionRecheck['verdict'], string> = {
  fixed: 'Fixed', still_failing: 'Still failing', regressed: 'Regressed', still_passing: 'Still passing',
  first_result: 'First result', not_rechecked: 'Not re-checked', not_comparable: 'Not comparable',
}

export function recheckCounts(a: AssertionRecheck): string {
  const count = (n?: number | null) => (n === null || n === undefined ? 'no count' : String(n))
  const expected = a.expected_count === null || a.expected_count === undefined ? '' : `, expected ${a.expected_count}`
  return `Before: ${a.before} (${count(a.before_count)}). Now: ${a.after ?? 'not checked'}${a.after ? ` (${count(a.after_count)})` : ''}${expected}.`
}

export const METRICS = [
  { id: 'score', label: 'Launch Ready', note: 'Weighted score across measured checks. Higher is better.' },
  { id: 'geo', label: 'AI readiness', note: 'How readable the site is for AI search. This does not measure citations.' },
  { id: 'seo', label: 'SEO', note: 'Technical SEO checks on the pages scanned. Higher is better.' },
  { id: 'security', label: 'Security hygiene', note: 'Public security signals only. This is not a security certification.' },
  { id: 'speed', label: 'Speed & accessibility', note: 'Combined score for the checks that completed. Open the report for individual measurements.' },
] as const
export type Metric = typeof METRICS[number]['id']

export function value(site: CompareSite, metric: Metric): number | null {
  if (site.error) return null
  const raw = metric === 'score' ? site.score : metric === 'geo' ? site.geo : site.areas?.[metric]
  return typeof raw === 'number' && Number.isFinite(raw) && raw >= 0 && raw <= 100 ? raw : null
}

export function host(site: string): string {
  try { return new URL(site).host } catch { return site }
}

// A weighted total is comparable only when the same areas contributed to it.
// Legacy reports with no area breakdown cannot support a trustworthy total-score gap.
export function comparable(a: CompareSite, b: CompareSite, metric: Metric): boolean {
  if (value(a, metric) === null || value(b, metric) === null) return false
  if ((metric === 'score' || metric === 'security') && (a.scope !== 'public' || b.scope !== 'public')) return false
  if (metric !== 'score' && metric !== 'speed') return true
  if (metric === 'speed') {
    const coverage = (s: CompareSite) => ['performance', 'accessibility'].filter((k) => s.checks?.[k] === 'complete').join(',')
    return !!coverage(a) && coverage(a) === coverage(b)
  }
  const areas = (s: CompareSite) => Object.entries(s.areas ?? {}).filter(([, v]) => typeof v === 'number' && Number.isFinite(v)).map(([k]) => k).sort().join(',')
  return !!areas(a) && areas(a) === areas(b) && (a.areas?.speed == null || comparable(a, b, 'speed'))
}

export function leaderGap(sites: CompareSite[], metric: Metric) {
  const own = sites.find((s) => s.yours)
  if (!own) return null
  const rivals = sites.filter((s) => !s.yours && comparable(own, s, metric)).sort((a, b) => value(b, metric)! - value(a, metric)!)
  if (!rivals.length) return null
  return { rival: rivals[0], gap: value(own, metric)! - value(rivals[0], metric)! }
}
