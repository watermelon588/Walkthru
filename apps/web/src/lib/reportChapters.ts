import type { Finding, Report, Run } from './runs'

// Report chapters (R-S5a). Mirror of apps/api/app/agent/report_chapters.py: the web report, CSV, fix prompts and MCP
// share chapter keys, issue ids and summaries. Both sides are checked against tests/fixtures/report-chapters.json.

export const CHAPTERS = [
  ['journey', 'Journey and UX'],
  ['accessibility', 'Accessibility'],
  ['performance', 'Performance'],
  ['seo', 'SEO foundations'],
  ['keywords', 'Keywords and content'],
  ['authority', 'Authority and backlinks'],
  ['geo', 'GEO readiness'],
  ['citations', 'AI citations'],
  ['security', 'Security and email hygiene'],
  ['evidence', 'Evidence and coverage'],
] as const

export type ChapterKey = (typeof CHAPTERS)[number][0]
export type ChapterStatus = 'issues' | 'clear' | 'unconfirmed' | 'not_measured' | 'not_tested' | 'separate' | 'reference' | 'advisory'
export type Chapter = { number: number; key: ChapterKey; title: string; status: ChapterStatus; label: string; summary: string; issue_ids: string[]; cross_links: string[] }
export type NextAction = { id: string; chapter: ChapterKey; severity: Finding['severity']; title: string; fix: string }

export const CHAPTER_TITLE = Object.fromEntries(CHAPTERS) as Record<ChapterKey, string>
const ORDER = Object.fromEntries(CHAPTERS.map(([key], i) => [key, i])) as Record<ChapterKey, number>
const BY_KIND: Record<Finding['kind'], ChapterKey> = { ux: 'journey', accessibility: 'accessibility', performance: 'performance', seo: 'seo', geo: 'geo', security: 'security' }
const SEVERITY = { high: 0, medium: 1, low: 2 }
const STATUS_LABEL: Record<Exclude<ChapterStatus, 'issues'>, string> = {
  clear: 'No issue observed in scope', unconfirmed: 'Outcome unconfirmed', not_measured: 'Not measured', not_tested: 'Not tested', separate: 'Measured separately', reference: 'Reference', advisory: 'Advisory, no search data',
}

export const chapterOf = (f: Finding): ChapterKey => BY_KIND[f.kind] ?? 'evidence'

/** Other chapters one shared cause also affects. Rule ids only: legacy findings without a rule get no cross-link. */
export function alsoAffects(f: Finding): ChapterKey[] {
  const rule = f.rule ?? ''
  if (rule.startsWith('geo.') && rule.includes('javascript')) return ['seo']
  if (rule === 'seo.image.alt_missing') return ['accessibility']
  if (rule === 'a11y.image.alt_missing') return ['seo']
  return []
}

// Same keys as the API (compare.fingerprint, report_contract.finding_ids). Kept here so this module stays free of the
// Supabase client that runs.ts loads.
const legacyKey = (f: Finding) => `${f.kind}:${f.title.toLowerCase().replace(/\d+/g, '#').split(/\s+/).filter(Boolean).join(' ')}`
const key = (f: Finding) => (f.rule?.trim() ? `${f.kind}:${f.rule}` : legacyKey(f))

/** The id an agent passes to MCP: the rule id (or fingerprint), with #2, #3 for repeats. */
export function findingIds(findings: Finding[]): string[] {
  const seen: Record<string, number> = {}
  return findings.map((f) => {
    const base = f.rule ? f.rule : key(f)
    seen[base] = (seen[base] ?? 0) + 1
    return seen[base] === 1 ? base : `${base}#${seen[base]}`
  })
}

const isIgnored = (f: Finding, ignored: Record<string, string>) => key(f) in ignored || legacyKey(f) in ignored
const count = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`

function measured(report: Report, kind: 'accessibility' | 'performance' | 'seo' | 'security' | 'geo'): boolean {
  const state = report.checks?.[kind]
  if (state) return state === 'complete'
  // Reports before per-check states: SEO and security always ran; GEO ran when its block is present.
  return kind === 'seo' || kind === 'security' || (kind === 'geo' && !!report.geo)
}

function status(key: ChapterKey, title: string, report: Report, kind: Run['kind'], runStatus: Run['status'], open: Finding[]): [ChapterStatus, string] {
  const assessment = report.version === 2 ? report.assessment : null
  if (key === 'keywords' && report.opportunities?.pages.length) return ['advisory', `${count(report.opportunities.pages.length, 'page')} mapped from the site's own copy. Intents are hypotheses to confirm; no search volume, difficulty, rank or traffic data was used.`]
  if (key === 'keywords') return ['not_measured', 'Not part of this report. Walkthru has no search demand data for this site, so it gives no keyword direction here.']
  if (key === 'authority') return ['not_measured', 'Not part of this report. Backlinks and earned-link opportunities were not measured, and none are invented.']
  if (key === 'citations') return ['separate', 'AI answers are sampled separately, each with its own date, engine and sources. This report does not include them.']
  if (key === 'evidence') {
    if (assessment) return ['reference', `What was tested and what was not: ${count(assessment.evidence_index.length, 'evidence record')}, ${count(assessment.coverage.audited_urls.length, 'audited page')} and ${count(assessment.limitations.length, 'stated limitation')}.`]
    return ['reference', 'Saved before detailed evidence records. Each finding shows its own evidence.']
  }
  if (open.length) return ['issues', `${count(open.length, 'open issue')}, ${open.filter((f) => f.severity === 'high').length} high priority. Each lists its evidence, the change and how to check it.`]
  if (key === 'journey') {
    if (kind !== 'test') return ['not_tested', 'No journey ran. This report checks public pages only.']
    const assertion = assessment?.assertions?.[0]
    if (assertion) {
      if (assertion.status !== 'passed') return ['unconfirmed', `Declared filtered count: ${assertion.status}. UI checkpoint completion is shown separately; inspect the count evidence above.`]
      return ['clear', 'The declared synthetic filtered count passed within its dataset, time and tolerance scope. Backend behavior remains unverified.']
    }
    if (assessment?.outcome === 'completed') return ['clear', 'The test user reached every declared checkpoint and recorded no journey issue.']
    if (!assessment && runStatus === 'done') return ['clear', 'The run reached its goal and recorded no journey issue.']  // legacy: no declared checkpoints
    return ['unconfirmed', 'No journey issue was recorded, but the requested outcome was not confirmed. See the scope above.']
  }
  if (!measured(report, key)) return ['not_measured', report.check_reasons?.[key] || 'This check did not run for this report.']
  return ['clear', `Checked within this report's scope and nothing to fix was found. That is not proof of perfect ${title.toLowerCase()}.`]
}

/** Every chapter in order. Ignored findings stay listed but do not count as open issues. */
export function chapters(report: Report, kind: Run['kind'] = 'scan', runStatus: Run['status'] = 'done', ignored: Record<string, string> = {}): Chapter[] {
  const ids = findingIds(report.findings)
  return CHAPTERS.map(([key, title], i) => {
    const mine = report.findings.map((f, j) => [ids[j], f] as const).filter(([, f]) => chapterOf(f) === key)
    const open = mine.map(([, f]) => f).filter((f) => !isIgnored(f, ignored))
    const [state, summary] = status(key, title, report, kind, runStatus, open)
    return {
      number: i + 1, key, title, status: state, label: state === 'issues' ? count(open.length, 'open issue') : STATUS_LABEL[state], summary,
      issue_ids: mine.map(([id]) => id),
      cross_links: [...new Set(report.findings.flatMap((f, j) => (alsoAffects(f).includes(key) ? [ids[j]] : [])))].sort(),
    }
  })
}

/** The first actions to take: open findings by severity, then chapter order, then report order. */
export function nextActions(report: Report, ignored: Record<string, string> = {}, limit = 3): NextAction[] {
  const ids = findingIds(report.findings)
  return report.findings
    .map((f, i) => ({ f, i, id: ids[i] }))
    .filter(({ f }) => !isIgnored(f, ignored))
    .sort((a, b) => (SEVERITY[a.f.severity] - SEVERITY[b.f.severity]) || (ORDER[chapterOf(a.f)] - ORDER[chapterOf(b.f)]) || (a.i - b.i))
    .slice(0, limit)
    .map(({ f, id }) => ({ id, chapter: chapterOf(f), severity: f.severity, title: f.title, fix: f.fix }))
}

/** A safe fragment id for an issue anchor (ids can hold ':' '#' and spaces). */
export const issueAnchor = (id: string) => `issue-${id.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`
