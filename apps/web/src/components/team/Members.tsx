import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'
import { changeRole, createLink, getMembers, inviteByEmail, removeMember, revokeInvite, ROLE_HELP, ROLE_LABEL, type Members as Data, type Role } from '../../lib/teams'
import { AccountAvatar } from '../AccountAvatar'
import { Snippet } from '../DomainVerification'
import { btnPrimary } from '../Shared'

type State = { kind: 'loading' } | { kind: 'ready'; data: Data } | { kind: 'error'; message: string }

const input = 'w-full rounded-xl border border-line bg-bg px-4 py-3 text-sm text-ink placeholder:text-muted focus:border-ink focus:outline-none'
const select = 'rounded-xl border border-line bg-bg px-3 py-2 text-sm text-ink focus:border-ink focus:outline-none disabled:opacity-60'
const small = 'text-xs text-muted underline decoration-line underline-offset-4 hover:text-ink'
const day = (iso: string) => new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })

/** People, roles, invitations and invite links. The API enforces every rule shown here. */
export function Members({ teamId, me, signal }: { teamId: string; me: string; signal: number }) {
  const navigate = useNavigate()
  const [state, setState] = useState<State>({ kind: 'loading' })
  const [msg, setMsg] = useState<{ text: string; error?: boolean } | null>(null)
  const [shown, setShown] = useState<{ label: string; value: string } | null>(null)

  const load = useCallback(() => getMembers(teamId).then((data) => setState({ kind: 'ready', data })).catch((e: Error) => setState({ kind: 'error', message: e.message })), [teamId])
  useEffect(() => { load() }, [load])
  useEffect(() => { if (signal) load() }, [signal, load])

  async function act(action: () => Promise<unknown>, done?: string) {
    setMsg(null)
    try {
      await action()
      if (done) setMsg({ text: done })
      await load()
    } catch (e) {
      setMsg({ text: e instanceof Error ? e.message : 'That did not work. Try again.', error: true })
    }
  }

  if (state.kind === 'loading') return <div aria-busy="true" aria-label="Loading members" className="h-48 animate-pulse rounded-2xl bg-surface motion-reduce:animate-none" />
  if (state.kind === 'error') {
    return (
      <div role="alert" className="rounded-2xl border border-line px-5 py-5">
        <p className="text-sm text-danger">Could not load members: {state.message}</p>
        <button type="button" onClick={() => { setState({ kind: 'loading' }); load() }} className="mt-3 text-sm text-ink underline decoration-line underline-offset-4 hover:decoration-ink">Try again</button>
      </div>
    )
  }
  const { members, invites, seats, seats_used, me: mine } = state.data
  const owner = mine.role === 'owner'
  const full = seats_used >= seats
  const roleChoices = (target: Role): Role[] => (owner ? ['admin', 'member', 'viewer'] : target === 'admin' ? [] : ['member', 'viewer'])

  return (
    <div className="grid gap-12">
      <section aria-labelledby="members-heading" className="grid gap-5">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 id="members-heading" className="text-xl font-light">People</h2>
            <p className="mt-1 text-sm text-muted">{seats_used} of {seats} seats used{invites.some((i) => i.kind === 'email') ? ', counting open invitations' : ''}.</p>
          </div>
        </div>
        {msg && <p role={msg.error ? 'alert' : 'status'} className={`text-sm ${msg.error ? 'text-danger' : 'text-muted'}`}>{msg.text}</p>}
        <ul className="divide-y divide-line rounded-2xl border border-line">
          {members.map((m) => {
            const self = m.user_id === me
            const choices = roleChoices(m.role)
            const editable = mine.can.manage_members && !self && m.role !== 'owner' && choices.length > 0
            return (
              <li key={m.user_id} className="flex flex-wrap items-center justify-between gap-4 px-5 py-4">
                <span className="flex min-w-0 items-center gap-3">
                  <span className="relative">
                    <AccountAvatar name={m.name} />
                    {m.online && <span className="absolute -right-0.5 -bottom-0.5 size-2.5 rounded-full border-2 border-bg bg-accent" aria-hidden />}
                  </span>
                  <span className="min-w-0">
                    <span className="block truncate text-sm text-ink">{m.name}{self && <span className="text-muted"> (you)</span>}</span>
                    <span className="block truncate text-xs text-muted">{m.email}{m.online ? ' · here now' : ''}</span>
                  </span>
                </span>
                <span className="flex items-center gap-4">
                  {editable ? (
                    <label className="flex items-center gap-2 text-xs text-muted">
                      <span className="sr-only">Role of {m.name}</span>
                      <select value={m.role} onChange={(e) => act(() => changeRole(teamId, m.user_id, e.target.value as Role), `${m.name} is now ${ROLE_LABEL[e.target.value as Role].toLowerCase()}.`)} className={select}>
                        {[...new Set([m.role, ...choices])].map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}
                      </select>
                    </label>
                  ) : (
                    <span className="text-xs text-muted">{ROLE_LABEL[m.role]}</span>
                  )}
                  {self && m.role !== 'owner' && (
                    <button type="button" className={small} onClick={() => window.confirm('Leave this workspace? You lose access to its reports and chat until someone invites you again.')
                      && act(async () => { await removeMember(teamId, me); navigate('/app/team', { replace: true }) })}>Leave</button>
                  )}
                  {editable && (
                    <button type="button" className={`${small} hover:text-danger`} onClick={() => window.confirm(`Remove ${m.name} from this workspace? Reports they shared stay.`)
                      && act(() => removeMember(teamId, m.user_id), `${m.name} was removed.`)}>Remove</button>
                  )}
                </span>
              </li>
            )
          })}
        </ul>
        <dl className="grid gap-3 text-xs text-muted sm:grid-cols-2">
          {(['owner', 'admin', 'member', 'viewer'] as Role[]).map((r) => (
            <div key={r}><dt className="inline text-ink">{ROLE_LABEL[r]}: </dt><dd className="inline">{ROLE_HELP[r]}</dd></div>
          ))}
        </dl>
      </section>

      {mine.can.invite ? (
        <section aria-labelledby="invite-heading" className="grid gap-8 border-t border-line pt-10 lg:grid-cols-2">
          <InviteByEmail teamId={teamId} owner={owner} full={full} seats={seats} onDone={(value, emailed) => {
            setShown({ label: emailed ? 'Invitation sent. You can also send this link yourself; it works only for that address.' : 'Email delivery is not set up, so send this link yourself. It works only for that address, once, for 7 days.', value })
            load()
          }} />
          <InviteLink teamId={teamId} onDone={(value) => { setShown({ label: 'Invite link. Anyone with it can join while seats are free, so share it only with your team. It is shown once.', value }); load() }} />
          {shown && <div className="lg:col-span-2"><Snippet label={shown.label} value={shown.value} /></div>}
        </section>
      ) : mine.can.manage_members ? (
        <p className="border-t border-line pt-10 text-sm text-muted">Invitations are paused while this workspace is read-only.</p>
      ) : null}

      {mine.can.manage_members && invites.length > 0 && (
        <section aria-labelledby="open-invites-heading" className="grid gap-4">
          <h2 id="open-invites-heading" className="text-lg font-light">Open invitations and links</h2>
          <ul className="divide-y divide-line rounded-2xl border border-line">
            {invites.map((i) => (
              <li key={i.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3 text-sm">
                <span className="min-w-0">
                  <span className="block truncate text-ink">{i.kind === 'email' ? i.email : `Invite link${i.email_domain ? ` for @${i.email_domain}` : ''}`}</span>
                  <span className="block text-xs text-muted">
                    {ROLE_LABEL[i.role]} · {i.kind === 'link' ? `${i.uses} of ${i.max_uses} used · ` : ''}until {day(i.expires_at)} · by {i.invited_by_name}
                  </span>
                </span>
                <button type="button" className={`${small} hover:text-danger`} onClick={() => act(() => revokeInvite(teamId, i.id), 'Invitation withdrawn.')}>Withdraw</button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}

function InviteByEmail({ teamId, owner, full, seats, onDone }: { teamId: string; owner: boolean; full: boolean; seats: number; onDone: (link: string, emailed: boolean) => void }) {
  const [email, setEmail] = useState('')
  const [role, setRole] = useState<Role>('member')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!/^\S+@\S+\.\S+$/.test(email.trim())) return setError('Enter the email address of the person to invite.')
    setBusy(true)
    setError(null)
    try {
      const sent = await inviteByEmail(teamId, email.trim(), role)
      setEmail('')
      onDone(sent.link, sent.emailed)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not send the invitation.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="grid content-start gap-4" noValidate aria-labelledby="invite-heading">
      <div>
        <h2 id="invite-heading" className="text-lg font-light">Invite by email</h2>
        <p className="mt-1 text-sm leading-relaxed text-muted">The invitation works only for that address, after they confirm it, once, for 7 days. It holds a seat until it is used or withdrawn.</p>
      </div>
      <label htmlFor="invite-email" className="grid gap-2 text-sm text-muted">
        Email address
        <input id="invite-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} className={input} placeholder="teammate@company.com" autoComplete="off" disabled={full} />
      </label>
      <label htmlFor="invite-role" className="grid gap-2 text-sm text-muted">
        Role
        <select id="invite-role" value={role} onChange={(e) => setRole(e.target.value as Role)} className={`${select} py-3`} disabled={full}>
          {owner && <option value="admin">Admin</option>}
          <option value="member">Member</option>
          <option value="viewer">Viewer</option>
        </select>
      </label>
      <div className="flex flex-wrap items-center gap-4">
        <button type="submit" disabled={busy || full} className={`${btnPrimary} disabled:opacity-50`}>{busy ? 'Sending' : 'Send invitation'}</button>
        {full && <p className="text-sm text-muted">All {seats} seats are taken.</p>}
        {error && <p role="alert" className="text-sm text-danger">{error}</p>}
      </div>
    </form>
  )
}

function InviteLink({ teamId, onDone }: { teamId: string; onDone: (link: string) => void }) {
  const [role, setRole] = useState<Role>('member')
  const [days, setDays] = useState(7)
  const [uses, setUses] = useState(5)
  const [domain, setDomain] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const made = await createLink(teamId, { role, days, max_uses: uses, email_domain: domain.trim() || null })
      onDone(made.link)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not make the link.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="grid content-start gap-4" noValidate aria-labelledby="link-heading">
      <div>
        <h2 id="link-heading" className="text-lg font-light">Invite link</h2>
        <p className="mt-1 text-sm leading-relaxed text-muted">A link, and a code people can type, for several people at once. Limit it to your company's email domain to keep it safe if it travels.</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        <label htmlFor="link-role" className="grid gap-2 text-sm text-muted">
          Role
          <select id="link-role" value={role} onChange={(e) => setRole(e.target.value as Role)} className={`${select} py-3`}>
            <option value="member">Member</option>
            <option value="viewer">Viewer</option>
          </select>
        </label>
        <label htmlFor="link-days" className="grid gap-2 text-sm text-muted">
          Works for
          <select id="link-days" value={days} onChange={(e) => setDays(Number(e.target.value))} className={`${select} py-3`}>
            <option value={1}>1 day</option><option value={7}>7 days</option><option value={30}>30 days</option>
          </select>
        </label>
        <label htmlFor="link-uses" className="grid gap-2 text-sm text-muted">
          Uses
          <select id="link-uses" value={uses} onChange={(e) => setUses(Number(e.target.value))} className={`${select} py-3`}>
            {[1, 5, 10, 25].map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </label>
      </div>
      <label htmlFor="link-domain" className="grid gap-2 text-sm text-muted">
        Only for this email domain (optional)
        <input id="link-domain" value={domain} onChange={(e) => setDomain(e.target.value)} className={input} placeholder="company.com" autoComplete="off" spellCheck={false} />
      </label>
      <div className="flex flex-wrap items-center gap-4">
        <button type="submit" disabled={busy} className="rounded-full border border-line px-6 py-3 text-sm text-ink transition hover:bg-surface disabled:opacity-50">{busy ? 'Making' : 'Make invite link'}</button>
        {error && <p role="alert" className="text-sm text-danger">{error}</p>}
      </div>
    </form>
  )
}
