// Pure scheduling: no DOM in here, so it runs under `node --test`.

export type LayerKind = 'box' | 'media' | 'text' | 'line'
/** 'dup' alt-drags a copy of a repeated component; 'guide' pulls a ruler guide out */
export type TaskKind = LayerKind | 'dup' | 'guide'

/** state: 0 waiting, 1 an agent has it, 2 done */
export interface Task {
  id: number
  /** layer index, or -1 for dup and guide tasks */
  layer: number
  kind: TaskKind
  x: number
  y: number
  /** ids of the tasks that must finish first */
  after: number[]
  state: 0 | 1 | 2
  /** index into the copies list for a dup task, else -1 */
  copy: number
  /** layers a dup task shows when the copy lands */
  reveals: number[]
}

export interface Plannable {
  kind: LayerKind
  x: number
  y: number
  parent: number
  /** solid background of a text element that is also a box (button, pill), else '' */
  fill: string
  /** which duplicate this layer sits in, or -1 */
  copy: number
  /** group id when this layer is part of the component the duplicates are copied from, else -1 */
  master: number
}

export interface CopyPlan {
  group: number
  x: number
  y: number
}

export interface Guide {
  x: number
  y: number
}

/** mulberry32: small seeded generator so a run can be replayed exactly */
export function rng(seed: number): () => number {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

export const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v))
export const ease = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2)
export const easeOut = (t: number) => 1 - Math.pow(1 - t, 3)

/** Left edges that several text blocks share: these are where a designer would drop a ruler guide. */
export function guides(layers: { kind: LayerKind; x: number; y: number }[], min = 4, max = 3): Guide[] {
  const seen = new Map<number, { n: number; y: number }>()
  for (const l of layers) {
    if (l.kind !== 'text') continue
    const x = Math.round(l.x)
    const g = seen.get(x)
    if (g) {
      g.n++
      g.y = Math.min(g.y, l.y)
    } else {
      seen.set(x, { n: 1, y: l.y })
    }
  }
  return [...seen]
    .filter(([, g]) => g.n >= min)
    .sort((a, b) => b[1].n - a[1].n || a[0] - b[0])
    .slice(0, max)
    .map(([x, g]) => ({ x, y: g.y }))
}

/**
 * One task per layer, with three exceptions:
 * - a painted label is two (draw the box, then type into it);
 * - layers inside a duplicate get one shared 'dup' task that lands the whole copy once the original is finished,
 *   after which only its text is retyped;
 * - guides get a task each and nothing waits for them.
 * Children wait for their parent's box.
 */
export function plan(layers: Plannable[], copies: CopyPlan[] = [], guideList: Guide[] = []): Task[] {
  const tasks: Task[] = []
  const first: number[] = []
  const dup: number[] = []
  const masters = new Map<number, number[]>()
  const add = (kind: TaskKind, layer: number, x: number, y: number, after: number[], copy = -1) => tasks.push({ id: tasks.length, layer, kind, x, y, after, state: 0, copy, reveals: [] }) - 1

  for (const g of guideList) add('guide', -1, g.x, g.y, [])
  layers.forEach((l, i) => {
    if (l.copy >= 0) {
      const c = copies[l.copy]
      dup[l.copy] ??= add('dup', -1, c.x, c.y, [...(masters.get(c.group) ?? [])], l.copy)
      const d = dup[l.copy]
      if (l.kind !== 'text' || l.fill) tasks[d].reveals.push(i)
      first[i] = l.kind === 'text' ? add('text', i, l.x, l.y, [d]) : d
      return
    }
    const after = l.parent >= 0 ? [first[l.parent]] : []
    const ids = [(first[i] = add(l.kind === 'text' && l.fill ? 'box' : l.kind, i, l.x, l.y, after))]
    if (l.kind === 'text' && l.fill) ids.push(add('text', i, l.x, l.y, [first[i]]))
    if (l.master >= 0) masters.set(l.master, [...(masters.get(l.master) ?? []), ...ids])
  })
  return tasks
}

export class Queue {
  tasks: Task[]
  done = 0

  constructor(tasks: Task[]) {
    this.tasks = tasks
  }

  open(t: Task, bottom: number) {
    return t.state === 0 && t.y < bottom && t.after.every((id) => this.tasks[id].state === 2)
  }

  /** how many tasks could start right now above `bottom` (page coordinates) */
  ready(bottom: number) {
    let n = 0
    for (const t of this.tasks) if (this.open(t, bottom)) n++
    return n
  }

  /** Hand the agent at (x, y) its next task: top of the page first, then nearest, with a little jitter so agents spread out. */
  take(x: number, y: number, bottom: number, rand: () => number): Task | null {
    let best: Task | null = null
    let score = Infinity
    for (const t of this.tasks) {
      if (!this.open(t, bottom)) continue
      const s = t.y + 0.35 * Math.hypot(t.x - x, t.y - y) + rand() * 140
      if (s < score) {
        score = s
        best = t
      }
    }
    if (best) best.state = 1
    return best
  }

  finish(t: Task) {
    t.state = 2
    this.done++
  }

  get left() {
    return this.tasks.length - this.done
  }
}
