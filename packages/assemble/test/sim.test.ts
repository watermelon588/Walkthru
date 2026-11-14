import assert from 'node:assert/strict'
import { test } from 'node:test'
import { guides, plan, Queue, rng, type CopyPlan, type Plannable } from '../src/sim.ts'

const L = (kind: Plannable['kind'], y: number, parent = -1, fill = '', copy = -1, master = -1): Plannable => ({ kind, x: 0, y, parent, fill, copy, master })

// Drain the queue with one agent and return the order tasks were handed out.
function drain(layers: Plannable[], seed: number, bottom = Infinity, copies: CopyPlan[] = []) {
  const q = new Queue(plan(layers, copies))
  const rand = rng(seed)
  const order: number[] = []
  for (;;) {
    const t = q.take(0, 0, bottom, rand)
    if (!t) break
    order.push(t.id)
    q.finish(t)
  }
  return { order, q }
}

test('rng is repeatable and in [0, 1)', () => {
  const a = rng(7)
  const b = rng(7)
  for (let i = 0; i < 100; i++) {
    const v = a()
    assert.equal(v, b())
    assert.ok(v >= 0 && v < 1)
  }
})

test('a painted label becomes a box task then a text task', () => {
  const tasks = plan([L('text', 10, -1, 'rgb(0, 0, 0)'), L('text', 20)])
  assert.deepEqual(tasks.map((t) => [t.kind, t.after]), [['box', []], ['text', [0]], ['text', []]])
})

test('no task is handed out before the ones it depends on', () => {
  // child sits above its parent on the page, so only the dependency can hold it back
  const layers = [L('box', 500), L('text', 0, 0), L('media', 5, 0), L('line', 2, 0), L('text', 900, -1, 'rgb(1, 1, 1)')]
  const { order, q } = drain(layers, 3)
  assert.equal(order.length, q.tasks.length)
  for (const t of q.tasks) for (const dep of t.after) assert.ok(order.indexOf(dep) < order.indexOf(t.id))
})

test('a held task is not offered while its parent is only in progress', () => {
  const q = new Queue(plan([L('box', 0), L('text', 10, 0)]))
  const rand = rng(1)
  const parent = q.take(0, 0, Infinity, rand)
  assert.equal(parent?.id, 0)
  assert.equal(q.take(0, 0, Infinity, rand), null)
  q.finish(parent!)
  assert.equal(q.take(0, 0, Infinity, rand)?.id, 1)
})

test('work is top down and stops at the bottom of the view', () => {
  const layers = [L('box', 4000), L('box', 0), L('box', 2000), L('box', 9000)]
  const { order, q } = drain(layers, 5, 5000)
  assert.deepEqual(order, [1, 2, 0])
  assert.equal(q.left, 1)
  assert.equal(q.ready(5000), 0)
  assert.equal(q.ready(Infinity), 1)
})

test('same seed, same order; different seed may differ but still completes', () => {
  const layers = Array.from({ length: 60 }, (_, i) => L(i % 3 ? 'text' : 'box', (i * 37) % 400))
  assert.deepEqual(drain(layers, 42).order, drain(layers, 42).order)
  assert.equal(drain(layers, 43).order.length, 60)
})

test('a duplicate is one drag after the whole original, then only its text is retyped', () => {
  // original card: box, title, image, button. one copy of it with the same four layers.
  const card = (copy: number, master: number, base: number): Plannable[] => [
    L('box', base, -1, '', copy, master),
    L('text', base + 10, 0, '', copy, master),
    L('media', base + 20, 0, '', copy, master),
    L('text', base + 30, 0, 'rgb(0, 0, 0)', copy, master),
  ]
  const tasks = plan([...card(-1, 0, 0), ...card(0, -1, 100)], [{ group: 0, x: 0, y: 100 }])
  const original = tasks.filter((t) => t.layer >= 0 && t.layer < 4).map((t) => t.id)
  assert.equal(original.length, 5, 'box, text, media, button box, button label')
  const dup = tasks.find((t) => t.kind === 'dup')!
  assert.deepEqual(dup.after, original, 'waits for every task of the original')
  assert.deepEqual(dup.reveals, [4, 6, 7], 'lands the box, the image and the button; plain text is typed')
  const retyped = tasks.filter((t) => t.layer >= 4)
  assert.deepEqual(retyped.map((t) => [t.kind, t.layer, t.after]), [['text', 5, [dup.id]], ['text', 7, [dup.id]]])
  const { order, q } = drain([...card(-1, 0, 0), ...card(0, -1, 100)], 9, Infinity, [{ group: 0, x: 0, y: 100 }])
  assert.equal(order.length, q.tasks.length)
  assert.ok(order.indexOf(dup.id) > Math.max(...original.map((id) => order.indexOf(id))))
})

test('guides are the left edges shared by several text blocks', () => {
  const at = (x: number, y: number, kind: Plannable['kind'] = 'text') => ({ kind, x, y })
  const layers = [at(80, 500), at(80.3, 40), at(80, 900), at(79.8, 700), at(300, 10), at(300, 20), at(80, 5, 'box')]
  assert.deepEqual(guides(layers), [{ x: 80, y: 40 }])
  assert.deepEqual(guides(layers, 2), [{ x: 80, y: 40 }, { x: 300, y: 10 }])
  const tasks = plan([], [], guides(layers))
  assert.deepEqual(tasks.map((t) => [t.kind, t.x, t.after]), [['guide', 80, []]])
})
