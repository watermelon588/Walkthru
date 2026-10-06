import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { chapters, issueAnchor, nextActions } from '../src/lib/reportChapters.ts'
import { reportCsvRows } from '../src/lib/reportContract.ts'
import type { Report, Run } from '../src/lib/runs.ts'

type Case = { name: string; kind: Run['kind']; status: Run['status']; report: Report; chapters: unknown; next_actions: unknown }
const cases = (): Case[] => JSON.parse(readFileSync(new URL('./fixtures/report-chapters.json', import.meta.url), 'utf8')).cases

test('chapters, ids, statuses and summaries match the API for every shared case', () => {
  const all = cases()
  assert.deepEqual(all.map((c) => c.name), ['v2-scan', 'long-legacy-journey', 'clean-scan', 'interrupted-journey', 'assertion-failed', 'keyword-advisory'])
  for (const c of all) {
    assert.deepEqual(chapters(c.report, c.kind, c.status), c.chapters, c.name)
    assert.deepEqual(nextActions(c.report), c.next_actions, c.name)
  }
})

test('ignored findings stay listed but leave the open count and next actions', () => {
  const long = cases()[1].report
  const ignored = { 'ux:ux.submit_network_error': 'known' }
  const journey = chapters(long, 'test', 'gave_up', ignored)[0]
  assert.equal(journey.status, 'unconfirmed')
  assert.deepEqual(journey.issue_ids, ['ux.submit_network_error'])
  assert.ok(!nextActions(long, ignored).some((a) => a.id === 'ux.submit_network_error'))
})

test('issue anchors are safe fragment ids for rule ids, repeats and legacy keys', () => {
  assert.equal(issueAnchor('sec.cookie.flags_missing#2'), 'issue-sec-cookie-flags-missing-2')
  assert.equal(issueAnchor('security:no spf record'), 'issue-security-no-spf-record')
})

test('v2 CSV adds the primary chapter and cross-links after the existing columns', () => {
  const rows = reportCsvRows({ report: cases()[0].report })
  assert.deepEqual(rows[0].slice(0, 6), ['kind', 'severity', 'title', 'detail', 'fix', 'evidence'])
  assert.deepEqual(rows[0].slice(-2), ['chapter', 'also_affects'])
  assert.equal(rows[1].at(-2), 'seo')
})
