import assert from 'node:assert/strict'
import test from 'node:test'
import { fieldCoverage, metricValue, type PerformanceMeasurement } from '../src/lib/performance.ts'

const legacy: PerformanceMeasurement = { url: 'https://site.test/', status: 'lab_only', lab_score: 95, lcp_ms: null, cls: null, inp_ms: null }

test('a healthy lab score cannot make missing field vitals healthy', () => {
  assert.match(fieldCoverage(legacy), /unavailable.*does not establish healthy/)
  assert.equal(metricValue(null), 'unavailable')
})
test('partial field values keep missing metrics explicit and true zero available', () => {
  assert.match(fieldCoverage({ ...legacy, lcp_ms: 3000, cls: 0 }), /2 of 3.*unknown/)
  assert.equal(metricValue(0, 'score'), '0')
  assert.equal(metricValue(3000), '3000 ms')
  assert.equal(metricValue(80000, 'bytes'), '80000 bytes')
})
