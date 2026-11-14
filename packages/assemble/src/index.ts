// assemble(target): blank a page (or one region) and let a crew of cursors rebuild it in place.
import { fromDOM, snapshot, type Layer } from './blueprint.ts'
import { Chrome, RULER, type Tool } from './chrome.ts'
import { define } from './element.ts'
import { Hud } from './hud.ts'
import { clamp, ease, easeOut, guides, plan, Queue, rng, type Task } from './sim.ts'
import { Sound } from './sound.ts'
import { Stage, type Caret } from './stage.ts'

export { assembleImage, type ImageOptions } from './image.ts'
export { regions, type Region } from './regions.ts'
export { define, fromDOM, snapshot, type Layer }

export interface Options {
  /** how many cursors work at once; grows with the backlog and with scroll speed between min and max */
  agents?: { min: number; max: number }
  palette?: string[]
  names?: string[]
  /** selection outline, badge and pen colour */
  outline?: string
  /** duplicate outline and ruler guide colour */
  copyColor?: string
  speed?: number
  seed?: number
  /**
   * 'follow': build what has been scrolled into view and wait for the visitor to scroll.
   * 'tour': same, but scroll the page for them at build pace.
   * 'none': build everything at once (the default for a region that is not the whole page).
   */
  scroll?: 'follow' | 'tour' | 'none'
  /** control pill with progress, Tour, speed and close; ends on "Rebuilt by N agents" with Replay and Done */
  hud?: boolean
  /** edge rulers and guides; off when scroll is 'none' */
  rulers?: boolean
  /** what the cursors are called in the control pill; default 'scouts' */
  noun?: string
  /** cursor size multiplier; default 1.3 */
  cursorScale?: number
  /** start with sound on. Browsers only allow it after a click, so the pill's Sound button is the reliable way. */
  sound?: boolean
  /** cursors stay inside this element; defaults to the target when it is not the whole page */
  bounds?: Element
  /** false: nothing moves until you call step(ms). For tests and frame-exact recording. */
  autoplay?: boolean
  /** set false to run even when the visitor asked for reduced motion (tests only) */
  respectReducedMotion?: boolean
  onProgress?(built: number, total: number): void
  /** the page is whole again (the end-state pill may still be showing) */
  onDone?(): void
}

export interface Stats {
  /** intro, build, outro, finished (page restored, end-state pill showing), done (everything removed) */
  phase: string
  total: number
  built: number
  /** ready: tasks that could start now; active: tasks an agent is working on. Both zero with built < total means "scroll to keep building". */
  ready: number
  active: number
  agents: number
  time: number
  log: string[]
}

export interface Handle {
  step(ms: number): void
  setSpeed(speed: number): void
  destroy(): void
  stats(): Stats
}

interface Agent {
  x: number
  y: number
  color: string
  name: string
  tool: Tool
  task: Task | null
  script: Script | null
  /** finale flock: velocity in px per ms and the way the arrow faces */
  vx: number
  vy: number
  angle: number
}

type Script = Generator<void, void, number>
type Seg = [number, number, number, number]

const PALETTE = ['#e5484d', '#f76b15', '#e2a336', '#46a758', '#12a594', '#0090ff', '#3e63dd', '#8e4ec6', '#d6409f', '#6f6e77']
const NAMES = ['Ivy', 'Moss', 'Juno', 'Kit', 'Remy', 'Sol', 'Wren', 'Pax', 'Nell', 'Odo', 'Tess', 'Zed', 'Lux', 'Bea', 'Finn', 'Mika']
const STEP = 1000 / 60
const INTRO = 260
const TOUR_PX_PER_MS = 0.42

function pageColor() {
  for (const el of [document.body, document.documentElement]) {
    const c = getComputedStyle(el).backgroundColor
    if (c && c !== 'transparent' && !/,\s*0\)$/.test(c)) return c
  }
  return '#fff'
}

function segments(r: DOMRect, sides: string): Seg[] {
  const cx = r.left + r.width / 2
  const cy = r.top + r.height / 2
  const at: Record<string, Seg> = {
    t: [r.left, r.top, r.right, r.top],
    b: [r.left, r.bottom, r.right, r.bottom],
    l: [r.left, r.top, r.left, r.bottom],
    r: [r.right, r.top, r.right, r.bottom],
    h: [r.left, cy, r.right, cy],
    v: [cx, r.top, cx, r.bottom],
  }
  return [...sides].map((s) => at[s])
}

function createRun(target: Element, options: Options, replay: () => void): Handle {
  const whole = target === document.body || target === document.documentElement
  const o = {
    agents: { min: 6, max: 18 },
    palette: PALETTE,
    names: NAMES,
    outline: '#0090ff',
    copyColor: '#e5484d',
    speed: 1,
    seed: 1,
    scroll: (whole ? 'follow' : 'none') as NonNullable<Options['scroll']>,
    hud: whole,
    rulers: true,
    noun: 'scouts',
    cursorScale: 1.3,
    sound: false,
    autoplay: true,
    respectReducedMotion: true,
    ...options,
  }
  const paged = o.scroll !== 'none'
  const boundsEl = options.bounds ?? (whole ? null : target)
  // where cursors may roam, in viewport coordinates
  const area = () => (boundsEl ? boundsEl.getBoundingClientRect() : new DOMRect(0, 0, chrome.w, chrome.h))
  const rand = rng(o.seed)
  const { layers, copies } = snapshot(target)
  const queue = new Queue(plan(layers, copies, paged && o.rulers ? guides(layers) : []))
  const chrome = new Chrome(o.outline, o.copyColor, o.cursorScale)
  const bg = pageColor()
  const agents: Agent[] = []
  const ghosts = new Map<number, { p: number; media: boolean }>()
  const flashes = new Map<number, number>()
  const typing = new Map<number, { caret: Caret; color: string }>()
  const covers = new Map<number, number>() // painted labels: characters typed so far
  const lines = new Map<number, { done: number; p: number }>() // pen: segments finished, progress on the current one
  const dups = new Map<number, { p: number; dist: number }>() // task id of a copy in flight
  const landed = new Map<number, number>() // copy index: ms left on its outline
  const placed: number[] = [] // page x of guides in place
  const dragging = new Set<{ x: number }>() // guides in flight, viewport x
  const log: string[] = []
  const t0 = performance.now()
  let stage: Stage | null = null
  let phase: 'intro' | 'build' | 'outro' | 'finished' | 'done' = 'intro'
  let time = 0
  let speed = o.speed
  let tour = o.scroll === 'tour'
  let raf = 0
  let last = 0
  let carry = 0
  let pan = 0
  let lastY = scrollY
  let velocity = 0 // smoothed scroll speed, px per second
  let idle = false
  let ruler = 0 // 0..1 fade
  let sound: Sound | null = null
  let pointer: [number, number] | null = null // where the visitor's own mouse is, for the finale
  let flockTime = 0

  function setSound(on: boolean) {
    sound?.close()
    sound = null
    try {
      if (on) sound = new Sound()
    } catch {
      // no Web Audio here: stay silent
    }
  }
  if (o.sound) setSound(true)

  const hud = o.hud
    ? new Hud(
        chrome.root,
        {
          tour: (on) => void (tour = on),
          speed: (n) => void (speed = n),
          close: () => destroy(),
          replay,
          sound: setSound,
        },
        tour,
        speed,
        o.noun,
        o.sound,
      )
    : null

  // ---- agent scripts: generators that receive the elapsed milliseconds on every tick

  function* wait(ms: number): Script {
    let t = 0
    while (t < ms) t += yield
  }

  // Glide along a slight arc, slow at both ends, so a path reads as a hand and not a straight tween.
  function* move(a: Agent, to: () => [number, number], ms?: number): Script {
    const x0 = a.x
    const y0 = a.y
    let [tx, ty] = to()
    const d = Math.hypot(tx - x0, ty - y0)
    const dur = ms ?? clamp(170 + d * 0.5, 170, 820)
    const bend = (rand() - 0.5) * 0.26 * d
    let t = 0
    while (t < dur) {
      t += yield
      ;[tx, ty] = to() // the page may scroll under us
      const k = ease(Math.min(1, t / dur))
      const len = Math.hypot(tx - x0, ty - y0) || 1
      const arc = Math.sin(Math.PI * k) * bend
      a.x = x0 + (tx - x0) * k - ((ty - y0) / len) * arc
      a.y = y0 + (ty - y0) * k + ((tx - x0) / len) * arc
    }
  }

  function reveal(i: number) {
    sound?.place(stage!.rect(i).left)
    if (layers[i].kind === 'text') covers.set(i, 0) // a button: show it with its label still painted over
    stage!.show(i)
  }

  function* drawBox(a: Agent, t: Task): Script {
    const s = stage!
    yield* move(a, () => {
      const r = s.rect(t.layer)
      return [r.left, r.top]
    })
    a.tool = 'cross'
    yield* wait(70)
    const r0 = s.rect(t.layer)
    const dur = clamp(230 + Math.hypot(r0.width, r0.height) * 0.42, 230, 780)
    const g = { p: 0, media: t.kind === 'media' }
    ghosts.set(t.layer, g)
    let e = 0
    while (e < dur) {
      e += yield
      g.p = easeOut(Math.min(1, e / dur))
      const r = s.rect(t.layer)
      a.x = r.left + r.width * g.p
      a.y = r.top + r.height * g.p
    }
    if (g.media) yield* wait(170)
    ghosts.delete(t.layer)
    reveal(t.layer)
    flashes.set(t.layer, 460)
    a.tool = 'arrow'
  }

  // Dividers and one-sided borders: click an anchor, pull the stroke to the other end.
  function* drawLine(a: Agent, t: Task): Script {
    const s = stage!
    const i = t.layer
    const segs = () => segments(s.rect(i), layers[i].sides)
    const state = { done: 0, p: 0 }
    for (let k = 0; k < segs().length; k++) {
      yield* move(a, () => [segs()[k][0], segs()[k][1]])
      a.tool = 'pen'
      yield* wait(60)
      state.done = k
      state.p = 0
      lines.set(i, state)
      const [x1, y1, x2, y2] = segs()[k]
      const dur = clamp(200 + Math.hypot(x2 - x1, y2 - y1) * 0.32, 200, 680)
      let e = 0
      while (e < dur) {
        e += yield
        state.p = ease(Math.min(1, e / dur))
        const [ax, ay, bx, by] = segs()[k]
        a.x = ax + (bx - ax) * state.p
        a.y = ay + (by - ay) * state.p
      }
      state.done = k + 1
      state.p = 0
    }
    yield* wait(80)
    lines.delete(i)
    s.show(i)
    sound?.stroke(a.x)
    a.tool = 'arrow'
  }

  // A repeated row or card: grab the finished original and drag a copy to where the next one goes.
  function* duplicate(a: Agent, t: Task): Script {
    const c = copies[t.copy]
    const from = () => c.from.getBoundingClientRect()
    const grip = (r: DOMRect): [number, number] => [r.left + Math.min(24, r.width / 2), r.top + Math.min(18, r.height / 2)]
    yield* move(a, () => grip(from()))
    yield* wait(100)
    const f = from()
    const to = c.el.getBoundingClientRect()
    const state = { p: 0, dist: Math.hypot(to.left - f.left, to.top - f.top) }
    dups.set(t.id, state)
    const dur = clamp(280 + state.dist * 0.5, 280, 900)
    let e = 0
    while (e < dur) {
      e += yield
      state.p = ease(Math.min(1, e / dur))
      ;[a.x, a.y] = grip(between(c, state.p))
    }
    dups.delete(t.id)
    for (const i of t.reveals) reveal(i)
    landed.set(t.copy, 420)
  }

  function between(c: (typeof copies)[number], p: number) {
    const f = c.from.getBoundingClientRect()
    const to = c.el.getBoundingClientRect()
    return new DOMRect(f.left + (to.left - f.left) * p, f.top + (to.top - f.top) * p, to.width, to.height)
  }

  function* dragGuide(a: Agent, t: Task): Script {
    const y = 80 + rand() * Math.max(40, chrome.h - 200)
    yield* move(a, () => [RULER / 2, y])
    yield* wait(90)
    const g = { x: RULER / 2 }
    dragging.add(g)
    let e = 0
    while (e < 460) {
      e += yield
      g.x = RULER / 2 + (t.x - scrollX - RULER / 2) * easeOut(Math.min(1, e / 460))
      a.x = g.x
    }
    dragging.delete(g)
    placed.push(t.x)
  }

  function* typeText(a: Agent, t: Task): Script {
    const s = stage!
    const i = t.layer
    const total = s.total(i)
    const painted = covers.has(i)
    const mid = (c: Caret): [number, number] => [c.x + 5, (c.top + c.bottom) / 2 + 3]
    yield* move(a, () => mid(s.caret(i, 0)))
    a.tool = 'text'
    yield* wait(90)
    const put = (n: number) => {
      const caret = painted ? s.caret(i, n) : s.type(i, n)
      if (painted) covers.set(i, n)
      typing.set(i, { caret, color: a.color })
      if (n) sound?.key(caret.x)
      ;[a.x, a.y] = mid(caret)
    }
    put(0)
    if (!painted) s.show(i)
    // whole block takes 0.35 to 2.4 s whatever its length; keystrokes are uneven so it reads as typing
    const per = clamp(total * 24, 350, 2400) / Math.max(1, total)
    let n = 0
    let due = per
    let acc = 0
    while (n < total) {
      acc += yield
      const before = n
      while (acc >= due && n < total) {
        acc -= due
        n++
        due = per * (0.4 + rand() * 1.2)
      }
      if (n !== before) put(n)
    }
    if (!painted) s.type(i, total)
    covers.delete(i)
    typing.delete(i)
    flashes.set(i, 260)
    a.tool = 'arrow'
  }

  function* wander(a: Agent): Script {
    const b = area()
    const x = clamp(a.x + (rand() - 0.5) * 320, b.left + 20, b.right - 20)
    const y = clamp(a.y + (rand() - 0.5) * 240, b.top + 20, b.bottom - 20)
    yield* move(a, () => [x, y], 700 + rand() * 900)
    yield* wait(200 + rand() * 600)
  }

  function* leave(a: Agent): Script {
    const b = area()
    const toSide = Math.min(a.x - b.left, b.right - a.x) < Math.min(a.y - b.top, b.bottom - a.y)
    const x = toSide ? (a.x < b.left + b.width / 2 ? b.left - 40 : b.right + 40) : a.x
    const y = toSide ? a.y : a.y < b.top + b.height / 2 ? b.top - 40 : b.bottom + 40
    yield* wait(rand() * 250)
    yield* move(a, () => [x, y], 520)
  }

  const scripts = { box: drawBox, media: drawBox, text: typeText, line: drawLine, dup: duplicate, guide: dragGuide }

  function spawn() {
    // enter from a random point just outside the area
    const b = area()
    const edge = Math.floor(rand() * 4)
    const along = rand()
    const x = edge === 0 ? b.left - 20 : edge === 1 ? b.right + 20 : b.left + along * b.width
    const y = edge === 2 ? b.top - 20 : edge === 3 ? b.bottom + 20 : b.top + along * b.height
    const n = agents.length
    agents.push({ x, y, color: o.palette[n % o.palette.length], name: o.names[n % o.names.length], tool: 'arrow', task: null, script: null, vx: 0, vy: 0, angle: 0 })
  }

  // Everything above this page y may be built. Scrolling to the very end unlocks whatever is left.
  function horizon() {
    if (!paged || scrollY + innerHeight >= document.documentElement.scrollHeight - 2) return Infinity
    return scrollY + innerHeight
  }

  // ---- one fixed step of the simulation

  // Finale: the crew flocks after the visitor's mouse (or drifts in a slow figure of eight until it moves).
  // Each scout steers toward its own spot around the target and away from close neighbours.
  function flock(dt: number) {
    flockTime += dt
    const t = flockTime / 1000
    const [tx, ty] = pointer ?? [chrome.w / 2 + Math.sin(t * 0.7) * chrome.w * 0.25, chrome.h / 2 + Math.sin(t * 1.4) * chrome.h * 0.18]
    agents.forEach((a, i) => {
      const ring = 16 * Math.sqrt(i + 1)
      const dx = tx + Math.cos(i * 2.4 + t) * ring - a.x
      const dy = ty + Math.sin(i * 2.4 + t) * ring - a.y
      const d = Math.hypot(dx, dy) || 1
      const want = Math.min(0.75, d * 0.004) // px per ms: fast when far, easing in when close
      let ax = (dx / d) * want - a.vx
      let ay = (dy / d) * want - a.vy
      for (const b of agents) {
        if (b === a) continue
        const sx = a.x - b.x
        const sy = a.y - b.y
        const gap = Math.hypot(sx, sy) || 1
        if (gap < 30) {
          ax += (sx / gap) * (30 - gap) * 0.02
          ay += (sy / gap) * (30 - gap) * 0.02
        }
      }
      const k = Math.min(1, dt * 0.006)
      a.vx += ax * k
      a.vy += ay * k
      a.x += a.vx * dt
      a.y += a.vy * dt
      if (Math.hypot(a.vx, a.vy) > 0.03) a.angle = Math.atan2(a.vy, a.vx) + (Math.PI * 3) / 4
    })
  }

  function tick(dt: number) {
    if (phase === 'finished') return flock(dt)
    time += dt
    velocity = velocity * 0.92 + ((Math.abs(scrollY - lastY) / dt) * 1000) * 0.08
    lastY = scrollY
    if (phase === 'intro') {
      while (agents.length < o.agents.min) spawn()
      if (time >= INTRO) {
        stage = new Stage(layers)
        phase = 'build'
        // Page wrappers and full-width section backgrounds are the canvas, not something to draw:
        // dragging out a box the size of the screen just greys everything. Show them at once.
        const big = 0.5 * chrome.w * chrome.h
        for (const t of queue.tasks) {
          if (t.kind === 'box' && layers[t.layer].kind === 'box' && layers[t.layer].w * layers[t.layer].h > big && t.after.every((id) => queue.tasks[id].state === 2)) {
            stage.show(t.layer)
            queue.finish(t)
          }
        }
      }
    }
    const bottom = horizon()
    if (phase === 'build') {
      const ready = queue.ready(bottom)
      // a bigger backlog and a faster scroll both call in more agents
      const want = clamp(Math.ceil(ready / 3) + Math.floor(velocity / 500), o.agents.min, o.agents.max)
      while (agents.length < want) spawn()
      idle = ready === 0 && queue.left > 0 && agents.every((a) => !a.task)
      // Tour: pan whenever nothing in view is waiting for an agent, slower while many are still busy,
      // so the page keeps moving at the crew's pace instead of stopping for every last task.
      if (tour && ready === 0 && queue.left > 0) {
        const free = agents.filter((a) => !a.task).length / agents.length
        pan += dt * TOUR_PX_PER_MS * Math.max(0.25, free)
        const px = Math.floor(pan)
        pan -= px
        if (px) scrollTo({ top: scrollY + px, behavior: 'instant' })
      }
      if (queue.left === 0) {
        phase = 'outro'
        idle = false
        for (const a of agents) a.script = leave(a)
      }
    }
    ruler = clamp(ruler + (phase === 'build' ? dt : -dt) / 300, 0, 1)
    for (const a of agents) {
      if (phase === 'build' && !a.task) {
        const t = queue.take(a.x + scrollX, a.y + scrollY, bottom, rand)
        if (t) {
          a.task = t
          a.tool = 'arrow'
          a.script = scripts[t.kind](a, t)
        }
      }
      if (!a.script) a.script = phase === 'outro' ? null : wander(a)
      if (a.script && a.script.next(dt).done) {
        a.script = null
        if (a.task) {
          queue.finish(a.task)
          log.push(`${Math.round(time)}:${a.task.id}:${agents.indexOf(a)}`)
          a.task = null
          o.onProgress?.(queue.done, queue.tasks.length)
        }
      }
    }
    for (const fading of [flashes, landed]) {
      for (const [i, ms] of fading) {
        if (ms <= dt) fading.delete(i)
        else fading.set(i, ms - dt)
      }
    }
    if (phase === 'outro' && agents.every((a) => !a.script)) finish()
  }

  function draw() {
    chrome.clear()
    if (phase === 'done') return
    if (phase === 'finished') {
      for (const a of agents) chrome.cursor(a.x, a.y, a.color, 'arrow', a.angle)
      return
    }
    if (boundsEl) chrome.clip(area())
    // the wash fades the whole screen, so it only belongs to a whole-page run
    if (phase === 'intro' && whole) chrome.wash(bg, ease(Math.min(1, time / INTRO)))
    if (stage) {
      if (paged && o.rulers) {
        for (const x of placed) chrome.guide(x - scrollX, ruler)
        for (const g of dragging) chrome.guide(g.x, 1)
      }
      for (const [i, g] of ghosts) {
        const r = stage.rect(i)
        const part = { left: r.left, top: r.top, width: r.width * g.p, height: r.height * g.p }
        chrome.ghost(part, g.media)
        chrome.select(part)
      }
      for (const [i, n] of covers) chrome.cover(stage.rest(i, n), layers[i].fill)
      for (const [i, l] of lines) {
        segments(stage.rect(i), layers[i].sides).forEach(([x1, y1, x2, y2], k) => {
          if (k <= l.done) chrome.line(x1, y1, x2, y2, k < l.done ? 1 : l.p)
        })
      }
      for (const [i, ms] of flashes) {
        if (typing.has(i)) continue
        const a = Math.min(1, ms / 180)
        // a finished text block gets the thin frame; a placed box (or a button waiting for its label) gets handles and a badge
        if (layers[i].kind === 'text' && !covers.has(i)) chrome.frame(stage.rect(i), a)
        else chrome.select(stage.rect(i), a)
      }
      for (const [id, d] of dups) chrome.copy(between(copies[queue.tasks[id].copy], d.p), d.dist * d.p)
      for (const [c, ms] of landed) chrome.copy(copies[c].el.getBoundingClientRect(), 0, Math.min(1, ms / 180))
      for (const [i, t] of typing) {
        const r = stage.rect(i)
        if (r.width < chrome.w * 1.1) chrome.frame(r) // a marquee wider than the screen would just draw stray lines
        chrome.caret(t.caret.x, t.caret.top, t.caret.bottom, t.color)
      }
      if (paged && o.rulers && ruler > 0) chrome.rulers(scrollX, scrollY, ruler)
    }
    for (const a of agents) chrome.cursor(a.x, a.y, a.color, a.tool)
    if (boundsEl) chrome.unclip()
    const busy = agents.filter((a) => a.task)
    hud?.update({
      agents: agents.length,
      faces: (busy.length ? busy : agents).slice(0, 5).map((a) => [a.color, a.name[0]]),
      built: queue.done,
      total: queue.tasks.length,
      idle: idle && !tour,
    })
  }

  function step(ms: number) {
    carry += ms * speed
    let guard = 0
    while (carry >= STEP && phase !== 'done' && guard++ < 600) {
      carry -= STEP
      tick(STEP)
    }
    draw()
  }

  function frame(now: number) {
    step(Math.min(100, now - (last || now)))
    last = now
    if (phase !== 'done') raf = requestAnimationFrame(frame)
  }

  const onMove = (e: PointerEvent) => {
    pointer = [e.clientX, e.clientY]
  }
  const onKey = (e: KeyboardEvent) => {
    if (e.key === 'Escape') destroy()
  }

  function restore() {
    stage?.destroy()
    stage = null
  }

  function destroy() {
    if (phase === 'done') return
    phase = 'done'
    cancelAnimationFrame(raf)
    restore()
    removeEventListener('keydown', onKey)
    removeEventListener('pointermove', onMove)
    sound?.close()
    chrome.destroy()
  }

  // The page is whole again. With a HUD the pill stays up with Replay and Done, and on a whole-page run the crew
  // comes back as a flock that follows the mouse until the visitor closes it. Without a HUD everything is removed.
  function finish() {
    sound?.done()
    if (hud) {
      phase = 'finished'
      restore()
      if (!whole) agents.length = 0
      hud.finish(agents.length, (o.autoplay ? performance.now() - t0 : time) / 1000)
    } else {
      destroy()
    }
    o.onDone?.()
  }

  addEventListener('keydown', onKey)
  addEventListener('pointermove', onMove, { passive: true })
  if (o.autoplay) raf = requestAnimationFrame(frame)

  return {
    step,
    setSpeed: (s) => void (speed = s),
    destroy,
    stats: () => ({ phase, total: queue.tasks.length, built: queue.done, ready: queue.ready(horizon()), active: agents.filter((a) => a.task).length, agents: agents.length, time, log }),
  }
}

export function assemble(target: Element = document.body, options: Options = {}): Handle {
  if (options.respectReducedMotion !== false && matchMedia('(prefers-reduced-motion: reduce)').matches) {
    // Reduced motion: no effect at all. The page is already on screen, so there is nothing gentler to show than leaving it alone.
    queueMicrotask(() => options.onDone?.())
    return { step() {}, setSpeed() {}, destroy() {}, stats: () => ({ phase: 'done', total: 0, built: 0, ready: 0, active: 0, agents: 0, time: 0, log: [] }) }
  }
  const replay = () => {
    run.destroy()
    run = createRun(target, options, replay)
  }
  let run = createRun(target, options, replay)
  return { step: (ms) => run.step(ms), setSpeed: (s) => run.setSpeed(s), destroy: () => run.destroy(), stats: () => run.stats() }
}

// A plain script tag gets <assemble-stage> without calling anything.
define()
