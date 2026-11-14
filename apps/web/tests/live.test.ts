import { test } from 'node:test'
import assert from 'node:assert/strict'
import { anyActive, believedDone, moments, momentPaths, restingPoint, cardLine, endedEarly, cursorAt, framePaths, inProgress, reportsPending, siteUrl, type LiveCard, type LiveTest } from '../src/lib/live.ts'
import type { Step } from '../src/lib/runs.ts'

const step = (evidence?: Step['evidence'], action: Step['action'] = 'click'): Step => ({ thought: 't', action, target_id: null, text: null, confusion: 0, url: 'https://a.example/', evidence })
const frame = (n: number, extra: Partial<NonNullable<Step['evidence']>> = {}) => ({ screenshot_path: `r/step-0${n}.jpg`, captured_at: '2026-11-12T00:00:00Z', result_url: 'https://a.example/', width: 1280, height: 900, ...extra })
const card = (extra: Partial<LiveCard>): LiveCard => ({ id: 'c', persona: 'first_timer', status: 'queued', error: null, run_id: null, created_at: '2026-11-12T00:00:00Z', updated_at: '2026-11-12T00:00:00Z', steps: [], report_ready: false, ...extra })
const live = (...runs: LiveCard[]): LiveTest => ({ group_id: 'g', site: 'https://a.example', goal: 'g', runs })

test('the cursor rests on the latest measured target and is never invented', () => {
  const steps = [step(frame(1), 'scroll'), step(frame(2, { pointer: { x: 0.2, y: 0.3 }, aim_path: 'r/step-02-aim.jpg' })), step(frame(3), 'scroll')]
  assert.equal(cursorAt(steps, 0), null)
  assert.deepEqual(cursorAt(steps, 1), { x: 0.2, y: 0.3 })
  assert.deepEqual(cursorAt(steps, 2), { x: 0.2, y: 0.3 })
  assert.deepEqual(cursorAt(steps, 99), { x: 0.2, y: 0.3 })
  assert.equal(cursorAt([], 0), null)
})

test('every stored frame is requested once, aim frames first', () => {
  const steps = [step(frame(1)), step(frame(2, { aim_path: 'r/step-02-aim.jpg' })), step(), step(frame(2, { aim_path: 'r/step-02-aim.jpg' }))]
  assert.deepEqual(framePaths(steps), ['r/step-01.jpg', 'r/step-02-aim.jpg', 'r/step-02.jpg'])
})

test('card lines state the queue position and never estimate a time', () => {
  assert.equal(cardLine(card({ ahead: 2 })), 'Queued, 2 ahead of you')
  assert.equal(cardLine(card({ ahead: 0 })), 'Queued, starting next')
  assert.equal(cardLine(card({ status: 'running' }), Date.parse('2026-11-12T00:00:10Z')), 'Opening the site')
  assert.equal(cardLine(card({ status: 'running', run_id: 'r', steps: [step()] })), 'Walking the site · 1 step')
  assert.equal(cardLine(card({ status: 'finished', run_id: 'r', steps: [step(), step()] })), 'Finished · 2 steps')
  assert.equal(cardLine(card({ status: 'blocked', error: 'no' })), 'Could not run')
})

test('polling continues until the queue is done and each journey has its report', () => {
  assert.equal(anyActive(live(card({ status: 'finished' }), card({ status: 'queued' }))), true)
  const done = live(card({ status: 'finished', run_id: 'r' }), card({ status: 'blocked' }))
  assert.equal(anyActive(done), false)
  assert.equal(reportsPending(done), true)
  assert.equal(reportsPending(live(card({ status: 'finished', run_id: 'r', report_ready: true }), card({ status: 'blocked' }))), false)
  assert.equal(reportsPending(live(card({ status: 'running', run_id: 'r' }))), false)
})

test('the pill uses the page-derived label in the present tense', () => {
  assert.equal(inProgress('Clicked "See pricing"', 'click'), 'Clicking "See pricing"')
  assert.equal(inProgress('Typed in "Search"', 'type'), 'Typing in "Search"')
  assert.equal(inProgress('Scrolled down', 'scroll'), 'Scrolling down')
  assert.equal(inProgress(undefined, 'back'), 'Going back')
})

test('site addresses accept a bare domain and refuse non-web input', () => {
  assert.equal(siteUrl(' yoursite.com '), 'https://yoursite.com/')
  assert.equal(siteUrl('http://a.example/pricing'), 'http://a.example/pricing')
  assert.equal(siteUrl('localhost'), null)
  assert.equal(siteUrl('javascript:alert(1)'), null)
  assert.equal(siteUrl(''), null)
})

test('a journey that ran but did not reach the goal is never called finished', () => {
  assert.equal(cardLine(card({ status: 'finished', run_id: 'r', run_status: 'agent_lost', steps: [step()] })), 'Stopped early · 1 step')
  assert.equal(cardLine(card({ status: 'finished', run_id: 'r', run_status: 'done', steps: [step()] })), 'Finished · 1 step')
  assert.equal(endedEarly({ run_status: 'gave_up' }), true)
  assert.equal(endedEarly({ run_status: 'running' }), false)
  assert.equal(endedEarly({}), false)
})

test('a test user that believed it was done is told apart from one that was lost', () => {
  const said = (thought: string) => [{ ...step(), thought }]
  assert.equal(believedDone({ run_status: 'agent_lost', steps: said('The form is here. (Walkthru could not confirm the requested outcome; unresolved checkpoints remain.)') }), true)
  assert.equal(believedDone({ run_status: 'agent_lost', steps: said('I cannot find the menu.') }), false)
  assert.equal(believedDone({ run_status: 'done', steps: said('could not confirm the requested outcome') }), false)
  assert.equal(believedDone({ run_status: 'agent_lost', steps: [] }), false)
})

test('each page is paired with what the test user said while looking at it', () => {
  const said = (thought: string, action: Step['action'], evidence?: Step['evidence']): Step => ({ ...step(evidence, action), thought })
  const steps = [
    said('I will open About', 'click', frame(1, { label: 'Clicked "About"', pointer: { x: 0.4, y: 0.1 }, aim_path: 'r/step-01-aim.jpg' })),
    said('The name is here, let me read on', 'scroll', frame(2, { label: 'Scrolled down' })),
    said('Rohit, a backend engineer. Done.', 'give_up', frame(3, { label: 'Stopped here' })),
  ]
  const list = moments(steps, 'r')
  assert.deepEqual(list.map((m) => [m.label, m.frame, m.thought]), [
    ['Landed on the page', 'r/step-00.jpg', 'I will open About'],
    ['Clicked "About"', 'r/step-01.jpg', 'The name is here, let me read on'],
    ['Scrolled down', 'r/step-02.jpg', 'Rohit, a backend engineer. Done.'],
  ])
  assert.equal(list[2].ended, 'give_up')
  assert.deepEqual(restingPoint(list, 0), null)
  assert.deepEqual(restingPoint(list, 2), { x: 0.4, y: 0.1 })
  assert.deepEqual(momentPaths(list), ['r/step-00.jpg', 'r/step-01-aim.jpg', 'r/step-01.jpg', 'r/step-02.jpg'])
})

test('an action still in progress belongs to the page it started from', () => {
  const list = moments([{ ...step(undefined, 'click'), thought: 'I will open About' }], 'r')
  assert.equal(list.length, 1)
  assert.equal(list[0].doing, 'Clicking')
  assert.equal(list[0].thought, 'I will open About')
  assert.deepEqual(moments([], 'r'), [])
  assert.equal(moments([step(frame(1, { aim_path: 'r/step-01-aim.jpg' }))])[0].frame, 'r/step-01-aim.jpg') // older run, no landing frame
})
