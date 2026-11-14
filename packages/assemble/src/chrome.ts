// Everything that is not the page itself: cursors, placeholder boxes, selection outlines, size badges, carets,
// pen lines, copy ghosts, rulers and guides. One canvas above the page, in viewport coordinates, inside a shadow root.
import { HOST_ATTR } from './blueprint.ts'

export type Tool = 'arrow' | 'cross' | 'text' | 'pen'

interface Box {
  left: number
  top: number
  width: number
  height: number
}

const MONO = '500 11px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace'
export const RULER = 18

export class Chrome {
  host = document.createElement('div')
  root: ShadowRoot
  canvas = document.createElement('canvas')
  ctx = this.canvas.getContext('2d')!
  outlineColor: string
  copyColor: string
  scale: number
  w = 0
  h = 0
  resize = () => {
    const dpr = Math.min(devicePixelRatio || 1, 2)
    this.w = innerWidth
    this.h = innerHeight
    this.canvas.width = Math.round(this.w * dpr)
    this.canvas.height = Math.round(this.h * dpr)
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  }

  constructor(outlineColor: string, copyColor: string, scale = 1) {
    this.outlineColor = outlineColor
    this.copyColor = copyColor
    this.scale = scale
    this.host.setAttribute(HOST_ATTR, '')
    this.host.style.cssText = 'position:fixed;inset:0;z-index:2147483647;pointer-events:none;'
    this.canvas.setAttribute('aria-hidden', 'true')
    this.canvas.style.cssText = 'display:block;width:100%;height:100%;'
    this.root = this.host.attachShadow({ mode: 'open' })
    this.root.append(this.canvas)
    document.documentElement.append(this.host)
    this.resize()
    addEventListener('resize', this.resize)
  }

  clear() {
    this.ctx.clearRect(0, 0, this.w, this.h)
  }

  /** keep everything drawn until unclip() inside one rectangle (a region of the page, not the whole screen) */
  clip(r: Box) {
    this.ctx.save()
    this.ctx.beginPath()
    this.ctx.rect(r.left, r.top, r.width, r.height)
    this.ctx.clip()
  }

  unclip() {
    this.ctx.restore()
  }

  /** flat page-coloured wash, used to fade the real page out before it is hidden */
  wash(color: string, a: number) {
    const c = this.ctx
    c.globalAlpha = a
    c.fillStyle = color
    c.fillRect(0, 0, this.w, this.h)
    c.globalAlpha = 1
  }

  /** grey placeholder being dragged out, before the real element is shown */
  ghost(r: Box, media: boolean) {
    const c = this.ctx
    c.fillStyle = 'rgba(127,127,127,0.16)'
    c.fillRect(r.left, r.top, r.width, r.height)
    if (media && r.width > 44 && r.height > 36) {
      const x = r.left + r.width / 2
      const y = r.top + r.height / 2
      c.strokeStyle = 'rgba(127,127,127,0.7)'
      c.lineWidth = 1.25
      c.lineJoin = 'round'
      c.strokeRect(x - 9, y - 7, 18, 14)
      c.beginPath()
      c.moveTo(x - 8, y + 5)
      c.lineTo(x - 2, y - 1)
      c.lineTo(x + 2, y + 3)
      c.lineTo(x + 5, y)
      c.lineTo(x + 8, y + 3)
      c.stroke()
      c.beginPath()
      c.arc(x - 4, y - 3, 1.5, 0, Math.PI * 2)
      c.stroke()
    }
  }

  private badge(label: string, cx: number, y: number, color: string) {
    const c = this.ctx
    c.font = MONO
    const tw = c.measureText(label).width + 10
    const bx = Math.round(cx - tw / 2)
    c.fillStyle = color
    c.beginPath()
    c.roundRect(bx, Math.round(y), tw, 17, 3)
    c.fill()
    c.fillStyle = '#fff'
    c.textBaseline = 'middle'
    c.textAlign = 'left'
    c.fillText(label, bx + 5, Math.round(y) + 9)
  }

  /** selection outline with corner handles and a size badge */
  select(r: Box, a = 1) {
    const c = this.ctx
    c.globalAlpha = a
    c.strokeStyle = this.outlineColor
    c.lineWidth = 1
    c.strokeRect(Math.round(r.left) + 0.5, Math.round(r.top) + 0.5, Math.round(r.width), Math.round(r.height))
    c.fillStyle = '#fff'
    for (const [x, y] of [[r.left, r.top], [r.left + r.width, r.top], [r.left, r.top + r.height], [r.left + r.width, r.top + r.height]]) {
      c.fillRect(Math.round(x) - 3, Math.round(y) - 3, 7, 7)
      c.strokeRect(Math.round(x) - 2.5, Math.round(y) - 2.5, 6, 6)
    }
    this.badge(`${Math.round(r.width)} × ${Math.round(r.height)}`, r.left + r.width / 2, r.top + r.height + 7, this.outlineColor)
    c.globalAlpha = 1
  }

  /** a component being alt-dragged to where its duplicate goes, with how far it has travelled */
  copy(r: Box, travelled: number, a = 1) {
    const c = this.ctx
    c.globalAlpha = a * 0.08
    c.fillStyle = this.copyColor
    c.fillRect(r.left, r.top, r.width, r.height)
    c.globalAlpha = a
    c.strokeStyle = this.copyColor
    c.lineWidth = 1
    c.strokeRect(Math.round(r.left) + 0.5, Math.round(r.top) + 0.5, Math.round(r.width), Math.round(r.height))
    if (travelled > 0) this.badge(String(Math.round(travelled)), r.left + r.width / 2, r.top - 22, this.copyColor)
    c.globalAlpha = 1
  }

  /** thin frame round a text block while it is typed */
  frame(r: Box, a = 1) {
    const c = this.ctx
    c.globalAlpha = a * 0.7
    c.strokeStyle = this.outlineColor
    c.lineWidth = 1
    c.strokeRect(Math.round(r.left) - 2.5, Math.round(r.top) - 2.5, Math.round(r.width) + 5, Math.round(r.height) + 5)
    c.globalAlpha = 1
  }

  caret(x: number, top: number, bottom: number, color: string) {
    this.ctx.fillStyle = color
    this.ctx.fillRect(Math.round(x), top, 1.5, bottom - top)
  }

  /** paint over the not-yet-typed part of a label with the button's own colour */
  cover(rects: Box[], color: string) {
    this.ctx.fillStyle = color
    for (const r of rects) this.ctx.fillRect(r.left - 1, r.top - 1, r.width + 2, r.height + 2)
  }

  /** pen stroke from one anchor point towards the other; p is how much of it is drawn */
  line(x1: number, y1: number, x2: number, y2: number, p: number) {
    const c = this.ctx
    const ex = x1 + (x2 - x1) * p
    const ey = y1 + (y2 - y1) * p
    c.strokeStyle = this.outlineColor
    c.lineWidth = 1
    c.beginPath()
    c.moveTo(x1, Math.round(y1) + 0.5)
    c.lineTo(ex, Math.round(ey) + 0.5)
    c.stroke()
    for (const [x, y] of [[x1, y1], [ex, ey]]) {
      c.fillStyle = '#fff'
      c.beginPath()
      c.arc(x, y, 3, 0, Math.PI * 2)
      c.fill()
      c.stroke()
    }
  }

  /** dark rulers along the top and left edges, ticked in page pixels */
  rulers(sx: number, sy: number, a: number) {
    const c = this.ctx
    c.globalAlpha = a
    c.fillStyle = 'rgba(28,28,31,0.94)'
    c.fillRect(0, 0, this.w, RULER)
    c.fillRect(0, RULER, RULER, this.h - RULER)
    c.strokeStyle = 'rgba(255,255,255,0.28)'
    c.fillStyle = 'rgba(255,255,255,0.6)'
    c.font = '9px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace'
    c.textBaseline = 'middle'
    c.textAlign = 'left'
    c.lineWidth = 1
    c.beginPath()
    for (let v = Math.ceil((sx + RULER) / 50) * 50; v - sx < this.w; v += 50) {
      const x = Math.round(v - sx) + 0.5
      c.moveTo(x, v % 100 ? RULER - 4 : RULER - 9)
      c.lineTo(x, RULER)
      if (v % 100 === 0) c.fillText(String(v), x + 3, 7)
    }
    for (let v = Math.ceil((sy + RULER) / 50) * 50; v - sy < this.h; v += 50) {
      const y = Math.round(v - sy) + 0.5
      c.moveTo(v % 100 ? RULER - 4 : RULER - 9, y)
      c.lineTo(RULER, y)
      if (v % 100 === 0) {
        c.save()
        c.translate(7, y - 3)
        c.rotate(-Math.PI / 2)
        c.fillText(String(v), 0, 0)
        c.restore()
      }
    }
    c.stroke()
    c.globalAlpha = 1
  }

  /** vertical ruler guide */
  guide(x: number, a: number) {
    const c = this.ctx
    c.globalAlpha = a * 0.75
    c.fillStyle = this.copyColor
    c.fillRect(Math.round(x), 0, 1, this.h)
    c.globalAlpha = 1
  }

  /** angle turns the arrow to face where it is heading (the finale flock); 0 is the usual up-left pointer */
  cursor(x: number, y: number, color: string, tool: Tool, angle = 0) {
    const c = this.ctx
    c.save()
    c.translate(x, y)
    if (angle) c.rotate(angle)
    c.scale(this.scale, this.scale)
    c.lineJoin = 'round'
    c.lineCap = 'round'
    if (tool === 'arrow' || tool === 'pen') {
      c.shadowColor = 'rgba(0,0,0,0.28)'
      c.shadowBlur = 4
      c.shadowOffsetY = 1
      c.beginPath()
      if (tool === 'arrow') {
        c.moveTo(0, 0)
        c.lineTo(14, 6)
        c.lineTo(7.2, 7.9)
        c.lineTo(5, 14.6)
      } else {
        // pen nib: tip on the point being drawn
        c.moveTo(0, 0)
        c.lineTo(4, 10)
        c.lineTo(9.5, 15.5)
        c.lineTo(15.5, 9.5)
        c.lineTo(10, 4)
      }
      c.closePath()
      c.fillStyle = color
      c.fill()
      c.shadowColor = 'transparent'
      c.strokeStyle = '#fff'
      c.lineWidth = 1.5
      c.stroke()
    } else {
      // crosshair or I-beam: white underlay so it reads on any background
      const lines = tool === 'cross' ? [[-7, 0, 7, 0], [0, -7, 0, 7]] : [[0, -8, 0, 8], [-3, -8, 3, -8], [-3, 8, 3, 8]]
      for (const [width, stroke] of [[3.5, '#fff'], [1.5, color]] as const) {
        c.lineWidth = width
        c.strokeStyle = stroke
        c.beginPath()
        for (const [x1, y1, x2, y2] of lines) {
          c.moveTo(x1, y1)
          c.lineTo(x2, y2)
        }
        c.stroke()
      }
    }
    c.restore()
  }

  destroy() {
    removeEventListener('resize', this.resize)
    this.host.remove()
  }
}
