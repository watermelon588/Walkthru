import { test } from 'node:test'
import assert from 'node:assert/strict'
import { comparable, leaderGap, value } from '../src/lib/comparison.ts'
import type { CompareSite } from '../src/lib/runs.ts'

const own: CompareSite = { site: 'https://mine.example', scope: 'public', yours: true, score: 70, areas: { seo: 60, geo: 80 }, geo: 80 }
const rival: CompareSite = { site: 'https://rival.example', scope: 'public', score: 85, areas: { seo: 90, geo: 80 }, geo: 80 }

test('failed and missing scores are not zero; a real zero remains measured', () => {
  assert.equal(value({ ...own, error: 'Failed' }, 'score'), null)
  assert.equal(value({ site: own.site }, 'score'), null)
  assert.equal(value({ ...own, score: NaN }, 'score'), null)
  assert.equal(value({ ...own, score: 101 }, 'score'), null)
  assert.equal(value({ ...own, score: 0 }, 'score'), 0)
})
test('total gaps require matching measured areas, not just two numbers', () => {
  assert.equal(leaderGap([own, rival], 'score')?.gap, -15)
  assert.equal(leaderGap([own, { ...rival, areas: { seo: 90 } }], 'score'), null)
  assert.equal(leaderGap([{ ...own, areas: undefined }, rival], 'score'), null)
  assert.equal(leaderGap([{ ...own, scope: undefined }, rival], 'score'), null)
})
test('speed gaps distinguish performance-only from accessibility-only checks', () => {
  const a = { ...own, areas: { speed: 80 }, checks: { performance: 'complete' } }
  const b = { ...rival, areas: { speed: 90 }, checks: { accessibility: 'complete' } }
  assert.equal(comparable(a, b, 'speed'), false)
  assert.equal(comparable(a, { ...b, checks: a.checks }, 'speed'), true)
  assert.equal(comparable(a, b, 'score'), false)
})
test('uses strongest available competitor, handles ties and owner failure', () => {
  assert.equal(leaderGap([own, rival, { ...rival, geo: 95 }], 'geo')?.gap, -15)
  assert.equal(leaderGap([own, rival], 'geo')?.gap, 0)
  assert.equal(leaderGap([{ ...own, error: 'Failed' }, rival], 'geo'), null)
  assert.equal(leaderGap([own], 'geo'), null)
})

// R-S13: the recheck verdict and counts read plainly; nothing but a like-for-like pass says Fixed.
test('recheck labels and counts', async () => {
  const { RECHECK_LABEL, recheckCounts } = await import('../src/lib/comparison.ts')
  assert.equal(RECHECK_LABEL.fixed, 'Fixed')
  assert.notEqual(RECHECK_LABEL.not_rechecked, 'Fixed')
  assert.notEqual(RECHECK_LABEL.not_comparable, 'Fixed')
  const base = { fingerprint: 'assertion:/d|Active|Filtered records', identity: '/d, Filter: Active, Filtered records', reason: 'r' }
  assert.equal(recheckCounts({ ...base, verdict: 'fixed', before: 'failed', after: 'passed', before_count: 3, after_count: 2, expected_count: 2 }),
    'Before: failed (3). Now: passed (2), expected 2.')
  assert.equal(recheckCounts({ ...base, verdict: 'not_rechecked', before: 'failed', after: null, before_count: 3, expected_count: 2 }),
    'Before: failed (3). Now: not checked, expected 2.')
  assert.equal(recheckCounts({ ...base, verdict: 'not_rechecked', before: 'failed', after: 'inconclusive', before_count: 3, after_count: null }),
    'Before: failed (3). Now: inconclusive (no count).')
})
