import { ArrowLeftIcon } from '@phosphor-icons/react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, NavLink, useParams } from 'react-router'
import { AppShell } from '../components/AppShell'
import { Chat } from '../components/team/Chat'
import { Findings } from '../components/team/Findings'
import { Members } from '../components/team/Members'
import { Overview } from '../components/team/Overview'
import { Reports } from '../components/team/Reports'
import { Settings } from '../components/team/Settings'
import NotFound from './NotFound'
import { getTeam, ROLE_A, useTeamLive, type Overview as Data } from '../lib/teams'

type State = { kind: 'loading' } | { kind: 'ready'; team: Data } | { kind: 'missing' } | { kind: 'error'; message: string }

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'chat', label: 'Chat' },
  { id: 'findings', label: 'Findings' },
  { id: 'reports', label: 'Reports' },
  { id: 'members', label: 'Members' },
  { id: 'settings', label: 'Settings' },
] as const

/** One workspace: /app/team/:id/:tab. The API answers 404 to non-members, shown here as "not found". */
export default function Team() {
  const { id = '', tab = 'overview' } = useParams()
  return <Workspace key={id} id={id} tab={tab} />  // a fresh page state per workspace
}

function Workspace({ id, tab }: { id: string; tab: string }) {
  const [state, setState] = useState<State>({ kind: 'loading' })
  const [signal, setSignal] = useState(0)  // shares, triage, members, activity changed: data tabs refetch
  const [chatSignal, setChatSignal] = useState(0)  // a message or comment changed: open threads refetch
  const timers = useRef<Record<string, number>>({})

  const load = useCallback(() =>
    getTeam(id)
      .then((team) => setState({ kind: 'ready', team }))
      .catch((e: Error) => setState((s) => (/not a member|No workspace/i.test(e.message) ? { kind: 'missing' } : s.kind === 'ready' ? s : { kind: 'error', message: e.message }))), [id])
  useEffect(() => { load() }, [load])

  // Realtime nudges, debounced. Messages and presence (read markers, last seen) change often, so they refresh only the
  // threads at once and the header counts after a pause; shares, triage and membership refresh everything quickly.
  const later = (key: string, ms: number, fn: () => void) => {
    window.clearTimeout(timers.current[key])
    timers.current[key] = window.setTimeout(fn, ms)
  }
  const live = useTeamLive(id, (table) => {
    if (table === 'team_messages') {
      later('chat', 300, () => setChatSignal((n) => n + 1))
      later('overview', 10_000, load)
    } else if (table === 'team_members') {
      later('overview', 10_000, () => { setSignal((n) => n + 1); load() })
    } else {
      later('overview', 600, () => { setSignal((n) => n + 1); load() })
    }
  })
  useEffect(() => {
    if (live) return
    const poll = window.setInterval(() => { if (document.visibilityState === 'visible') load() }, 30_000)
    return () => window.clearInterval(poll)
  }, [live, load])
  useEffect(() => () => Object.values(timers.current).forEach((t) => window.clearTimeout(t)), [])

  if (state.kind === 'missing') return <NotFound />
  const team = state.kind === 'ready' ? state.team : null
  const valid = TABS.some((t) => t.id === tab)

  return (
    <AppShell title={team ? `${team.team.name}, ${TABS.find((t) => t.id === tab)?.label ?? 'Team'}` : 'Team'}>
      <Link to="/app/team" className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-ink">
        <ArrowLeftIcon className="size-4" /> All workspaces
      </Link>

      {state.kind === 'loading' && <div aria-busy="true" aria-label="Loading the workspace" className="mt-8 h-64 animate-pulse rounded-2xl bg-surface motion-reduce:animate-none" />}
      {state.kind === 'error' && (
        <div role="alert" className="mt-8 rounded-2xl border border-line px-5 py-5">
          <p className="text-sm text-danger">Could not load the workspace: {state.message}</p>
          <button type="button" onClick={() => { setState({ kind: 'loading' }); load() }} className="mt-3 text-sm text-ink underline decoration-line underline-offset-4 hover:decoration-ink">Try again</button>
        </div>
      )}

      {team && (
        <>
          <header className="mt-6 grid gap-6 border-b border-line pb-8 sm:grid-cols-[1fr_auto] sm:items-end">
            <div className="min-w-0">
              <p className="font-mono text-xs uppercase tracking-[0.16em] text-accent">Team workspace</p>
              <h1 className="mt-3 truncate text-4xl font-extralight tracking-tight md:text-5xl">{team.team.name}</h1>
              <p className="mt-3 text-sm text-muted">
                You are {ROLE_A[team.me.role]} ·{' '}
                {team.members.length} of {team.team.seats} seats · {team.members.filter((m) => m.online).length} here now
                <span className="sr-only">{live ? '. Live updates on.' : '. Updates every 30 seconds.'}</span>
              </p>
            </div>
          </header>

          {!team.team.active && (
            <p role="status" className="mt-6 rounded-2xl border border-line bg-surface/50 px-5 py-4 text-sm leading-relaxed text-muted">
              <span className="text-ink">This workspace is read-only.</span> Its owner's Plus plan has ended, so chat, sharing, triage and invitations are paused. Everything stays readable.
              {team.me.can.transfer ? ' Renew Plus, or hand the workspace to a member who is on Plus in Settings.' : ' Ask the owner to renew Plus or hand the workspace over.'}
            </p>
          )}

          <nav aria-label="Workspace sections" className="mt-6 -mx-5 overflow-x-auto px-5 md:mx-0 md:px-0">
            <ul className="flex min-w-max gap-1 border-b border-line">
              {TABS.map((t) => (
                <li key={t.id}>
                  <NavLink
                    to={t.id === 'overview' ? `/app/team/${id}` : `/app/team/${id}/${t.id}`}
                    end
                    className={({ isActive }) => `-mb-px flex min-h-11 items-center gap-2 border-b px-3 text-sm transition-colors ${isActive || (t.id === 'overview' && tab === 'overview') ? 'border-ink text-ink' : 'border-transparent text-muted hover:text-ink'}`}
                  >
                    {t.label}
                    {t.id === 'chat' && team.unread > 0 && tab !== 'chat' && <span className="font-mono text-[11px] text-accent" aria-label={`${team.unread} unread`}>{team.unread >= 100 ? '99+' : team.unread}</span>}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>

          <div className="mt-10">
            {!valid && <p className="text-sm text-muted">There is no such section. <Link to={`/app/team/${id}`} className="text-ink underline decoration-line underline-offset-4">Back to the overview</Link></p>}
            {tab === 'overview' && <Overview team={team} />}
            {tab === 'chat' && (
              <div className="grid gap-4">
                <div>
                  <h2 className="text-xl font-light">Chat</h2>
                  <p className="mt-1 max-w-[60ch] text-sm leading-relaxed text-muted">One channel for the whole workspace. It stays here for everyone who joins later. Reports and findings have their own comment threads.</p>
                </div>
                <Chat teamId={id} thread="general" me={team.me.user_id} members={team.members} canChat={team.me.can.chat} canModerate={team.me.can.manage_members}
                  live={live} signal={chatSignal} title={`${team.team.name} chat`} empty="No messages yet. Say hello, or share what you are working on." />
              </div>
            )}
            {tab === 'findings' && <Findings teamId={id} me={team.me.user_id} members={team.members} live={live} signal={signal} chatSignal={chatSignal} canChat={team.me.can.chat} canModerate={team.me.can.manage_members} />}
            {tab === 'reports' && <Reports teamId={id} me={team.me.user_id} role={team.me.role} signal={signal} />}
            {tab === 'members' && <Members teamId={id} me={team.me.user_id} signal={signal} />}
            {tab === 'settings' && <Settings team={team} onChange={load} />}
          </div>
        </>
      )}
    </AppShell>
  )
}
