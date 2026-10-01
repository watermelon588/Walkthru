import { test } from 'node:test'
import assert from 'node:assert/strict'
import { connectSession, extensionMessage, sameLogin, type ExtensionRuntime } from '../src/lib/sessionHandoff.ts'

const session = { access_token: 'a', refresh_token: 'r', expires_at: 2_000_000_000, user: { id: 'user-a' } }

test('website handoff requires an acknowledged challenge and current identity', async () => {
  const sent: any[] = []
  const runtime: ExtensionRuntime = { sendMessage: (_id, msg, cb) => { sent.push(msg); cb(sent.length === 1 ? { ok: true, challenge: 'nonce' } : { ok: true }) } }
  assert.equal(await connectSession(runtime, 'named-extension', async () => session, () => true), true)
  assert.equal(sent[1].session.user_id, session.user.id)
  assert.equal(sent[1].session.user, undefined)
  assert.equal(await connectSession(runtime, 'named-extension', async () => session, () => true), false)
})

test('logout or account switch during handoff prevents credential transfer', async () => {
  let reads = 0, sends = 0
  const runtime: ExtensionRuntime = { sendMessage: (_id, _msg, cb) => { sends++; cb({ ok: true, challenge: 'nonce' }) } }
  assert.equal(await connectSession(runtime, 'id', async () => ++reads === 1 ? session : null, () => true), false)
  assert.equal(sends, 1)
  reads = 0
  assert.equal(await connectSession(runtime, 'id', async () => ++reads === 1 ? session : { ...session, user: { id: 'user-b' } }, () => true), false)
  assert.equal(sends, 2)
  let allowed = true
  runtime.sendMessage = (_id, _msg, cb) => { allowed = false; cb({ ok: true, challenge: 'nonce' }) }
  assert.equal(await connectSession(runtime, 'id', async () => session, () => allowed), false)
})

test('missing, rejected and failed extension never count as a successful connection', async () => {
  assert.equal(await extensionMessage(undefined, 'id', {}), null)
  assert.equal(await connectSession({ sendMessage: (_id, _msg, cb) => cb({ ok: false }) }, 'id', async () => session, () => true), false)
  assert.equal(await extensionMessage({ sendMessage: () => { throw new Error('not installed') } }, 'id', {}), null)
  assert.equal(await extensionMessage({ sendMessage: () => {} }, 'id', {}), null)
})

test('logout identity fence allows refresh but rejects another account or a newer login of the same user', () => {
  const token = (id: string, marker: string) => `${marker}.${btoa(JSON.stringify({ session_id: id }))}.signature`
  const id = '00000000-0000-0000-0000-000000000001'
  const first = { ...session, access_token: token(id, 'old') }
  assert.equal(sameLogin(first, { ...first, access_token: token(id, 'fresh') }), true)
  assert.equal(sameLogin(first, { ...first, access_token: token('00000000-0000-0000-0000-000000000002', 'new') }), false)
  assert.equal(sameLogin(first, { ...first, user: { id: 'user-b' } }), false)
  assert.equal(sameLogin(first, null), false)
})

test('a late handoff acknowledgment cannot show a stale connected status', async () => {
  let sends = 0, allowed = true, reads = 0
  const runtime: ExtensionRuntime = { sendMessage: (_id, _msg, cb) => {
    sends++
    if (sends === 2) allowed = false
    cb({ ok: true, challenge: 'nonce' })
  } }
  assert.equal(await connectSession(runtime, 'id', async () => session, () => allowed), false)
  allowed = true
  runtime.sendMessage = (_id, _msg, cb) => cb({ ok: true, challenge: 'nonce' })
  assert.equal(await connectSession(runtime, 'id', async () => ++reads < 3 ? session : null, () => allowed), false)
})
