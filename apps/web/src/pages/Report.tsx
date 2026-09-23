import { ArrowLeftIcon, DownloadSimpleIcon, EnvelopeSimpleIcon, LinkIcon, PrinterIcon, TrashIcon } from '@phosphor-icons/react'
import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { AppShell } from '../components/AppShell'
import { ReportView } from '../components/ReportView'
import { btnGhost } from '../components/Shared'
import { deleteRun, emailRun, findingsCsv, getRun, shareRun, stopRun, type Run } from '../lib/runs'

type State = { kind: 'loading' } | { kind: 'ready'; run: Run } | { kind: 'missing' } | { kind: 'error'; message: string }

const POLL_MS = 5000

async function copyText(text: string): Promise<boolean> {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      // Clipboard permission can be unavailable in embedded and local contexts.
    }
  }
  const input = document.createElement('textarea')
  input.value = text
  input.setAttribute('readonly', '')
  input.style.position = 'fixed'
  input.style.opacity = '0'
  document.body.appendChild(input)
  input.select()
  const copied = document.execCommand('copy')
  input.remove()
  return copied
}

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
          {state.run.status === 'running' && (
            <EndRunningRun
              run={state.run}
              onStopped={(steps) => setState({ kind: 'ready', run: { ...state.run, status: 'stopped', steps } })}
            />
          )}
          {state.run.report && <Actions run={state.run} onShared={() => setState({ kind: 'ready', run: { ...state.run, public: true } })} />}
          <ReportView run={state.run} />
        </div>
      )}
    </AppShell>
  )
}

function EndRunningRun({ run, onStopped }: { run: Run; onStopped: (steps: Run['steps']) => void }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function end() {
    setBusy(true)
    setError(null)
    try {
      const stopped = await stopRun(run.id)
      onStopped(stopped.steps)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not end this run.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="no-print mb-8 rounded-2xl border border-line bg-surface px-5 py-4">
      <p className="text-sm">This browser session is no longer progressing?</p>
      <p className="mt-1 text-xs leading-relaxed text-muted">End it now to keep its completed steps and generate a partial report.</p>
      <button type="button" onClick={end} disabled={busy} className={`${btnGhost} mt-4`}>
        {busy ? 'Ending run...' : 'End run and build report'}
      </button>
      {error && <p role="alert" className="mt-3 text-xs text-danger">{error}</p>}
    </div>
  )
}

function Actions({ run, onShared }: { run: Run; onShared: () => void }) {
  const navigate = useNavigate()
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
      const copied = await copyText(url)
      return copied ? `Public link copied: ${url}` : `Public link ready: ${url}`
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
      if (sent) return `Sent to ${to}.`
      const subject = `Walkthru report: ${run.site}`
      const body = `Your Walkthru report is ready:\n\n${location.origin}/app/runs/${run.id}`
      location.href = `mailto:${encodeURIComponent(to)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
      return `Email delivery is not configured, so a ready-to-send draft was opened for ${to}.`
    })
  }

  function remove() {
    if (!window.confirm('Delete this run, its report and its screenshots? This cannot be undone.')) return
    return act('delete', async () => {
      await deleteRun(run.id)
      navigate('/app', { replace: true })
      return 'Run deleted.'
    })
  }

  async function savePdf() {
    setBusy('pdf')
    setMsg('Preparing screenshots for the PDF.')
    const expectedFrames = run.steps.filter((step) => step.evidence).length
    const deadline = Date.now() + 8000
    while (expectedFrames > 0 && document.querySelectorAll<HTMLImageElement>('.report-print-frame img').length < expectedFrames && Date.now() < deadline) {
      await new Promise((resolve) => window.setTimeout(resolve, 100))
    }
    const images = [...document.querySelectorAll<HTMLImageElement>('.report-print-frame img')]
    await Promise.all(images.map((image) => image.decode().catch(() => {})))
    setMsg(null)
    setBusy(null)
    window.print()
  }

  return (
    <div className="no-print mb-8 flex flex-wrap items-center gap-2">
      <button type="button" onClick={share} disabled={busy !== null} className={btnGhost}>
        <LinkIcon weight="light" className="size-4" /> {run.public ? 'Copy public link' : 'Share'}
      </button>
      <button type="button" onClick={exportCsv} className={btnGhost}>
        <DownloadSimpleIcon weight="light" className="size-4" /> Export CSV
      </button>
      <button type="button" onClick={savePdf} disabled={busy !== null} className={btnGhost}>
        <PrinterIcon weight="light" className="size-4" /> {busy === 'pdf' ? 'Preparing PDF' : 'Save PDF'}
      </button>
      <button type="button" onClick={email} disabled={busy !== null} className={btnGhost}>
        <EnvelopeSimpleIcon weight="light" className="size-4" /> Email me
      </button>
      <button type="button" onClick={remove} disabled={busy !== null} className={`${btnGhost} text-danger`}>
        <TrashIcon weight="light" className="size-4" /> {busy === 'delete' ? 'Deleting' : 'Delete run'}
      </button>
      {msg && <p role="status" className="basis-full text-xs text-muted">{msg}</p>}
    </div>
  )
}
