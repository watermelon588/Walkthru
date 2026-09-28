import { test } from 'node:test'
import assert from 'node:assert/strict'
import { apiError } from '../src/lib/apiError.ts'

test('API errors show a usable request reference without exposing raw error bodies', async () => {
  const id = 'a'.repeat(32)
  assert.equal(await apiError(new Response(JSON.stringify({ detail: 'Try again.' }), {status: 503, headers: {'X-Request-Id': id}})), `Try again. Reference: ${id}.`)
  assert.equal(await apiError(new Response('private upstream debug page', {status: 500, headers: {'X-Request-Id': id}})), `Request failed (500) Reference: ${id}.`)
  assert.equal(await apiError(new Response('{}', {status: 400, headers: {'X-Request-Id': 'untrusted-value'}})), 'Request failed (400)')
  assert.equal(await apiError(new Response('null', {status: 500})), 'Request failed (500)')
})
