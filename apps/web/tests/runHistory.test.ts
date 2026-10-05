import { test } from 'node:test'
import assert from 'node:assert/strict'
import { HistoryPager, HISTORY_PAGE_SIZE, RUN_SUMMARY_COLUMNS, decodeRunCursor, encodeRunCursor, runCursorFilter, type HistoryPage } from '../src/lib/runHistory.ts'

const id = (value: number) => value.toString(16).padStart(32, '0')
const time = '2026-10-05T01:02:03.123456+00:00'
type Row = { id: string; created_at: string }
const row = (value: number): Row => ({ id: id(value), created_at: time })
function deferred<T>() {
  let resolve!: (value: T) => void, reject!: (reason: Error) => void
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
function ready(pager: HistoryPager<Row>) {
  const state = pager.snapshot()
  assert.equal(state.kind, 'ready')
  if (state.kind !== 'ready') throw new Error('Expected loaded history')
  return state
}

test('cursor retains all PostgreSQL microseconds and the actual 32-hex run ID', () => {
  assert.deepEqual(decodeRunCursor(encodeRunCursor(row(2))), { v: 1, created_at: time, id: id(2) })
  assert.equal(runCursorFilter(encodeRunCursor(row(2))), `created_at.lt.${time},and(created_at.eq.${time},id.lt.${id(2)})`)
  assert.equal(HISTORY_PAGE_SIZE, 50)
  assert.deepEqual(RUN_SUMMARY_COLUMNS.split(','), ['id', 'site', 'goal', 'persona', 'kind', 'status', 'public', 'created_at', 'updated_at', 'group_id'])
})

test('invalid, rolled-over, oversized and filter-injecting cursors fail clearly', () => {
  const malformed = ['?', '', 'a'.repeat(257), encodeRunCursor({ created_at: time, id: 'uuid-with-hyphens' }),
    ...['2026-02-30T00:00:00Z', '2025-02-29T00:00:00Z', '2026-13-01T00:00:00Z', '2026-01-01T24:00:00Z', '2026-01-01T00:00:60Z', '2026-01-01T00:00:00Z),id.gt.0'].map((created_at) => encodeRunCursor({ id: id(1), created_at })),
    btoa(JSON.stringify({ v: 2, created_at: time, id: id(1) })).replace(/=+$/, ''),
    btoa(JSON.stringify({ v: 1, created_at: time, id: id(1), extra: true })).replace(/=+$/, '')]
  for (const cursor of malformed) assert.throws(() => decodeRunCursor(cursor), /Invalid run history cursor/)
  assert.equal(decodeRunCursor(encodeRunCursor({ created_at: '2024-02-29T00:00:00.000001Z', id: id(1) })).created_at, '2024-02-29T00:00:00.000001Z')
})

test('more than fifty tied rows continue without duplicates despite a new insertion', async () => {
  const rows = Array.from({ length: 127 }, (_, i) => row(127 - i))
  const query = async (cursor: string | undefined): Promise<HistoryPage<Row>> => {
    const after = cursor ? decodeRunCursor(cursor) : null
    const page = rows.filter((run) => !after || run.created_at < after.created_at || (run.created_at === after.created_at && run.id < after.id)).slice(0, 50)
    return { runs: page, next_cursor: page.length ? encodeRunCursor(page.at(-1)!) : null }
  }
  const pager = new HistoryPager(query)
  await pager.refresh()
  rows.unshift({ id: id(128), created_at: '2026-10-05T01:02:03.123457+00:00' })
  await pager.more(); await pager.more(); await pager.more()
  assert.equal(ready(pager).runs.length, 127)
  assert.equal(new Set(ready(pager).runs.map((run) => run.id)).size, 127)
  assert.equal(ready(pager).nextCursor, null)
  await pager.refresh()
  assert.equal(ready(pager).runs[0]!.id, id(128))
})

test('short server-capped pages continue until an empty keyset page', async () => {
  const rows = Array.from({ length: 60 }, (_, i) => row(60 - i))
  let requests = 0
  const pager = new HistoryPager(async (cursor) => {
    requests++
    const page = rows.filter((run) => !cursor || run.id < decodeRunCursor(cursor).id).slice(0, 7)
    return { runs: page, next_cursor: page.length ? encodeRunCursor(page.at(-1)!) : null }
  })
  await pager.refresh()
  while (ready(pager).nextCursor) await pager.more()
  assert.equal(ready(pager).runs.length, 60)
  assert.equal(requests, 10)
})

test('failed continuation preserves rows and cursor for recovery; duplicate requests coalesce', async () => {
  const later = deferred<HistoryPage<Row>>()
  let calls = 0
  const cursor = encodeRunCursor(row(2))
  const pager = new HistoryPager(async () => ++calls === 1 ? { runs: [row(2)], next_cursor: cursor } : calls === 2 ? later.promise : { runs: [row(1)], next_cursor: null })
  await pager.refresh()
  const pending = pager.more(); await pager.more()
  assert.equal(calls, 2)
  later.reject(new Error('offline'))
  await pending
  assert.equal(ready(pager).moreError, 'offline')
  assert.equal(ready(pager).runs.length, 1)
  assert.equal(ready(pager).nextCursor, cursor)
  await pager.more()
  assert.equal(ready(pager).runs.length, 2)
  assert.equal(ready(pager).moreError, null)
})

test('notification refresh aborts an old continuation and drops its stale late reply', async () => {
  const late = deferred<HistoryPage<Row>>()
  let calls = 0, oldSignal: AbortSignal | undefined
  const pager = new HistoryPager(async (_cursor, signal) => {
    calls++
    if (calls === 2) { oldSignal = signal; return late.promise }
    return { runs: [row(calls === 1 ? 2 : 3)], next_cursor: encodeRunCursor(row(2)) }
  })
  await pager.refresh()
  const pending = pager.more()
  await pager.refresh()
  assert.equal(oldSignal!.aborted, true)
  late.resolve({ runs: [row(1)], next_cursor: null }); await pending
  assert.deepEqual(ready(pager).runs.map((run) => run.id), [id(3)])
})

test('switching accounts or signing out disposes old work before any late reply', async () => {
  const late = deferred<HistoryPage<Row>>()
  let signal: AbortSignal | undefined
  const old = new HistoryPager<Row>(async (_cursor, current) => { signal = current; return late.promise })
  const pending = old.refresh()
  old.dispose()
  const next = new HistoryPager<Row>(async () => ({ runs: [row(9)], next_cursor: null }))
  assert.equal(next.snapshot().kind, 'loading')
  await next.refresh()
  late.resolve({ runs: [row(1)], next_cursor: null }); await pending
  assert.equal(signal!.aborted, true)
  assert.equal(old.snapshot().kind, 'loading')
  assert.deepEqual(ready(next).runs.map((run) => run.id), [id(9)])
})

test('initial errors can retry, empty pages remain explicit and repeated rows are deduplicated', async () => {
  let calls = 0
  const pager = new HistoryPager<Row>(async () => {
    if (++calls === 1) throw new Error('offline')
    return { runs: calls === 2 ? [] : [row(1), row(1)], next_cursor: null }
  })
  await pager.refresh()
  assert.equal(pager.snapshot().kind, 'error')
  await pager.refresh()
  assert.deepEqual(ready(pager).runs, [])
  await pager.refresh()
  assert.equal(ready(pager).runs.length, 1)
})
