import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { AppShell } from '../components/AppShell'
import { Locked, PageHeader } from '../components/PageHeader'
import { getPlan, getRun, listRuns, startCompare, timeAgo, type CompareSite, type Run } from '../lib/runs'

const input = 'w-full rounded-xl border border-line bg-bg px-4 py-3 text-sm text-ink placeholder:text-muted focus:border-ink focus:outline-none'
const full = (raw: string) => (raw.startsWith('http') ? raw : `https://${raw}`)

/** Paid plans: your site and up to three competitors through the same passive checks. */
export default function Compare() {
  const navigate = useNavigate()
  const [paid, setPaid] = useState<boolean | null>(null)
  const [past, setPast] = useState<Run[]>([])
  const [urls, setUrls] = useState(['', '', '', ''])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getPlan().then((p) => setPaid(p.plan !== 'free')).catch(() => setPaid(false))
    listRuns().then((runs) => setPast(runs.filter((r) => r.kind === 'compare'))).catch(() => setPast([]))
  }, [])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const [mine, ...rivals] = urls.map((u) => u.trim())
    const competitors = rivals.filter(Boolean)
    if (!mine || !competitors.length) return setError('Enter your site and at least one competitor.')
    setBusy(true)
    setError(null)
    try {
      const { run_id } = await startCompare(full(mine), competitors.map(full))
      navigate(`/app/compare/${run_id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not start the comparison.')
      setBusy(false)
    }
  }

  return (
    <AppShell title="Compare">
      <PageHeader kicker="Paid plans" title="Competitor side by side">
        Your site and up to three competitors through the same checks: Launch Ready score, AI search readiness, SEO, passive security and a first impression. Public pages only, and never the deep security checks on sites you do not own.
      </PageHeader>

      {paid === null && <div aria-busy="true" aria-label="Loading" className="mt-14 h-40 animate-pulse rounded-2xl bg-surface motion-reduce:animate-none" />}
      {paid === false && <Locked>Competitor comparison is part of the paid plans.</Locked>}
      {paid && (
        <section aria-labelledby="compare-heading" className="mt-14">
          <div className="grid gap-10 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
            <div>
              <h2 id="compare-heading" className="text-xl font-light">Start a comparison</h2>
              <p className="mt-2 max-w-[48ch] text-sm leading-relaxed text-muted">
                The sites are scanned together and take about a minute. Each scan counts toward your daily scan limit.
              </p>
              <Link to="/docs#compare" className="mt-4 inline-block text-sm text-ink underline decoration-line underline-offset-4 transition hover:decoration-ink">What is compared</Link>
            </div>
            <div className="grid min-w-0 content-start gap-5">
              <form onSubmit={submit} className="grid gap-4">
                {['Your site', 'Competitor 1', 'Competitor 2 (optional)', 'Competitor 3 (optional)'].map((label, i) => (
                  <label key={label} htmlFor={`compare-${i}`} className="grid gap-2 text-sm text-muted">
                    {label}
                    <input id={`compare-${i}`} value={urls[i]} onChange={(e) => setUrls((u) => u.map((v, j) => (j === i ? e.target.value : v)))} placeholder={i === 0 ? 'yoursite.com' : 'competitor.com'} disabled={busy} className={input} />
                  </label>
                ))}
                <div className="flex flex-wrap items-center gap-4">
                  <button type="submit" disabled={busy} className="rounded-full bg-ink px-6 py-3 text-sm text-bg transition hover:opacity-85 disabled:opacity-60">{busy ? 'Starting...' : 'Compare'}</button>
                  {error && <p role="alert" className="text-sm text-danger">{error}</p>}
                </div>
              </form>
              {past.length > 0 && (
                <div>
                  <h3 className="text-sm text-muted">Earlier comparisons</h3>
                  <ul className="mt-2 border-t border-line">
                    {past.map((r) => (
                      <li key={r.id} className="border-b border-line">
                        <Link to={`/app/compare/${r.id}`} className="flex flex-wrap items-baseline justify-between gap-3 py-3 text-sm transition hover:text-ink">
                          <span className="min-w-0 truncate font-mono text-xs text-ink">{r.site}</span>
                          <span className="text-xs text-muted">{r.goal}, {timeAgo(r.created_at)}</span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </section>
      )}
    </AppShell>
  )
}

const ROWS: { label: string; value: (s: CompareSite) => number | null | undefined; better: 'high' | 'low'; format?: (v: number) => string }[] = [
  { label: 'Launch Ready score', value: (s) => s.score, better: 'high' },
  { label: 'AI search readiness', value: (s) => s.geo, better: 'high' },
  { label: 'SEO', value: (s) => s.areas?.seo, better: 'high' },
  { label: 'Security hygiene', value: (s) => s.areas?.security, better: 'high' },
  { label: 'Speed and accessibility', value: (s) => s.areas?.speed, better: 'high' },
  { label: 'High-priority findings', value: (s) => s.findings?.high, better: 'low' },
  { label: 'All findings', value: (s) => (s.findings ? s.findings.high + s.findings.medium + s.findings.low : null), better: 'low' },
  { label: 'Pages checked', value: (s) => s.pages, better: 'high' },
]

/** One comparison: waits for the scans, then shows every site side by side, yours first. */
export function CompareResult() {
  const { id = '' } = useParams()
  const [run, setRun] = useState<Run | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let timer = 0
    const poll = () =>
      getRun(id)
        .then((r) => {
          setRun(r)
          if (r?.status === 'running') timer = window.setTimeout(poll, 4000)
        })
        .catch((e: Error) => setError(e.message))
    poll()
    return () => window.clearTimeout(timer)
  }, [id])

  const sites = run?.report?.compare ?? []
  return (
    <AppShell title="Comparison">
      <PageHeader kicker="Competitor side by side" title={run ? run.site : 'Comparison'}>
        {run ? `${run.goal}. Passive public checks only, so every site is measured the same way.` : 'Loading the comparison.'}
      </PageHeader>
      {error && <p role="alert" className="mt-10 text-sm text-danger">Could not load this comparison: {error}</p>}
      {run === null && !error && <div aria-busy="true" aria-label="Loading the comparison" className="mt-14 h-60 animate-pulse rounded-2xl bg-surface motion-reduce:animate-none" />}
      {run?.status === 'running' && (
        <p role="status" className="mt-10 text-muted">Scanning every site. This takes about a minute and updates by itself.</p>
      )}
      {sites.length > 0 && (
        <div className="mt-12 overflow-x-auto">
          <table className="w-full min-w-[40rem] border-collapse text-sm">
            <thead>
              <tr className="border-b border-line text-left">
                <th scope="col" className="py-3 pr-4 font-normal text-muted">Check</th>
                {sites.map((s) => (
                  <th key={s.site} scope="col" className="py-3 pr-4 align-bottom font-normal">
                    <span className="block text-xs text-muted">{s.yours ? 'Your site' : 'Competitor'}</span>
                    {s.run_id ? <Link to={`/app/runs/${s.run_id}`} className="block max-w-[14rem] truncate font-mono text-xs text-ink underline decoration-line underline-offset-4 hover:decoration-ink">{s.site}</Link> : <span className="block max-w-[14rem] truncate font-mono text-xs text-ink">{s.site}</span>}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ROWS.map((row) => {
                const values = sites.map((s) => (s.error ? null : row.value(s) ?? null))
                const known = values.filter((v): v is number => v != null)
                const best = known.length > 1 ? (row.better === 'high' ? Math.max(...known) : Math.min(...known)) : null
                return (
                  <tr key={row.label} className="border-b border-line">
                    <th scope="row" className="py-3 pr-4 text-left font-normal">{row.label}</th>
                    {values.map((v, i) => (
                      <td key={sites[i].site} className={`py-3 pr-4 tabular-nums ${v != null && v === best ? 'font-medium text-accent' : v == null ? 'text-muted' : 'text-ink'}`}>
                        {sites[i].error ? 'Not scanned' : v ?? 'Not measured'}
                      </td>
                    ))}
                  </tr>
                )
              })}
              <tr className="border-b border-line align-top">
                <th scope="row" className="py-3 pr-4 text-left font-normal">First impression</th>
                {sites.map((s) => <td key={s.site} className="max-w-[16rem] py-3 pr-4 text-muted">{s.error ?? s.impression ?? 'Not judged'}</td>)}
              </tr>
            </tbody>
          </table>
          <p className="mt-4 text-xs text-muted">The best value in each row is highlighted. Open any site for its full report.</p>
        </div>
      )}
    </AppShell>
  )
}
