import { UsersThreeIcon } from '@phosphor-icons/react'
import { useEffect, useState } from 'react'
import { runTeams, shareRun, unshareRun } from '../lib/teams'
import { btnGhost } from './Shared'

type Team = { id: string; name: string; shared: boolean }

/** On the owner's report page: put this report into one or more of their team workspaces (Plus teams).
 *  Hidden when the owner is in no workspace where they can share. */
export function ShareToTeam({ runId }: { runId: string }) {
  const [teams, setTeams] = useState<Team[] | null>(null)
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => { runTeams(runId).then((r) => setTeams(r.teams)).catch(() => setTeams([])) }, [runId])
  if (!teams || teams.length === 0) return null
  const count = teams.filter((t) => t.shared).length

  async function toggle(team: Team) {
    const flip = (shared: boolean) => setTeams((current) => current?.map((t) => (t.id === team.id ? { ...t, shared } : t)) ?? null)
    setBusy(team.id)
    setError(null)
    flip(!team.shared)  // show the change at once; undo it if the API refuses
    try {
      await (team.shared ? unshareRun(team.id, runId) : shareRun(team.id, runId))
    } catch (e) {
      flip(team.shared)
      setError(e instanceof Error ? e.message : 'That did not work. Try again.')
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="relative">
      <button type="button" aria-expanded={open} aria-controls="share-to-team" onClick={() => setOpen((o) => !o)} className={btnGhost}>
        <UsersThreeIcon weight="light" className="size-4" /> {count ? `In ${count} workspace${count > 1 ? 's' : ''}` : 'Share to workspace'}
      </button>
      {open && (
        <div id="share-to-team" className="absolute left-0 z-10 mt-2 w-72 rounded-2xl border border-line bg-bg p-4 shadow-[0_24px_60px_-30px_rgba(27,27,31,0.35)]">
          <fieldset>
            <legend className="text-xs text-muted">Members of these workspaces can read this report and comment on it.</legend>
            <div className="mt-3 grid gap-2">
              {teams.map((t) => (
                <label key={t.id} className="flex items-center gap-3 text-sm text-ink">
                  <input type="checkbox" checked={t.shared} disabled={busy !== null} onChange={() => toggle(t)} className="size-4 accent-ink" />
                  <span className="min-w-0 truncate">{t.name}</span>
                </label>
              ))}
            </div>
          </fieldset>
          {error && <p role="alert" className="mt-3 text-xs text-danger">{error}</p>}
        </div>
      )}
    </div>
  )
}
