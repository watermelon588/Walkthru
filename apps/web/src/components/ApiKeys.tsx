import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import { createApiKey, getPlan, listApiKeys, MCP_URL, revokeApiKey, type ApiKey } from '../lib/runs'
import { Snippet } from './DomainVerification'

type State = { kind: 'loading' } | { kind: 'locked' } | { kind: 'ready'; keys: ApiKey[] } | { kind: 'error'; message: string }

const day = (iso: string) => new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })

/** Personal API keys for the Walkthru MCP server (Plus). Same layout as "Verify your domain" above it. */
export function ApiKeys() {
  const [state, setState] = useState<State>({ kind: 'loading' })
  const [name, setName] = useState('')
  const [created, setCreated] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = () =>
    getPlan()
      .then((plan) => (plan.plan === 'plus' ? listApiKeys().then((keys) => setState({ kind: 'ready', keys })) : setState({ kind: 'locked' })))
      .catch((e: Error) => setState({ kind: 'error', message: e.message }))
  useEffect(() => { load() }, [])

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!name.trim()) return setError('Give the key a name, like the editor or computer it is for.')
    setBusy(true)
    setError(null)
    try {
      const made = await createApiKey(name.trim())
      setCreated(made.key)
      setName('')
      await load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not create the key.')
    } finally {
      setBusy(false)
    }
  }

  async function revoke(key: ApiKey) {
    if (!window.confirm(`Revoke "${key.name}"? Editors using it stop working at once.`)) return
    setError(null)
    try {
      await revokeApiKey(key.id)
      await load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not revoke the key.')
    }
  }

  return (
    <section id="mcp" aria-labelledby="mcp-heading" className="mt-14 scroll-mt-24 border-t border-line pt-10">
      <div className="grid gap-10 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
        <div>
          <h2 id="mcp-heading" className="text-xl font-light">API keys and MCP</h2>
          <p className="mt-2 max-w-[48ch] text-sm leading-relaxed text-muted">
            Let Claude Code, Cursor or any MCP client scan your site, read reports and pull the fix prompt without leaving the editor. Each key is shown once; revoke it here any time.
          </p>
          <Link to="/docs#mcp" className="mt-4 inline-block text-sm text-ink underline decoration-line underline-offset-4 transition hover:decoration-ink">How to connect your editor</Link>
        </div>

        <div aria-live="polite" className="min-w-0">
          {state.kind === 'loading' && <div aria-busy="true" aria-label="Loading your API keys" className="h-40 animate-pulse rounded-2xl bg-surface motion-reduce:animate-none" />}
          {state.kind === 'error' && (
            <div role="alert" className="rounded-2xl border border-line px-5 py-5">
              <p className="text-sm text-danger">Could not load your API keys: {state.message}</p>
              <button type="button" onClick={() => { setState({ kind: 'loading' }); load() }} className="mt-3 text-sm text-ink underline decoration-line underline-offset-4 hover:decoration-ink">Try again</button>
            </div>
          )}
          {state.kind === 'locked' && (
            <div className="rounded-2xl border border-line px-5 py-5">
              <p className="text-sm text-ink">The Walkthru MCP server is part of the Plus plan.</p>
              <p className="mt-1 text-sm text-muted">Plus opens after launch. <Link to="/#pricing" className="text-ink underline decoration-line underline-offset-4 hover:decoration-ink">See the plans</Link></p>
            </div>
          )}
          {state.kind === 'ready' && (
            <div className="grid gap-5">
              {created && (
                <div className="grid gap-4 rounded-2xl border border-line px-5 py-5">
                  <p className="text-sm text-ink">Copy your key now. It will not be shown again.</p>
                  <Snippet label="Your new API key" value={created} />
                  <Snippet label="Claude Code: run this in your project" value={`claude mcp add --transport http walkthru ${MCP_URL} --header "Authorization: Bearer ${created}"`} />
                  <Snippet label="Cursor: add this to .cursor/mcp.json" value={JSON.stringify({ mcpServers: { walkthru: { url: MCP_URL, headers: { Authorization: `Bearer ${created}` } } } })} />
                </div>
              )}

              <form onSubmit={create} className="flex flex-wrap items-end gap-3">
                <label htmlFor="key-name" className="grid min-w-0 flex-1 gap-2 text-sm text-muted">
                  Key name
                  <input id="key-name" value={name} onChange={(e) => setName(e.target.value)} maxLength={60} placeholder="Cursor on my laptop" disabled={busy}
                    className="w-full rounded-xl border border-line bg-bg px-4 py-3 text-sm text-ink placeholder:text-muted focus:border-ink focus:outline-none" />
                </label>
                <button type="submit" disabled={busy} className="rounded-full bg-ink px-5 py-3 text-sm text-bg transition hover:opacity-85 disabled:opacity-60">
                  {busy ? 'Creating...' : 'Create key'}
                </button>
              </form>
              {error && <p role="alert" className="text-sm text-danger">{error}</p>}

              {state.keys.length === 0 ? (
                <p className="text-sm text-muted">No keys yet.</p>
              ) : (
                <ul className="border-t border-line">
                  {state.keys.map((k) => (
                    <li key={k.id} className="flex flex-wrap items-center justify-between gap-3 border-b border-line py-3">
                      <span className="min-w-0">
                        <span className="block truncate text-sm text-ink">{k.name}</span>
                        <span className="block text-xs text-muted">Created {day(k.created_at)}, {k.last_used_at ? `last used ${day(k.last_used_at)}` : 'never used'}</span>
                      </span>
                      <button type="button" onClick={() => revoke(k)} className="text-sm text-muted underline decoration-line underline-offset-4 transition hover:text-danger hover:decoration-danger">Revoke</button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
