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
  assert.equal(result.named, 5)
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
