import { test } from 'node:test'
import assert from 'node:assert/strict'
import { inviteCode, loginError, loginErrorCode } from '../src/lib/loginErrors.ts'

test('expired and refused callbacks retain usable errors without provider text or tokens', () => {
  assert.match(loginError('', '#error=access_denied&error_code=otp_expired&error_description=private-token')!, /expired/)
  assert.equal(loginErrorCode('', '#error=access_denied&error_code=otp_expired'), 'otp_expired')
  assert.match(loginError('?auth_error=access_denied', '')!, /cancelled/)
  assert.equal(loginErrorCode('?error=unknown-secret', ''), 'callback_failed')
  assert.doesNotMatch(loginError('?error=unknown-secret', '')!, /unknown-secret/)
  assert.equal(loginError('', '#access_token=secret&refresh_token=secret'), null)
})
test('malformed invitation fragments never crash; valid encoded codes survive', () => {
  assert.equal(inviteCode('#%E0%A4%A'), '')
  assert.equal(inviteCode('#ABCD%2DEFGH'), 'ABCD-EFGH')
})
