import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router'
import { brand } from '../brand'
import { ReportView } from '../components/ReportView'
import { btnPrimary, Logo, SkipLink } from '../components/Shared'
import { getRun, instantScan, type Run, type ScanReuse } from '../lib/runs'
import { SkeletonReport } from '../components/Loading'

type State = { kind: 'loading' } | { kind: 'ready'; run: Run } | { kind: 'missing' } | { kind: 'error'; message: string }

/** Public share page: anyone with the link. Reads through Supabase's "public = true" policy. */
export default function Public() {
  const { id = '' } = useParams()
  const [state, setState] = useState<State>({ kind: 'loading' })

  useEffect(() => {
    let timer: number | undefined
    const load = () =>
      getRun(id)
        .then((run) => {
          setState(run ? { kind: 'ready', run } : { kind: 'missing' })
          if (run && !run.report) timer = window.setTimeout(load, 5000)
        })
        .catch((e: Error) => setState({ kind: 'error', message: e.message }))
    load()
    return () => window.clearTimeout(timer)
  }, [id])

  return (
    <div className="min-h-[100dvh] bg-bg text-ink">
      <title>{state.kind === 'ready' ? `${state.run.site} report${state.run.report?.launch_ready?.score != null ? `, Launch Ready ${state.run.report.launch_ready.score}` : ''} · ${brand.name}` : `Report · ${brand.name}`}</title>      <SkipLink />
      <header className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 md:px-10">
        <Logo />
        <Link to="/" className="text-sm text-muted hover:text-ink">Tested with {brand.name}</Link>
      </header>
      <main id="main" className="mx-auto max-w-7xl px-5 pb-24 pt-8 md:px-10">
        {state.kind === 'loading' && <SkeletonReport label="Loading report" />}
        {state.kind === 'missing' && <p role="status" className="text-muted">This report is private or does not exist.</p>}
        {state.kind === 'error' && <p role="alert" className="text-sm text-danger">Could not load the report: {state.message}</p>}
        {state.kind === 'ready' && <ReuseNote site={state.run.site} />}
        {state.kind === 'ready' && <ReportView run={state.run} />}

        <aside className="mt-16 rounded-2xl bg-surface px-6 py-8 sm:flex sm:items-center sm:justify-between sm:gap-6">
          <div>
            <p className="text-lg font-light">{brand.tagline}</p>
            <p className="mt-1 max-w-[52ch] text-sm leading-relaxed text-muted">Run an Instant Scan of your own homepage, free, no install. Or let AI test users try your signup flow in your own browser.</p>
          </div>
          <Link to="/#scan" className={`${btnPrimary} mt-4 sm:mt-0`}>Scan my site</Link>
        </aside>
      </main>
    </div>
  )
}

/** After an Instant Scan reused a saved result (or waited for another visitor's scan of the same page), say when the
 *  evidence was observed and offer a fresh scan, so a fix made in the last minutes is never checked against old evidence. */
export function ReuseNote({ site }: { site: string }) {
  const reuse = (useLocation().state as { reuse?: ScanReuse } | null)?.reuse
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  if (!reuse || reuse.status === 'fresh') return null
  const minutes = Math.max(1, Math.round(reuse.age_seconds / 60))
  const again = async () => {
    setBusy(true)
    setError('')
    try {
      const { run_id, reuse: next } = await instantScan(site, undefined, true)
      navigate(`/r/${run_id}`, { state: { reuse: next } })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'The scan failed. Try again in a minute.')
    } finally {
      setBusy(false)
    }
  }
  return (
    <section aria-label="Saved scan" className="mb-8 flex flex-col gap-3 rounded-2xl border border-line px-5 py-4 text-sm sm:flex-row sm:items-center sm:justify-between">
      <p className="max-w-[64ch] leading-relaxed text-muted">
        <span className="text-ink">{reuse.status === 'coalesced' ? 'Shared with a scan that was already running.' : 'Saved scan, reused.'}</span>{' '}
        Observed {minutes === 1 ? 'about a minute' : `${minutes} minutes`} ago, at <time dateTime={reuse.observed_at}>{new Date(reuse.observed_at).toLocaleTimeString()}</time>. Scans of the same page are reused for ten minutes. Changed something since? Scan again for fresh results.
      </p>
      <div className="shrink-0">
        <button type="button" onClick={again} disabled={busy} className="rounded-full border border-line px-4 py-2 transition hover:border-ink disabled:opacity-50">{busy ? 'Scanning...' : 'Scan again now'}</button>
        {error && <p role="alert" className="mt-2 text-xs text-danger">{error}</p>}
      </div>
    </section>
  )
}
