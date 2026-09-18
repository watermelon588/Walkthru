import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'
import { brand } from '../brand'
import { ReportView } from '../components/ReportView'
import { btnPrimary, Logo } from '../components/Shared'
import { getRun, type Run } from '../lib/runs'

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
      <header className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 md:px-10">
        <Logo />
        <Link to="/" className="text-sm text-muted hover:text-ink">Tested with {brand.name}</Link>
      </header>
      <main className="mx-auto max-w-7xl px-5 pb-24 pt-8 md:px-10">
        {state.kind === 'loading' && <div aria-busy="true" aria-label="Loading report" className="h-24 animate-pulse rounded-2xl bg-surface motion-reduce:animate-none" />}
        {state.kind === 'missing' && <p role="status" className="text-muted">This report is private or does not exist.</p>}
        {state.kind === 'error' && <p role="alert" className="text-sm text-danger">Could not load the report: {state.message}</p>}
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
