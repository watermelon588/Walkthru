import { toCsv, type Cell } from './export.ts'
import { alsoAffects, chapterOf } from './reportChapters.ts'
import type { Report, Run } from './runs'

export const OUTCOME_LABEL = {
  completed: 'Declared checkpoints confirmed', unconfirmed: 'Outcome unconfirmed', blocked: 'Stopped at a boundary', not_tested: 'Journey not tested',
}

export type ReportEvidence = { id: string; source: 'scanner' | 'step' | 'milestone' | 'first_impression' | 'assertion'; observed: string; url: string | null; step: number | null; finding_index: number | null }
export type ReportAssertion = {
  id: 'filtered_count:1'; status: 'passed' | 'failed' | 'blocked' | 'inconclusive'
  expected: { path: string; filter_value: string; count_label: string; expected_count: number | null; dataset_id: string | null; dataset_at: string | null; max_age_seconds: number; tolerance: number }
  observed_count: number | null; observed_dataset_id: string | null; observed_dataset_at: string | null
  evaluated_at: string; state_reached: boolean; reason: string; evidence_refs: string[]
}
export type ReportIssue = {
  id: string; finding_index: number; observation_type: 'scanner' | 'browser_observation' | 'subjective'
  observed_facts: string[]; expected_result: string | null; actual_result: string; interpretation: string
  cause_hypothesis: string | null; proposed_change: string; reproduction_steps: string[]; acceptance_test: string; evidence_refs: string[]
}
export type ReportAssessment = {
  objective: string; outcome: 'completed' | 'unconfirmed' | 'blocked' | 'not_tested'; stop_reason: string
  coverage: { checks: Record<string, 'complete' | 'unavailable'>; actions_with_outcomes: number; declared_checkpoints: number; confirmed_checkpoints: number; audited_urls: string[]; crawl_truncated: boolean }
  limitations: string[]
  checkpoints: { description: string; expected_result: string | null; actual_result: string | null; status: 'passed' | 'unconfirmed' | 'not_tested'; evidence_refs: string[] }[]
  issues: ReportIssue[]; evidence_index: ReportEvidence[]
  assertions?: ReportAssertion[]
}

/** Missing version means the saved legacy contract. Never treat an unknown version as legacy. */
export function assertSupportedReport(report: Report | null | undefined): void {
  if (!report) return
  const version = report.version === undefined ? 1 : report.version
  if (version !== 1 && version !== 2) throw new Error('Unsupported report version. Update Walkthru to read this report.')
  if (version === 1) {
    if (report.assessment != null) throw new Error('Report version does not match its assessment.')
    return
  }
  const a = report.assessment
  const invalid = () => { throw new Error('Report version 2 contains invalid evidence or coverage.') }
  if (!a || !Array.isArray(a.issues) || !Array.isArray(a.evidence_index) || !Array.isArray(a.checkpoints) || !Array.isArray(a.limitations) || !a.coverage) return invalid()
  const strings = (values: unknown): values is string[] => Array.isArray(values) && values.every((v) => typeof v === 'string')
  const nullableText = (v: unknown) => v === null || typeof v === 'string'
  if (typeof a.objective !== 'string' || typeof a.stop_reason !== 'string' || !['completed', 'unconfirmed', 'blocked', 'not_tested'].includes(a.outcome) || !strings(a.limitations)) return invalid()
  if (a.evidence_index.some((e) => !e || typeof e.id !== 'string' || typeof e.observed !== 'string' || !nullableText(e.url) || !['scanner', 'step', 'milestone', 'first_impression', 'assertion'].includes(e.source))) return invalid()
  if (a.issues.some((i) => !i || typeof i.id !== 'string' || !Number.isInteger(i.finding_index) || !['scanner', 'browser_observation', 'subjective'].includes(i.observation_type) || !strings(i.observed_facts) || !strings(i.evidence_refs) || !strings(i.reproduction_steps) || !nullableText(i.expected_result) || !nullableText(i.cause_hypothesis) || [i.actual_result, i.interpretation, i.proposed_change, i.acceptance_test].some((v) => typeof v !== 'string'))) return invalid()
  if (a.checkpoints.some((c) => !c || typeof c.description !== 'string' || !nullableText(c.expected_result) || !nullableText(c.actual_result) || !strings(c.evidence_refs) || c.evidence_refs.length > 1 || !['passed', 'unconfirmed', 'not_tested'].includes(c.status))) return invalid()
  if (!a.coverage.checks || typeof a.coverage.checks !== 'object' || Array.isArray(a.coverage.checks) || Object.values(a.coverage.checks).some((v) => v !== 'complete' && v !== 'unavailable') || !strings(a.coverage.audited_urls) || typeof a.coverage.crawl_truncated !== 'boolean' || !Number.isInteger(a.coverage.actions_with_outcomes) || a.coverage.actions_with_outcomes !== a.evidence_index.filter((e) => e.source === 'step').length) return invalid()
  const records = new Map(a.evidence_index.map((e) => [e.id, e]))
  if (a.assertions !== undefined && (!Array.isArray(a.assertions) || a.assertions.length > 1)) return invalid()
  for (const check of a.assertions ?? []) {
    const e = check?.expected
    if (!check || !e || check.id !== 'filtered_count:1' || !['passed', 'failed', 'blocked', 'inconclusive'].includes(check.status) || typeof check.reason !== 'string' || typeof check.state_reached !== 'boolean' || !strings(check.evidence_refs) || check.evidence_refs.length > 1 || check.evidence_refs.some((ref) => records.get(ref)?.source !== 'assertion')) return invalid()
    if ([e.path, e.filter_value, e.count_label, check.evaluated_at].some((v) => typeof v !== 'string') || !nullableText(e.dataset_id) || !nullableText(e.dataset_at) || !nullableText(check.observed_dataset_id) || !nullableText(check.observed_dataset_at) || !Number.isInteger(e.tolerance) || e.tolerance < 0 || e.tolerance > 100 || !Number.isInteger(e.max_age_seconds) || e.max_age_seconds < 1 || e.max_age_seconds > 86400) return invalid()
    if ([e.expected_count, check.observed_count].some((v) => v !== null && (!Number.isInteger(v) || v < 0 || v > 100000))) return invalid()
    if (check.state_reached !== !!check.evidence_refs.length || (!check.state_reached && [check.observed_count, check.observed_dataset_id, check.observed_dataset_at].some((v) => v !== null))) return invalid()
    for (const ref of check.evidence_refs) {
      const record = records.get(ref)!
      const step = records.get(`step:${record.step}`)
      if (!step || step.source !== 'step' || step.url !== record.url || !record.observed.includes(`Filter: ${e.filter_value};`)) return invalid()
      if (check.observed_dataset_id && !record.observed.includes(`Dataset: ${check.observed_dataset_id};`)) return invalid()
      const recordedTime = record.observed.match(/Dataset time: ([^;]+);/)?.[1]
      if (check.observed_dataset_at && Date.parse(recordedTime ?? '') !== Date.parse(check.observed_dataset_at)) return invalid()
    }
    if (check.observed_count !== null && check.evidence_refs.length && !records.get(check.evidence_refs[0])!.observed.includes(`${e.count_label}: ${check.observed_count};`)) return invalid()
    if (check.status === 'passed' || check.status === 'failed') {
      const age = (Date.parse(check.evaluated_at) - Date.parse(e.dataset_at ?? '')) / 1000
      if (!check.state_reached || !check.evidence_refs.length || check.observed_count === null || e.expected_count === null || !e.dataset_id || check.observed_dataset_id !== e.dataset_id || Date.parse(check.observed_dataset_at ?? '') !== Date.parse(e.dataset_at ?? '') || !(age >= 0 && age <= e.max_age_seconds)) return invalid()
      if ((check.status === 'passed') !== (Math.abs(check.observed_count - e.expected_count) <= e.tolerance)) return invalid()
    }
  }
  if (records.size !== a.evidence_index.length || a.issues.length !== report.findings.length || new Set(a.issues.map((i) => i.id)).size !== a.issues.length) return invalid()
  const indexes = a.issues.map((i) => i.finding_index).sort((x, y) => x - y)
  const sources = { scanner: 'scanner', browser_observation: 'step', subjective: 'first_impression' }
  for (const [index, value] of indexes.entries()) if (index !== value) return invalid()
  for (const issue of a.issues) {
    if (!Array.isArray(issue.evidence_refs) || issue.evidence_refs.length === 0 || !Array.isArray(issue.observed_facts)) return invalid()
    const evidence = issue.evidence_refs.map((ref) => records.get(ref))
    if (evidence.some((e) => !e || e.source !== sources[issue.observation_type] || (e.source === 'scanner' && e.finding_index !== issue.finding_index))) return invalid()
    if (issue.observed_facts.length !== evidence.length || issue.observed_facts.some((fact, i) => fact !== evidence[i]?.observed)) return invalid()
    if (issue.actual_result !== Array.from(issue.observed_facts.join('; ')).slice(0, 4000).join('') || (issue.expected_result !== null && !a.checkpoints.some((c) => c.expected_result === issue.expected_result))) return invalid()
  }
  for (const [index, checkpoint] of a.checkpoints.entries()) {
    if (!Array.isArray(checkpoint.evidence_refs) || checkpoint.evidence_refs.some((ref) => records.get(ref)?.source !== 'milestone')) return invalid()
    if (checkpoint.status === 'passed' && checkpoint.evidence_refs.length === 0) return invalid()
    if (checkpoint.status === 'passed' && (checkpoint.expected_result === null || checkpoint.evidence_refs[0] !== `milestone:${index + 1}` || checkpoint.actual_result !== records.get(checkpoint.evidence_refs[0])?.observed)) return invalid()
  }
  if (a.outcome === 'completed' && (a.checkpoints.length === 0 || a.checkpoints.some((c) => c.status !== 'passed'))) return invalid()
  if (a.coverage.declared_checkpoints !== a.checkpoints.length || a.coverage.confirmed_checkpoints !== a.checkpoints.filter((c) => c.status === 'passed').length) return invalid()
}

export function reportProblem(report: Report | null): string | null {
  try { assertSupportedReport(report); return null } catch (error) { return error instanceof Error ? error.message : 'Could not read this report.' }
}

export function reportCsvRows(run: Pick<Run, 'report'>): Cell[][] {
  assertSupportedReport(run.report)
  const report = run.report
  const header = ['kind', 'severity', 'title', 'detail', 'fix', 'evidence']
  const rows = (report?.findings ?? []).map((f) => [f.kind, f.severity, f.title, f.detail, f.fix, f.evidence])
  if (report?.version !== 2) return [header, ...rows]
  header.push('id', 'observation_type', 'observed_facts', 'expected_result', 'actual_result', 'interpretation', 'cause_hypothesis', 'proposed_change', 'reproduction_steps', 'acceptance_test', 'evidence_refs', 'outcome', 'limitations', 'chapter', 'also_affects')
  return [header, ...rows.map((row, i) => {
    const issue = report.assessment!.issues.find((item) => item.finding_index === i)!
    const finding = report.findings[i]
    return [...row, issue.id, issue.observation_type, issue.observed_facts.join('\n'), issue.expected_result, issue.actual_result, issue.interpretation,
      issue.cause_hypothesis, issue.proposed_change, issue.reproduction_steps.join('\n'), issue.acceptance_test, issue.evidence_refs.join('\n'), report.assessment!.outcome, report.assessment!.limitations.join('\n'),
      chapterOf(finding), alsoAffects(finding).join('\n')]
  })]
}

export function reportCsv(run: Pick<Run, 'report'>): string {
  return toCsv(reportCsvRows(run))
}
