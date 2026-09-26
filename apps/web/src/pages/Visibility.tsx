import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { AppShell } from '../components/AppShell'
import { CitationResults } from '../components/CitationResults'
import { Locked, PageHeader } from '../components/PageHeader'
import { btnPrimary } from '../components/Shared'
import { NOTIFICATION_EVENT, type Notification } from '../lib/notifications'
import { checkCitationsNow, editCitationSite, getCitations, getCitationSite, trackCitations, untrackCitations, type CitationLimit, type CitationSite, type CitationView } from '../lib/runs'
import { toast } from '../lib/toast'

type List = { kind: 'loading' } | { kind: 'error'; message: string } | { kind: 'ready'; sites: CitationSite[]; limit: CitationLimit | null }
const input = 'w-full rounded-xl border border-line bg-bg px-4 py-3 text-sm text-ink placeholder:text-muted focus:border-ink focus:outline-none'
const lines = (text: string) => text.split('\n').map((l) => l.trim()).filter(Boolean)

/** AI answers (P3.2): does AI name and cite your site for the questions buyers ask, against your competitors? */
export default function Visibility() {
  const [list, setList] = useState<List>({ kind: 'loading' })
  const [selected, setSelected] = useState<string | null>(null)

  const load = useCallback(() => getCitations()
    .then((r) => {
      setList({ kind: 'ready', sites: r.sites, limit: r.limit })
      setSelected((id) => (id && r.sites.some((s) => s.id === id) ? id : r.sites[0]?.id ?? null))
    })
    .catch((e: Error) => setList({ kind: 'error', message: e.message })), [])
  useEffect(() => { load() }, [load])

  return (
    <AppShell title="AI answers">
      <PageHeader kicker="Paid plans" title="AI answers">
        Ask AI the questions your buyers ask, and see whether it names your site, cites your pages, and how often it picks your competitors instead. It reports what the AI said on the day; nobody can promise a citation.
      </PageHeader>

      {list.kind === 'loading' && <div aria-busy="true" aria-label="Loading tracked sites" className="mt-14 h-40 animate-pulse rounded-2xl bg-surface motion-reduce:animate-none" />}
      {list.kind === 'error' && (
        <div role="alert" className="mt-14 rounded-2xl border border-line px-5 py-5">
          <p className="text-sm text-danger">Could not load your tracked sites: {list.message}</p>
          <button type="button" onClick={() => { setList({ kind: 'loading' }); load() }} className="mt-3 text-sm text-ink underline decoration-line underline-offset-4 hover:decoration-ink">Try again</button>
        </div>
      )}
      {list.kind === 'ready' && !list.limit && <Locked>AI answer tracking is part of the paid plans: Launch Pack checks once, Pro weekly, Plus weekly on two engines.</Locked>}
      {list.kind === 'ready' && list.limit && (
        <div className="mt-14 grid gap-10">
          <nav aria-label="Tracked sites" className="flex flex-wrap items-center gap-2">
            {list.sites.map((s) => (
              <button key={s.id} type="button" onClick={() => setSelected(s.id)} aria-current={selected === s.id ? 'page' : undefined}
                className={`rounded-full border px-4 py-2 font-mono text-xs transition-colors ${selected === s.id ? 'border-ink bg-ink text-bg' : 'border-line text-muted hover:border-ink hover:text-ink'}`}>
                {s.site.replace(/^https?:\/\//, '')}
              </button>
            ))}
            {list.sites.length < (list.limit.sites ?? 1) && (
              <button type="button" onClick={() => setSelected(null)} aria-current={selected === null ? 'page' : undefined}
                className={`rounded-full border border-dashed px-4 py-2 text-xs transition-colors ${selected === null ? 'border-ink text-ink' : 'border-line text-muted hover:text-ink'}`}>
                + Track a site
              </button>
            )}
          </nav>
          {selected ? <SiteView key={selected} id={selected} onRemoved={load} /> : <AddSite limit={list.limit} onAdded={(id) => { load(); setSelected(id) }} />}
        </div>
      )}
    </AppShell>
  )
}

function AddSite({ limit, onAdded }: { limit: CitationLimit; onAdded: (id: string) => void }) {
  const [site, setSite] = useState('')
  const [rivals, setRivals] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const raw = site.trim()
    if (!raw) return setError('Enter the address of your site, like yoursite.com.')
    setBusy(true)
    setError(null)
    try {
      const view = await trackCitations(raw.startsWith('http') ? raw : `https://${raw}`, lines(rivals))
      toast({ title: 'Tracking started', body: `${view.prompts.length} prompts suggested from your homepage. Edit them any time.` })
      onAdded(view.site.id)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not start tracking.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="grid max-w-2xl gap-5">
      <p className="text-sm leading-relaxed text-muted">
        Up to {limit.prompts} prompts per site, {limit.weekly ? 'checked every week' : 'checked once'}. We suggest prompts from your homepage; you can change every one.
      </p>
      <label htmlFor="cite-site" className="grid gap-2 text-sm text-muted">
        Your site
        <input id="cite-site" value={site} onChange={(e) => setSite(e.target.value)} placeholder="yoursite.com" className={input} />
      </label>
      <label htmlFor="cite-rivals" className="grid gap-2 text-sm text-muted">
        Competitors, one per line (optional, up to 5)
        <textarea id="cite-rivals" rows={4} value={rivals} onChange={(e) => setRivals(e.target.value)} placeholder={'Notion (notion.so)\ncoda.io'} className={input} />
      </label>
      <div className="flex flex-wrap items-center gap-4">
        <button type="submit" disabled={busy} className={`${btnPrimary} disabled:opacity-60`}>{busy ? 'Reading your homepage...' : 'Start tracking'}</button>
        {error && <p role="alert" className="text-sm text-danger">{error}</p>}
      </div>
    </form>
  )
}

function SiteView({ id, onRemoved }: { id: string; onRemoved: () => void }) {
  const [view, setView] = useState<CitationView | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState(false)

  const load = useCallback(() => getCitationSite(id).then(setView).catch((e: Error) => setError(e.message)), [id])
  useEffect(() => { load() }, [load])
  // Answers arrive one at a time; refresh while some are waiting, and when the "done" notification lands.
  const queued = view?.status.queued ?? 0
  useEffect(() => {
    if (!queued) return
    const timer = window.setInterval(load, 30_000)
    return () => window.clearInterval(timer)
  }, [queued, load])
  useEffect(() => {
    const onNote = (e: Event) => { if ((e as CustomEvent<Notification>).detail?.section === 'visibility') load() }
    window.addEventListener(NOTIFICATION_EVENT, onNote)
    return () => window.removeEventListener(NOTIFICATION_EVENT, onNote)
  }, [load])

  async function act(run: () => Promise<unknown>, done: string) {
    try {
      await run()
      toast({ title: done })
      await load()
    } catch (e) {
      toast({ title: e instanceof Error ? e.message : 'That did not work. Try again.', tone: 'danger' })
    }
  }

  if (error) return <p role="alert" className="text-sm text-danger">Could not load this site: {error}</p>
  if (!view) return <div aria-busy="true" aria-label="Loading answers" className="h-40 animate-pulse rounded-2xl bg-surface motion-reduce:animate-none" />

  return (
    <section aria-labelledby="site-heading">
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-line pb-6">
        <div>
          <h2 id="site-heading" className="text-2xl font-extralight tracking-tight">{view.site.brand}</h2>
          <p className="mt-1 text-sm text-muted">
            {view.prompts.length} prompts{view.site.competitors.length ? ` against ${view.site.competitors.map((c) => c.name).join(', ')}` : ', no competitors yet'}
          </p>
        </div>
        <div className="flex flex-wrap gap-x-4 gap-y-2 text-sm">
          <button type="button" onClick={() => act(async () => { const r = await checkCitationsNow(id); return r }, 'Checking now. Answers arrive over the next minutes.')} disabled={queued > 0}
            className="text-ink underline decoration-line underline-offset-4 hover:decoration-ink disabled:text-muted disabled:no-underline">Check now</button>
          <button type="button" onClick={() => setEditing((v) => !v)} aria-expanded={editing} className="text-muted underline decoration-line underline-offset-4 hover:text-ink">
            {editing ? 'Close setup' : 'Prompts and competitors'}
          </button>
          <button type="button" onClick={() => window.confirm(`Stop tracking ${view.site.site}? Its answers are deleted.`) && act(async () => { await untrackCitations(id); onRemoved() }, 'Stopped tracking.')}
            className="text-muted underline decoration-line underline-offset-4 hover:text-danger">Remove</button>
        </div>
      </div>
      {editing && <Setup view={view} onSaved={(v) => { setView(v); setEditing(false) }} />}
      <CitationResults view={view} />
    </section>
  )
}

function Setup({ view, onSaved }: { view: CitationView; onSaved: (v: CitationView) => void }) {
  const [brand, setBrand] = useState(view.site.brand)
  const [rivals, setRivals] = useState(view.site.competitors.map((c) => (c.domain ? `${c.name} (${c.domain})` : c.name)).join('\n'))
  const [prompts, setPrompts] = useState(view.prompts.map((p) => p.prompt).join('\n'))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const max = view.limit?.prompts ?? 10
  const count = lines(prompts).length

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      onSaved(await editCitationSite(view.site.id, { brand: brand.trim(), competitors: lines(rivals), prompts: lines(prompts) }))
      toast({ title: 'Saved. The next check uses these prompts.' })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not save.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={save} className="mt-6 grid max-w-3xl gap-5 rounded-2xl border border-line p-5">
      <label htmlFor="cite-brand" className="grid gap-2 text-sm text-muted">
        Your brand name, as people write it
        <input id="cite-brand" value={brand} onChange={(e) => setBrand(e.target.value)} maxLength={80} required className={input} />
      </label>
      <label htmlFor="cite-edit-rivals" className="grid gap-2 text-sm text-muted">
        Competitors, one per line, with their domain in brackets to count citations
        <textarea id="cite-edit-rivals" rows={4} value={rivals} onChange={(e) => setRivals(e.target.value)} placeholder="Notion (notion.so)" className={input} />
      </label>
      <label htmlFor="cite-prompts" className="grid gap-2 text-sm text-muted">
        <span className="flex justify-between"><span>Prompts, one per line</span><span className={`tabular-nums ${count > max ? 'text-danger' : ''}`}>{count} of {max}</span></span>
        <textarea id="cite-prompts" rows={8} value={prompts} onChange={(e) => setPrompts(e.target.value)} className={input} />
      </label>
      <div className="flex flex-wrap items-center gap-4">
        <button type="submit" disabled={busy || count > max || count === 0} className={`${btnPrimary} disabled:opacity-60`}>{busy ? 'Saving...' : 'Save'}</button>
        {error && <p role="alert" className="text-sm text-danger">{error}</p>}
      </div>
    </form>
  )
}
