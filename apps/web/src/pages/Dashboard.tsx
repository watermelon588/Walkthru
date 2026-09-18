import { PlugsConnectedIcon } from '@phosphor-icons/react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { AppShell } from '../components/AppShell'
import { StatusPill } from '../components/ReportView'
import { btnGhost, ScanForm } from '../components/Shared'
import { useSession } from '../lib/auth'
import { listRuns, PERSONA_LABEL, timeAgo, type Run } from '../lib/runs'

type Runs = { kind: 'loading' } | { kind: 'ready'; runs: Run[] } | { kind: 'error'; message: string }

const extensionId = import.meta.env.VITE_EXTENSION_ID as string | undefined

export default function Dashboard() {
  const [runs, setRuns] = useState<Runs>({ kind: 'loading' })

  useEffect(() => {
    listRuns()
      .then((r) => setRuns({ kind: 'ready', runs: r }))
      .catch((e: Error) => setRuns({ kind: 'error', message: e.message }))
  }, [])

  return (
    <AppShell>
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <h1 className="text-4xl font-extralight tracking-tight md:text-5xl">Your test runs</h1>
          <p className="mt-3 max-w-[52ch] leading-relaxed text-muted">Every run the extension finishes lands here with the test user's think-aloud log.</p>
        </div>
        <ConnectExtension />
      </div>

      <section aria-label="Instant Scan" className="mt-10 rounded-2xl border border-line px-5 py-5 md:px-6">
        <h2 className="text-lg font-light">Instant Scan</h2>
        <p className="mt-1 mb-4 text-sm text-muted">First impression, SEO basics and security headers for any homepage. No extension needed.</p>
        <ScanForm />
      </section>

      <section aria-label="Runs" className="mt-12">
        {runs.kind === 'loading' && (
          <div aria-busy="true" aria-label="Loading runs" className="grid gap-px overflow-hidden rounded-2xl bg-line">
            {[0, 1, 2].map((i) => <div key={i} className="h-16 animate-pulse bg-surface motion-reduce:animate-none" />)}
          </div>
        )}
        {runs.kind === 'error' && (
          <p role="alert" className="text-sm text-danger">Could not load runs: {runs.message}</p>
        )}
        {runs.kind === 'ready' && runs.runs.length === 0 && (
          <div role="status" className="rounded-2xl bg-surface px-6 py-12 text-center">
            <p className="text-lg font-light">No runs yet.</p>
            <p className="mx-auto mt-2 max-w-[44ch] text-sm leading-relaxed text-muted">
              Connect the extension, open the site you want tested, click the Walkthru bird in the toolbar and start a test.
            </p>
          </div>
        )}
        {runs.kind === 'ready' && runs.runs.length > 0 && (
          <ol className="grid gap-px overflow-hidden rounded-2xl bg-line">
            {runs.runs.map((r) => (
              <li key={r.id} className="bg-bg">
                <Link to={`/app/runs/${r.id}`} className="grid gap-1 px-5 py-4 transition-colors hover:bg-surface sm:grid-cols-[1fr_auto] sm:items-center sm:gap-4">
                  <div className="min-w-0">
                    <p className="truncate">{r.kind === 'scan' ? 'Instant Scan' : r.goal}</p>
                    <p className="mt-0.5 truncate font-mono text-xs text-muted">{r.site}</p>
                  </div>
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted sm:justify-end">
                    <span>{r.kind === 'scan' ? 'Instant Scan' : PERSONA_LABEL[r.persona] ?? r.persona}</span>
                    {r.kind === 'test' && <StatusPill status={r.status} />}
                    <time dateTime={r.created_at}>{timeAgo(r.created_at)}</time>
                  </div>
                </Link>
              </li>
            ))}
          </ol>
        )}
      </section>
    </AppShell>
  )
}


/** Hands the current session to the extension so it can call the API as you. Only the extension we name receives it. */
function ConnectExtension() {
  const { session } = useSession()
  const [msg, setMsg] = useState<string | null>(null)

  function connect() {
    const runtime = (window as unknown as { chrome?: { runtime?: { sendMessage: (id: string, msg: unknown, cb: (r: unknown) => void) => void; lastError?: { message: string } } } }).chrome?.runtime
    if (!extensionId) return setMsg('Set VITE_EXTENSION_ID in apps/web/.env to the id shown on chrome://extensions.')
    if (!runtime?.sendMessage || !session) return setMsg('Open this page in Chrome with the Walkthru extension installed.')
    const { access_token, refresh_token, expires_at } = session
    runtime.sendMessage(extensionId, { type: 'session', session: { access_token, refresh_token, expires_at } }, () => {
      setMsg(runtime.lastError ? 'Extension not found. Is it installed and enabled?' : 'Extension connected. Open a site and click the bird.')
    })
  }

  return (
    <div className="flex flex-col items-start gap-2">
      <button type="button" onClick={connect} className={btnGhost}>
        <PlugsConnectedIcon weight="light" className="size-4" /> Connect extension
      </button>
      {msg && <p role="status" className="max-w-[40ch] text-xs leading-relaxed text-muted">{msg}</p>}
    </div>
  )
}
