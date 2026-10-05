import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router'
import { AppShell } from '../components/AppShell'
import { Locked, PageHeader } from '../components/PageHeader'
import { ComparisonCharts } from '../components/ComparisonCharts'
import { comparable } from '../lib/comparison'
import { getPlan, getRun, listRuns, startCompare, timeAgo, type CompareSite, type Run, type RunSummary } from '../lib/runs'
import { Skeleton, SkeletonPanel, Working } from '../components/Loading'
import { fileStamp, slug, type Cell } from '../lib/export'
import { ExportBar, PrintHeader } from '../components/ExportBar'

const input = 'w-full rounded-xl border border-line bg-bg px-4 py-3 text-sm text-ink placeholder:text-muted focus:border-ink focus:outline-none'
const full = (raw: string) => (/^https?:\/\//i.test(raw) ? raw : `https://${raw}`)

/** Paid plans: your site and up to three competitors through the same passive checks. */
export default function Compare() {
  const navigate = useNavigate()
  const [search] = useSearchParams()
  const [paid, setPaid] = useState<boolean | null>(null)
  const [past, setPast] = useState<RunSummary[]>([])
  const [urls, setUrls] = useState(['', search.get('competitor') ?? '', '', ''])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let active = true
    Promise.all([getPlan(), listRuns()]).then(([p, runs]) => {
      if (active) { setPaid(p.plan !== 'free'); setPast(runs.filter((r) => r.kind === 'compare')) }
    }).catch((e: Error) => { if (active) setLoadError(e.message) })
    return () => { active = false }
  }, [attempt])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const [mine, ...rivals] = urls.map((u) => u.trim())
    const competitors = rivals.filter(Boolean)
    if (!mine || !competitors.length) return setError('Enter your site and at least one competitor.')
    try {
      const parsed = [mine, ...competitors].map((u) => new URL(full(u)))
      if (parsed.some((u) => !['http:', 'https:'].includes(u.protocol) || u.username || u.password)) throw new Error()
      if (new Set(parsed.map((u) => u.host.toLowerCase())).size !== parsed.length) return setError('Use a different website for each competitor.')
    } catch { return setError('Enter valid website addresses, such as example.com.') }
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
        See where your site leads, where competitors are ahead, and what to fix next. Compare up to four sites using the same public checks.
      </PageHeader>
      <div className="mt-8 rounded-2xl border border-line px-5 py-5 text-sm leading-relaxed">
        <p className="text-ink">No ownership verification or extension needed.</p>
        <p className="mt-1 max-w-[75ch] text-muted">Paste the public URLs below. We read public pages without signing in, submitting forms or running owner-only security checks. Sites that block access or opt out cannot be scanned.</p>
      </div>

      {loadError && <div role="alert" className="mt-8 text-sm text-danger">Could not load comparisons: {loadError} <button type="button" onClick={() => { setLoadError(null); setAttempt((n) => n + 1) }} className="ml-2 underline">Try again</button></div>}
      {paid === null && !loadError && <SkeletonPanel label="Loading" className="mt-14" />}
      {paid === false && <Locked>Competitor comparison is part of the paid plans.</Locked>}
      {paid && (
        <section aria-labelledby="compare-heading" className="mt-14">
          <div className="grid gap-10 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
            <div>
              <h2 id="compare-heading" className="text-xl font-light">Start a comparison</h2>
              <p className="mt-2 max-w-[48ch] text-sm leading-relaxed text-muted">
                The sites are scanned together. Results update automatically when ready; busy providers can take longer. Each site counts toward your daily scan limit.
              </p>
              <Link to="/docs#compare" className="mt-4 inline-block text-sm text-ink underline decoration-line underline-offset-4 transition hover:decoration-ink">What is compared</Link>
            </div>
            <div className="grid min-w-0 content-start gap-5">
              <form onSubmit={submit} className="grid gap-4">
                {['Your site', 'Competitor 1', 'Competitor 2 (optional)', 'Competitor 3 (optional)'].map((label, i) => (
                  <label key={label} htmlFor={`compare-${i}`} className="grid gap-2 text-sm text-muted">
                    {label}
                    <input id={`compare-${i}`} inputMode="url" autoCapitalize="none" spellCheck={false} required={i < 2} value={urls[i]} onChange={(e) => setUrls((u) => u.map((v, j) => (j === i ? e.target.value : v)))} placeholder={i === 0 ? 'yoursite.com' : 'competitor.com'} disabled={busy} className={input} />
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

function compareCsv(sites: CompareSite[]): Cell[][] {
  const cells = (f: (s: CompareSite) => Cell) => sites.map((s) => (s.error ? 'Not scanned' : f(s) ?? 'Not measured'))
  return [
    ['Check', ...sites.map((s) => `${s.site}${s.yours ? ' (your site)' : ''}`)],
    ...ROWS.map((row) => [row.label, ...cells(row.value)]),
    ['Pages checked', ...cells((s) => s.pages)],
    ['First impression', ...cells((s) => s.impression)],
    ['Scan error', ...sites.map((s) => s.error ?? '')],
  ]
}

const ROWS: { label: string; value: (s: CompareSite) => number | null | undefined; better: 'high' | 'low'; format?: (v: number) => string }[] = [
  { label: 'Launch Ready score', value: (s) => s.score, better: 'high' },
  { label: 'AI search readiness', value: (s) => s.geo, better: 'high' },
  { label: 'SEO', value: (s) => s.areas?.seo, better: 'high' },
  { label: 'Security hygiene', value: (s) => s.areas?.security, better: 'high' },
  { label: 'Speed and accessibility', value: (s) => s.areas?.speed, better: 'high' },
  { label: 'High-priority findings', value: (s) => s.findings?.high, better: 'low' },
  { label: 'All findings', value: (s) => (s.findings ? s.findings.high + s.findings.medium + s.findings.low : null), better: 'low' },
]

/** One comparison: waits for the scans, then shows every site side by side, yours first. */
export function CompareResult() {
  const { id = '' } = useParams()
  return <Result key={id} id={id} />
}

function Result({ id }: { id: string }) {
  const [run, setRun] = useState<Run | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let timer = 0
    let active = true
    const poll = () =>
      getRun(id)
        .then((r) => {
          if (!active) return
          if (!r) { setError('Comparison not found or no longer available.'); return }
          if (r.kind !== 'compare') { setError('This report is not a competitor comparison.'); return }
          setRun(r)
          if (r?.status === 'running') timer = window.setTimeout(poll, 4000)
        })
        .catch((e: Error) => { if (active) setError(e.message) })
    poll()
    return () => { active = false; window.clearTimeout(timer) }
  }, [id, attempt])

  const sites = run?.report?.compare ?? []
  return (
    <AppShell title="Comparison">
      <PageHeader kicker="Competitor side by side" title={run ? run.site : 'Comparison'}>
        {run ? `${run.goal}. Results from ${new Date(run.created_at).toLocaleString()}. These are scan scores, not search rankings or conversion predictions.` : 'Loading the comparison.'}
      </PageHeader>
      {run && <PrintHeader title={`Competitor comparison: ${run.site}`} detail={`Scanned ${new Date(run.created_at).toLocaleString()}`} />}
      <div className="no-print mt-6 flex flex-wrap items-center justify-between gap-4">
        <Link to="/app/compare" className="text-sm underline decoration-line underline-offset-4">New comparison</Link>
        {sites.length > 0 && run && <ExportBar filename={`walkthru-compare-${slug(run.site)}-${fileStamp()}`} csv={() => compareCsv(sites)} />}
      </div>
      {error && <p role="alert" className="mt-10 text-sm text-danger">Could not load this comparison: {error} <button type="button" onClick={() => { setError(null); setRun(null); setAttempt((n) => n + 1) }} className="ml-2 underline">Try again</button></p>}
      {run === null && !error && <SkeletonPanel label="Loading the comparison" className="mt-14" />}
      {run?.status === 'running' && (
        <>
          <Working className="mt-10" state="connecting" every={5000} title="Scanning every site side by side"
            steps={["Reading each site's public pages", 'Checking SEO on every site', 'Checking what AI crawlers can read', 'Checking public security signals', 'Scoring each site on the same scale', 'Lining up the gaps']} />
          <p className="mt-3 text-xs text-muted">This page updates by itself when the comparison is ready. You can leave and come back from Compare.</p>
          <div aria-hidden className="mt-10 grid gap-7 rounded-2xl border border-line px-5 py-6 opacity-70 sm:px-8">
            {[80, 62, 71, 48].map((w, i) => <div key={i} className="grid gap-2"><Skeleton className="h-3 w-32" /><Skeleton className="h-8 rounded-md" style={{ width: `${w}%` }} /></div>)}
          </div>
        </>
      )}
      {run && run.status !== 'running' && !sites.length && <p role="status" className="mt-10 text-muted">No comparison results were saved. Start a new comparison to try again.</p>}
      {!!sites.length && <ComparisonCharts sites={sites} />}
      {sites.length > 0 && (
        <section className="mt-12" aria-labelledby="evidence-heading">
          <h2 id="evidence-heading" className="text-2xl font-light">The numbers behind the charts</h2>
          <p className="mt-3 text-sm leading-relaxed text-muted">Missing checks stay unmeasured. Page counts describe coverage, not performance. Open a site to inspect its evidence.</p>
          {sites.some((s) => !s.error && s.scope !== 'public') && <p className="mt-3 text-sm text-muted">This older comparison may include different security scopes. Run a new comparison for matching public checks.</p>}
        <div className="mt-6 overflow-x-auto" tabIndex={0} role="region" aria-label="Detailed comparison table">
          <table className="w-full min-w-[40rem] border-collapse text-sm">
            <thead>
              <tr className="border-b border-line text-left">
                <th scope="col" className="py-3 pr-4 font-normal text-muted">Check</th>
                {sites.map((s, i) => (
                  <th key={`${s.site}-${i}`} scope="col" className="py-3 pr-4 align-bottom font-normal">
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
                const checked = sites.filter((s) => !s.error)
                const matching = row.label === 'Launch Ready score' ? checked.every((s) => comparable(checked[0], s, 'score')) : row.label === 'Speed and accessibility' ? checked.every((s) => comparable(checked[0], s, 'speed')) : row.label === 'Security hygiene' ? checked.every((s) => comparable(checked[0], s, 'security')) : true
                const best = known.length > 1 && matching && !row.label.includes('findings') ? Math.max(...known) : null
                return (
                  <tr key={row.label} className="border-b border-line">
                    <th scope="row" className="py-3 pr-4 text-left font-normal">{row.label}</th>
                    {values.map((v, i) => (
                      <td key={i} className={`py-3 pr-4 tabular-nums ${v != null && v === best ? 'font-medium text-accent' : v == null ? 'text-muted' : 'text-ink'}`}>
                        {sites[i].error ? 'Not scanned' : v ?? 'Not measured'}
                      </td>
                    ))}
                  </tr>
                )
              })}
              <tr className="border-b border-line"><th scope="row" className="py-3 pr-4 text-left font-normal">Pages checked</th>{sites.map((s, i) => <td key={i} className="py-3 pr-4 tabular-nums">{s.error ? 'Not scanned' : s.pages ?? 'Unknown'}{s.truncated && <span className="block text-xs text-muted">Scan limit reached</span>}</td>)}</tr>
              <tr className="border-b border-line align-top">
                <th scope="row" className="py-3 pr-4 text-left font-normal">First impression</th>
                {sites.map((s, i) => <td key={i} className="max-w-[16rem] py-3 pr-4 text-muted">{s.error ?? s.impression ?? 'Not judged'}</td>)}
              </tr>
            </tbody>
          </table>
          <p className="mt-4 text-xs text-muted">Higher comparable scores are highlighted. Finding counts are not ranked because scan coverage can differ.</p>
        </div>
        </section>
      )}
    </AppShell>
  )
}
