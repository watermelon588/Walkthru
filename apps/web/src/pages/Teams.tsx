import { ArrowRightIcon } from '@phosphor-icons/react'
import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'
import { AppShell } from '../components/AppShell'
import { PageHeader } from '../components/PageHeader'
import { btnPrimary } from '../components/Shared'
import { acceptListedInvite, createTeam, declineInvite, listTeams, ROLE_A, ROLE_LABEL, type TeamList } from '../lib/teams'

type State = { kind: 'loading' } | { kind: 'ready'; list: TeamList } | { kind: 'error'; message: string }

const input = 'w-full rounded-xl border border-line bg-bg px-4 py-3 text-sm text-ink placeholder:text-muted focus:border-ink focus:outline-none'
const link = 'text-sm text-ink underline decoration-line underline-offset-4 hover:decoration-ink'

/** Plus: team workspaces. Anyone can be invited into one; creating one needs Plus. */
export default function Teams() {
  const [state, setState] = useState<State>({ kind: 'loading' })
  const load = () => listTeams().then((list) => setState({ kind: 'ready', list })).catch((e: Error) => setState({ kind: 'error', message: e.message }))
  useEffect(() => { load() }, [])

  return (
    <AppShell title="Team">
      <PageHeader kicker="Plus" title="Team workspaces">
        One shared place for your team or your client: every report you share, the findings you are fixing with who owns each one, and a chat that stays with the work.
      </PageHeader>

      {state.kind === 'loading' && <div aria-busy="true" aria-label="Loading your workspaces" className="mt-14 h-40 animate-pulse rounded-2xl bg-surface motion-reduce:animate-none" />}
      {state.kind === 'error' && (
        <div role="alert" className="mt-14 rounded-2xl border border-line px-5 py-5">
          <p className="text-sm text-danger">Could not load your workspaces: {state.message}</p>
          <button type="button" onClick={() => { setState({ kind: 'loading' }); load() }} className={`mt-3 ${link}`}>Try again</button>
        </div>
      )}
      {state.kind === 'ready' && (
        <>
          {state.list.invitations.length > 0 && <Invitations list={state.list} onChange={load} />}
          <section aria-labelledby="teams-heading" className="mt-14">
            <div className="grid gap-10 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
              <div>
                <h2 id="teams-heading" className="text-xl font-light">Your workspaces</h2>
                <p className="mt-2 max-w-[48ch] text-sm leading-relaxed text-muted">
                  A Plus plan owns up to {state.list.max_owned} workspaces with {state.list.seats} seats each. People you invite do not need a plan of their own.
                </p>
                <Link to="/docs#team" className={`mt-4 inline-block ${link}`}>How workspaces work</Link>
              </div>
              <div className="grid min-w-0 content-start gap-5">
                {state.list.teams.length > 0 ? (
                  <ul className="divide-y divide-line rounded-2xl border border-line">
                    {state.list.teams.map((team) => (
                      <li key={team.id}>
                        <Link to={`/app/team/${team.id}`} className="flex items-center justify-between gap-4 px-5 py-4 transition hover:bg-surface/60">
                          <span className="min-w-0">
                            <span className="block truncate text-ink">{team.name}</span>
                            <span className="mt-0.5 block text-xs text-muted">{ROLE_LABEL[team.role]}{team.active ? '' : ' · read-only'}</span>
                          </span>
                          <span className="flex shrink-0 items-center gap-3">
                            {team.mentions > 0 && <span className="rounded-full border border-line px-2 py-0.5 font-mono text-[11px] text-accent">@{team.mentions}</span>}
                            {team.unread > 0 && <span className="font-mono text-xs text-ink" aria-label={`${team.unread} unread messages`}>{team.unread >= 100 ? '99+' : team.unread} new</span>}
                            <ArrowRightIcon weight="light" className="size-4 text-muted" aria-hidden />
                          </span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="rounded-2xl border border-line px-5 py-4 text-sm text-muted">You are not in a workspace yet. Create one below, or join with a code from a teammate.</p>
                )}
                <CreateTeam list={state.list} />
              </div>
            </div>
          </section>
          <JoinWithCode />
        </>
      )}
    </AppShell>
  )
}

function Invitations({ list, onChange }: { list: TeamList; onChange: () => void }) {
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)

  async function act(id: string, accept: boolean) {
    setBusy(id)
    setError(null)
    try {
      if (accept) {
        const { team_id } = await acceptListedInvite(id)
        navigate(`/app/team/${team_id}`)
      } else {
        await declineInvite(id)
        onChange()
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'That did not work. Try again.')
    } finally {
      setBusy(null)
    }
  }

  return (
    <section aria-labelledby="invitations-heading" className="mt-10 rounded-2xl border border-line bg-surface/50 px-5 py-5">
      <h2 id="invitations-heading" className="text-lg font-light">Invitations for you</h2>
      <ul className="mt-3 divide-y divide-line">
        {list.invitations.map((inv) => (
          <li key={inv.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
            <p className="min-w-0 text-sm text-muted">
              <span className="text-ink">{inv.invited_by_name}</span> invited you to <span className="text-ink">{inv.team.name}</span> as {ROLE_A[inv.role]}.
            </p>
            <span className="flex items-center gap-4">
              <button type="button" disabled={busy !== null} onClick={() => act(inv.id, true)} className={`${btnPrimary} py-2 disabled:opacity-50`}>{busy === inv.id ? 'Joining' : 'Join'}</button>
              <button type="button" disabled={busy !== null} onClick={() => act(inv.id, false)} className="text-sm text-muted underline decoration-line underline-offset-4 hover:text-ink">Decline</button>
            </span>
          </li>
        ))}
      </ul>
      {error && <p role="alert" className="mt-2 text-sm text-danger">{error}</p>}
    </section>
  )
}

function CreateTeam({ list }: { list: TeamList }) {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!list.plus) {
    return (
      <div className="rounded-2xl border border-line px-5 py-5">
        <p className="text-sm text-ink">Creating a workspace is part of the Plus plan.</p>
        <p className="mt-1 text-sm text-muted">You can still join one when a Plus teammate invites you. <Link to="/#pricing" className={link}>See the plans</Link></p>
      </div>
    )
  }
  if (!list.can_create) return <p className="text-sm text-muted">You own {list.owned} workspaces, the most one Plus account can own.</p>

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!name.trim()) return setError('Name the workspace, for example your company or the client you work for.')
    setBusy(true)
    setError(null)
    try {
      const team = await createTeam(name.trim())
      navigate(`/app/team/${team.id}/members`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not create the workspace.')
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="grid gap-3" noValidate>
      <label htmlFor="team-name" className="grid gap-2 text-sm text-muted">
        New workspace
        <input id="team-name" value={name} onChange={(e) => setName(e.target.value)} maxLength={60} className={input} placeholder="Acme Studio, or Northwind launch" />
      </label>
      <div className="flex flex-wrap items-center gap-4">
        <button type="submit" disabled={busy} className={`${btnPrimary} disabled:opacity-50`}>{busy ? 'Creating' : 'Create workspace'}</button>
        {error && <p role="alert" className="text-sm text-danger">{error}</p>}
      </div>
    </form>
  )
}

function JoinWithCode() {
  const navigate = useNavigate()
  const [code, setCode] = useState('')
  const [error, setError] = useState<string | null>(null)

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const value = code.trim().split('#').pop() ?? ''
    if (value.replace(/[\s-]/g, '').length !== 24) return setError('Paste the whole invite link or the 24-character code.')
    navigate(`/join#${value}`)
  }

  return (
    <section aria-labelledby="join-heading" className="mt-14 border-t border-line pt-10">
      <div className="grid gap-10 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
        <div>
          <h2 id="join-heading" className="text-xl font-light">Join with a code</h2>
          <p className="mt-2 max-w-[48ch] text-sm leading-relaxed text-muted">Got an invite link or a code from a teammate? Paste it here. You see the workspace before you join.</p>
        </div>
        <form onSubmit={submit} className="flex flex-wrap items-end gap-3" noValidate>
          <label htmlFor="join-code" className="grid min-w-0 flex-1 gap-2 text-sm text-muted">
            Invite link or code
            <input id="join-code" value={code} onChange={(e) => { setCode(e.target.value); setError(null) }} className={`${input} font-mono`} placeholder="ABCD-EFGH-2345-JKLM-NPQR-STUV" autoComplete="off" spellCheck={false} />
          </label>
          <button type="submit" className="rounded-full border border-line px-5 py-3 text-sm text-ink transition hover:bg-surface">Continue</button>
          {error && <p role="alert" className="w-full text-sm text-danger">{error}</p>}
        </form>
      </div>
    </section>
  )
}
