import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { assertSupportedReport } from '../src/lib/reportContract.ts'
import type { Report } from '../src/lib/runs.ts'

const fixture = (): Report => JSON.parse(readFileSync(new URL('./fixtures/report-assertion.json', import.meta.url), 'utf8'))

test('Python count failure preserves completed UI state and zero invented findings', () => {
  const report = fixture()
  assert.doesNotThrow(() => assertSupportedReport(report))
  assert.equal(report.assessment!.outcome, 'completed')
  assert.equal(report.assessment!.assertions![0].status, 'failed')
  assert.deepEqual(report.findings, [])
})

test('saved verdict arithmetic, freshness, dataset and executed-step evidence must agree', () => {
  for (const mutate of [
    (r: Report) => { r.assessment!.assertions![0].status = 'passed' },
    (r: Report) => { r.assessment!.assertions![0].status = 'inconclusive'; r.assessment!.assertions![0].evidence_refs = [] },
    (r: Report) => { r.assessment!.assertions![0].evaluated_at = '2026-10-07T04:00:00Z' },
    (r: Report) => { r.assessment!.assertions![0].observed_dataset_id = 'other' },
    (r: Report) => { r.assessment!.evidence_index.at(-1)!.step = 99 },
    (r: Report) => { r.assessment!.evidence_index.at(-1)!.url = 'https://other.test/dashboard' },
    (r: Report) => { r.assessment!.evidence_index.at(-1)!.observed = 'Filter: Active; Filtered records: 3; Dataset: other;' },
  ]) {
    const report = fixture(); mutate(report)
    assert.throws(() => assertSupportedReport(report), /invalid evidence/)
  }
})

test('old report v2 without assertions remains readable', () => {
  const report = fixture()
  delete report.assessment!.assertions
  assert.doesNotThrow(() => assertSupportedReport(report))
})
