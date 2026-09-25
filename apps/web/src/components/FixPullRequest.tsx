import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { fixPullRequest, getGitHub, listGitHubRepos, type FixPr, type GitHubRepo } from '../lib/runs'

type State = { kind: 'hidden' } | { kind: 'connect' } | { kind: 'ready'; repos: GitHubRepo[] }

const select = 'min-w-0 flex-1 rounded-xl border border-line bg-bg px-3 py-2 text-sm text-ink focus:border-ink focus:outline-none'
const button = 'rounded-full border border-line px-4 py-2 text-sm transition hover:border-ink disabled:opacity-50'

/** Plus, owner's report page: preview then open a pull request with the config-only fixes (P4.4). */
export function FixPullRequest({ runId }: { runId: string }) {
  const [state, setState] = useState<State>({ kind: 'hidden' })
  const [repo, setRepo] = useState('')
  const [preview, setPreview] = useState<FixPr | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getGitHub()
      .then(async (g) => {
        if (!g.plus || !g.configured) return
        if (!g.installations.length) return setState({ kind: 'connect' })
        const { repos } = await listGitHubRepos()
        setState({ kind: 'ready', repos })
        setRepo(repos[0]?.full_name ?? '')
      })
      .catch(() => setState({ kind: 'hidden' }))
  }, [])

  if (state.kind === 'hidden') return null
  const chosen = state.kind === 'ready' ? state.repos.find((r) => r.full_name === repo) : undefined

  async function run(confirm: boolean) {
    if (!chosen) return
    setBusy(true)
    setError(null)
    try {
      setPreview(await fixPullRequest(runId, chosen, confirm))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'That did not work. Try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section aria-labelledby="fix-pr-title" className="no-print mb-8 rounded-2xl border border-line px-5 py-5">
      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Plus</p>
      <h2 id="fix-pr-title" className="mt-2 text-xl font-light tracking-tight">Open a fix pull request</h2>
      <p className="mt-2 max-w-[62ch] text-sm leading-relaxed text-muted">Walkthru adds the safe config fixes (security headers for your host, llms.txt) on a new branch and explains the rest. You review and merge.</p>
      {state.kind === 'connect' && <p className="mt-4 text-sm"><Link to="/app/settings#github" className="text-ink underline decoration-line underline-offset-4 hover:decoration-ink">Connect GitHub in Settings</Link></p>}
      {state.kind === 'ready' && (state.repos.length === 0 ? (
        <p className="mt-4 text-sm text-muted">The GitHub App has no repositories yet. Add one in the App's settings on GitHub.</p>
      ) : (
        <div className="mt-4 grid gap-4">
          <div className="flex flex-wrap items-center gap-3">
            <label htmlFor="fix-pr-repo" className="sr-only">Repository</label>
            <select id="fix-pr-repo" value={repo} onChange={(e) => { setRepo(e.target.value); setPreview(null) }} className={select}>
              {state.repos.map((r) => <option key={r.full_name} value={r.full_name}>{r.full_name}</option>)}
            </select>
            <button type="button" className={button} disabled={busy || !chosen} onClick={() => run(false)}>{busy && !preview ? 'Checking' : 'Preview changes'}</button>
          </div>
          {preview && !preview.url && (preview.changes.length ? (
            <div className="grid gap-3">
              <ul className="divide-y divide-line rounded-2xl border border-line text-sm">
                {preview.changes.map((c) => (
                  <li key={c.path} className="px-4 py-3"><span className="font-mono text-xs text-ink">{c.path}</span> <span className="text-muted">({c.action}): {c.summary}</span></li>
                ))}
              </ul>
              {preview.left.length > 0 && <p className="text-xs text-muted">{preview.left.length} other finding{preview.left.length === 1 ? '' : 's'} need code or dashboard changes; the pull request lists them.</p>}
              <button type="button" className={`${button} justify-self-start`} disabled={busy}
                onClick={() => window.confirm(`Open a pull request on ${preview.repo} (${preview.changes.length} file${preview.changes.length === 1 ? '' : 's'})? It is a new branch; nothing is merged.`) && run(true)}>
                {busy ? 'Opening' : 'Open pull request'}
              </button>
            </div>
          ) : <p className="text-sm text-muted">Nothing Walkthru can change safely in {preview.repo}: the config fixes are already there, or these findings need code or dashboard changes. Use the fix plan instead.</p>)}
          {preview?.url && <p role="status" className="text-sm text-ink">Pull request opened: <a href={preview.url} target="_blank" rel="noopener noreferrer" className="underline decoration-line underline-offset-4 hover:decoration-ink">{preview.repo} #{preview.number}</a></p>}
        </div>
      ))}
      {error && <p role="alert" className="mt-3 text-sm text-danger">{error}</p>}
    </section>
  )
}
