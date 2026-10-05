import { PlugsConnectedIcon } from '@phosphor-icons/react'
import { useLayoutEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router'
import { AgentPresence, type AgentPresenceState } from '../components/AgentPresence'
import { AppShell } from '../components/AppShell'
import { ReadinessPipeline } from '../components/ReadinessPipeline'
import { Skeleton } from '../components/Loading'
import { PlanMeter } from '../components/PlanMeter'
import { btnGhost, ScanForm } from '../components/Shared'
import { connectExtension } from '../lib/extension'
import { useSession } from '../lib/auth'
import { authSessionId } from '../lib/sessionHandoff'
import { stopRun, type RunSummary } from '../lib/runs'
import { useRunHistory } from '../lib/useRunHistory'
import { accountIdentity } from '../lib/planCache'
import { RunHistoryPanel } from '../components/RunHistoryPanel'



export default function Dashboard() {
  const { session } = useSession()
  const identity = accountIdentity(session)
  const currentIdentity = useRef(identity)
  useLayoutEffect(() => { currentIdentity.current = identity }, [identity])
  const history = useRunHistory(identity)
  const runs = history.state
  const [scoutOpen, setScoutOpen] = useState(false)
  const [runAction, setRunAction] = useState<{ identity: string; id: string | null; error: string | null } | null>(null)
  const endingRun = runAction?.identity === identity ? runAction.id : null
  const runActionError = runAction?.identity === identity ? runAction.error : null
  const navigate = useNavigate()


  const agentState: AgentPresenceState = runs.kind === 'error'
    ? 'stopped'
    : runs.kind === 'loading'
      ? 'observing'
      : runs.runs.length > 0
        ? 'complete'
        : 'ready'
  const agentActivity = runs.kind === 'error'
    ? 'Could not read your runs'
    : runs.kind === 'loading'
      ? 'Reading your recent runs'
      : runs.runs.length > 0
        ? 'Watching your recent runs'
        : 'Ready for your first test'

  async function endRun(run: RunSummary) {
    setRunAction({ identity, id: run.id, error: null })
    try {
      await stopRun(run.id)
      if (currentIdentity.current === identity) navigate(`/app/runs/${run.id}`)
    } catch (error) {
      if (currentIdentity.current === identity) setRunAction({ identity, id: null, error: error instanceof Error ? error.message : 'Could not end this run.' })
    } finally {
      setRunAction((state) => state?.identity === identity ? { ...state, id: null } : state)
    }
  }

  return (
    <AppShell title="Runs">
      <div className="grid gap-8 border-b border-line pb-10 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Workspace overview</p>
          <h1 className="mt-3 max-w-[12ch] text-4xl font-extralight tracking-[-0.035em] md:text-6xl">Launch with evidence, not guesses.</h1>
          <p className="mt-4 max-w-[58ch] leading-relaxed text-muted">Scout follows a real journey, saves the important screens, checks launch basics and turns everything into one report your team can act on.</p>
        </div>
        <div className="flex flex-col items-start gap-4 md:items-end">
          <AgentPresence
            activity={agentActivity}
            state={agentState}
            phase={0.24}
            onActivate={() => setScoutOpen((value) => !value)}
            actionLabel="Ask Scout what to do next"
            expanded={scoutOpen}
          />
          {scoutOpen && (
            <p role="status" className="max-w-[34ch] text-sm leading-relaxed text-muted md:text-right">
              Open the site you want tested, connect the extension, then start a goal. I will keep the journey safe and bring the evidence back here.
            </p>
          )}
          <ConnectExtension />
        </div>
      </div>

      <PlanMeter />

      {runs.kind === 'ready' && <ReadinessPipeline runs={runs.runs} />}
      {runs.kind === 'loading' && (
        <div role="status" aria-busy="true" aria-label="Loading launch readiness" className="mt-10">
          <Skeleton className="h-6 w-64" />
          <div className="mt-5 grid gap-px overflow-hidden rounded-2xl border border-line bg-line sm:grid-cols-2 lg:grid-cols-4">
            {[0, 1, 2, 3].map((i) => <div key={i} className="grid gap-3 bg-bg px-5 py-5"><Skeleton className="ml-auto h-5 w-8" /><Skeleton className="mt-4 h-3.5 w-3/4" /><Skeleton className="h-3 w-1/2" /></div>)}
          </div>
        </div>
      )}

      <section aria-label="Instant Scan" className="mt-12 grid gap-5 border-y border-line py-6 md:grid-cols-[minmax(0,0.7fr)_minmax(20rem,1.3fr)] md:items-end">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Fast path</p>
          <h2 className="mt-2 text-2xl font-light">Scan a homepage now</h2>
          <p className="mt-2 text-sm leading-relaxed text-muted">First impression, SEO basics and passive security headers. No extension needed.</p>
        </div>
        <ScanForm />
      </section>

      <RunHistoryPanel runs={runs} refresh={history.refresh} more={history.more} endRun={endRun} endingRun={endingRun} runActionError={runActionError} />
    </AppShell>
  )
}


/** Hands the current session to the extension so it can call the API as you. Only the extension we name receives it. */
function ConnectExtension() {
  const { session } = useSession()
  const identity = `${session?.user.id ?? ''}:${authSessionId(session?.access_token ?? '') ?? session?.access_token ?? ''}`
  const [feedback, setFeedback] = useState<{ identity: string; message: string } | null>(null)
  const msg = feedback?.identity === identity ? feedback.message : null
  const [busy, setBusy] = useState(false)

  async function connect() {
    setBusy(true)
    try {
      setFeedback({ identity, message: await connectExtension() ? 'Extension connected. Open a site and click the bird.'
        : 'Could not connect. Open Chrome, reload the current Walkthru extension, then sign in and try again.' })
    } catch { setFeedback({ identity, message: 'Could not connect. Sign in and try again.' }) }
    finally { setBusy(false) }
  }

  return (
    <div className="flex flex-col items-start gap-2">
      <button type="button" onClick={connect} disabled={busy} className={btnGhost}>
        <PlugsConnectedIcon weight="light" className="size-4" /> {busy ? 'Connecting' : 'Connect extension'}
      </button>
      {msg && <p role="status" className="max-w-[40ch] text-xs leading-relaxed text-muted">{msg}</p>}
    </div>
  )
}
