import { Link } from 'react-router'
import type { Compared, Report } from '../lib/runs'

type Comparison = NonNullable<Report['comparison']>

const SHOWN = 8 // per column; the full list is in All findings

function path(url: string): string {
  try {
    return new URL(url).pathname
  } catch {
    return url
  }
}

/** Page-level detail for a finding that is still reported: where it went away and where it showed up. */
function PageChange({ item }: { item: Compared }) {
  const parts = [
    item.pages_fixed?.length ? `fixed on ${item.pages_fixed.length} page${item.pages_fixed.length === 1 ? '' : 's'}` : null,
    item.pages_new?.length ? `now on ${item.pages_new.map(path).join(', ')}` : null,
    item.pages_unchecked?.length ? `${item.pages_unchecked.length} not re-checked` : null,
  ].filter(Boolean)
  return parts.length ? <span className="block text-xs text-muted">{parts.join(' · ')}</span> : null
}

/** Fixed, new and still broken against the previous run of the same goal (paid plans, apps/api/app/agent/compare.py). */
export function RerunComparison({ comparison, linkPrevious }: { comparison: Comparison; linkPrevious: boolean }) {
  const when = new Date(comparison.previous_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  const groups = [
    { label: 'Fixed', tone: 'text-accent', items: comparison.fixed },
    { label: 'New', tone: 'text-danger', items: comparison.new },
    { label: 'Still broken', tone: 'text-ink', items: comparison.still_broken },
  ]
  const unchecked = comparison.not_rechecked ?? []
  return (
    <section aria-labelledby="compare-title" className="report-print-section mt-12">
      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Since your last run</p>
      <h2 id="compare-title" className="mt-2 text-xl font-light tracking-tight">
        {comparison.fixed.length} fixed, {comparison.new.length} new, {comparison.still_broken.length} still broken
      </h2>
      <p className="mt-2 max-w-[64ch] text-sm leading-relaxed text-muted">
        Compared with the same goal on {linkPrevious ? <Link to={`/app/runs/${comparison.previous_run_id}`} className="text-ink underline decoration-line underline-offset-4 hover:decoration-ink">{when}</Link> : when}.
        {' '}UX findings come from the journey, so a different path can change them. Ignored findings are left out.
      </p>
      <div className="mt-5 grid gap-px overflow-hidden rounded-2xl bg-line sm:grid-cols-3">
        {groups.map(({ label, tone, items }) => (
          <div key={label} className="bg-bg px-5 py-4">
            <h3 className={`text-sm font-medium ${tone}`}>
              {label} <span className="font-mono text-xs text-muted">{items.length}</span>
            </h3>
            <ul className="mt-2 grid gap-1.5 text-sm">
              {items.length === 0
                ? <li className="text-muted">None</li>
                : items.slice(0, SHOWN).map((item) => <li key={item.fingerprint}>{item.title}<PageChange item={item} /></li>)}
              {items.length > SHOWN && <li className="text-muted">+{items.length - SHOWN} more in All findings below</li>}
            </ul>
          </div>
        ))}
      </div>
      {unchecked.length > 0 && (
        <p className="mt-3 text-xs leading-relaxed text-muted">
          Not re-checked: {unchecked.map((item) => item.title).join(', ')}. Its pages were outside this run's crawl, so it is not marked fixed.
        </p>
      )}
    </section>
  )
}
