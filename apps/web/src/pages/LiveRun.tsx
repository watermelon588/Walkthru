import { ArrowSquareOutIcon, CheckCircleIcon, CircleNotchIcon } from '@phosphor-icons/react'
import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router'
import { AppShell } from '../components/AppShell'
import { Orb, SkeletonPanel } from '../components/Loading'
import { SessionPlayer } from '../components/SessionPlayer'
import { anyActive, believedDone, cardLine, endedEarly, isActive, personaOrb, reportsPending, type LiveCard, type LiveTest } from '../lib/live'
import { getLive, PERSONA_LABEL, STATUS_LABEL, stopLive } from '../lib/runs'

const POLL_MS = 1500
const personaName = (card: LiveCard) => PERSONA_LABEL[card.persona] ?? card.persona
const linkCls = 'text-ink underline decoration-line underline-offset-4 hover:decoration-ink'

/** One live test, in one column: the goal, a tab per test user with its real state, the selected test user's
 *  session, then the report hand-off. */
export default function LiveRun() {
  const { groupId = '' } = useParams()
  const [test, setTest] = useState<LiveTest | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [missing, setMissing] = useState(false)
  const [picked, setPicked] = useState<string | null>(null)
  const [stopping, setStopping] = useState(false)
  const failures = useRef(0)

  // Poll while anything is queued, running or waiting on its report. Paused while the tab is hidden; slower after errors.
  useEffect(() => {
    let timer = 0
    let active = true
    async function tick() {
      if (!active) return
      if (document.hidden) { timer = window.setTimeout(tick, POLL_MS); return }
      try {
        const next = await getLive(groupId)
        if (!active) return
        failures.current = 0
        setError(null)
        setTest(next)
        if (anyActive(next) || reportsPending(next)) timer = window.setTimeout(tick, anyActive(next) ? POLL_MS : POLL_MS * 2)
      } catch (e) {
        if (!active) return
        const message = e instanceof Error ? e.message : 'Could not load this live test.'
        if (/unknown live test/i.test(message)) return setMissing(true)
        failures.current += 1
        setError(message)
        timer = window.setTimeout(tick, Math.min(15_000, POLL_MS * 2 ** failures.current))
      }
    }
    tick()
    return () => { active = false; window.clearTimeout(timer) }
  }, [groupId])

  async function stop() {
    setStopping(true)
    try { await stopLive(groupId) } catch (e) { setError(e instanceof Error ? e.message : 'Could not stop the test.') }
    setStopping(false)
  }

  const runs = test?.runs ?? []
  // Follow the test user who is walking now, unless the reader picked one.
  const shown = runs.find((card) => card.id === picked) ?? runs.find((card) => card.status === 'running') ?? [...runs].reverse().find((card) => card.steps.length > 0) ?? runs[0]
  const done = runs.filter((card) => !isActive(card)).length
  const withRun = runs.filter((card) => card.run_id)
  const settled = !!test && !anyActive(test)
  const writing = settled && withRun.some((card) => !card.report_ready)
  const headOrb = !test ? 'breathing' : settled ? (writing ? 'composing' : 'breathing') : shown ? personaOrb(shown.persona) : 'working'

  return (
    <AppShell title="Live run">
      <div className="relative isolate mx-auto max-w-5xl">
        <div aria-hidden className="pointer-events-none absolute -top-40 right-0 -z-10 opacity-20 max-md:hidden">
          <Orb size={520} state={settled ? 'breathing' : 'working'} speed={0.45} />
        </div>

        <header className="flex items-start gap-5 md:gap-7">
          <span className="mt-1 shrink-0 max-sm:hidden"><Orb size={72} state={headOrb} speed={settled && !writing ? 0.35 : 1} /></span>
          <div className="min-w-0 flex-1">
            <p className="flex items-center gap-2.5 font-mono text-xs uppercase tracking-[0.16em] text-accent">
              Live run
              {test && (
                <span className={`inline-flex items-center gap-1.5 rounded-full border border-line px-2 py-0.5 text-[10px] tracking-[0.12em] ${settled ? 'text-accent' : 'text-ink'}`}>
                  <span aria-hidden className={`size-1.5 rounded-full ${settled ? 'bg-accent' : 'animate-pulse bg-ink motion-reduce:animate-none'}`} />
                  {settled ? 'Finished' : 'Running'}
                </span>
              )}
            </p>
            <h1 className="mt-3 max-w-[26ch] text-3xl font-extralight tracking-[-0.03em] text-balance md:text-5xl">{test?.goal ?? 'Loading the test'}</h1>
            {test && (
              <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-3 text-sm text-muted">
                <a href={test.site} target="_blank" rel="noreferrer" className="inline-flex max-w-full min-w-0 items-center gap-1.5 rounded-full border border-line bg-bg/70 px-3 py-1 font-mono text-xs text-ink transition-colors hover:border-ink/40">
                  <span className="truncate">{test.site.replace(/^https?:\/\//, '')}</span><ArrowSquareOutIcon aria-hidden className="size-3.5 shrink-0 text-muted" />
                </a>
                <span>{done} of {runs.length} test {runs.length === 1 ? 'user' : 'users'} done</span>
                {!settled && (
                  <button type="button" onClick={stop} disabled={stopping} className="ml-auto rounded-full border border-line px-4 py-1.5 text-sm text-danger transition-[background-color,transform] duration-150 hover:bg-surface active:scale-[0.97] disabled:opacity-60">
                    {stopping ? 'Stopping...' : 'Stop test'}
                  </button>
                )}
              </div>
            )}
          </div>
        </header>

        {missing && <p role="status" className="mt-12 text-muted">This live test does not exist or belongs to another account. <Link to="/app/live" className={linkCls}>Start a new one</Link>.</p>}
        {error && !missing && <p role="alert" className="mt-6 text-sm text-danger">{error}{test ? ' Trying again.' : ''}</p>}
        {!test && !missing && !error && <SkeletonPanel label="Loading the live test" className="mt-12" />}

        {test && shown && (
          <>
            <div role="group" aria-label="Test users" className="mt-10 flex flex-wrap gap-2">
              {runs.map((card) => {
                const selected = card.id === shown.id
                return (
                  <button key={card.id} type="button" aria-pressed={selected} onClick={() => setPicked(card.id)}
                    className={`inline-flex items-center gap-2.5 rounded-full border py-1.5 pr-4 pl-1.5 text-left text-sm transition-[background-color,border-color,transform] duration-150 active:scale-[0.97] focus-visible:outline-2 focus-visible:outline-accent ${selected ? 'border-ink bg-surface' : 'border-line hover:border-ink/30'}`}>
                    <Orb size={28} state={personaOrb(card.persona)} speed={card.status === 'running' ? 1 : 0.2} className={card.status === 'running' || selected ? '' : 'opacity-60'} />
                    <span className="text-ink">{personaName(card)}</span>
                    <span className="text-xs text-muted max-sm:hidden">{cardLine(card)}</span>
                    <StatusMark card={card} />
                  </button>
                )
              })}
            </div>

            <section aria-label={`${personaName(shown)}'s session`} className="mt-5">
              {(shown.status === 'blocked' || shown.status === 'failed') && shown.error && (
                <Notice tone="danger" title={shown.status === 'blocked' ? 'This test user could not run.' : 'This test user ended early.'}>{shown.error}</Notice>
              )}
              {shown.status === 'finished' && endedEarly(shown) && (
                believedDone(shown)
                  ? <Notice tone="muted" title={`${personaName(shown)} believes it reached the goal.`} last={shown.steps.at(-1)?.thought}>Walkthru's automatic check found no proof on the page, so the result is recorded as not confirmed. Watch the steps and judge for yourself.</Notice>
                  : <Notice tone="danger" title={`${personaName(shown)} stopped before reaching the goal.`} last={shown.steps.at(-1)?.thought}>{STATUS_LABEL[shown.run_status as keyof typeof STATUS_LABEL] ?? 'The test ended early'}.</Notice>
              )}
              {shown.status === 'queued' ? (
                <div role="status" className="grid aspect-[16/9] place-items-center overflow-hidden rounded-2xl border border-line bg-surface/40 px-6 text-center">
                  <div className="grid justify-items-center">
                    <Orb size={120} state={personaOrb(shown.persona)} speed={0.7} />
                    <p className="mt-5 text-lg font-light">{cardLine(shown)}</p>
                    <p className="mt-2 max-w-[44ch] text-sm leading-relaxed text-muted">One browser runs at a time. {personaName(shown)} starts when the ones ahead finish, each within four minutes.</p>
                  </div>
                </div>
              ) : (
                <SessionPlayer key={shown.id} steps={shown.steps} runId={shown.run_id} name={personaName(shown)} orb={personaOrb(shown.persona)} live={shown.status === 'running'} />
              )}
            </section>

            {settled && (
              <section aria-labelledby="live-next" className="mt-10 overflow-hidden rounded-2xl border border-line bg-surface/30 px-6 py-7 sm:px-8">
                <div className="flex items-center gap-5">
                  <Orb size={56} state={writing ? 'composing' : 'breathing'} speed={writing ? 1 : 0.35} className="shrink-0" />
                  <div className="min-w-0">
                    <h2 id="live-next" className="text-2xl font-light tracking-tight">{withRun.length === 0 ? 'No journey ran' : writing ? 'Writing the report' : 'The report is ready'}</h2>
                    <p className="mt-1 text-sm text-muted">{withRun.length === 0 ? 'Nothing was tested, so no run was used.' : writing ? 'Checking the pages it visited and writing up what it found.' : 'Page checks, findings and the full replay are in.'}</p>
                  </div>
                </div>
                {withRun.length === 0 ? (
                  <p className="mt-5 text-sm"><Link to="/app/live" className={linkCls}>Start another test</Link></p>
                ) : (
                  <ul className="mt-6 grid gap-px overflow-hidden rounded-xl border border-line bg-line text-sm">
                    <Stage done label={`${withRun.length === 1 ? 'The test user' : 'Test users'} finished walking the site`} />
                    {withRun.map((card) => (
                      <Stage key={card.id} done={card.report_ready} label={card.report_ready ? `${personaName(card)}: checks done and report written` : `${personaName(card)}: checking the pages and writing the report`}>
                        {card.report_ready && <Link to={`/app/runs/${card.run_id}`} className="ml-auto rounded-full bg-ink px-4 py-1.5 text-xs text-bg transition-[opacity,transform] duration-150 hover:opacity-90 active:scale-[0.97]">Open report</Link>}
                      </Stage>
                    ))}
                  </ul>
                )}
              </section>
            )}
          </>
        )}
      </div>
    </AppShell>
  )
}

function StatusMark({ card }: { card: LiveCard }) {
  if (card.status === 'running') return <CircleNotchIcon aria-label="Running" className="size-3.5 shrink-0 animate-spin text-ink motion-reduce:animate-none" />
  if (card.status === 'queued') return null
  if (card.status === 'finished' && !endedEarly(card)) return <CheckCircleIcon aria-label="Finished" weight="fill" className="size-4 shrink-0 text-accent" />
  if (card.status === 'finished') return <span className={`shrink-0 text-[11px] ${believedDone(card) ? 'text-muted' : 'text-danger'}`}>{believedDone(card) ? 'Not confirmed' : 'Goal not reached'}</span>
  return <span className="shrink-0 text-[11px] text-danger">{card.status === 'stopped' ? 'Stopped' : card.status === 'blocked' ? 'Not run' : 'Ended early'}</span>
}

function Notice({ tone, title, last, children }: { tone: 'danger' | 'muted'; title: string; last?: string; children: React.ReactNode }) {
  return (
    <div role="status" className="mb-5 rounded-2xl border border-line bg-bg/70 px-5 py-4 text-sm">
      <p><span className={tone === 'danger' ? 'text-danger' : 'text-ink'}>{title}</span> <span className="text-muted">{children}</span></p>
      {last && <p className="mt-2 leading-relaxed text-muted">Its last words: "{last}"</p>}
      <p className="mt-2 text-xs text-muted">The page checks in the report still ran. <Link to="/app/live" className={linkCls}>Try a different goal</Link></p>
    </div>
  )
}

/** One line of the finish list. Each line reflects a state the server reported; none advances on a timer. */
function Stage({ done, label, children }: { done: boolean; label: string; children?: React.ReactNode }) {
  return (
    <li className="flex flex-wrap items-center gap-3 bg-bg px-4 py-3">
      {done ? <CheckCircleIcon weight="fill" className="size-5 shrink-0 text-accent" aria-hidden /> : <CircleNotchIcon className="size-5 shrink-0 animate-spin text-muted motion-reduce:animate-none" aria-hidden />}
      <span className={done ? 'text-ink' : 'text-muted'}>{label}</span>
      {children}
    </li>
  )
}
