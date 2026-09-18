import { ArrowLeftIcon } from '@phosphor-icons/react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'
import { AppShell } from '../components/AppShell'
import { getRun, PERSONA_LABEL, STATUS_LABEL, type Run } from '../lib/runs'
import { StatusPill } from './Dashboard'

type State = { kind: 'loading' } | { kind: 'ready'; run: Run } | { kind: 'missing' } | { kind: 'error'; message: string }

export default function Report() {
  const { id = '' } = useParams()
  const [state, setState] = useState<State>({ kind: 'loading' })

  useEffect(() => {
    getRun(id)
      .then((run) => setState(run ? { kind: 'ready', run } : { kind: 'missing' }))
      .catch((e: Error) => setState({ kind: 'error', message: e.message }))
  }, [id])

  return (
    <AppShell>
      <Link to="/app" className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-ink">
        <ArrowLeftIcon className="size-4" /> All runs
      </Link>

      {state.kind === 'loading' && <div aria-busy="true" aria-label="Loading run" className="mt-8 h-24 animate-pulse rounded-2xl bg-surface motion-reduce:animate-none" />}
      {state.kind === 'missing' && <p role="status" className="mt-8 text-muted">This run does not exist or belongs to another account.</p>}
      {state.kind === 'error' && <p role="alert" className="mt-8 text-sm text-danger">Could not load the run: {state.message}</p>}

      {state.kind === 'ready' && <RunView run={state.run} />}
    </AppShell>
  )
}

function RunView({ run }: { run: Run }) {
  const peak = Math.max(0, ...run.steps.map((s) => s.confusion))
  const stuckAt = run.steps.findIndex((s) => s.confusion >= 2)
  return (
    <article className="mt-6">
      <header>
        <p className="font-mono text-xs text-muted">{run.site}</p>
        <h1 className="mt-2 text-3xl font-extralight tracking-tight md:text-5xl">{run.goal}</h1>
        <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted">
          <span>{PERSONA_LABEL[run.persona] ?? run.persona}</span>
          <StatusPill status={run.status} />
          <time dateTime={run.created_at}>{new Date(run.created_at).toLocaleString()}</time>
        </div>
      </header>

      <section aria-label="Summary" className="mt-8 grid gap-px overflow-hidden rounded-2xl bg-line sm:grid-cols-3">
        <Stat label="Outcome" value={STATUS_LABEL[run.status]} />
        <Stat label="Steps" value={String(run.steps.length)} />
        <Stat label="Peak confusion" value={`${peak} of 3`} note={stuckAt >= 0 ? `first at step ${stuckAt + 1}` : 'never confused'} />
      </section>

      <section aria-label="Think-aloud log" className="mt-12">
        <h2 className="text-xl font-light tracking-tight">What the test user did</h2>
        {run.steps.length === 0 ? (
          <p role="status" className="mt-4 text-sm text-muted">{run.status === 'running' ? 'The run is still in progress.' : 'No steps were recorded.'}</p>
        ) : (
          <ol className="mt-4 border-t border-line">
            {run.steps.map((s, i) => (
              <li key={i} className={`grid grid-cols-[2rem_1fr] gap-3 border-b border-line py-4 ${s.confusion >= 2 ? 'bg-surface/60 -mx-3 px-3 rounded-xl' : ''}`}>
                <span className="pt-0.5 font-mono text-xs text-muted">{i + 1}</span>
                <div className="min-w-0">
                  <p className="leading-relaxed">{s.thought}</p>
                  <p className="mt-1 truncate font-mono text-xs text-muted">
                    {s.action}{s.target_id != null ? ` #${s.target_id}` : ''}{s.text ? ` "${s.text}"` : ''} · {s.url}
                    {s.confusion >= 2 && <span className="ml-2 text-danger">confused ({s.confusion})</span>}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>
    </article>
  )
}

function Stat({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="bg-bg px-5 py-4">
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-1 text-lg font-light">{value}</p>
      {note && <p className="text-xs text-muted">{note}</p>}
    </div>
  )
}
