import { test } from 'node:test'
import assert from 'node:assert/strict'
import { accountIdentity, PlanCache } from '../src/lib/planCache.ts'
import type { PlanSummary } from '../src/lib/runs.ts'

const plan = (left: number): PlanSummary => ({ plan: 'free', runs_allowed: 5, runs_left: left, expires_at: null, max_steps: 10, logged_in: false, personas: [], sites: 1, sites_used: [] })
function deferred<T>() {
  let resolve!: (value: T) => void, reject!: (reason: Error) => void
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}

test('plan display shares an in-flight request and expires after sixty seconds', async () => {
  const cache = new PlanCache(), response = deferred<PlanSummary>()
  let reads = 0
  const load = () => { reads++; return response.promise }
  const first = cache.read('a:token', load, false, 0)
  assert.equal(cache.read('a:token', load, false, 1), first)
  response.resolve(plan(5)); await first
  await cache.read('a:token', load, false, 59_999)
  assert.equal(reads, 1)
  await cache.read('a:token', load, false, 60_000)
  assert.equal(reads, 2)
})

test('one notification invalidation gives all meters one fresh promise, replacing stale pending data', async () => {
  const cache = new PlanCache(), old = deferred<PlanSummary>(), fresh = deferred<PlanSummary>()
  const stale = cache.read('a:token', () => old.promise)
  const staleFailure = assert.rejects(stale, /account or plan changed/)
  cache.clear() // Single module-level notification listener invalidates before mounted meter listeners.
  let reads = 0
  const load = () => { reads++; return fresh.promise }
  const mini = cache.read('a:token', load), meter = cache.read('a:token', load)
  assert.equal(mini, meter)
  fresh.resolve(plan(4)); old.resolve(plan(5))
  assert.deepEqual(await Promise.all([mini, meter]), [plan(4), plan(4)])
  await staleFailure
  assert.equal(reads, 1)
})

test('account switches, token rotation and logout reject late data and never reuse another identity', async () => {
  for (const identity of ['b:token', 'a:new-token', '']) {
    const cache = new PlanCache(), old = deferred<PlanSummary>()
    const pending = cache.read('a:token', () => old.promise)
    const rejection = assert.rejects(pending, /account or plan changed/)
    cache.observe(identity)
    old.resolve(plan(5)); await rejection
    if (identity) assert.deepEqual(await cache.read(identity, async () => plan(1)), plan(1))
    else await assert.rejects(cache.read('', async () => plan(1)), /Sign in first/)
  }
})

test('signing out then returning to the same login cannot resurrect its pending response', async () => {
  const cache = new PlanCache(), old = deferred<PlanSummary>()
  const pending = cache.read('a:token', () => old.promise)
  const rejection = assert.rejects(pending, /account or plan changed/)
  cache.clear()
  assert.deepEqual(await cache.read('a:token', async () => plan(2)), plan(2))
  old.resolve(plan(5)); await rejection
})

test('an old failed request cannot erase a newer fresh cache; failures remain retryable', async () => {
  const cache = new PlanCache(), old = deferred<PlanSummary>()
  const pending = cache.read('a:token', () => old.promise)
  const rejection = assert.rejects(pending, /offline/)
  const fresh = cache.read('a:token', async () => plan(3), true)
  old.reject(new Error('offline')); await rejection
  assert.equal(cache.read('a:token', async () => plan(1)), fresh)
  assert.deepEqual(await fresh, plan(3))
  cache.clear()
  await assert.rejects(cache.read('a:token', async () => { throw new Error('503 counts unavailable') }), /503/)
  assert.deepEqual(await cache.read('a:token', async () => plan(2)), plan(2))
})

test('account identity includes the full token and is memory-only with an empty signed-out identity', () => {
  assert.equal(accountIdentity(null), '')
  assert.notEqual(accountIdentity({ user: { id: 'a' }, access_token: 'one' }), accountIdentity({ user: { id: 'a' }, access_token: 'two' }))
})

test('retry invalidation is consumed immediately, so a later account switch still shares one new read', async () => {
  const cache = new PlanCache(), old = deferred<PlanSummary>()
  await assert.rejects(cache.read('a:token', async () => { throw new Error('offline') }), /offline/)
  cache.clear() // Retry handler consumes invalidation before the effect; effects always read without freshness.
  const pending = cache.read('a:token', () => old.promise)
  const rejection = assert.rejects(pending, /account or plan changed/)
  cache.observe('b:token')
  let reads = 0
  const load = async () => { reads++; return plan(2) }
  const mini = cache.read('b:token', load), meter = cache.read('b:token', load)
  assert.equal(mini, meter)
  assert.deepEqual(await Promise.all([mini, meter]), [plan(2), plan(2)])
  old.resolve(plan(5)); await rejection
  assert.equal(reads, 1)
})
