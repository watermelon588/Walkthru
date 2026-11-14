import assert from 'node:assert/strict'
import { test } from 'node:test'
import { pickFormat, sceneAt, storyboard, videoName, wrapLines } from '../src/lib/sessionVideo.ts'

const m = (thought: string, pointer?: { x: number; y: number }) => ({ thought, pointer })

test('storyboard: the cursor travels only to a measured point, and longer comments stay up longer', () => {
  const { scenes, total } = storyboard([m('Short.'), m('x'.repeat(60), { x: 0.5, y: 0.5 }), m('', undefined), m('y'.repeat(400), { x: 0.1, y: 0.1 })])
  assert.deepEqual(scenes.map((s) => s.travel), [0, 1100, 0, 1100], 'no travel for the first page or a step without a target')
  assert.equal(scenes[0].hold, 2000, 'short comments get the minimum')
  assert.equal(scenes[1].hold, 900 + 60 * 38)
  assert.equal(scenes[3].hold, 4600, 'long comments are capped')
  assert.equal(scenes[1].start, scenes[0].hold)
  assert.equal(total, scenes[3].start + scenes[3].travel + scenes[3].hold)
  assert.equal(sceneAt(scenes, 0).index, 0)
  assert.equal(sceneAt(scenes, scenes[2].start).index, 2)
  assert.equal(sceneAt(scenes, total + 5000).index, 3)
  assert.deepEqual(storyboard([]), { scenes: [], total: 0 })
})

test('wrapLines wraps on words and cuts to the line limit with an ellipsis', () => {
  const measure = (s: string) => s.length * 10
  assert.deepEqual(wrapLines('one two three four', 90, 3, measure), ['one two', 'three', 'four'])
  const cut = wrapLines('alpha beta gamma delta epsilon zeta', 100, 2, measure)
  assert.equal(cut.length, 2)
  assert.ok(cut[1].endsWith('…') && measure(cut[1]) <= 100)
  assert.deepEqual(wrapLines('', 100, 2, measure), [])
  assert.deepEqual(wrapLines('unbreakablylongword next', 50, 2, measure), ['unbreakablylongword', 'next'])
})

test('pickFormat prefers MP4 and falls back to WebM', () => {
  assert.deepEqual(pickFormat((t) => t.startsWith('video/mp4')), { mime: 'video/mp4;codecs=avc1.42E01E', ext: 'mp4' })
  assert.deepEqual(pickFormat((t) => t === 'video/webm'), { mime: 'video/webm', ext: 'webm' })
  assert.equal(pickFormat(() => false), null)
})

test('videoName is a safe file name', () => {
  assert.equal(videoName('https://My-Site.com/pricing?x=1', 'First-time visitor', 'mp4'), 'walkthru-my-site-com-pricing-x-1-first-time-visitor.mp4')
  assert.equal(videoName('', 'buyer', 'webm'), 'walkthru-visit-buyer.webm')
})
