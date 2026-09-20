import { ArrowLeftIcon, DownloadSimpleIcon, EnvelopeSimpleIcon, LinkIcon, PrinterIcon } from '@phosphor-icons/react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'
import { AppShell } from '../components/AppShell'
import { ReportView } from '../components/ReportView'
import { btnGhost } from '../components/Shared'
import { emailRun, findingsCsv, getRun, shareRun, type Run } from '../lib/runs'

type State = { kind: 'loading' } | { kind: 'ready'; run: Run } | { kind: 'missing' } | { kind: 'error'; message: string }

const POLL_MS = 5000

export default function Report() {
  const { id = '' } = useParams()
  const [state, setState] = useState<State>({ kind: 'loading' })

  useEffect(() => {
    let timer: number | undefined
    const load = () =>
      getRun(id)
        .then((run) => {
          setState(run ? { kind: 'ready', run } : { kind: 'missing' })
          // Keep polling while the run is in progress or the report is still being written.
          if (run && (run.status === 'running' || !run.report)) timer = window.setTimeout(load, POLL_MS)
        })
        .catch((e: Error) => setState({ kind: 'error', message: e.message }))
    load()
    return () => window.clearTimeout(timer)
  }, [id])

  return (
    <AppShell>
      <Link to="/app" className="no-print inline-flex items-center gap-1.5 text-sm text-muted hover:text-ink">
        <ArrowLeftIcon className="size-4" /> All runs
      </Link>

      {state.kind === 'loading' && <div aria-busy="true" aria-label="Loading run" className="mt-8 h-24 animate-pulse rounded-2xl bg-surface motion-reduce:animate-none" />}
      {state.kind === 'missing' && <p role="status" className="mt-8 text-muted">This run does not exist or belongs to another account.</p>}
      {state.kind === 'error' && <p role="alert" className="mt-8 text-sm text-danger">Could not load the run: {state.message}</p>}

      {state.kind === 'ready' && (
        <div className="mt-6">
          {state.run.report && <Actions run={state.run} onShared={() => setState({ kind: 'ready', run: { ...state.run, public: true } })} />}
          <ReportView run={state.run} />
        </div>
      )}
    </AppShell>
  )
}

function Actions({ run, onShared }: { run: Run; onShared: () => void }) {
  const [msg, setMsg] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)

  async function act(name: string, fn: () => Promise<string>) {
    setBusy(name)
    try {
      setMsg(await fn())
    } catch (e) {
      setMsg(e instanceof Error ? e.message : 'Something went wrong.')
    } finally {
      setBusy(null)
    }
  }

  function share() {
    return act('share', async () => {
      const { url } = await shareRun(run.id)
      onShared()
      await navigator.clipboard?.writeText(url).catch(() => {})
      return `Public link copied: ${url}`
    })
  }

  function exportCsv() {
    const blob = new Blob([findingsCsv(run)], { type: 'text/csv' })
    const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: `walkthru-${run.id.slice(0, 8)}.csv` })
    a.click()
    URL.revokeObjectURL(a.href)
    setMsg('CSV downloaded. Import it into Google Sheets with File, Import.')
  }

  function email() {
    return act('email', async () => {
      const { sent, to } = await emailRun(run.id)
      return sent ? `Sent to ${to}.` : 'Email is not configured on the server yet.'
    })
  }

  return (
    <div className="no-print mb-8 flex flex-wrap items-center gap-2">
      <button type="button" onClick={share} disabled={busy !== null} className={btnGhost}>
        <LinkIcon weight="light" className="size-4" /> {run.public ? 'Copy public link' : 'Share'}
      </button>
      <button type="button" onClick={exportCsv} className={btnGhost}>
        <DownloadSimpleIcon weight="light" className="size-4" /> Export CSV
      </button>
      <button type="button" onClick={() => window.print()} className={btnGhost}>
        <PrinterIcon weight="light" className="size-4" /> Save PDF
      </button>
      <button type="button" onClick={email} disabled={busy !== null} className={btnGhost}>
        <EnvelopeSimpleIcon weight="light" className="size-4" /> Email me
      </button>
      {msg && <p role="status" className="basis-full text-xs text-muted">{msg}</p>}
    </div>
  )
}
