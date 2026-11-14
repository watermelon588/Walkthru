import { test } from 'node:test'
import assert from 'node:assert/strict'
import { worklogRows } from '../src/lib/harness.ts'

const event = { sequence: 1, step: 1, node: 'assess', reason: 'missing_outcome_expectation', progress: 0, checkpoint: 1 }

test('legacy and malformed reports have no invented worklog', () => {
  for (const value of [undefined, null, {}, 'bad', [null], [{ ...event, step: '1' }], [{ ...event, reason: '<script>' }]]) {
    assert.deepEqual(worklogRows(value), [])
  }
})

test('missing success criteria are explained as uncertainty and fields are allowlisted', () => {
  const [row] = worklogRows([{ ...event, thought: 'Invented success', text: 'private form value' }])
  assert.match(row.explanation, /no observable success condition/)
  assert.equal(row.progress, 0)
  assert.ok(!JSON.stringify(row).includes('private form'))
  assert.ok(!JSON.stringify(row).includes('Invented success'))
})

test('forward compatible reasons do not become success claims or raw markup', () => {
  const [row] = worklogRows([{ ...event, reason: 'future_reason', action: '<img>', checkpoint: 20 }])
  assert.match(row.explanation, /newer version/)
  assert.equal(row.action, null)
  assert.equal(row.checkpoint, null)
  assert.equal(worklogRows(Array.from({ length: 300 }, () => event)).length, 256)
})
