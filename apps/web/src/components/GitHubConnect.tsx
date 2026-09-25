import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { connectGitHub, disconnectGitHub, getGitHub, type GitHubStatus } from '../lib/runs'
import { btnPrimary } from './Shared'

type State = { kind: 'loading' } | { kind: 'ready'; status: GitHubStatus } | { kind: 'error'; message: string }

/** Plus: connect the Walkthru GitHub App so a report can open a fix pull request (P4.4). GitHub sends the owner back
 *  here with ?installation_id, code and state; the API checks them before anything is stored. */
export function GitHubConnect() {
  const [state, setState] = useState<State>({ kind: 'loading' })
  const [msg, setMsg] = useState<{ text: string; error?: boolean } | null>(null)

  const load = () => getGitHub().then((status) => setState({ kind: 'ready', status })).catch((e: Error) => setState({ kind: 'error', message: e.message }))
  useEffect(() => {
    const q = new URLSearchParams(window.location.search)
    const id = Number(q.get('installation_id'))
    const code = q.get('code')
    const st = q.get('state')
    if (id && code && st) {
      window.history.replaceState(null, '', `${window.location.pathname}#github`)  // the code is single use; keep it out of history
      connectGitHub(id, code, st)
        .then((r) => setMsg({ text: `Connected GitHub (${r.account}).` }))
        .catch((e: Error) => setMsg({ text: e.message, error: true }))
        .finally(load)
    } else {
      load()
    }
  }, [])

  async function disconnect(id: number, account: string) {
    if (!window.confirm(`Disconnect ${account}? Walkthru forgets it now. To revoke the App on GitHub too, uninstall it under your GitHub settings, Applications.`)) return
    try {
      await disconnectGitHub(id)
      setMsg({ text: `Disconnected ${account}.` })
      load()
    } catch (e) {
      setMsg({ text: e instanceof Error ? e.message : 'Could not disconnect.', error: true })
    }
  }

  return (
    <section id="github" aria-labelledby="github-heading" className="mt-14 scroll-mt-24 border-t border-line pt-10">
      <div className="grid gap-10 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
        <div>
          <h2 id="github-heading" className="text-xl font-light">GitHub fix pull requests</h2>
          <p className="mt-2 max-w-[48ch] text-sm leading-relaxed text-muted">
            Connect the Walkthru GitHub App to the repositories you choose. From a report you can then open a pull request with the safe config fixes (security headers, llms.txt). You review and merge it; Walkthru never merges and never stores a GitHub token.
          </p>
        </div>
        <div aria-live="polite" className="grid min-w-0 content-start gap-4">
          {state.kind === 'loading' && <div aria-busy="true" aria-label="Loading GitHub" className="h-24 animate-pulse rounded-2xl bg-surface motion-reduce:animate-none" />}
          {state.kind === 'error' && <p role="alert" className="text-sm text-danger">Could not load GitHub: {state.message}</p>}
          {state.kind === 'ready' && !state.status.plus && (
            <div className="rounded-2xl border border-line px-5 py-5">
              <p className="text-sm text-ink">Fix pull requests are part of the Plus plan.</p>
              <p className="mt-1 text-sm text-muted"><Link to="/#pricing" className="text-ink underline decoration-line underline-offset-4 hover:decoration-ink">See the plans</Link></p>
            </div>
          )}
          {state.kind === 'ready' && state.status.plus && !state.status.configured && (
            <p className="rounded-2xl border border-line px-5 py-4 text-sm text-muted">The GitHub App is not set up on this server yet.</p>
          )}
          {state.kind === 'ready' && state.status.plus && state.status.configured && (
            <>
              {state.status.installations.length > 0 ? (
                <ul className="divide-y divide-line rounded-2xl border border-line">
                  {state.status.installations.map((i) => (
                    <li key={i.id} className="flex items-center justify-between gap-4 px-5 py-4">
                      <span className="text-sm text-ink">{i.account || `Installation ${i.id}`}</span>
                      <button type="button" onClick={() => disconnect(i.id, i.account)} className="text-xs text-muted underline decoration-line underline-offset-4 hover:text-danger">Disconnect</button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="rounded-2xl border border-line px-5 py-4 text-sm text-muted">No GitHub account connected yet.</p>
              )}
              {state.status.install_url && (
                <a href={state.status.install_url} className={`${btnPrimary} justify-self-start`}>{state.status.installations.length ? 'Connect another account' : 'Connect GitHub'}</a>
              )}
            </>
          )}
          {msg && <p role={msg.error ? 'alert' : 'status'} className={`text-sm ${msg.error ? 'text-danger' : 'text-muted'}`}>{msg.text}</p>}
        </div>
      </div>
    </section>
  )
}
