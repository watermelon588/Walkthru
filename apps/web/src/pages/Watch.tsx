import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import { AppShell } from '../components/AppShell'
import { Snippet } from '../components/DomainVerification'
import { Locked, PageHeader } from '../components/PageHeader'
import { checkSiteNow, createDeployHook, getWatch, unwatchSite, watchSite, type WatchedSite } from '../lib/runs'

type State = { kind: 'loading' } | { kind: 'ready'; sites: WatchedSite[]; plus: boolean; limit: number; email: boolean } | { kind: 'error'; message: string }

const when = (iso: string) => new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
const input = 'w-full rounded-xl border border-line bg-bg px-4 py-3 text-sm text-ink placeholder:text-muted focus:border-ink focus:outline-none'

/** Plus: weekly rechecks and deploy hooks, with an email only when something changed. */
export default function Watch() {
  const [state, setState] = useState<State>({ kind: 'loading' })
  const [site, setSite] = useState('')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<{ text: string; error?: boolean } | null>(null)
  const [hooks, setHooks] = useState<Record<string, string>>({})

  const load = () =>
    getWatch()
      .then((w) => setState({ kind: 'ready', sites: w.sites, plus: w.plan === 'plus', limit: w.limit, email: w.email }))
      .catch((e: Error) => setState({ kind: 'error', message: e.message }))
  useEffect(() => { load() }, [])

  async function run(action: () => Promise<unknown>, done: string) {
    setMsg(null)
    try {
      await action()
      setMsg({ text: done })
      await load()
      window.setTimeout(load, 45_000) // checks take about half a minute; show the result without a manual refresh
    } catch (e) {
      setMsg({ text: e instanceof Error ? e.message : 'That did not work. Try again.', error: true })
    }
  }

  async function add(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const raw = site.trim()
    if (!raw) return setMsg({ text: 'Enter the address of a site you own, like yoursite.com.', error: true })
    setBusy(true)
    await run(() => watchSite(raw.startsWith('http') ? raw : `https://${raw}`), 'Watching. The first check runs now and becomes the baseline.')
    setSite('')
    setBusy(false)
  }

  return (
    <AppShell title="Watch">
      <PageHeader kicker="Plus" title="Weekly watch">
        Walkthru rechecks your sites every week and after each deploy, and tells you only when something changed: a blocked AI crawler, lost structured data, a new security gap or a fix that landed.
      </PageHeader>

      {state.kind === 'loading' && <div aria-busy="true" aria-label="Loading watched sites" className="mt-14 h-40 animate-pulse rounded-2xl bg-surface motion-reduce:animate-none" />}
      {state.kind === 'error' && (
        <div role="alert" className="mt-14 rounded-2xl border border-line px-5 py-5">
          <p className="text-sm text-danger">Could not load your watched sites: {state.message}</p>
          <button type="button" onClick={() => { setState({ kind: 'loading' }); load() }} className="mt-3 text-sm text-ink underline decoration-line underline-offset-4 hover:decoration-ink">Try again</button>
        </div>
      )}
      {state.kind === 'ready' && !state.plus && <Locked>Weekly watch and deploy hooks are part of the Plus plan.</Locked>}
      {state.kind === 'ready' && state.plus && (
        <section aria-labelledby="watch-heading" className="mt-14">
          <div className="grid gap-10 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
            <div>
              <h2 id="watch-heading" className="text-xl font-light">Your watched sites</h2>
              <p className="mt-2 max-w-[48ch] text-sm leading-relaxed text-muted">
                Up to {state.limit} sites. Each check covers SEO, AI search readiness and passive security; journeys still run from the extension.
                {state.email ? ' You get an email when a check finds something new or fixed.' : ' Email alerts start once email delivery is set up; until then, changes show here.'}
              </p>
              <Link to="/docs#watch" className="mt-4 inline-block text-sm text-ink underline decoration-line underline-offset-4 transition hover:decoration-ink">How watch and deploy hooks work</Link>
            </div>

            <div aria-live="polite" className="grid min-w-0 content-start gap-5">
              <form onSubmit={add} className="flex flex-wrap items-end gap-3">
                <label htmlFor="watch-site" className="grid min-w-0 flex-1 gap-2 text-sm text-muted">
                  Site to watch
                  <input id="watch-site" value={site} onChange={(e) => setSite(e.target.value)} placeholder="yoursite.com" disabled={busy || state.sites.length >= state.limit} className={input} />
                </label>
                <button type="submit" disabled={busy || state.sites.length >= state.limit} className="rounded-full bg-ink px-5 py-3 text-sm text-bg transition hover:opacity-85 disabled:opacity-60">
                  {busy ? 'Adding...' : 'Watch'}
                </button>
              </form>
              {msg && <p role={msg.error ? 'alert' : 'status'} className={`text-sm ${msg.error ? 'text-danger' : 'text-muted'}`}>{msg.text}</p>}

              {state.sites.length === 0 ? (
                <p className="text-sm text-muted">No watched sites yet.</p>
              ) : (
                <ul className="border-t border-line">
                  {state.sites.map((s) => {
                    const c = s.last_changes
                    return (
                      <li key={s.id} className="grid gap-3 border-b border-line py-4">
                        <div className="flex flex-wrap items-baseline justify-between gap-3">
                          <span className="min-w-0 truncate font-mono text-xs text-ink">{s.site}</span>
                          <span className="text-xs text-muted">{c ? `Next check ${when(s.next_check_at)}` : 'First check running'}</span>
                        </div>
                        {c && (
                          <p className="text-sm text-muted">
                            {c.baseline ? `Baseline set ${when(c.at)}` : `Checked ${when(c.at)}${c.reason === 'deploy' ? ' after a deploy' : ''}`}
                            {c.score != null && `, score ${c.score}`}
                            {!c.baseline && (c.new.length || c.fixed.length ? `: ${c.new.length} new, ${c.fixed.length} fixed` : ': nothing changed')}
                            {c.new.length > 0 && !c.baseline && <span className="mt-1 block text-danger">New: {c.new.slice(0, 3).join('; ')}{c.new.length > 3 ? ` and ${c.new.length - 3} more` : ''}</span>}
                            {c.fixed.length > 0 && !c.baseline && <span className="mt-1 block text-accent">Fixed: {c.fixed.slice(0, 3).join('; ')}{c.fixed.length > 3 ? ` and ${c.fixed.length - 3} more` : ''}</span>}
                          </p>
                        )}
                        <div className="flex flex-wrap gap-x-4 gap-y-2 text-sm">
                          {s.last_run_id && <Link to={`/app/runs/${s.last_run_id}`} className="text-ink underline decoration-line underline-offset-4 hover:decoration-ink">Open the latest report</Link>}
                          <button type="button" onClick={() => run(() => checkSiteNow(s.id), 'Checking now. The result appears here in about half a minute.')} className="text-muted underline decoration-line underline-offset-4 hover:text-ink">Check now</button>
                          <button type="button" onClick={() => run(async () => { const { url } = await createDeployHook(s.id); setHooks((h) => ({ ...h, [s.id]: url })) }, 'Deploy hook created. Copy it now; it is shown once.')} className="text-muted underline decoration-line underline-offset-4 hover:text-ink">{s.last_hook_at || hooks[s.id] ? 'New deploy hook' : 'Deploy hook'}</button>
                          <button type="button" onClick={() => window.confirm(`Stop watching ${s.site}?`) && run(() => unwatchSite(s.id), 'Stopped watching.')} className="text-muted underline decoration-line underline-offset-4 hover:text-danger">Remove</button>
                        </div>
                        {hooks[s.id] && <Snippet label="Send a POST to this URL after each deploy, for example from a Netlify deploy notification or a CI step (curl -X POST ...). It checks at most once every 10 minutes." value={hooks[s.id]} />}
                      </li>
                    )
                  })}
                </ul>
              )}
            </div>
          </div>
        </section>
      )}
    </AppShell>
  )
}
