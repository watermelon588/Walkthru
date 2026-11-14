// Hides the real elements and reveals them again. The only things this adds to the host page are a
// `data-asm` attribute per layer, one <style>, and a temporary inline clip-path while text is typed.
import type { Layer } from './blueprint.ts'

export interface Caret {
  x: number
  top: number
  bottom: number
}

// A hidden parent hides its children by inheritance, so a revealed child needs an explicit `visible`.
const CSS = '[data-asm="0"]{visibility:hidden!important}[data-asm="1"]{visibility:visible!important}'
const PAD = 40
const WIPE_LINE = 22 // px: assumed line height of text inside a screenshot
const WIPE_COLS = 24 // "characters" per wiped line

export class Stage {
  layers: Layer[]
  style = document.createElement('style')
  texts = new Map<number, { nodes: Text[]; total: number }>()
  clips = new Map<number, string>()
  range = document.createRange()

  // ponytail: tags are applied once. If a host framework re-creates an element mid-run it shows early;
  // add a MutationObserver that re-tags when that is seen on a real page.
  constructor(layers: Layer[]) {
    this.layers = layers
    this.style.textContent = CSS
    document.head.append(this.style)
    for (const l of layers) l.el.setAttribute('data-asm', '0')
  }

  show(i: number) {
    this.layers[i].el.setAttribute('data-asm', '1')
  }

  rect(i: number) {
    return this.layers[i].el.getBoundingClientRect()
  }

  private text(i: number) {
    let t = this.texts.get(i)
    if (!t) {
      const nodes: Text[] = []
      let total = 0
      const tw = document.createTreeWalker(this.layers[i].el, NodeFilter.SHOW_TEXT)
      for (let n = tw.nextNode(); n; n = tw.nextNode()) {
        if (!n.nodeValue!.trim()) continue
        nodes.push(n as Text)
        total += n.nodeValue!.length
      }
      this.texts.set(i, (t = { nodes, total }))
    }
    return t
  }

  // A "text" layer with no text in it is a picture of text (image mode): it is wiped in line by line instead.
  private wipe(i: number) {
    if (this.text(i).nodes.length) return 0
    return Math.max(1, Math.round(this.layers[i].h / WIPE_LINE))
  }

  total(i: number) {
    return this.wipe(i) * WIPE_COLS || this.text(i).total
  }

  private locate(i: number, n: number): [Node, number] {
    const { nodes } = this.text(i)
    if (!nodes.length) return [this.layers[i].el, 0]
    let left = n
    for (const node of nodes) {
      if (left <= node.length) return [node, left]
      left -= node.length
    }
    const last = nodes[nodes.length - 1]
    return [last, last.length]
  }

  /** where the caret sits after `n` characters, in viewport coordinates */
  caret(i: number, n: number): Caret {
    const el = this.layers[i].el
    const lines = this.wipe(i)
    if (lines) {
      const r = el.getBoundingClientRect()
      const line = Math.min(lines - 1, Math.floor(n / WIPE_COLS))
      const top = r.top + (r.height / lines) * line
      return { x: r.left + (r.width * Math.min(WIPE_COLS, n - line * WIPE_COLS)) / WIPE_COLS, top, bottom: top + r.height / lines }
    }
    const [node, offset] = this.locate(i, n)
    this.range.setStart(node, offset)
    this.range.setEnd(node, offset)
    let r: DOMRect | undefined = this.range.getClientRects()[0]
    if (!r && node.nodeType === 3 && (node as Text).length) {
      // a collapsed range at a line edge can have no box; measure the neighbouring character instead
      const at = Math.min(offset, (node as Text).length - 1)
      this.range.setStart(node, at)
      this.range.setEnd(node, at + 1)
      const c = this.range.getClientRects()[0]
      if (c) return { x: offset > at ? c.right : c.left, top: c.top, bottom: c.bottom }
    }
    r ||= el.getBoundingClientRect()
    return { x: r.left, top: r.top, bottom: r.bottom }
  }

  /** Clip the real element so only its first `n` characters show: every line above the caret, then the caret line up to the caret. */
  type(i: number, n: number): Caret {
    const el = this.layers[i].el
    if (!this.clips.has(i)) this.clips.set(i, el.style.clipPath)
    const c = this.caret(i, n)
    if (n >= this.total(i)) {
      el.style.clipPath = this.clips.get(i)!
      return c
    }
    const box = el.getBoundingClientRect()
    const x = c.x - box.left
    const y1 = c.top - box.top
    const y2 = c.bottom - box.top
    const far = box.width + PAD
    el.style.clipPath = `polygon(${-PAD}px ${-PAD}px,${far}px ${-PAD}px,${far}px ${y1}px,${x}px ${y1}px,${x}px ${y2}px,${-PAD}px ${y2}px)`
    return c
  }

  /** boxes of the characters after `n`: painted over on the canvas while a label inside a button is typed */
  rest(i: number, n: number): DOMRect[] {
    const { nodes } = this.text(i)
    if (!nodes.length) return []
    const [node, offset] = this.locate(i, n)
    const last = nodes[nodes.length - 1]
    this.range.setStart(node, offset)
    this.range.setEnd(last, last.length)
    return [...this.range.getClientRects()]
  }

  destroy() {
    for (const [i, clip] of this.clips) this.layers[i].el.style.clipPath = clip
    for (const l of this.layers) {
      l.el.removeAttribute('data-asm')
      if (l.el.getAttribute('style') === '') l.el.removeAttribute('style')
    }
    this.style.remove()
  }
}
