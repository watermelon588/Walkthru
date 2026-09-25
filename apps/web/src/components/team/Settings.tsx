import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'
import { deleteTeam, renameTeam, setAutoShare, transferTeam, type Overview } from '../../lib/teams'
import { btnGhost, btnPrimary } from '../Shared'

const input = 'w-full rounded-xl border border-line bg-bg px-4 py-3 text-sm text-ink placeholder:text-muted focus:border-ink focus:outline-none'
const select = 'w-full rounded-xl border border-line bg-bg px-4 py-3 text-sm text-ink focus:border-ink focus:outline-none'
const row = 'grid gap-6 border-t border-line pt-10 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]'

/** Workspace settings: your auto-share, then (by role) the name, handing over and deleting. */
export function Settings({ team, onChange }: { team: Overview; onChange: () => void }) {
  const navigate = useNavigate()
  const { can } = team.me
  const [name, setName] = useState(team.team.name)
  const [to, setTo] = useState('')
  const [confirm, setConfirm] = useState('')
  const [msg, setMsg] = useState<{ where: string; text: string; error?: boolean } | null>(null)

  async function act(where: string, action: () => Promise<unknown>, done: string) {
    setMsg(null)
    try {
      await action()
      setMsg({ where, text: done })
      onChange()
    } catch (e) {
      setMsg({ where, text: e instanceof Error ? e.message : 'That did not work. Try again.', error: true })
    }
  }
  const note = (where: string) => msg?.where === where && <p role={msg.error ? 'alert' : 'status'} className={`text-sm ${msg.error ? 'text-danger' : 'text-muted'}`}>{msg.text}</p>
  const heirs = team.members.filter((m) => m.user_id !== team.me.user_id && m.role !== 'viewer')

  return (
    <div className="grid gap-10">
      <section aria-labelledby="auto-share-heading" className={row}>
        <div>
          <h2 id="auto-share-heading" className="text-xl font-light">Auto-share my reports</h2>
          <p className="mt-2 max-w-[48ch] text-sm leading-relaxed text-muted">Every new test run, scan and watch check you start lands in this workspace. Only your own reports; nothing already made moves.</p>
        </div>
        <div className="grid content-start gap-3">
          <label className="flex items-center gap-3 text-sm text-ink">
            <input type="checkbox" checked={team.me.auto_share} disabled={team.me.role === 'viewer'} className="size-4 accent-ink"
              onChange={(e) => act('auto', () => setAutoShare(team.team.id, e.target.checked), e.target.checked ? 'New reports will be shared here.' : 'Auto-share is off.')} />
            Share my new reports with {team.team.name}
          </label>
          {team.me.role === 'viewer' && <p className="text-sm text-muted">Viewers read and comment; they do not share reports.</p>}
          {note('auto')}
        </div>
      </section>

      {can.rename && (
        <section aria-labelledby="rename-heading" className={row}>
          <div>
            <h2 id="rename-heading" className="text-xl font-light">Name</h2>
            <p className="mt-2 max-w-[48ch] text-sm leading-relaxed text-muted">Shown to members and in invitation emails.</p>
          </div>
          <form className="grid content-start gap-3" noValidate onSubmit={(e: FormEvent) => { e.preventDefault(); act('rename', () => renameTeam(team.team.id, name.trim()), 'Saved.') }}>
            <label htmlFor="team-rename" className="grid gap-2 text-sm text-muted">
              Workspace name
              <input id="team-rename" value={name} onChange={(e) => setName(e.target.value)} maxLength={60} className={input} />
            </label>
            <div className="flex flex-wrap items-center gap-4">
              <button type="submit" disabled={!name.trim() || name.trim() === team.team.name} className={`${btnPrimary} disabled:opacity-50`}>Save name</button>
              {note('rename')}
            </div>
          </form>
        </section>
      )}

      {can.transfer && (
        <section aria-labelledby="transfer-heading" className={row}>
          <div>
            <h2 id="transfer-heading" className="text-xl font-light">Hand the workspace over</h2>
            <p className="mt-2 max-w-[48ch] text-sm leading-relaxed text-muted">
              The new owner's Plus plan keeps the workspace active. You stay on as an admin. Use this before you cancel Plus or leave the company.
            </p>
          </div>
          <form className="grid content-start gap-3" noValidate onSubmit={(e: FormEvent) => {
            e.preventDefault()
            const heir = heirs.find((m) => m.user_id === to)
            if (heir && window.confirm(`Make ${heir.name} the owner of ${team.team.name}? You become an admin.`)) act('transfer', () => transferTeam(team.team.id, heir.user_id), `${heir.name} owns the workspace now.`)
          }}>
            <label htmlFor="team-heir" className="grid gap-2 text-sm text-muted">
              New owner
              <select id="team-heir" value={to} onChange={(e) => setTo(e.target.value)} className={select} disabled={heirs.length === 0}>
                <option value="">{heirs.length ? 'Pick a member or admin' : 'Invite a member first'}</option>
                {heirs.map((m) => <option key={m.user_id} value={m.user_id}>{m.name} ({m.email})</option>)}
              </select>
            </label>
            <div className="flex flex-wrap items-center gap-4">
              <button type="submit" disabled={!to} className={`${btnGhost} disabled:opacity-50`}>Hand over</button>
              {note('transfer')}
            </div>
          </form>
        </section>
      )}

      {can.delete && (
        <section aria-labelledby="delete-heading" className={row}>
          <div>
            <h2 id="delete-heading" className="text-xl font-light text-danger">Delete the workspace</h2>
            <p className="mt-2 max-w-[48ch] text-sm leading-relaxed text-muted">
              Removes the chat, comments, triage, invitations and activity for everyone. Reports stay in the accounts of the people who ran them.
            </p>
          </div>
          <form className="grid content-start gap-3" noValidate onSubmit={async (e: FormEvent) => {
            e.preventDefault()
            setMsg(null)
            try {
              await deleteTeam(team.team.id, confirm)
              navigate('/app/team', { replace: true })
            } catch (err) {
              setMsg({ where: 'delete', text: err instanceof Error ? err.message : 'Could not delete the workspace.', error: true })
            }
          }}>
            <label htmlFor="team-delete" className="grid gap-2 text-sm text-muted">
              Type the workspace name to confirm
              <input id="team-delete" value={confirm} onChange={(e) => setConfirm(e.target.value)} className={input} placeholder={team.team.name} autoComplete="off" />
            </label>
            <div className="flex flex-wrap items-center gap-4">
              <button type="submit" disabled={confirm.trim() !== team.team.name} className="rounded-full border border-danger px-6 py-3 text-sm text-danger transition hover:bg-surface disabled:opacity-50">Delete workspace</button>
              {note('delete')}
            </div>
          </form>
        </section>
      )}
    </div>
  )
}
