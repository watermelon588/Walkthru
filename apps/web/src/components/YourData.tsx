import { DownloadSimpleIcon, TrashIcon } from '@phosphor-icons/react'
import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'
import { signOut } from '../lib/auth'
import { deleteAccount, EVIDENCE_RETENTION_DAYS, exportAccount } from '../lib/runs'
import { btnGhost } from './Shared'

/** Retention policy, data export and account deletion. Lives on the settings page. */
export function YourData({ email }: { email: string }) {
  const navigate = useNavigate()
  const [msg, setMsg] = useState<string | null>(null)
  const [busy, setBusy] = useState<'export' | 'delete' | null>(null)
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState<string | null>(null)
  const matches = email !== '' && confirm.trim().toLowerCase() === email.toLowerCase()

  async function download() {
    setBusy('export')
    setMsg(null)
    try {
      const data = await exportAccount()
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: `walkthru-export-${new Date().toISOString().slice(0, 10)}.json` })
      a.click()
      URL.revokeObjectURL(a.href)
      setMsg('Export downloaded.')
    } catch (e) {
      setMsg(e instanceof Error ? e.message : 'Export failed.')
    } finally {
      setBusy(null)
    }
  }

  async function remove(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!matches) return setError('Type your account email exactly to confirm.')
    setBusy('delete')
    setError(null)
    try {
      await deleteAccount(confirm)
      await signOut()
      navigate('/', { replace: true })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Deletion failed. Nothing was removed from your account.')
      setBusy(null)
    }
  }

  return (
    <section aria-labelledby="data-heading" className="mt-14 border-t border-line pt-10">
      <h2 id="data-heading" className="text-xl font-light">Your data</h2>
      <div className="mt-6 grid gap-10 lg:grid-cols-2">
        <div>
          <h3 className="text-sm text-ink">What we keep, and for how long</h3>
          <ul className="mt-3 grid gap-2 text-sm leading-relaxed text-muted">
            <li>Journey screenshots are deleted automatically {EVIDENCE_RETENTION_DAYS} days after each run.</li>
            <li>Runs, steps and reports are kept until you delete them, one at a time from a report or all at once below.</li>
            <li>Emails typed into Instant Scan are erased after {EVIDENCE_RETENTION_DAYS} days.</li>
          </ul>
          <button type="button" onClick={download} disabled={busy !== null} className={`${btnGhost} mt-6`}>
            <DownloadSimpleIcon weight="light" className="size-4" /> {busy === 'export' ? 'Preparing export' : 'Export my data'}
          </button>
          {msg && <p role="status" className="mt-2 text-xs text-muted">{msg}</p>}
        </div>

        <form onSubmit={remove} noValidate className="rounded-2xl border border-line px-5 py-5">
          <h3 className="text-sm text-danger">Delete account</h3>
          <p className="mt-2 text-sm leading-relaxed text-muted">
            Permanently removes your account, every run and report, and all screenshots. This cannot be undone.
          </p>
          <label htmlFor="delete-confirm" className="mt-5 block text-xs text-muted">Type {email || 'your account email'} to confirm</label>
          <input
            id="delete-confirm"
            type="email"
            autoComplete="off"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            disabled={busy !== null}
            aria-invalid={!!error}
            aria-describedby="delete-error"
            className="mt-2 w-full rounded-xl border border-line bg-bg px-4 py-3 text-sm placeholder:text-muted focus:border-ink focus:outline-none"
          />
          <p id="delete-error" role="alert" className="mt-2 min-h-5 text-xs text-danger">{error ?? ''}</p>
          <button type="submit" disabled={!matches || busy !== null} className={`${btnGhost} text-danger disabled:opacity-50`}>
            <TrashIcon weight="light" className="size-4" /> {busy === 'delete' ? 'Deleting account' : 'Delete my account'}
          </button>
        </form>
      </div>
    </section>
  )
}
