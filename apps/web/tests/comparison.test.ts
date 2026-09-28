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
