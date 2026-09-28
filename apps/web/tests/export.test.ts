import { test } from 'node:test'
import assert from 'node:assert/strict'
import { toCsv } from '../src/lib/export.ts'

test('quotes cells, doubles quotes and neutralises formulas', () => {
  assert.equal(toCsv([['a', 'say "hi"', null, 3], ['=HYPERLINK("x")', '+1', '-2', '@SUM(A1)']]),
    '"a","say ""hi""","","3"\n"\'=HYPERLINK(""x"")","\'+1","\'-2","\'@SUM(A1)"')
})
