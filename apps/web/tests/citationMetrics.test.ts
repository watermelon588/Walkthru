import { test } from 'node:test'
import assert from 'node:assert/strict'
import { citationLabel, citationMetrics } from '../src/lib/citationMetrics.ts'
import type { CitationAnswer } from '../src/lib/runs.ts'

function answer(status: string, cited: boolean | null): CitationAnswer {
  return { id: 1, prompt: 'Best tools?', engine: 'web', status: 'done', model: 'test', answer: 'Acme', sources: [], checked_at: null,
    result: { measurement_version: 2, citation_status: status, citation_eligible: status === 'measured',
      brands: [{ name: 'Acme', domain: 'acme.example', you: true, mentioned: true, mention_rank: 1, cited, source_rank: cited ? 1 : null }] } }
}

test('only resolved web answers form the citation denominator', () => {
  const rows = [answer('measured', true), answer('measured', false), answer('not_applicable', null), answer('unresolved', null), answer('legacy', null)]
  const result = citationMetrics([...rows, { ...answer('measured', false), status: 'failed' }])
  assert.equal(result.nameOnly, 5) // names without identity evidence are not counted as you
  assert.equal(result.cited, 1)
  assert.equal(result.citationAnswers, 2)
  assert.equal(citationMetrics([answer('not_applicable', null)]).citationAnswers, 0)
})

test('saved mode label survives changes to engine configuration', () => {
  const a = answer('not_applicable', null)
  a.engine = 'memory'
  a.result.provenance = { mode: 'memory', label: 'Gemini, from memory' }
  assert.equal(citationLabel(a), 'Gemini, from memory')
  delete a.result.provenance
  assert.equal(citationLabel(a), 'Gemini (historical mode unknown)')
})

function identified(entity_status: 'verified' | 'ambiguous' | 'other' | 'absent' | undefined): CitationAnswer {
  const a = answer('not_applicable', null)
  a.result.brands![0] = { ...a.result.brands![0], mentioned: entity_status !== 'absent', entity_status }
  return a
}

test('a matched name only counts as you when the identity is confirmed', () => {
  const result = citationMetrics(['verified', 'ambiguous', 'other', 'absent', undefined].map((s) => identified(s as never)))
  assert.equal(result.identified, 1)
  assert.equal(result.nameOnly, 2) // ambiguous, plus an older answer saved before identity was checked
  assert.equal(result.otherEntity, 1)
})

test('unknown citation answers stay unknown and coverage is shown', () => {
  const rows = [answer('measured', true), answer('measured', false), answer('measured', false), answer('unresolved', null), answer('not_applicable', null)]
  const failed = { ...answer('measured', false), status: 'failed' as const }
  const r = citationMetrics([...rows, failed])
  assert.deepEqual({ C: r.cited, D: r.citationAnswers, T: r.citationSlots, U: r.unknown }, { C: 1, D: 3, T: 5, U: 2 })
  assert.deepEqual(r.bounds, [20, 60]) // 1 of 5 if every unknown is a miss, 3 of 5 if every unknown cited you
  assert.equal(citationMetrics([answer('not_applicable', null)]).citationSlots, 0) // memory answers are not citation slots
})
