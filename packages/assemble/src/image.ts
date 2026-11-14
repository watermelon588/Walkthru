// Rebuild a picture of a page (a screenshot) instead of a live page.
// The screenshot is cut into its content blocks (regions.ts), each block becomes a tile showing its part of the
// picture, and the normal engine builds those tiles over a blank layer. When it finishes the layer is removed and
// whatever the host was already showing underneath (the real <img>) is back, untouched.
import { assemble, type Handle, type Options } from './index.ts'
import { regions, type Region } from './regions.ts'

export interface ImageOptions extends Options {
  /** resolves once the picture has been analysed and the run has started */
  onStart?(tiles: number): void
}

const SAMPLE = 192

function analyse(img: HTMLImageElement) {
  const w = SAMPLE
  const h = Math.max(1, Math.round((img.naturalHeight / img.naturalWidth) * SAMPLE))
  const canvas = document.createElement('canvas')
  canvas.width = w
  canvas.height = h
  const ctx = canvas.getContext('2d', { willReadFrequently: true })!
  ctx.drawImage(img, 0, 0, w, h)
  return regions(ctx.getImageData(0, 0, w, h).data, w, h) // throws when the picture is cross-origin without CORS
}

// ponytail: when the pixels cannot be read, fall back to a plain grid of tiles on a neutral backdrop
function grid(): { bg: string; list: Region[] } {
  const list: Region[] = []
  for (let r = 0; r < 3; r++) for (let c = 0; c < 4; c++) list.push({ x: c / 4, y: r / 3, w: 1 / 4, h: 1 / 3, kind: 'media' })
  return { bg: '', list }
}

/**
 * Play the rebuild over `host`, which should be a positioned box already showing `src` at its full size.
 * Returns straight away; the run starts once the picture has loaded. destroy() is safe at any time.
 */
export function assembleImage(host: HTMLElement, src: string, options: ImageOptions = {}): Handle {
  let run: Handle | null = null
  let dead = false
  const layer = document.createElement('div')
  layer.style.cssText = 'position:absolute;inset:0;overflow:hidden;'
  const idle = { phase: 'loading', total: 0, built: 0, ready: 0, active: 0, agents: 0, time: 0, log: [] as string[] }

  function start(found: { bg: string; list: Region[] }) {
    if (dead) return
    layer.style.background = found.bg || getComputedStyle(host).backgroundColor
    for (const r of found.list) {
      const tile = document.createElement('div')
      tile.setAttribute('data-asm-kind', r.kind)
      // show this tile's part of the picture: scale the picture to the layer, then slide it into place
      const px = r.w < 1 ? (r.x / (1 - r.w)) * 100 : 0
      const py = r.h < 1 ? (r.y / (1 - r.h)) * 100 : 0
      tile.style.cssText = `position:absolute;left:${r.x * 100}%;top:${r.y * 100}%;width:${r.w * 100}%;height:${r.h * 100}%;background:url("${src.replace(/"/g, '%22')}") ${px}% ${py}% / ${100 / r.w}% ${100 / r.h}% no-repeat;`
      layer.append(tile)
    }
    // No fade needed: until the engine hides them a moment later, the tiles show exactly what is underneath.
    host.append(layer)
    run = assemble(layer, {
      scroll: 'none',
      hud: false,
      rulers: false,
      bounds: host,
      agents: { min: 5, max: 9 },
      speed: 1.5,
      ...options,
      onDone() {
        layer.remove()
        options.onDone?.()
      },
    })
    options.onStart?.(found.list.length)
  }

  const img = new Image()
  img.crossOrigin = 'anonymous'
  img.onload = () => {
    let found: { bg: string; list: Region[] }
    try {
      const { bg, list } = analyse(img)
      found = list.length ? { bg: `rgb(${bg.join(',')})`, list } : grid()
    } catch {
      found = grid()
    }
    start(found)
  }
  // no CORS headers on the picture: it still displays in tiles, we just cannot read its pixels
  img.onerror = () => start(grid())
  img.src = src

  return {
    step: (ms) => run?.step(ms),
    setSpeed: (s) => run?.setSpeed(s),
    destroy() {
      dead = true
      run?.destroy()
      layer.remove()
    },
    stats: () => run?.stats() ?? idle,
  }
}
