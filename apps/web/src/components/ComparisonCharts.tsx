import { useState } from 'react'
import { Link } from 'react-router'
import type { CompareSite } from '../lib/runs'
import { host, leaderGap, METRICS, value, type Metric } from '../lib/comparison'

export function ComparisonCharts({ sites }: { sites: CompareSite[] }) {
  const [metric, setMetric] = useState<Metric>('score')
  const [view, setView] = useState<'scores' | 'findings'>('scores')
  const selected = METRICS.find((m) => m.id === metric)!
  const own = sites.find((s) => s.yours)
  const gap = leaderGap(sites, metric)
  const measured = sites.filter((s) => value(s, metric) !== null).length
  const maxFindings = Math.max(1, ...sites.map((s) => s.error ? 0 : total(s)))
  const opportunities = METRICS.filter((m) => m.id !== 'score').map((m) => ({ ...m, comparison: leaderGap(sites, m.id) }))
    .filter((m) => m.comparison && m.comparison.gap < 0).sort((a, b) => a.comparison!.gap - b.comparison!.gap)

  return (
    <div className="mt-12 grid gap-12">
      <section aria-label="Comparison overview" className="grid gap-6 border-y border-line py-6 sm:grid-cols-3 sm:gap-10">
        <div><p className="text-xs text-muted">Your Launch Ready score</p><p className="mt-2 text-5xl font-extralight tracking-tight tabular-nums">{own ? value(own, 'score') ?? 'N/A' : 'N/A'}<span className="ml-2 text-sm text-muted">/ 100</span></p><p className="mt-2 text-xs text-muted">Across the checks that completed</p></div>
        <div><p className="text-xs text-muted">Where to focus</p><p className="mt-2 text-2xl font-light tracking-tight">{opportunities[0]?.label ?? 'Review the evidence'}</p><p className="mt-2 text-xs leading-relaxed text-muted">{opportunities[0] ? `${Math.abs(opportunities[0].comparison!.gap)} points behind ${host(opportunities[0].comparison!.rival.site)}` : 'No measured category gap, or not enough matching data.'}</p></div>
        <div><p className="text-xs text-muted">Scan coverage</p><p className="mt-2 text-2xl font-light tabular-nums">{sites.filter((s) => !s.error).length} of {sites.length} sites</p><p className="mt-2 text-xs leading-relaxed text-muted">A snapshot of public pages. Different page counts can affect the results.</p></div>
      </section>

      <section aria-labelledby="visual-heading">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div><p className="text-xs text-muted">Explore the difference</p><h2 id="visual-heading" className="mt-2 text-3xl font-light tracking-tight">Your market, side by side</h2></div>
          <div role="group" aria-label="Chart view" className="no-print flex rounded-full border border-line p-1">
            {(['scores', 'findings'] as const).map((v) => <button key={v} type="button" aria-pressed={view === v} onClick={() => setView(v)} className={`rounded-full px-4 py-2 text-sm transition-colors ${view === v ? 'bg-ink text-bg' : 'text-muted hover:text-ink'}`}>{v === 'scores' ? 'Scores' : 'Findings'}</button>)}
          </div>
        </div>
        {view === 'scores' && <div role="group" aria-label="Metric" className="no-print mt-6 flex flex-wrap gap-2">
          {METRICS.map((m) => <button key={m.id} type="button" aria-pressed={metric === m.id} onClick={() => setMetric(m.id)} className={`rounded-full border px-4 py-2 text-xs transition-colors ${metric === m.id ? 'border-ink bg-surface text-ink' : 'border-line text-muted hover:border-muted hover:text-ink'}`}>{m.label}</button>)}
        </div>}
        <p className="mt-5 max-w-[70ch] text-sm leading-relaxed text-muted">{view === 'scores' ? selected.note : 'Findings by severity on a shared count scale. Fewer findings can reflect fewer pages checked, not a better site.'}</p>
        <div className="mt-8 rounded-2xl border border-line px-5 py-6 sm:px-8 sm:py-8">
          <div className="mb-6 flex flex-wrap items-center justify-between gap-3 text-xs text-muted">
            <span>{view === 'scores' ? `${selected.label} / 100` : 'Number of findings'}</span>
            {view === 'findings' ? <span className="flex gap-4"><span>■ High</span><span>▧ Medium</span><span>□ Low</span></span> : <span>Solid: your site · striped: competitors</span>}
          </div>
          <ul className="grid gap-7" aria-label={view === 'scores' ? `${selected.label} comparison` : 'Finding severity comparison'}>
            {sites.map((s, i) => {
              const n = value(s, metric)
              const available = !s.error && (view === 'scores' ? n !== null : !!s.findings)
              return <li key={`${s.site}-${i}`} className="grid gap-2">
                <div className="flex items-baseline justify-between gap-4 text-sm">
                  <span className="min-w-0 break-all text-ink">{host(s.site)}{s.yours && <span className="ml-2 text-xs text-muted">Your site</span>}</span>
                  <span className="shrink-0 font-mono text-xs tabular-nums">{s.error ? 'Not scanned' : !available ? 'Not measured' : view === 'scores' ? `${n} / 100` : `${total(s)} total`}</span>
                </div>
                <div aria-hidden="true" className="relative h-8 overflow-hidden rounded-md bg-surface">
                  {available && view === 'scores' && <div className={`h-full border-r-2 border-ink ${s.yours ? 'bg-ink' : 'bg-muted/30'}`} style={{ width: `${n}%`, ...(!s.yours ? { backgroundImage: 'repeating-linear-gradient(135deg, transparent, transparent 4px, var(--muted) 4px, var(--muted) 5px)' } : {}) }} />}
                  {available && view === 'findings' && <div className="flex h-full">
                    <div className="h-full bg-ink" style={{ width: `${100 * s.findings!.high / maxFindings}%` }} />
                    <div className="h-full bg-muted/30" style={{ width: `${100 * s.findings!.medium / maxFindings}%`, backgroundImage: 'repeating-linear-gradient(135deg, transparent, transparent 4px, var(--muted) 4px, var(--muted) 5px)' }} />
                    <div className="h-full border border-muted bg-bg" style={{ width: `${100 * s.findings!.low / maxFindings}%`, borderWidth: s.findings!.low ? 1 : 0 }} />
                  </div>}
                  {!available && <span className="absolute inset-0 flex items-center px-3 text-xs text-muted">{s.error ? 'Open scan details below' : 'No measurement available'}</span>}
                </div>
                {view === 'findings' && available && <p className="text-xs text-muted">{s.findings!.high} high · {s.findings!.medium} medium · {s.findings!.low} low · {s.pages ?? 'Unknown'} pages checked</p>}
              </li>
            })}
          </ul>
          <div aria-hidden="true" className="mt-4 flex justify-between border-t border-line pt-2 font-mono text-[10px] text-muted">{(view === 'scores' ? [0, 25, 50, 75, 100] : [0, maxFindings]).map((v) => <span key={v}>{v}</span>)}</div>
          {view === 'scores' && <p role="status" className="mt-6 border-t border-line pt-4 text-sm leading-relaxed text-ink">
            {gap ? gap.gap < 0 ? `${host(gap.rival.site)} leads your site by ${-gap.gap} points on ${selected.label.toLowerCase()}.` : gap.gap > 0 ? `Your site leads the strongest comparable competitor by ${gap.gap} points on ${selected.label.toLowerCase()}.` : `Your site matches the strongest comparable competitor on ${selected.label.toLowerCase()}.` : `Measured for ${measured} of ${sites.length} sites. A score gap needs your result and a competitor with matching check coverage.`}
          </p>}
        </div>
      </section>

      <section aria-labelledby="next-heading" className="grid gap-8 lg:grid-cols-[0.7fr_1.3fr]">
        <div><h2 id="next-heading" className="text-2xl font-light">Turn a gap into a fix</h2><p className="mt-3 max-w-[45ch] text-sm leading-relaxed text-muted">Start with the largest measured gap. Open your report for the findings and fix instructions, then run another comparison.</p>{own?.run_id && <Link className="mt-5 inline-block rounded-full bg-ink px-5 py-3 text-sm text-bg hover:opacity-85" to={`/app/runs/${own.run_id}`}>Open your fix list</Link>}</div>
        <div className="border-t border-line">{opportunities.length ? opportunities.map((m) => <button key={m.id} type="button" onClick={() => { setMetric(m.id); setView('scores'); document.getElementById('visual-heading')?.scrollIntoView({ block: 'start' }) }} className="flex w-full items-center justify-between gap-4 border-b border-line py-5 text-left hover:bg-surface focus-visible:outline-2 focus-visible:outline-ink"><span><span className="block text-sm text-ink">{m.label}</span><span className="mt-1 block text-xs text-muted">Compared with {host(m.comparison!.rival.site)}</span></span><span className="shrink-0 font-mono text-sm">{Math.abs(m.comparison!.gap)} pt gap ↗</span></button>) : <p className="py-5 text-sm leading-relaxed text-muted">No measured category deficit to prioritize. Review missing checks and individual findings before drawing a conclusion.</p>}</div>
      </section>
    </div>
  )
}

function total(s: CompareSite) { return s.findings ? s.findings.high + s.findings.medium + s.findings.low : 0 }
