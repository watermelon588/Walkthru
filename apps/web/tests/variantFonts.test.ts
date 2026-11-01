import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

for (const name of ['fresh', 'darkroom', 'markup']) {
  test(`${name} preview CSS does not block lazy loading on an external font import`, () => {
    const css = readFileSync(new URL(`../src/variants/${name}.css`, import.meta.url), 'utf8')
    assert.doesNotMatch(css, /@import\s+(?:url\(\s*)?["']?https?:/i)
    assert.match(css, /Geist Variable/)
  })
}
