// Find the content blocks in a screenshot so they can be rebuilt one by one. Pure: runs under `node --test`.
// Works on a small copy of the image (about 192 px wide): find the background colour, then keep cutting the picture
// along its widest empty rows and columns until each piece is one block of content.

export interface Region {
  /** fractions of the image, 0 to 1 */
  x: number
  y: number
  w: number
  h: number
  /** text: sparse, typed in line by line. media: a solid picture. box: anything else. */
  kind: 'box' | 'media' | 'text'
}

export interface Regions {
  /** background colour as r, g, b */
  bg: [number, number, number]
  list: Region[]
}

const MAX_REGIONS = 48

export function regions(data: ArrayLike<number>, w: number, h: number): Regions {
  // most common colour in a rectangle, at 4 bits per channel
  const mode = (x0: number, y0: number, x1: number, y1: number): [number, number, number] => {
    const seen = new Map<number, number>()
    let best = 0
    let top = -1
    for (let y = y0; y < y1; y++) {
      for (let x = x0; x < x1; x++) {
        const i = (y * w + x) * 4
        const key = ((data[i] >> 4) << 8) | ((data[i + 1] >> 4) << 4) | (data[i + 2] >> 4)
        const n = (seen.get(key) ?? 0) + 1
        seen.set(key, n)
        if (n > top) {
          top = n
          best = key
        }
      }
    }
    return [((best >> 8) << 4) + 8, (((best >> 4) & 15) << 4) + 8, ((best & 15) << 4) + 8]
  }
  const ink = (x: number, y: number, bg: number[]) => {
    const i = (y * w + x) * 4
    return Math.abs(data[i] - bg[0]) > 28 || Math.abs(data[i + 1] - bg[1]) > 28 || Math.abs(data[i + 2] - bg[2]) > 28
  }
  // widest run of empty entries strictly inside the list: [length, start]
  const gap = (has: boolean[]) => {
    let best = 0
    let at = 0
    let run = 0
    for (let i = 0; i < has.length; i++) {
      run = has[i] ? 0 : run + 1
      if (run > best) {
        best = run
        at = i - run + 1
      }
    }
    return [best, at]
  }

  const bg = mode(0, 0, w, h)

  function collect(scale: number) {
    const out: Region[] = []
    const emit = (x0: number, y0: number, x1: number, y1: number, kind: Region['kind']) => {
      // one cell of padding so anti-aliased edges are not cut off
      const l = Math.max(0, x0 - 1)
      const t = Math.max(0, y0 - 1)
      out.push({ x: l / w, y: t / h, w: (Math.min(w, x1 + 1) - l) / w, h: (Math.min(h, y1 + 1) - t) / h, kind })
    }

    function cut(x0: number, y0: number, x1: number, y1: number, back: number[], depth: number, banded: boolean) {
      const rows: boolean[] = []
      const cols: boolean[] = []
      let filled = 0
      for (let y = y0; y < y1; y++) {
        for (let x = x0; x < x1; x++) {
          if (!ink(x, y, back)) continue
          rows[y - y0] = cols[x - x0] = true
          filled++
        }
      }
      if (!filled) return
      // trim to the content
      const first = (a: boolean[]) => a.findIndex(Boolean)
      const lastOf = (a: boolean[]) => a.length - 1 - [...a].reverse().findIndex(Boolean)
      const ty = y0 + first(rows)
      const by = y0 + lastOf(rows) + 1
      const lx = x0 + first(cols)
      const rx = x0 + lastOf(cols) + 1
      const [gr, ar] = gap(Array.from({ length: by - ty }, (_, i) => !!rows[ty - y0 + i]))
      const [gc, ac] = gap(Array.from({ length: rx - lx }, (_, i) => !!cols[lx - x0 + i]))
      const needRow = 3 * scale
      const needCol = 5 * scale
      if (depth < 9 && (gr >= needRow || gc >= needCol)) {
        if (gr / needRow >= gc / needCol) {
          cut(lx, ty, rx, ty + ar, back, depth + 1, banded)
          cut(lx, ty + ar + gr, rx, by, back, depth + 1, banded)
        } else {
          cut(lx, ty, lx + ac, by, back, depth + 1, banded)
          cut(lx + ac + gc, ty, rx, by, back, depth + 1, banded)
        }
        return
      }
      const area = (rx - lx) * (by - ty)
      const fill = filled / area
      // a coloured band or card: place it, then look for its contents against its own colour
      if (!banded && fill > 0.85 && area > 0.04 * w * h) {
        const own = mode(lx, ty, rx, by)
        if (own.some((c, i) => Math.abs(c - back[i]) > 28)) {
          emit(lx, ty, rx, by, 'box')
          const band = out[out.length - 1]
          const before = out.length
          cut(lx + 1, ty + 1, rx - 1, by - 1, own, depth + 1, true)
          if (out.length === before) band.kind = 'media' // nothing inside it: a flat picture, not a container
          return
        }
      }
      emit(lx, ty, rx, by, fill < 0.55 ? 'text' : fill > 0.8 && area > 0.012 * w * h ? 'media' : 'box')
    }

    cut(0, 0, w, h, bg, 0, false)
    return out
  }

  // a busy page: ask for wider gaps until the count is manageable
  let list: Region[] = []
  for (const scale of [1, 1.5, 2, 3, 5]) {
    list = collect(scale)
    if (list.length <= MAX_REGIONS) break
  }
  return { bg, list: list.slice(0, MAX_REGIONS) }
}
