import { CameraIcon, CaretLeftIcon, CaretRightIcon, PauseIcon, PlayIcon } from '@phosphor-icons/react'
import { assembleImage } from 'assemble'
import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react'
import { inProgress, momentPaths, moments, restingPoint } from '../lib/live'
import { evidenceUrls, type Step } from '../lib/runs'
import type { OrbState } from 'thinking-orbs'
import { Orb } from './Loading'

const SPEEDS = [1, 2, 4] as const
const TRAVEL_MS = 1500 // the cursor crosses to its target and rests on it for a beat
const ACT_MS = 800 // an action with no target to point at (a scroll, a wait)
const DWELL_MS = 2600 // time to read what the test user said about a page
const REST = { x: 0.88, y: 0.82 } // where the cursor waits before its first measured target
const reducedMotion = () => typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches

/** Replays one test user's journey as a visitor would watch it: a page, what the test user says about it, then the
 *  cursor moving to what it presses and the page that follows (lib/live.ts `moments`). Frames are saved moments, not
 *  a recording. The cursor rests in a corner until its first measured target and only ever clicks on a point the
 *  runner measured. A frame is swapped in only once it has downloaded, so a change is a cross-fade, never a blank
 *  stage. `live` follows new steps as they arrive, one at a time. */
export function SessionPlayer({ steps, name, runId, live = false, orb = 'breathing' }: { steps: Step[]; name: string; runId?: string | null; live?: boolean; orb?: OrbState }) {
  const list = useMemo(() => moments(steps, runId), [steps, runId])
  const [index, setIndex] = useState(0) // the page on screen
  const [heading, setHeading] = useState<number | null>(null) // the page the test user is on its way to
  const [follow, setFollow] = useState(live)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState<(typeof SPEEDS)[number]>(1)
  const [urls, setUrls] = useState<Record<string, string>>({})
  const [ready, setReady] = useState<Set<string>>(() => new Set()) // paths whose image has downloaded
  const [failed, setFailed] = useState<Set<string>>(() => new Set())
  const [stage, setStage] = useState<{ path: string; under?: string; enter?: 'up' | 'down' } | null>(null)
  const asked = useRef(new Set<string>())
  const fx = useRef<HTMLDivElement>(null) // the cursor crew draws in here; React never puts anything inside it
  const builtFor = useRef<string | null>(null) // address of the page the crew last rebuilt
  const paths = useMemo(() => momentPaths(list), [list])
  const pathsKey = paths.join('|')
  const last = list.length - 1
  const at = Math.min(index, Math.max(0, last))
  const here = list[at]
  const next = heading !== null ? list[heading] : undefined

  // Sign each frame once, as it appears, and download it straight away so a change never waits on the network.
  useEffect(() => {
    const missing = paths.filter((path) => !asked.current.has(path))
    if (missing.length === 0) return
    missing.forEach((path) => asked.current.add(path))
    // No cancel flag: each path is asked for once, so a discarded answer (React re-running the effect) would never come back.
    evidenceUrls(missing).then((signed) => {
      setUrls((known) => ({ ...known, ...signed }))
      for (const path of missing) {
        if (!signed[path]) { setFailed((known) => new Set(known).add(path)); continue }
        const image = new Image()
        image.onload = () => setReady((known) => new Set(known).add(path))
        image.onerror = () => setFailed((known) => new Set(known).add(path))
        image.src = signed[path]
      }
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps -- pathsKey is the content of paths
  }, [pathsKey])

  /** Step forward by one with the journey played out; any other jump lands directly. */
  function go(to: number, animated: boolean) {
    const target = Math.min(Math.max(0, to), Math.max(0, last))
    if (animated && !reducedMotion() && target === at + 1) return setHeading(target)
    setHeading(null)
    setIndex(target)
  }

  // Following a live run, or playing: advance one page at a time so every move is seen.
  useEffect(() => {
    if (heading !== null || at >= last) { if (playing && at >= last && heading === null) setPlaying(false); return }
    if (!follow && !playing) return
    const timer = window.setTimeout(() => go(at + 1, true), (follow && !playing ? 600 : DWELL_MS) / speed)
    return () => window.clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps -- go reads the current list
  }, [follow, playing, at, last, heading, speed])

  // What should be on the stage now. On the way to a page: the view the test user aimed in, when one was saved.
  const wanted = next ? next.aim ?? here?.frame : here?.frame
  const settled = !wanted || stage?.path === wanted || failed.has(wanted)

  useEffect(() => {
    if (!wanted || !ready.has(wanted) || stage?.path === wanted) return
    const scrolled = !next && here?.action === 'scroll' ? (here.label.toLowerCase().includes('up') ? 'up' : 'down') : undefined
    setStage({ path: wanted, under: stage?.path, enter: scrolled })
  }, [wanted, ready, stage, next, here])

  // The move starts once its view is on screen, and the page changes when the cursor has reached the target.
  useEffect(() => {
    if (heading === null || !settled) return
    const timer = window.setTimeout(() => { setIndex(heading); setHeading(null) }, (next?.pointer ? TRAVEL_MS : ACT_MS) / speed)
    return () => window.clearTimeout(timer)
  }, [heading, settled, next, speed])

  // A new page arriving is rebuilt once by a crew of cursors (packages/assemble, image mode): they redraw the saved
  // frame's own blocks over it, then leave. It is presentation only: the test user's cursor above it still moves
  // only to measured points. A scroll or a later view of the same address just cross-fades as before.
  const stagePath = stage?.path
  useEffect(() => {
    const src = stagePath && urls[stagePath]
    if (!fx.current || !src || next || !here || stagePath !== here.frame || builtFor.current === here.url) return
    const before = builtFor.current
    builtFor.current = here.url
    const ink = getComputedStyle(document.documentElement).getPropertyValue('--ink').trim() || undefined
    const run = assembleImage(fx.current, src, { outline: ink })
    return () => {
      // cut short (the view changed, or React re-ran the effect): let the next view of this page play it
      if (run.stats().phase !== 'done') builtFor.current = before
      run.destroy()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- runs when the frame on stage changes, reads the rest as it is then
  }, [stagePath])

  function select(to: number) {
    setPlaying(false)
    setFollow(false)
    go(to, false)
  }

  function onKey(event: KeyboardEvent<HTMLDivElement>) {
    if ((event.target as HTMLElement).closest('button, a, input')) return
    if (event.key === 'ArrowLeft') { event.preventDefault(); select(at - 1) }
    if (event.key === 'ArrowRight') { event.preventDefault(); select(at + 1) }
    if (event.key === ' ') { event.preventDefault(); toggle() }
  }

  function toggle() {
    setFollow(false)
    if (!playing && at >= last) { setHeading(null); setIndex(0) }
    setPlaying((value) => !value)
  }

  if (!here) {
    return (
      <div role="status" className="grid aspect-[16/9] place-items-center rounded-2xl border border-line bg-surface/40 px-6 text-center">
        <div className="grid justify-items-center">
          <Orb size={120} state={live ? orb : 'breathing'} speed={live ? 1 : 0.3} />
          <p className="mt-5 text-lg font-light">{live ? `${name} is opening the site` : 'No steps were recorded'}</p>
          {live && <p className="mt-2 max-w-[40ch] text-sm leading-relaxed text-muted">The first view appears here as soon as the page has loaded.</p>}
        </div>
      </div>
    )
  }

  const arrived = !next && !!here.frame && stage?.path === here.frame
  const point = next?.pointer ?? restingPoint(list, at) ?? REST
  const clicked = arrived && !!here.pointer && here.action === 'click'
  const pill = next ? inProgress(next.label, next.action ?? 'click') : here.doing ? `${here.doing}...` : null
  const loading = !!wanted && !settled

  return (
    <div role="group" aria-label={`${name}'s session, view ${at + 1} of ${list.length}`} tabIndex={0} onKeyDown={onKey}
      className="overflow-hidden rounded-2xl border border-line bg-bg shadow-2xl shadow-ink/5 focus-visible:outline-2 focus-visible:outline-accent">
      {/* The page under test, framed as a browser window: address, then the view itself, full width. */}
      <div className="flex items-center gap-3 border-b border-line px-4 py-2.5">
        <span aria-hidden className="flex gap-1.5">{[0, 1, 2].map((i) => <span key={i} className="size-2.5 rounded-full bg-line" />)}</span>
        <span className="block min-w-0 flex-1 truncate rounded-full bg-surface px-3 py-1 text-center font-mono text-[11px] text-muted">{here.url.replace(/^https?:\/\//, '')}</span>
        <p className="shrink-0 font-mono text-[11px] text-muted">{at + 1} / {list.length}</p>
      </div>

      <div className="bg-surface/50 p-3 sm:p-5">
          <div className="relative mx-auto overflow-hidden rounded-xl border border-line bg-surface" style={{ aspectRatio: `${here.width} / ${here.height}`, width: `min(100%, calc(38rem * ${here.width} / ${here.height}))` }}>
            {stage ? (
              <>
                {stage.under && urls[stage.under] && <img src={urls[stage.under]} alt="" aria-hidden className="absolute inset-0 h-full w-full object-fill" />}
                <img key={stage.path} src={urls[stage.path]} data-enter={stage.enter} alt={`What ${name} saw: ${here.label}`} className="live-frame absolute inset-0 h-full w-full object-fill" />
                <div ref={fx} aria-hidden className="pointer-events-none absolute inset-0" />
              </>
            ) : (
              <div className="absolute inset-0 grid place-items-center px-6 text-center">
                <div>
                  <CameraIcon className="mx-auto size-7 text-muted" weight="light" />
                  <p className="mt-3 text-sm">{wanted && failed.has(wanted) ? 'Frame unavailable' : 'Loading the page view'}</p>
                </div>
              </div>
            )}
            {arrived && here.regions?.map((r, i) => (
              <span key={i} aria-hidden className="pointer-events-none absolute rounded border-2 border-danger" style={{ left: `${r.x * 100}%`, top: `${r.y * 100}%`, width: `${r.w * 100}%`, height: `${r.h * 100}%` }} />
            ))}
            {stage && (
              <span aria-hidden className="live-cursor pointer-events-none absolute left-0 top-0 h-full w-full" style={{ transform: `translate(${point.x * 100}%, ${point.y * 100}%)`, transitionDuration: `${1100 / speed}ms` }}>
                <span className="absolute -left-5 -top-5 size-10 rounded-full bg-ink/10" />
                {clicked && <span key={`${at}-ring`} className="live-ring absolute -left-6 -top-6 size-12 rounded-full border-2 border-ink" />}
                <svg key={clicked ? `${at}-press` : 'rest'} viewBox="0 0 20 20" className={`absolute left-0 top-0 size-7 drop-shadow ${clicked ? 'live-press' : ''}`}><path d="M2 1.5 17 9l-6.4 1.9L8.4 17.5Z" className="fill-ink stroke-bg" strokeWidth="1.4" strokeLinejoin="round" /></svg>
                <span className="absolute left-6 top-6 whitespace-nowrap rounded-full bg-ink px-2.5 py-1 text-[11px] text-bg shadow-sm">{name}</span>
              </span>
            )}
            {loading && stage && <span role="status" aria-label="Loading the next view" className="absolute right-3 top-3 size-2.5 animate-pulse rounded-full bg-ink/70 motion-reduce:animate-none" />}
            {pill && <span role="status" className="live-pill absolute bottom-3 left-1/2 max-w-[90%] -translate-x-1/2 truncate rounded-full bg-ink/90 px-3 py-1 text-xs text-bg">{pill}</span>}
          </div>
      </div>

      {/* What the test user said, under the view it is about. */}
      <div aria-live="polite" className="flex gap-4 border-t border-line px-5 py-5 sm:gap-5 sm:px-6">
        <Orb size={44} state={orb} speed={live && at === last ? 1 : 0.3} className="mt-0.5 shrink-0" />
        <div className="min-w-0 flex-1">
          <p className="flex flex-wrap items-baseline gap-x-2 font-mono text-[10px] uppercase tracking-[0.18em] text-muted">
            <span className="text-ink">{name}</span><span>· {here.label}</span>
            {here.ended && <span className={here.ended === 'done' ? 'text-accent' : 'text-danger'}>· {here.ended === 'done' ? 'finished here' : 'stopped here'}</span>}
          </p>
          <p key={at} className="live-thought mt-2 max-w-[68ch] text-lg leading-relaxed font-light text-ink">{here.thought || (live && at === last ? 'Reading the page...' : 'No comment on this page.')}</p>
          {here.note && <p className="mt-3 max-w-[68ch] text-xs leading-relaxed text-muted">{here.note}</p>}
        </div>
        <div className="hidden w-28 shrink-0 self-start pt-1 sm:block">
          <p className="text-[11px] text-muted">Confusion</p>
          <span className="mt-2 flex gap-1" role="img" aria-label={`Confusion ${here.confusion} of 3`}>
            {[0, 1, 2].map((level) => <span key={level} className={`h-1.5 flex-1 rounded-full transition-colors duration-300 ${level < here.confusion ? 'bg-danger' : 'bg-line'}`} />)}
          </span>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3 border-t border-line px-4 py-3">
        <div className="flex items-center gap-1.5">
          <Control label="Previous view" onClick={() => select(at - 1)} disabled={at === 0}><CaretLeftIcon /></Control>
          <Control label={playing ? 'Pause replay' : 'Play replay'} onClick={toggle} disabled={list.length < 2}>{playing ? <PauseIcon weight="fill" /> : <PlayIcon weight="fill" />}</Control>
          <Control label="Next view" onClick={() => select(at + 1)} disabled={at >= last}><CaretRightIcon /></Control>
        </div>
        <ol aria-label="Views" className="order-last flex w-full min-w-0 flex-wrap items-center gap-1 sm:order-none sm:w-auto sm:flex-1">
          {list.map((moment, i) => (
            <li key={i}>
              <button type="button" onClick={() => select(i)} aria-label={`View ${i + 1}: ${moment.label}`} aria-current={i === at ? 'step' : undefined}
                className="grid size-5 place-items-center rounded-full focus-visible:outline-2 focus-visible:outline-accent">
                <span className={`block rounded-full transition-[transform,background-color] duration-150 ${i === at ? 'size-2.5 bg-ink' : i < at ? 'size-1.5 bg-ink/50' : 'size-1.5 bg-line'}`} />
              </button>
            </li>
          ))}
        </ol>
        {live && !follow && <button type="button" onClick={() => { setPlaying(false); setFollow(true) }} className="rounded-full border border-line px-3 py-1 text-xs transition-colors hover:bg-surface">Follow live</button>}
        <div role="group" aria-label="Replay speed" className="flex items-center gap-0.5 rounded-full border border-line p-0.5">
          {SPEEDS.map((value) => (
            <button key={value} type="button" onClick={() => setSpeed(value)} aria-pressed={speed === value} className={`rounded-full px-2 py-0.5 font-mono text-[11px] transition-colors ${speed === value ? 'bg-ink text-bg' : 'text-muted hover:text-ink'}`}>{value}x</button>
          ))}
        </div>
      </div>
      <p className="px-4 pb-3 text-[11px] leading-relaxed text-muted">Frames are saved moments, not a recording. Form fields are blurred before each capture. A click ring marks where the control was measured.</p>
    </div>
  )
}

function Control({ label, onClick, disabled, children }: { label: string; onClick: () => void; disabled: boolean; children: React.ReactNode }) {
  return (
    <button type="button" aria-label={label} onClick={onClick} disabled={disabled} className="grid size-8 place-items-center rounded-full border border-line transition-[background-color,transform] duration-150 hover:bg-surface active:scale-[0.96] disabled:cursor-default disabled:opacity-35">
      {children}
    </button>
  )
}
