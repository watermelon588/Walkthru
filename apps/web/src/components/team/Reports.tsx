import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router'
import { PERSONA_LABEL, STATUS_LABEL, timeAgo, type Run } from '../../lib/runs'
import { sharedRuns, unshareRun, type Role, type SharedRun } from '../../lib/teams'

type State = { kind: 'loading' } | { kind: 'ready'; runs: SharedRun[]; more: boolean } | { kind: 'error'; message: string }

const host = (url: string) => url.replace(/^https?:\/\//, '').replace(/\/$/, '')
const what = (r: SharedRun) => (r.kind === 'test' ? `${PERSONA_LABEL[r.persona] ?? r.persona}: ${r.goal}` : r.kind === 'watch' ? 'Weekly watch check' : 'Homepage scan')

/** Reports shared into the workspace, newest first. Each opens read-only with its own comment thread. */
export function Reports({ teamId, me, role, signal }: { teamId: string; me: string; role: Role; signal: number }) {
  const [state, setState] = useState<State>({ kind: 'loading' })
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => sharedRuns(teamId).then((p) => setState({ kind: 'ready', runs: p.runs, more: p.has_more })).catch((e: Error) => setState({ kind: 'error', message: e.message })), [teamId])
  useEffect(() => { load() }, [load])
  useEffect(() => { if (signal) load() }, [signal, load])

  async function more() {
    if (state.kind !== 'ready') return
    try {
      const page = await sharedRuns(teamId, state.runs.at(-1)?.shared_at)
      setState({ kind: 'ready', runs: [...state.runs, ...page.runs], more: page.has_more })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load more reports.')
    }
  }

  async function remove(r: SharedRun) {
    if (!window.confirm(`Remove the report on ${host(r.site)} from this workspace? The report itself stays in its owner's account.`)) return
    setError(null)
    try {
      await unshareRun(teamId, r.run_id)
      setState((s) => (s.kind === 'ready' ? { ...s, runs: s.runs.filter((x) => x.run_id !== r.run_id) } : s))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not remove the report.')
    }
  }

  if (state.kind === 'loading') return <div aria-busy="true" aria-label="Loading shared reports" className="h-48 animate-pulse rounded-2xl bg-surface motion-reduce:animate-none" />
  if (state.kind === 'error') {
    return (
      <div role="alert" className="rounded-2xl border border-line px-5 py-5">
        <p className="text-sm text-danger">Could not load shared reports: {state.message}</p>
        <button type="button" onClick={() => { setState({ kind: 'loading' }); load() }} className="mt-3 text-sm text-ink underline decoration-line underline-offset-4 hover:decoration-ink">Try again</button>
      </div>
    )
  }
  const admin = role === 'owner' || role === 'admin'

  return (
    <section aria-labelledby="reports-heading" className="grid gap-5">
      <div>
        <h2 id="reports-heading" className="text-xl font-light">Shared reports</h2>
        <p className="mt-1 max-w-[60ch] text-sm leading-relaxed text-muted">
          Share a report from its page with Share to workspace, or turn on auto-share in Settings so every new report lands here.
        </p>
      </div>
      {error && <p role="alert" className="text-sm text-danger">{error}</p>}
      {state.runs.length === 0 ? (
        <p className="rounded-2xl border border-line px-5 py-4 text-sm text-muted">No reports shared yet.</p>
      ) : (
        <ul className="divide-y divide-line rounded-2xl border border-line">
          {state.runs.map((r) => (
            <li key={r.run_id} className="grid gap-3 px-5 py-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
              <Link to={`/app/team/${teamId}/runs/${r.run_id}`} className="group min-w-0">
                <span className="block truncate font-mono text-xs text-muted">{host(r.site)}</span>
                <span className="mt-1 block truncate text-ink group-hover:underline group-hover:decoration-line group-hover:underline-offset-4">{what(r)}</span>
                <span className="mt-1 block text-xs text-muted">
                  {STATUS_LABEL[r.status as Run['status']] ?? r.status} · {r.findings.high} high, {r.findings.medium} medium, {r.findings.low} low
                  {r.comments > 0 && ` · ${r.comments} comment${r.comments === 1 ? '' : 's'}`} · shared by {r.shared_by === me ? 'you' : r.shared_by_name} {timeAgo(r.shared_at)}
                </span>
              </Link>
              <span className="flex items-center gap-4 sm:justify-end">
                <span className="font-mono text-lg font-light text-ink" aria-label={r.score === null ? 'No score' : `Launch Ready score ${r.score}`}>{r.score ?? 'N/A'}</span>
                {(admin || r.shared_by === me || r.owner_id === me) && (
                  <button type="button" onClick={() => remove(r)} className="text-xs text-muted underline decoration-line underline-offset-4 hover:text-danger">Remove</button>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}
      {state.more && <button type="button" onClick={more} className="justify-self-start text-sm text-ink underline decoration-line underline-offset-4 hover:decoration-ink">Show older reports</button>}
    </section>
  )
}
