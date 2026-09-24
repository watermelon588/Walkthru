import { PlugsConnectedIcon } from '@phosphor-icons/react'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { AgentPresence, type AgentPresenceState } from '../components/AgentPresence'
import { AppShell } from '../components/AppShell'
import { ReadinessPipeline } from '../components/ReadinessPipeline'
import { StatusPill } from '../components/ReportView'
import { btnGhost, ScanForm } from '../components/Shared'
import { useSession } from '../lib/auth'
import { getPlan, listRuns, PERSONA_LABEL, stopRun, timeAgo, type PlanSummary, type Run } from '../lib/runs'

type Runs = { kind: 'loading' } | { kind: 'ready'; runs: Run[] } | { kind: 'error'; message: string }

const extensionId = import.meta.env.VITE_EXTENSION_ID as string | undefined

const firstRun = [
  { title: 'Install the extension', body: 'Add Walkthru to Chrome and pin the bird to your toolbar.', link: 'How to install', href: '/docs#install' },
  { title: 'Connect it', body: 'Use Connect extension above so tests run as you.', link: 'Why it is safe', href: '/security#extension' },
  { title: 'Start a test', body: 'Open your site, click the bird and give the test user one goal.', link: 'Write a good goal', href: '/docs#goals' },
]

export default function Dashboard() {
  const [runs, setRuns] = useState<Runs>({ kind: 'loading' })
  const [scoutOpen, setScoutOpen] = useState(false)
  const [endingRun, setEndingRun] = useState<string | null>(null)
  const [runActionError, setRunActionError] = useState<string | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    listRuns()
      .then((r) => setRuns({ kind: 'ready', runs: r }))
      .catch((e: Error) => setRuns({ kind: 'error', message: e.message }))
  }, [])

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

  async function endRun(run: Run) {
    setEndingRun(run.id)
    setRunActionError(null)
    try {
      const stopped = await stopRun(run.id)
      setRuns((state) => state.kind === 'ready'
        ? { kind: 'ready', runs: state.runs.map((item) => item.id === run.id ? { ...item, status: 'stopped', steps: stopped.steps } : item) }
        : state)
      navigate(`/app/runs/${run.id}`)
    } catch (error) {
      setRunActionError(error instanceof Error ? error.message : 'Could not end this run.')
    } finally {
      setEndingRun(null)
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
          <PlanLine />
        </div>
      </div>

      {runs.kind === 'ready' && <ReadinessPipeline runs={runs.runs} />}
      {runs.kind === 'loading' && <div aria-busy="true" aria-label="Loading launch readiness" className="mt-10 h-36 animate-pulse rounded-2xl bg-surface motion-reduce:animate-none" />}

      <section aria-label="Instant Scan" className="mt-12 grid gap-5 border-y border-line py-6 md:grid-cols-[minmax(0,0.7fr)_minmax(20rem,1.3fr)] md:items-end">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Fast path</p>
          <h2 className="mt-2 text-2xl font-light">Scan a homepage now</h2>
          <p className="mt-2 text-sm leading-relaxed text-muted">First impression, SEO basics and passive security headers. No extension needed.</p>
        </div>
        <ScanForm />
      </section>

      <section aria-labelledby="recent-runs-title" className="mt-14">
        <div className="mb-5 flex items-end justify-between gap-4">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">History</p>
            <h2 id="recent-runs-title" className="mt-2 text-2xl font-light tracking-tight">Recent runs</h2>
          </div>
          {runs.kind === 'ready' && <span className="font-mono text-xs text-muted">{runs.runs.length} total</span>}
        </div>
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
            <ol className="mx-auto mt-8 grid max-w-3xl gap-px overflow-hidden rounded-2xl bg-line text-left sm:grid-cols-3">
              {firstRun.map((s, i) => (
                <li key={s.title} className="flex flex-col bg-bg px-5 py-5">
                  <span className="grid size-6 place-items-center rounded-full border border-line font-mono text-[11px] text-muted">{i + 1}</span>
                  <h3 className="mt-4 text-sm font-medium">{s.title}</h3>
                  <p className="mt-1 flex-1 text-xs leading-relaxed text-muted">{s.body}</p>
                  <Link to={s.href} className="mt-4 self-start text-xs text-ink underline decoration-line underline-offset-4 transition hover:decoration-ink">{s.link}</Link>
                </li>
              ))}
            </ol>
          </div>
        )}
        {runs.kind === 'ready' && runs.runs.length > 0 && (
          <>
          {runs.runs.some((run) => run.status === 'running') && (
            <p className="mb-4 max-w-[64ch] text-sm leading-relaxed text-muted">
              A run stays open when its browser tab or extension closes before the journey finishes. End it to preserve the completed steps and build a partial report.
            </p>
          )}
          {runActionError && <p role="alert" className="mb-4 text-sm text-danger">Could not end the run: {runActionError}</p>}
          <ol className="grid gap-px overflow-hidden rounded-2xl bg-line">
            {runs.runs.map((r) => (
              <li key={r.id} className="grid bg-bg transition-colors hover:bg-surface sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
                <Link to={`/app/runs/${r.id}`} className="min-w-0 px-5 pt-4 pb-2 focus-visible:outline-2 focus-visible:outline-accent sm:py-4">
                  <div className="min-w-0">
                    <p className="truncate">{r.kind === 'scan' ? 'Instant Scan' : r.goal}</p>
                    <p className="mt-0.5 truncate font-mono text-xs text-muted">{r.site}</p>
                  </div>
                </Link>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-2 px-5 pb-4 text-xs text-muted sm:justify-end sm:py-4 sm:pl-0">
                    <span>{r.kind === 'scan' ? 'Instant Scan' : PERSONA_LABEL[r.persona] ?? r.persona}</span>
                    {r.steps.some((step) => step.evidence) && <span>{r.steps.filter((step) => step.evidence).length} frames</span>}
                    {r.report && <span>{r.report.findings.length} findings</span>}
                    {r.kind === 'test' && <StatusPill status={r.status} />}
                    <time dateTime={r.created_at}>{timeAgo(r.created_at)}</time>
                    {r.status === 'running' && (
                      <button
                        type="button"
                        onClick={() => endRun(r)}
                        disabled={endingRun !== null}
                        aria-label={`End ${r.goal} and build its partial report`}
                        className="rounded-full border border-line px-3 py-1.5 text-xs text-ink transition-colors hover:bg-bg disabled:opacity-50"
                      >
                        {endingRun === r.id ? 'Ending...' : 'End and report'}
                      </button>
                    )}
                </div>
              </li>
            ))}
          </ol>
          </>
        )}
      </section>
    </AppShell>
  )
}


/** Hands the current session to the extension so it can call the API as you. Only the extension we name receives it. */
const PLAN_NAME: Record<PlanSummary['plan'], string> = { free: 'Free plan', launch: 'Launch Pack', pro: 'Pro', plus: 'Plus' }

/** Runs left in the current month or pass. Quiet when the API cannot be reached: the runs list says so already. */
function PlanLine() {
  const [plan, setPlan] = useState<PlanSummary | null>(null)
  useEffect(() => {
    getPlan().then(setPlan).catch(() => setPlan(null))
  }, [])
  if (!plan) return null
  const until = plan.expires_at ? new Date(plan.expires_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : null
  const window = plan.plan === 'free' ? `this month${until ? `, renews ${until}` : ''}` : `in your pass${until ? `, until ${until}` : ''}`
  return (
    <p role="status" className="font-mono text-xs text-muted md:text-right">
      {PLAN_NAME[plan.plan]}: {plan.runs_left} of {plan.runs_allowed} test runs left {window}
    </p>
  )
}

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
