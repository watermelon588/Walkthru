import { useGSAP } from '@gsap/react'
import { ArrowRightIcon, LightningIcon, PathIcon, PlugsConnectedIcon } from '@phosphor-icons/react'
import gsap from 'gsap'
import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { ThinkingOrb } from 'thinking-orbs'
import { AgentPresence, type AgentPresenceState } from '../components/AgentPresence'
import { AppShell } from '../components/AppShell'
import { Card, Pill, type Tone } from '../components/Card'
import { PlanFigures } from '../components/PlanMeter'
import { ScanForm } from '../components/Shared'
import { accountProfile, useSession } from '../lib/auth'
import { usePlan } from '../lib/plan'
import { listRuns, stopRun, STATUS_LABEL, timeAgo, type Run } from '../lib/runs'

gsap.registerPlugin(useGSAP)

type Runs = { kind: 'loading' } | { kind: 'ready'; runs: Run[] } | { kind: 'error'; message: string }

const extensionId = import.meta.env.VITE_EXTENSION_ID as string | undefined

const firstRun = [
  { title: 'Install the extension', body: 'Add Walkthru to Chrome and pin the bird to your toolbar.', link: 'How to install', href: '/docs#install' },
  { title: 'Connect it', body: 'Press Connect extension at the top of this page so tests run as you.', link: 'Why it is safe', href: '/security#extension' },
  { title: 'Start a test', body: 'Open your site, click the bird and give the test user one goal.', link: 'Write a good goal', href: '/docs#goals' },
]

// Same bands as the Launch Ready badge (apps/api/app/agent/score.py).
const scoreTone = (score: number): Tone => (score >= 85 ? 'ok' : score >= 60 ? 'neutral' : 'bad')
const statusTone = (status: Run['status']): Tone => (status === 'done' || status === 'safe_stop' ? 'ok' : status === 'running' || status === 'looping' || status === 'stopped' ? 'neutral' : 'bad')

function greeting(): string {
  const hour = new Date().getHours()
  return hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'
}

export default function Dashboard() {
  const [runs, setRuns] = useState<Runs>({ kind: 'loading' })
  const [endingRun, setEndingRun] = useState<string | null>(null)
  const [runActionError, setRunActionError] = useState<string | null>(null)
  const plan = usePlan()
  const { session } = useSession()
  const navigate = useNavigate()
  const root = useRef<HTMLDivElement>(null)
  const firstName = accountProfile(session).full_name.split(' ')[0]

  useEffect(() => {
    listRuns()
      .then((r) => setRuns({ kind: 'ready', runs: r }))
      .catch((e: Error) => setRuns({ kind: 'error', message: e.message }))
  }, [])

  // One authored moment: the numbers count up and the history settles in, once, when the data lands.
  const ready = runs.kind === 'ready' && plan.kind === 'ready'
  useGSAP(() => {
    if (!ready) return
    gsap.matchMedia().add('(prefers-reduced-motion: no-preference)', () => {
      gsap.utils.toArray<HTMLElement>('[data-count]').forEach((el) => {
        const tween = { value: 0 }
        gsap.to(tween, { value: Number(el.dataset.count), duration: 1.1, ease: 'expo.out', onUpdate: () => { el.textContent = String(Math.round(tween.value)) } })
      })
      gsap.from('[data-row]', { autoAlpha: 0, y: 8, duration: 0.6, ease: 'expo.out', stagger: 0.03, clearProps: 'all' })
    })
  }, { scope: root, dependencies: [ready] })

  const list = runs.kind === 'ready' ? runs.runs : []
  const scored = list.find((r) => r.report?.launch_ready?.score != null)
  const score = scored?.report?.launch_ready?.score
  const open = list.filter((r) => r.status === 'running')
  const agentState: AgentPresenceState = runs.kind === 'error' ? 'stopped' : runs.kind === 'loading' || open.length ? 'observing' : list.length ? 'complete' : 'ready'
  const agentActivity = runs.kind === 'error'
    ? 'Could not read your runs'
    : runs.kind === 'loading'
      ? 'Reading your recent runs'
      : open.length
        ? `${open.length} run${open.length > 1 ? 's' : ''} still open`
        : list.length ? 'Watching your recent runs' : 'Ready for your first test'

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
      <div ref={root}>
        <header className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <h1 className="text-3xl font-light tracking-[-0.03em] md:text-4xl">{greeting()}{firstName ? `, ${firstName}` : ''}.</h1>
            <p className="mt-2 text-muted">Here is where your launch stands.</p>
          </div>
          <AgentPresence activity={agentActivity} state={agentState} phase={0.24} />
        </header>

        <Card className="mt-8 p-6" aria-label="Your launch at a glance">
          <div className="flex items-baseline justify-between gap-4">
            <h2 className="text-sm font-medium">Your launch</h2>
            <ConnectExtension />
          </div>
          <div className="mt-5 flex flex-wrap items-start gap-x-14 gap-y-6">
            <PlanFigures state={plan} />
            <div>
              {runs.kind === 'loading' ? (
                <div aria-busy="true" aria-label="Loading your latest score" className="h-10 w-20 animate-pulse rounded-xl bg-surface motion-reduce:animate-none" />
              ) : score != null && scored ? (
                <Link to={`/app/runs/${scored.id}`} className="group block">
                  <p className="text-4xl leading-none font-extralight tracking-[-0.02em] tabular-nums"><span data-count={score}>{score}</span></p>
                  <p className="mt-2 inline-flex items-center gap-1 text-xs text-muted group-hover:text-ink">
                    Latest Launch Ready score <ArrowRightIcon weight="bold" className="size-3 transition-transform group-hover:translate-x-0.5 motion-reduce:transition-none" aria-hidden />
                  </p>
                </Link>
              ) : (
                <>
                  <p className="text-4xl leading-none font-extralight tracking-[-0.02em] text-muted">None yet</p>
                  <p className="mt-2 text-xs text-muted">Scan a site below for your first score</p>
                </>
              )}
            </div>
          </div>
        </Card>

        <Card className="mt-6 p-6" aria-labelledby="scan-title">
          <div className="grid gap-5 md:grid-cols-[minmax(0,0.8fr)_minmax(20rem,1.2fr)] md:items-center">
            <div>
              <h2 id="scan-title" className="flex items-center gap-2 font-medium"><LightningIcon weight="light" className="size-5 text-accent" aria-hidden />Scan a site</h2>
              <p className="mt-1 text-sm leading-relaxed text-muted">SEO, AI search readiness and passive security in about 20 seconds. It does not use a test run.</p>
            </div>
            <ScanForm />
          </div>
        </Card>

        <Card className="mt-6 px-6 pt-5 pb-2" aria-labelledby="recent-runs-title">
          <div className="flex items-baseline justify-between gap-4">
            <h2 id="recent-runs-title" className="flex items-center gap-2 font-medium"><PathIcon weight="light" className="size-5 text-accent" aria-hidden />Recent runs</h2>
            {list.length > 0 && <span className="text-xs text-muted tabular-nums">{list.length} shown</span>}
          </div>
          {runs.kind === 'loading' && (
            <div aria-busy="true" aria-label="Loading runs" className="mt-3 grid gap-3 pb-4">
              {[0, 1, 2].map((i) => <div key={i} className="h-12 animate-pulse rounded-xl bg-surface motion-reduce:animate-none" />)}
            </div>
          )}
          {runs.kind === 'error' && <p role="alert" className="py-4 text-sm text-danger">Could not load your runs: {runs.message}. Reload the page to try again.</p>}
          {runs.kind === 'ready' && list.length === 0 && <FirstRun />}
          {runActionError && <p role="alert" className="pt-3 text-sm text-danger">Could not end the run: {runActionError}</p>}
          {open.length > 0 && <p className="pt-3 text-xs leading-relaxed text-muted">A run stays open when its tab or the extension closes early. End it to keep its steps and get a partial report.</p>}
          {list.length > 0 && (
            <ol className="mt-2">
              {list.map((r) => <RunRow key={r.id} run={r} ending={endingRun} onEnd={endRun} />)}
            </ol>
          )}
        </Card>
      </div>
    </AppShell>
  )
}

function RunRow({ run: r, ending, onEnd }: { run: Run; ending: string | null; onEnd: (run: Run) => void }) {
  const isScan = r.kind === 'scan'
  const high = r.report?.findings.filter((f) => f.severity === 'high').length ?? 0
  const score = r.report?.launch_ready?.score
  const Icon = isScan ? LightningIcon : PathIcon
  return (
    <li data-row className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-line py-3.5 last:border-b-0">
      <Link to={`/app/runs/${r.id}`} className="group flex min-w-0 flex-1 basis-64 items-center gap-3.5">
        <span className="grid size-9 shrink-0 place-items-center rounded-full bg-surface text-muted">
          {r.status === 'running'
            ? <ThinkingOrb state="working" size={20} theme="light" aria-label="Still running" />
            : <Icon weight="light" className="size-4" aria-hidden />}
        </span>
        <span className="min-w-0">
          <span className="block truncate text-sm text-ink group-hover:underline group-hover:decoration-line group-hover:underline-offset-4">{isScan ? 'Instant Scan' : r.goal}</span>
          <span className="block truncate text-xs text-muted">{r.site}</span>
        </span>
      </Link>
      <div className="flex items-center gap-2 pl-[3.125rem] sm:pl-0">
        {high > 0 && <Pill tone="bad">{high} high</Pill>}
        {!isScan && <Pill tone={statusTone(r.status)}>{STATUS_LABEL[r.status]}</Pill>}
        {score != null && <Pill tone={scoreTone(score)}>Score {score}</Pill>}
        <time dateTime={r.created_at} className="w-20 text-right text-xs text-muted tabular-nums">{timeAgo(r.created_at)}</time>
        {r.status === 'running' && (
          <button
            type="button"
            onClick={() => onEnd(r)}
            disabled={ending !== null}
            aria-label={`End ${r.goal} and build its partial report`}
            className="rounded-full border border-line px-3 py-1 text-xs text-ink transition-colors hover:bg-surface disabled:opacity-50"
          >
            {ending === r.id ? 'Ending...' : 'End and report'}
          </button>
        )}
      </div>
    </li>
  )
}

function FirstRun() {
  return (
    <div role="status" className="pt-3 pb-5">
      <p className="text-sm text-muted">No runs yet. Three steps to your first report:</p>
      <ol className="mt-4 grid gap-5 sm:grid-cols-3">
        {firstRun.map((s, i) => (
          <li key={s.title}>
            <span className="grid size-6 place-items-center rounded-full bg-ink text-xs text-bg tabular-nums">{i + 1}</span>
            <h3 className="mt-3 text-sm font-medium">{s.title}</h3>
            <p className="mt-1 text-sm leading-relaxed text-muted">{s.body}</p>
            <Link to={s.href} className="mt-2 inline-block text-sm text-ink underline decoration-line underline-offset-4 transition hover:decoration-ink">{s.link}</Link>
          </li>
        ))}
      </ol>
    </div>
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
    <div className="relative">
      <button type="button" onClick={connect} className="inline-flex items-center gap-1.5 text-sm text-ink transition hover:opacity-70">
        <PlugsConnectedIcon weight="light" className="size-4" aria-hidden /> Connect extension
      </button>
      {msg && <p role="status" className="absolute top-full right-0 z-10 mt-2 w-72 rounded-xl border border-line bg-card px-3 py-2 text-xs leading-relaxed text-muted shadow-[0_12px_30px_-18px_rgba(27,27,31,0.35)]">{msg}</p>}
    </div>
  )
}
