import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router'
import { KIND_LABEL } from '../../lib/runs'
import { getBoard, STATUS_TEXT, triage, type Board, type BoardItem, type Member, type Status } from '../../lib/teams'
import { Chat } from './Chat'

type State = { kind: 'loading' } | { kind: 'ready'; board: Board } | { kind: 'error'; message: string }
type Filter = 'active' | 'all' | Status

const select = 'rounded-xl border border-line bg-bg px-3 py-2 text-sm text-ink focus:border-ink focus:outline-none disabled:opacity-60'
const host = (url: string) => url.replace(/^https?:\/\//, '').replace(/\/$/, '')
const day = (iso: string) => new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })

/** Every finding across the workspace's shared reports, one row per site and problem, with its status and owner. */
export function Findings({ teamId, me, members, live, signal, canChat, canModerate }: { teamId: string; me: string; members: Member[]; live: boolean; signal: number; canChat: boolean; canModerate: boolean }) {
  const [state, setState] = useState<State>({ kind: 'loading' })
  const [filter, setFilter] = useState<Filter>('active')
  const [severity, setSeverity] = useState<'all' | BoardItem['severity']>('all')
  const [site, setSite] = useState('all')
  const [mine, setMine] = useState(false)
  const [open, setOpen] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => getBoard(teamId).then((board) => setState({ kind: 'ready', board })).catch((e: Error) => setState({ kind: 'error', message: e.message })), [teamId])
  useEffect(() => { load() }, [load])
  useEffect(() => { if (signal) load() }, [signal, load])

  const board = state.kind === 'ready' ? state.board : null
  const sites = useMemo(() => [...new Set(board?.findings.map((f) => f.origin) ?? [])], [board])
  const shown = (board?.findings ?? []).filter((f) =>
    (filter === 'all' || (filter === 'active' ? f.status === 'open' || f.status === 'in_progress' || f.seen_again : f.status === filter))
    && (severity === 'all' || f.severity === severity) && (site === 'all' || f.origin === site) && (!mine || f.assignee_id === me))

  async function change(item: BoardItem, update: { status?: Status; assignee_id?: string | null }) {
    setError(null)
    try {
      const saved = await triage(teamId, item, update)
      setState((s) => s.kind === 'ready' ? { kind: 'ready', board: { ...s.board, findings: s.board.findings.map((f) => f.thread === saved.thread ? saved : f) } } : s)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not save the change.')
    }
  }

  if (state.kind === 'loading') return <div aria-busy="true" aria-label="Loading findings" className="h-64 animate-pulse rounded-2xl bg-surface motion-reduce:animate-none" />
  if (state.kind === 'error') {
    return (
      <div role="alert" className="rounded-2xl border border-line px-5 py-5">
        <p className="text-sm text-danger">Could not load findings: {state.message}</p>
        <button type="button" onClick={() => { setState({ kind: 'loading' }); load() }} className="mt-3 text-sm text-ink underline decoration-line underline-offset-4 hover:decoration-ink">Try again</button>
      </div>
    )
  }
  const { findings, assignees, can_triage } = state.board

  return (
    <section aria-labelledby="board-heading" className="grid gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 id="board-heading" className="text-xl font-light">Findings board</h2>
          <p className="mt-1 max-w-[60ch] text-sm leading-relaxed text-muted">One row per problem and site, across every report in this workspace. Give each one a status and an owner.</p>
        </div>
        <p className="font-mono text-xs text-muted">{shown.length} of {findings.length}</p>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <label className="grid gap-1 text-xs text-muted">Status
          <select value={filter} onChange={(e) => setFilter(e.target.value as Filter)} className={select}>
            <option value="active">To do (open, in progress, found again)</option>
            <option value="all">All</option>
            {(Object.keys(STATUS_TEXT) as Status[]).map((s) => <option key={s} value={s}>{STATUS_TEXT[s]}</option>)}
          </select>
        </label>
        <label className="grid gap-1 text-xs text-muted">Severity
          <select value={severity} onChange={(e) => setSeverity(e.target.value as typeof severity)} className={select}>
            <option value="all">All</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option>
          </select>
        </label>
        {sites.length > 1 && (
          <label className="grid gap-1 text-xs text-muted">Site
            <select value={site} onChange={(e) => setSite(e.target.value)} className={select}>
              <option value="all">All sites</option>
              {sites.map((s) => <option key={s} value={s}>{host(s)}</option>)}
            </select>
          </label>
        )}
        <label className="flex items-center gap-2 pb-2 text-sm text-muted">
          <input type="checkbox" checked={mine} onChange={(e) => setMine(e.target.checked)} className="size-4 accent-ink" /> Assigned to me
        </label>
      </div>
      {error && <p role="alert" className="text-sm text-danger">{error}</p>}

      {findings.length === 0 ? (
        <p className="rounded-2xl border border-line px-5 py-4 text-sm text-muted">No findings yet. Share a report into this workspace from its report page, and its findings land here.</p>
      ) : shown.length === 0 ? (
        <p className="rounded-2xl border border-line px-5 py-4 text-sm text-muted">Nothing matches these filters.</p>
      ) : (
        <ul className="border-t border-line">
          {shown.map((f) => (
            <li key={f.thread} className="grid gap-3 border-b border-line py-5 lg:grid-cols-[minmax(0,1fr)_auto]">
              <div className="min-w-0">
                <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
                  <span className={f.severity === 'high' ? 'text-danger' : 'text-ink'}>{f.severity[0].toUpperCase() + f.severity.slice(1)}</span>
                  <span>{KIND_LABEL[f.kind]}</span>
                  <span className="font-mono">{host(f.site)}</span>
                  <span>in {f.reports} report{f.reports === 1 ? '' : 's'}, last {day(f.last_seen)}</span>
                  {f.seen_again && <span className="rounded-full border border-line px-2 py-0.5 text-danger">Found again after a fix</span>}
                </p>
                <p className="mt-1.5 text-ink">{f.title}</p>
                <details className="mt-2 text-sm">
                  <summary className="cursor-pointer text-muted hover:text-ink">How to fix</summary>
                  <p className="mt-2 leading-relaxed">{f.fix || f.detail}</p>
                  {f.evidence && <p className="mt-2 font-mono text-xs break-all text-muted">{f.evidence}</p>}
                  <Link to={`/app/team/${teamId}/runs/${f.run_id}`} className="mt-2 inline-block text-ink underline decoration-line underline-offset-4 hover:decoration-ink">Open the latest report</Link>
                </details>
                <button type="button" aria-expanded={open === f.thread} onClick={() => setOpen(open === f.thread ? null : f.thread)} className="mt-2 text-xs text-muted underline decoration-line underline-offset-4 hover:text-ink">
                  {open === f.thread ? 'Hide comments' : f.comments ? `Comments (${f.comments})` : 'Comment'}
                </button>
                {open === f.thread && (
                  <div className="mt-3">
                    <Chat teamId={teamId} thread={f.thread} me={me} members={members} canChat={canChat} canModerate={canModerate}
                      live={live} signal={signal} title={`Comments on ${f.title}`} empty="No comments yet. Say what you found or what you changed." compact />
                  </div>
                )}
              </div>
              <div className="flex flex-wrap items-start gap-3 lg:justify-end">
                <label className="grid gap-1 text-xs text-muted">Status
                  <select value={f.status} disabled={!can_triage} onChange={(e) => change(f, { status: e.target.value as Status })} className={select}>
                    {(Object.keys(STATUS_TEXT) as Status[]).map((s) => <option key={s} value={s}>{STATUS_TEXT[s]}</option>)}
                  </select>
                </label>
                <label className="grid gap-1 text-xs text-muted">Owner
                  <select value={f.assignee_id ?? ''} disabled={!can_triage} onChange={(e) => change(f, { assignee_id: e.target.value || null })} className={select}>
                    <option value="">No one</option>
                    {f.assignee_id && !assignees.some((a) => a.user_id === f.assignee_id) && <option value={f.assignee_id}>{f.assignee_name}</option>}
                    {assignees.map((a) => <option key={a.user_id} value={a.user_id}>{a.user_id === me ? `${a.name} (you)` : a.name}</option>)}
                  </select>
                </label>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
