// Walk a live subtree and list what the crew has to "build". Nothing is cloned; every layer points at the real element.
import type { LayerKind } from './sim.ts'

export interface Layer {
  el: HTMLElement
  kind: LayerKind
  /** page coordinates at snapshot time; used for ordering only, the engine re-measures when it draws */
  x: number
  y: number
  w: number
  h: number
  /** index of the nearest ancestor layer, or -1 */
  parent: number
  /** solid background of a text element that is also a box (button, pill), else '' */
  fill: string
  /** for a line: which edges to draw (t, r, b, l), or h / v for a thin rule through the middle */
  sides: string
  /** index into `copies` when this layer sits inside a duplicate, else -1 */
  copy: number
  /** group id when this layer is part of the component the duplicates are copied from, else -1 */
  master: number
}

/** one repeated sibling that is alt-dragged from the first of its kind instead of being built from scratch */
export interface Copy {
  el: HTMLElement
  from: HTMLElement
  group: number
  x: number
  y: number
}

export interface Blueprint {
  layers: Layer[]
  copies: Copy[]
}

/** ponytail: hard cap; elements past it are simply never hidden. Build near-viewport batches if a page needs more. */
export const MAX_LAYERS = 1500
export const HOST_ATTR = 'data-asm-host'
/** a run of this many alike siblings is treated as one component plus duplicates */
const MIN_REPEAT = 3

const SKIP = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE', 'BR', 'WBR', 'HEAD', 'LINK', 'META'])
const MEDIA = new Set(['IMG', 'svg', 'CANVAS', 'VIDEO', 'IFRAME', 'PICTURE', 'INPUT', 'TEXTAREA', 'SELECT', 'EMBED', 'OBJECT'])

function alpha(color: string) {
  if (color === 'transparent') return 0
  const m = color.match(/(?:,|\/)\s*([\d.]+)(%?)\s*\)$/)
  if (!m || !/^rgba|\//.test(color)) return 1
  return m[2] ? parseFloat(m[1]) / 100 : parseFloat(m[1])
}

// What an element paints by itself: '' nothing, 'box' a filled or fully bordered box,
// or the edges of a divider (a section with only a top border is a pen line, not a box).
function shape(el: Element, cs: CSSStyleDeclaration, r: DOMRect): string {
  let sides = ''
  for (const [key, side] of [['t', 'Top'], ['r', 'Right'], ['b', 'Bottom'], ['l', 'Left']] as const) {
    if (parseFloat(cs[`border${side}Width`]) > 0 && cs[`border${side}Style`] !== 'none' && alpha(cs[`border${side}Color`]) > 0) sides += key
  }
  let filled = cs.backgroundImage !== 'none' || cs.boxShadow !== 'none' || alpha(cs.backgroundColor) > 0
  for (const which of ['::before', '::after']) {
    const content = getComputedStyle(el, which).content
    if (content && content !== 'none' && content !== 'normal') filled = true
  }
  if (!filled && !sides) return ''
  if (r.height <= 3 && r.width > 12) return 'h'
  if (r.width <= 3 && r.height > 12) return 'v'
  if (!filled && (sides.length === 1 || sides === 'tb' || sides === 'rl')) return sides
  return 'box'
}

// True when everything inside lays out inline, so the element reads as one run of text
// (a headline split into per-word spans is still one headline). Flex and grid children are block-level, so rows stay separate.
function inlineOnly(el: Element): boolean {
  for (const kid of el.children) {
    if (SKIP.has(kid.tagName)) continue
    const display = getComputedStyle(kid).display
    if (display === 'none') continue
    if (!display.startsWith('inline') && display !== 'contents') return false
    if (!MEDIA.has(kid.tagName) && !inlineOnly(kid)) return false
  }
  return true
}

function ownText(el: Element) {
  for (const n of el.childNodes) if (n.nodeType === 3 && n.nodeValue!.trim()) return true
  return false
}

export function snapshot(root: Element): Blueprint {
  const layers: Layer[] = []
  const copies: Copy[] = []
  const sx = scrollX
  const sy = scrollY
  let groups = 0

  function walk(el: Element, parent: number, top: boolean, veiled = false) {
    if (layers.length >= MAX_LAYERS || SKIP.has(el.tagName) || el.hasAttribute(HOST_ATTR)) return
    const cs = getComputedStyle(el)
    if (cs.display === 'none') return
    const r = el.getBoundingClientRect()
    // Invisible on screen right now: a hover overlay or similar, leave it alone.
    // Faded out below the fold: almost always a scroll reveal the page will fade in as we get there, so it is built
    // like the rest. Animation libraries often pair opacity 0 with visibility hidden, which the children inherit.
    const faded = cs.opacity === '0'
    if (faded && r.top < innerHeight) return
    if (cs.visibility === 'hidden' && !faded && !veiled) return
    veiled ||= faded
    const sized = r.width >= 1 && r.height >= 1
    const push = (kind: LayerKind, fill = '', sides = '') =>
      layers.push({ el: el as HTMLElement, kind, x: r.left + sx, y: r.top + sy, w: r.width, h: r.height, parent, fill, sides, copy: -1, master: -1 }) - 1

    // image mode (image.ts) builds its own tiles and says what each one is
    const forced = el.getAttribute('data-asm-kind') as LayerKind | null
    if (forced) {
      if (sized) push(forced)
      return
    }
    if (MEDIA.has(el.tagName)) {
      if (sized) push('media')
      return
    }
    // the root is never a layer: hiding <body> would take its background (the blank canvas) with it
    if (!top && el.textContent!.trim() && (inlineOnly(el) || ownText(el))) {
      if (sized) push('text', alpha(cs.backgroundColor) > 0.9 ? cs.backgroundColor : '')
      return
    }
    let me = parent
    if (!top && sized) {
      const s = shape(el, cs, r)
      if (s) me = s === 'box' ? push('box') : push('line', '', s)
    }
    // remember which layers each child produced, to spot repeated components afterwards
    const spans: { kid: Element; from: number; to: number }[] = []
    for (const kid of el.children) {
      const from = layers.length
      walk(kid, me, false, veiled)
      spans.push({ kid, from, to: layers.length })
    }
    repeats(spans)
  }

  // Alike siblings in a row (same tag and classes, each with a few layers): the first is built, the rest are copies of it.
  function repeats(spans: { kid: Element; from: number; to: number }[]) {
    const sig = (s: (typeof spans)[number]) => (s.to - s.from >= 2 ? s.kid.tagName + '|' + s.kid.getAttribute('class') : '')
    for (let i = 0; i < spans.length; ) {
      let j = i + 1
      const key = sig(spans[i])
      while (key && j < spans.length && sig(spans[j]) === key) j++
      const run = spans.slice(i, j)
      i = j
      // an inner run found earlier keeps its layers; nesting copies inside copies is not worth the bookkeeping
      if (run.length < MIN_REPEAT || run.some((s) => layers.slice(s.from, s.to).some((l) => l.copy >= 0 || l.master >= 0))) continue
      const group = groups++
      run.forEach((s, n) => {
        const r = s.kid.getBoundingClientRect()
        const copy = n ? copies.push({ el: s.kid as HTMLElement, from: run[0].kid as HTMLElement, group, x: r.left + sx, y: r.top + sy }) - 1 : -1
        for (const l of layers.slice(s.from, s.to)) {
          if (n) l.copy = copy
          else l.master = group
        }
      })
    }
  }

  walk(root, -1, true)
  return { layers, copies }
}

export const fromDOM = (root: Element) => snapshot(root).layers
