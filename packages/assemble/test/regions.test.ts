import assert from 'node:assert/strict'
import { test } from 'node:test'
import { regions } from '../src/regions.ts'

const W = 192
const H = 120

// Paint a tiny fake screenshot: light page, then rectangles of [x, y, w, h, grey, everyOtherPixel?]
function page(rects: [number, number, number, number, number, boolean?][], bg = 240) {
  const data = new Uint8ClampedArray(W * H * 4).fill(bg)
  for (const [x, y, w, h, v, sparse] of rects) {
    for (let yy = y; yy < y + h; yy++) {
      for (let xx = x; xx < x + w; xx++) {
        if (sparse && (xx + yy) % 3) continue
        const i = (yy * W + xx) * 4
        data[i] = data[i + 1] = data[i + 2] = v
      }
    }
  }
  return data
}

const near = (a: number, b: number) => Math.abs(a - b) < 0.02

test('an empty page has no regions and reports its background', () => {
  const r = regions(page([]), W, H)
  assert.deepEqual(r.list, [])
  assert.ok(r.bg.every((c) => Math.abs(c - 240) <= 8))
})

test('separate blocks become separate regions with the right kind', () => {
  // headline (sparse), a photo (solid), a paragraph (sparse) under the headline
  const r = regions(page([[10, 10, 80, 6, 20, true], [120, 10, 60, 50, 60], [10, 30, 90, 20, 20, true]]), W, H)
  assert.equal(r.list.length, 3)
  const photo = r.list.find((g) => g.kind === 'media')!
  assert.ok(near(photo.x, 119 / W) && near(photo.y, 9 / H) && near(photo.w, 62 / W) && near(photo.h, 52 / H))
  assert.equal(r.list.filter((g) => g.kind === 'text').length, 2)
})

test('a coloured band is placed first, then its contents are found against its own colour', () => {
  const r = regions(page([[0, 60, W, 50, 30], [20, 75, 70, 6, 230, true]]), W, H)
  assert.equal(r.list[0].kind, 'box')
  assert.ok(r.list[0].w > 0.95 && near(r.list[0].y, 59 / H))
  assert.equal(r.list.length, 2)
  assert.equal(r.list[1].kind, 'text')
  assert.ok(r.list[1].y > r.list[0].y && r.list[1].x > 0.08)
})

test('a busy page is capped', () => {
  const dots: [number, number, number, number, number][] = []
  for (let y = 2; y < H - 6; y += 10) for (let x = 2; x < W - 6; x += 12) dots.push([x, y, 4, 4, 20])
  const r = regions(page(dots), W, H)
  assert.ok(r.list.length > 0 && r.list.length <= 48)
})
