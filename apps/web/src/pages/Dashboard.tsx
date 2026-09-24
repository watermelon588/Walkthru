import { useGSAP } from '@gsap/react'
import { ArrowRightIcon, CameraIcon, LightningIcon, MagnifyingGlassIcon, PathIcon, PlugsConnectedIcon, WarningCircleIcon } from '@phosphor-icons/react'
import gsap from 'gsap'
import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { ThinkingOrb } from 'thinking-orbs'
import { AgentPresence, type AgentPresenceState } from '../components/AgentPresence'
import { AppShell } from '../components/AppShell'
import { PlanMeter } from '../components/PlanMeter'
import { usePlan } from '../lib/plan'
import { StatusPill } from '../components/ReportView'
import { btnGhost, ScanForm } from '../components/Shared'
import { accountProfile, useSession } from '../lib/auth'
import { listRuns, PERSONA_LABEL, stopRun, timeAgo, type Run } from '../lib/runs'

gsap.registerPlugin(useGSAP)

type Runs = { kind: 'loading' } | { kind: 'ready'; runs: Run[] } | { kind: 'error'; message: string }

const extensionId = import.meta.env.VITE_EXTENSION_ID as string | undefined

const firstRun = [
  { title: 'Install the extension', body: 'Add Walkthru to Chrome and pin the bird to your toolbar.', link: 'How to install', href: '/docs#install' },
  { title: 'Connect it', body: 'Press Connect extension at the top of this page so tests run as you.', link: 'Why it is safe', href: '/security#extension' },
  { title: 'Start a test', body: 'Open your site, click the bird and give the test user one goal.', link: 'Write a good goal', href: '/docs#goals' },
]

// Same bands as the Launch Ready badge (apps/api/app/agent/score.py).
function scoreTone(score: number): string {
  return score >= 85 ? 'text-accent' : score >= 60 ? 'text-ink' : 'text-danger'
}
function scoreBand(score: number): string {
  return score >= 85 ? 'Launch ready' : score >= 60 ? 'Almost ready' : 'Needs work'
}

function greeting(): string {
  const hour = new Date().getHours()
  return hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'
}

export default function Dashboard() {
  const [runs, setRuns] = useState<Runs>({ kind: 'loading' })
  const [scoutOpen, setScoutOpen] = useState(false)
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
        const end = Number(el.dataset.count)
        const tween = { value: 0 }
        gsap.to(tween, { value: end, duration: 1.1, ease: 'expo.out', onUpdate: () => { el.textContent = String(Math.round(tween.value)) } })
      })
      gsap.from('[data-row]', { autoAlpha: 0, y: 10, duration: 0.6, ease: 'expo.out', stagger: 0.035, clearProps: 'all' })
    })
  }, { scope: root, dependencies: [ready] })

  const list = runs.kind === 'ready' ? runs.runs : []
  const scored = list.find((r) => r.report?.launch_ready?.score != null)
  const running = list.filter((r) => r.status === 'running')
  const agentState: AgentPresenceState = runs.kind === 'error' ? 'stopped' : runs.kind === 'loading' || running.length ? 'observing' : list.length ? 'complete' : 'ready'
  const agentActivity = runs.kind === 'error'
    ? 'Could not read your runs'
    : runs.kind === 'loading'
      ? 'Reading your recent runs'
      : running.length
        ? `${running.length} run${running.length > 1 ? 's' : ''} still open`
        : list.length
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
      <div ref={root}>
        <header className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <h1 className="text-3xl font-light tracking-[-0.03em] md:text-4xl">{greeting()}{firstName ? `, ${firstName}` : ''}.</h1>
            <p className="mt-2 max-w-[56ch] text-muted">Here is where your launch stands, and what to test next.</p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <ConnectExtension />
            <a href="#scan" className="inline-flex items-center gap-2 rounded-full bg-ink px-5 py-2.5 text-sm whitespace-nowrap text-bg transition hover:opacity-85 active:scale-[0.98]">
              <MagnifyingGlassIcon weight="bold" className="size-4" aria-hidden /> Scan my site
            </a>
          </div>
        </header>

        <section aria-label="Your launch at a glance" className="mt-8 grid gap-px overflow-hidden rounded-2xl border border-line bg-line lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)_minmax(0,1fr)]">
          <PlanMeter state={plan} />
          <LatestScore run={scored} loading={runs.kind === 'loading'} />
          <div className="flex flex-col bg-bg p-6">
            <h2 className="text-sm font-medium">Scout</h2>
            <div className="mt-4">
              <AgentPresence
                activity={agentActivity}
                state={agentState}
                phase={0.24}
                onActivate={() => setScoutOpen((value) => !value)}
                actionLabel="Ask Scout what to do next"
                expanded={scoutOpen}
              />
            </div>
            <p role="status" className="mt-4 text-sm leading-relaxed text-muted">
              {scoutOpen || !list.length
                ? 'Open the site you want tested, connect the extension, then give me one goal. I keep the journey safe and bring the evidence back here.'
                : running.length
                  ? 'A run stays open when its tab or the extension closes early. End it below to keep the steps and get a partial report.'
                  : `${list.filter((r) => r.kind === 'test').length} tests and ${list.filter((r) => r.kind === 'scan').length} scans so far. Rerun a goal after a fix to see what changed.`}
            </p>
          </div>
        </section>

        <section aria-labelledby="recent-runs-title" className="mt-14">
          <div className="mb-4 flex items-end justify-between gap-4">
            <h2 id="recent-runs-title" className="text-2xl font-light tracking-tight">Recent runs</h2>
            {runs.kind === 'ready' && list.length > 0 && <span className="text-xs text-muted tabular-nums">{list.length} shown</span>}
          </div>
          {runs.kind === 'loading' && (
            <div aria-busy="true" aria-label="Loading runs" className="grid gap-px overflow-hidden rounded-2xl border border-line bg-line">
              {[0, 1, 2].map((i) => <div key={i} className="h-[4.5rem] animate-pulse bg-bg motion-reduce:animate-none" />)}
            </div>
          )}
          {runs.kind === 'error' && (
            <p role="alert" className="rounded-2xl border border-line px-5 py-4 text-sm text-danger">Could not load your runs: {runs.message}. Reload the page to try again.</p>
          )}
          {runs.kind === 'ready' && list.length === 0 && <FirstRun />}
          {runs.kind === 'ready' && list.length > 0 && (
            <>
              {runActionError && <p role="alert" className="mb-4 text-sm text-danger">Could not end the run: {runActionError}</p>}
              <ol className="grid gap-px overflow-hidden rounded-2xl border border-line bg-line">
                {list.map((r) => <RunRow key={r.id} run={r} ending={endingRun} onEnd={endRun} />)}
              </ol>
            </>
          )}
        </section>

        <section id="scan" aria-labelledby="scan-title" className="mt-14 scroll-mt-24 grid gap-6 rounded-2xl bg-surface p-6 md:grid-cols-[minmax(0,0.8fr)_minmax(20rem,1.2fr)] md:items-center md:p-8">
          <div>
            <h2 id="scan-title" className="flex items-center gap-2 text-2xl font-light tracking-tight">
              <LightningIcon weight="light" className="size-6 text-accent" aria-hidden /> Scan a site now
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-muted">SEO, AI search readiness and passive security in about 20 seconds. No extension needed, and it does not use a test run.</p>
          </div>
          <ScanForm />
        </section>
      </div>
    </AppShell>
  )
}

function LatestScore({ run, loading }: { run?: Run; loading: boolean }) {
  const score = run?.report?.launch_ready?.score
  return (
    <section aria-labelledby="score-title" className="flex flex-col bg-bg p-6">
      <h2 id="score-title" className="text-sm font-medium">Latest Launch Ready score</h2>
      {loading ? (
        <div aria-busy="true" aria-label="Loading your latest score" className="mt-6 h-14 w-24 animate-pulse rounded-xl bg-surface motion-reduce:animate-none" />
      ) : run && score != null ? (
        <>
          <p className="mt-6 flex items-baseline gap-3">
            <span data-count={score} className={`text-6xl leading-none font-extralight tracking-[-0.03em] tabular-nums ${scoreTone(score)}`}>{score}</span>
            <span className="text-sm text-muted">{scoreBand(score)}</span>
          </p>
          <p className="mt-5 truncate font-mono text-xs text-muted">{run.site}</p>
          <Link to={`/app/runs/${run.id}`} className="group mt-auto inline-flex items-center gap-1.5 pt-5 text-sm text-ink">
            Open the report <ArrowRightIcon weight="bold" className="size-3.5 transition-transform group-hover:translate-x-0.5 motion-reduce:transition-none" aria-hidden />
          </Link>
        </>
      ) : (
        <>
          <p className="mt-6 text-sm leading-relaxed text-muted">No score yet. Every new report gets one number for journeys, security, AI search, SEO and speed.</p>
          <a href="#scan" className="group mt-auto inline-flex items-center gap-1.5 pt-5 text-sm text-ink">
            Get your first score <ArrowRightIcon weight="bold" className="size-3.5 transition-transform group-hover:translate-x-0.5 motion-reduce:transition-none" aria-hidden />
          </a>
        </>
      )}
    </section>
  )
}

function RunRow({ run: r, ending, onEnd }: { run: Run; ending: string | null; onEnd: (run: Run) => void }) {
  const isScan = r.kind === 'scan'
  const frames = r.steps.filter((step) => step.evidence).length
  const high = r.report?.findings.filter((f) => f.severity === 'high').length ?? 0
  const score = r.report?.launch_ready?.score
  const Icon = isScan ? LightningIcon : PathIcon
  return (
    <li data-row className="group grid bg-bg transition-colors hover:bg-surface/60 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
      <Link to={`/app/runs/${r.id}`} className="flex min-w-0 items-center gap-4 px-5 pt-4 pb-2 sm:py-4">
        <span className="grid size-10 shrink-0 place-items-center rounded-full border border-line bg-bg text-muted">
          {r.status === 'running'
            ? <ThinkingOrb state="working" size={20} theme="light" aria-label="Still running" />
            : <Icon weight="light" className="size-[18px]" aria-hidden />}
        </span>
        <span className="min-w-0">
          <span className="block truncate text-ink">{isScan ? 'Instant Scan' : r.goal}</span>
          <span className="mt-0.5 block truncate font-mono text-xs text-muted">{r.site}</span>
        </span>
      </Link>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 px-5 pb-4 pl-[4.75rem] text-xs text-muted sm:justify-end sm:py-4 sm:pl-0">
        {!isScan && <span className="hidden md:inline">{PERSONA_LABEL[r.persona] ?? r.persona}</span>}
        {frames > 0 && <span className="inline-flex items-center gap-1"><CameraIcon weight="light" className="size-3.5" aria-hidden />{frames}</span>}
        {high > 0 && <span className="inline-flex items-center gap-1 text-danger"><WarningCircleIcon weight="fill" className="size-3.5" aria-hidden />{high} high</span>}
        {!isScan && <StatusPill status={r.status} />}
        {score != null && (
          <span className={`min-w-10 rounded-full border border-line px-2.5 py-0.5 text-center font-medium tabular-nums ${scoreTone(score)}`} title={`Launch Ready ${score}: ${scoreBand(score)}`}>
            {score}
          </span>
        )}
        <time dateTime={r.created_at} className="tabular-nums">{timeAgo(r.created_at)}</time>
        {r.status === 'running' && (
          <button
            type="button"
            onClick={() => onEnd(r)}
            disabled={ending !== null}
            aria-label={`End ${r.goal} and build its partial report`}
            className="rounded-full border border-line px-3 py-1.5 text-xs text-ink transition-colors hover:bg-bg disabled:opacity-50"
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
    <div role="status" className="rounded-2xl border border-line px-6 py-10">
      <p className="text-lg font-light">No runs yet. Three steps to your first report:</p>
      <ol className="mt-6 grid gap-px overflow-hidden rounded-2xl bg-line sm:grid-cols-3">
        {firstRun.map((s, i) => (
          <li key={s.title} className="flex flex-col bg-bg px-5 py-5">
            <span className="grid size-7 place-items-center rounded-full bg-ink font-mono text-xs text-bg">{i + 1}</span>
            <h3 className="mt-4 text-sm font-medium">{s.title}</h3>
            <p className="mt-1 flex-1 text-sm leading-relaxed text-muted">{s.body}</p>
            <Link to={s.href} className="mt-4 self-start text-sm text-ink underline decoration-line underline-offset-4 transition hover:decoration-ink">{s.link}</Link>
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
      <button type="button" onClick={connect} className={`${btnGhost} px-5 py-2.5`}>
        <PlugsConnectedIcon weight="light" className="size-4" aria-hidden /> Connect extension
      </button>
      {msg && <p role="status" className="absolute top-full right-0 z-10 mt-2 w-72 rounded-xl border border-line bg-bg px-3 py-2 text-xs leading-relaxed text-muted shadow-[0_12px_30px_-18px_rgba(27,27,31,0.35)]">{msg}</p>}
    </div>
  )
}
