import { test } from 'node:test'
import assert from 'node:assert/strict'
import { confirmedAccessRequest } from '../src/lib/accessRequest.ts'

const row = { id: 'request-a', plan: 'pro', note: 'Test signup', status: 'pending', created_at: new Date().toISOString() }
test('lost access-request reply is reconciled from saved state with one mutation', async () => {
  let writes = 0, reads = 0
  const result = await confirmedAccessRequest(async () => { writes++; throw new TypeError('Failed to fetch') }, async () => { reads++; return { requests: [row] } }, async () => true, row.plan, row.note)
  assert.equal(result.id, row.id)
  assert.equal(writes, 1)
  assert.equal(reads, 1)
})
test('a response lost after a quick founder decision still reads the newly saved request', async () => {
  assert.equal((await confirmedAccessRequest(async () => { throw new Error('lost') }, async () => ({ requests: [{ ...row, status: 'approved' }] }), async () => true, row.plan, row.note)).id, row.id)
})
test('different and historical requests never masquerade as the current submission', async () => {
  const fail = async () => { throw new Error('original failure') }
  for (const other of [{ ...row, note: 'Different goal' }, { ...row, plan: 'plus' }, { ...row, status: 'approved', created_at: '2020-01-01' }]) {
    await assert.rejects(confirmedAccessRequest(fail, async () => ({ requests: [other] }), async () => true, row.plan, row.note), /original failure/)
  }
})
test('unconfirmed state and account changes never trigger an automatic second mutation', async () => {
  const fail = async () => { throw new Error('lost') }
  await assert.rejects(confirmedAccessRequest(fail, async () => { throw new Error('offline') }, async () => true, row.plan, row.note), /Reload Plan & billing/)
  let reads = 0
  await assert.rejects(confirmedAccessRequest(fail, async () => { reads++; return { requests: [row] } }, async () => false, row.plan, row.note), /account changed/)
  assert.equal(reads, 0)
  let checks = 0
  await assert.rejects(confirmedAccessRequest(fail, async () => ({ requests: [row] }), async () => ++checks === 1, row.plan, row.note), /account changed/)
})
