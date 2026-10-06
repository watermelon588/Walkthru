import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { assertSupportedReport, reportCsv } from '../src/lib/reportContract.ts'
import type { Report } from '../src/lib/runs.ts'

const fixture = (): Report => JSON.parse(readFileSync(new URL('./fixtures/report-v2.json', import.meta.url), 'utf8'))

test('accepts a serialized Python v2 report and preserves the six legacy CSV columns', () => {
  const report = fixture()
  assert.doesNotThrow(() => assertSupportedReport(report))
  const csv = reportCsv({ report })
  assert.ok(csv.startsWith('"kind","severity","title","detail","fix","evidence",'))
  assert.ok(csv.includes('scanner:0'))
  assert.ok(csv.includes('"not_tested"'))
  assert.equal(report.assessment!.issues[0].expected_result, null)
  assert.ok(csv.includes('seo.title.missing'))
  assert.ok(csv.includes('"acceptance_test"'))
})

test('missing version is legacy and its CSV remains exactly the original shape', () => {
  const report = fixture()
  delete report.version
  delete report.assessment
  assert.doesNotThrow(() => assertSupportedReport(report))
  const csv = reportCsv({ report })
  assert.equal(csv.split('\n')[0], '"kind","severity","title","detail","fix","evidence"')
  assert.equal(csv.split('\n').length, 2)
})

test('unknown versions fail clearly instead of silently rendering as legacy', () => {
  for (const version of [3, '2', true, null]) {
    const report = { ...fixture(), version } as unknown as Report
    assert.throws(() => assertSupportedReport(report), /Unsupported report version/)
    assert.throws(() => reportCsv({ report }), /Unsupported report version/)
  }
})

test('unknown and unrelated evidence references cannot support a claim', () => {
  const report = fixture()
  report.assessment!.issues[0].evidence_refs = ['step:999']
  assert.throws(() => assertSupportedReport(report), /invalid evidence/)
  report.assessment!.evidence_index.push({ id: 'step:999', source: 'step', observed: 'Other action', step: 999, finding_index: null, url: null })
  assert.throws(() => assertSupportedReport(report), /invalid evidence/)
})

test('invented observed facts, results, expectations and coverage are rejected', () => {
  for (const mutate of [
    (r: Report) => { r.assessment!.issues[0].observed_facts = ['Account created'] },
    (r: Report) => { r.assessment!.issues[0].actual_result = 'Account created' },
    (r: Report) => { r.assessment!.issues[0].expected_result = 'Account created' },
    (r: Report) => { r.assessment!.coverage.confirmed_checkpoints = 1 },
    (r: Report) => { r.assessment!.coverage.actions_with_outcomes = 1 },
    (r: Report) => { r.assessment!.outcome = 'completed' },
  ]) {
    const report = fixture(); mutate(report)
    assert.throws(() => assertSupportedReport(report), /invalid evidence/)
  }
})

test('malformed records fail with a clear contract error before the renderer reads them', () => {
  for (const mutate of [
    (r: Report) => { (r.assessment!.evidence_index as unknown[])[0] = null },
    (r: Report) => { (r.assessment!.issues as unknown[])[0] = null },
    (r: Report) => { r.assessment!.issues[0].reproduction_steps = null as unknown as string[] },
    (r: Report) => { r.assessment!.coverage.checks = null as unknown as Record<string, 'complete'> },
  ]) {
    const report = fixture(); mutate(report)
    assert.throws(() => assertSupportedReport(report), /invalid evidence/)
  }
  assert.throws(() => assertSupportedReport({ ...fixture(), version: 1 }), /does not match/)
})

test('a clean report exports no fabricated finding and spreadsheet formulas stay inert', () => {
  const report = fixture()
  report.findings[0].title = '=HYPERLINK("malicious")'
  assert.ok(reportCsv({ report }).includes('"\'=HYPERLINK(""malicious"")"'))
  report.findings = []; report.assessment!.issues = []
  assert.equal(reportCsv({ report }).split('\n').length, 1)
})

test('actual-result bounds count Unicode characters consistently with Python', () => {
  const report = fixture(), a = report.assessment!, issue = a.issues[0]
  a.evidence_index = Array.from({ length: 5 }, (_, i) => ({ ...a.evidence_index[0], id: `scanner:0:${i}`, observed: '😀'.repeat(1000) }))
  issue.evidence_refs = a.evidence_index.map((e) => e.id)
  issue.observed_facts = a.evidence_index.map((e) => e.observed)
  issue.actual_result = Array.from(issue.observed_facts.join('; ')).slice(0, 4000).join('')
  assert.doesNotThrow(() => assertSupportedReport(report))
})
