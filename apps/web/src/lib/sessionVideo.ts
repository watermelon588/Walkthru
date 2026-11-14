/** Export one test user's visit as a video file, made in the browser (no server, no upload). The saved frames are
 *  drawn to a canvas with the measured cursor, what the test user said, and watermark badges, and the canvas is
 *  recorded with MediaRecorder. Recording runs in real time, so a 40 second replay takes 40 seconds to export.
 *  The pure helpers at the top are tested in tests/sessionVideo.test.ts; they import types only. */
import type { Moment } from './live'

export const VIDEO = { width: 1280, height: 720, fps: 30 }
const TRAVEL_MS = 1100
const RING_MS = 500

export type Scene = { index: number; start: number; travel: number; hold: number }

/** When each page is on screen. The cursor travels to a measured target first; the page then stays long enough to read the comment. */
export function storyboard(list: Pick<Moment, 'pointer' | 'thought'>[]): { scenes: Scene[]; total: number } {
  let at = 0
  const scenes = list.map((moment, index) => {
    const travel = index > 0 && moment.pointer ? TRAVEL_MS : 0
    const hold = Math.min(4600, Math.max(2000, 900 + moment.thought.length * 38))
    const scene = { index, start: at, travel, hold }
    at += travel + hold
    return scene
  })
  return { scenes, total: at }
}

export function sceneAt(scenes: Scene[], ms: number): Scene {
  let found = scenes[0]
  for (const scene of scenes) if (scene.start <= ms) found = scene
  return found
}

/** Greedy word wrap with a measuring function, cut to `maxLines` with an ellipsis. */
export function wrapLines(text: string, maxWidth: number, maxLines: number, measure: (s: string) => number): string[] {
  const lines: string[] = []
  let line = ''
  for (const word of text.split(/\s+/).filter(Boolean)) {
    const next = line ? `${line} ${word}` : word
    if (!line || measure(next) <= maxWidth) { line = next; continue }
    lines.push(line)
    line = word
  }
  if (line) lines.push(line)
  if (lines.length <= maxLines) return lines
  const kept = lines.slice(0, maxLines)
  let last = kept[maxLines - 1]
  while (last && measure(`${last}…`) > maxWidth) last = last.slice(0, -1).trimEnd()
  kept[maxLines - 1] = `${last}…`
  return kept
}

/** MP4 where the browser can record it (recent Chrome, Edge, Safari), otherwise WebM. */
export function pickFormat(supported: (type: string) => boolean): { mime: string; ext: 'mp4' | 'webm' } | null {
  for (const mime of ['video/mp4;codecs=avc1.42E01E', 'video/mp4']) if (supported(mime)) return { mime, ext: 'mp4' }
  for (const mime of ['video/webm;codecs=vp9', 'video/webm']) if (supported(mime)) return { mime, ext: 'webm' }
  return null
}

export const videoName = (site: string, persona: string, ext: string) =>
  `walkthru-${site.replace(/^https?:\/\//, '').replace(/[^a-z0-9]+/gi, '-').replace(/^-|-$/g, '').toLowerCase() || 'visit'}-${persona.replace(/[^a-z0-9]+/gi, '-').toLowerCase()}.${ext}`

export type VideoJob = {
  list: Moment[]
  /** signed address of each frame path */
  urls: Record<string, string>
  name: string
  site: string
  /** badges in the corner: Walkthru's mark and name, and the owner's own name when they have set report branding */
  watermark: { mark: string; name: string; owner?: string }
  colors: { bg: string; ink: string; muted: string; line: string; surface: string; danger: string }
  onProgress?: (done: number, total: number) => void
  signal?: AbortSignal
}

const loadImage = (src: string) =>
  new Promise<HTMLImageElement>((resolve, reject) => {
    const image = new Image()
    image.crossOrigin = 'anonymous' // the canvas can only be recorded if every picture on it may be read
    image.onload = () => resolve(image)
    image.onerror = () => reject(new Error('A saved frame could not be loaded for the video.'))
    image.src = src
  })

const ease = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2)

export async function recordSession(job: VideoJob): Promise<{ blob: Blob; ext: 'mp4' | 'webm' }> {
  if (typeof MediaRecorder === 'undefined') throw new Error('This browser cannot record video. Try Chrome or Edge.')
  const format = pickFormat((type) => MediaRecorder.isTypeSupported(type))
  if (!format) throw new Error('This browser cannot record video. Try Chrome or Edge.')
  const { list, colors } = job
  const { scenes, total } = storyboard(list)
  if (!scenes.length) throw new Error('There is nothing to export for this visit.')

  const paths = [...new Set(list.map((m) => m.frame).filter((p): p is string => !!p && !!job.urls[p]))]
  const frames = new Map<string, HTMLImageElement>()
  await Promise.all(paths.map(async (path) => frames.set(path, await loadImage(job.urls[path]))))
  const mark = await loadImage(job.watermark.mark).catch(() => null)

  const { width: W, height: H } = VIDEO
  const canvas = document.createElement('canvas')
  canvas.width = W
  canvas.height = H
  const c = canvas.getContext('2d')!
  const SANS = 'system-ui, -apple-system, "Segoe UI", sans-serif'
  const MONO = 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace'
  const stage = { x: 40, y: 64, w: W - 80, h: 468 }
  const points = list.map((_, i) => { for (let k = i; k >= 0; k--) if (list[k].pointer) return list[k].pointer!; return { x: 0.88, y: 0.82 } })

  function pill(text: string, right: number, y: number, fill: string, color: string, icon?: HTMLImageElement | null) {
    c.font = `500 13px ${SANS}`
    const w = c.measureText(text).width + 24 + (icon ? 22 : 0)
    c.fillStyle = fill
    c.beginPath()
    c.roundRect(right - w, y, w, 28, 14)
    c.fill()
    if (icon) c.drawImage(icon, right - w + 10, y + 5, 18, 18)
    c.fillStyle = color
    c.textBaseline = 'middle'
    c.textAlign = 'left'
    c.fillText(text, right - w + 12 + (icon ? 22 : 0), y + 14.5)
    return right - w - 8
  }

  function draw(ms: number) {
    const scene = sceneAt(scenes, ms)
    const moment = list[scene.index]
    const local = ms - scene.start
    const travelling = local < scene.travel
    // while the cursor is on its way the previous page is still up; the new one appears when it arrives
    const shown = travelling ? list[scene.index - 1] : moment
    c.fillStyle = colors.bg
    c.fillRect(0, 0, W, H)

    // address bar
    c.fillStyle = colors.muted
    c.font = `12px ${MONO}`
    c.textBaseline = 'middle'
    c.textAlign = 'left'
    c.fillText(shown.url.replace(/^https?:\/\//, '').slice(0, 90), stage.x, 36)
    c.textAlign = 'right'
    c.fillText(`${scene.index + (travelling ? 0 : 1)} / ${list.length}`, stage.x + stage.w, 36)

    // the page, fitted inside the stage
    c.fillStyle = colors.surface
    c.beginPath()
    c.roundRect(stage.x, stage.y, stage.w, stage.h, 12)
    c.fill()
    const image = shown.frame ? frames.get(shown.frame) : undefined
    let box = { x: stage.x, y: stage.y, w: stage.w, h: stage.h }
    if (image) {
      const scale = Math.min(stage.w / image.naturalWidth, stage.h / image.naturalHeight)
      box = { w: image.naturalWidth * scale, h: image.naturalHeight * scale, x: 0, y: stage.y }
      box.x = stage.x + (stage.w - box.w) / 2
      box.y = stage.y + (stage.h - box.h) / 2
      c.save()
      c.beginPath()
      c.roundRect(box.x, box.y, box.w, box.h, 8)
      c.clip()
      c.drawImage(image, box.x, box.y, box.w, box.h)
      c.restore()
    }
    c.strokeStyle = colors.line
    c.lineWidth = 1
    c.beginPath()
    c.roundRect(stage.x + 0.5, stage.y + 0.5, stage.w - 1, stage.h - 1, 12)
    c.stroke()

    // the test user's cursor: only ever between measured points
    const from = points[Math.max(0, scene.index - 1)]
    const to = points[scene.index]
    const k = scene.travel ? ease(Math.min(1, local / scene.travel)) : 1
    const px = box.x + (from.x + (to.x - from.x) * k) * box.w
    const py = box.y + (from.y + (to.y - from.y) * k) * box.h
    const sinceArrive = local - scene.travel
    if (moment.pointer && moment.action === 'click' && sinceArrive >= 0 && sinceArrive < RING_MS) {
      const t = sinceArrive / RING_MS
      c.globalAlpha = 1 - t
      c.strokeStyle = colors.ink
      c.lineWidth = 2
      c.beginPath()
      c.arc(px, py, 8 + t * 22, 0, Math.PI * 2)
      c.stroke()
      c.globalAlpha = 1
    }
    c.save()
    c.translate(px, py)
    c.scale(1.5, 1.5)
    c.beginPath()
    c.moveTo(1, 0.5)
    c.lineTo(16, 8)
    c.lineTo(9.6, 9.9)
    c.lineTo(7.4, 16.5)
    c.closePath()
    c.fillStyle = colors.ink
    c.fill()
    c.strokeStyle = colors.bg
    c.lineWidth = 1.4
    c.lineJoin = 'round'
    c.stroke()
    c.restore()
    c.font = `500 13px ${SANS}` // the font pill() measures with, so the name tag sits just right of the cursor
    pill(job.name, px + 30 + c.measureText(job.name).width + 24, py + 26, colors.ink, colors.bg)

    // what the test user said
    c.textAlign = 'left'
    c.fillStyle = colors.muted
    c.font = `11px ${MONO}`
    c.fillText(`${job.name.toUpperCase()}  ·  ${(travelling ? moment.label : shown.label).toUpperCase()}`.slice(0, 110), stage.x, 566)
    c.fillStyle = colors.ink
    c.font = `300 22px ${SANS}`
    const said = shown.thought || 'No comment on this page.'
    wrapLines(said, W - 80 - 300, 3, (s) => c.measureText(s).width).forEach((line, i) => c.fillText(line, stage.x, 600 + i * 32))

    // watermark badges
    let right = W - 40
    // light pills: the mark is ink on clear, so it would vanish on a dark one
    right = pill(job.watermark.name, right, H - 60, colors.surface, colors.ink, mark)
    if (job.watermark.owner) pill(job.watermark.owner, right, H - 60, colors.surface, colors.ink)

    // progress
    c.fillStyle = colors.line
    c.fillRect(0, H - 4, W, 4)
    c.fillStyle = colors.ink
    c.fillRect(0, H - 4, W * Math.min(1, ms / total), 4)
  }

  draw(0) // fails here, before recording starts, if a frame came without permission to be read
  try {
    c.getImageData(0, 0, 1, 1)
  } catch {
    throw new Error('The saved frames cannot be read for a video in this browser.')
  }

  const recorder = new MediaRecorder(canvas.captureStream(VIDEO.fps), { mimeType: format.mime, videoBitsPerSecond: 4_000_000 })
  const chunks: Blob[] = []
  recorder.ondataavailable = (event) => { if (event.data.size) chunks.push(event.data) }
  const stopped = new Promise<void>((resolve) => { recorder.onstop = () => resolve() })
  recorder.start(500)
  const began = performance.now()
  await new Promise<void>((resolve, reject) => {
    function frame() {
      if (job.signal?.aborted) return reject(new DOMException('Export cancelled', 'AbortError'))
      const ms = performance.now() - began
      draw(Math.min(ms, total))
      job.onProgress?.(Math.min(ms, total), total)
      if (ms >= total + 400) return resolve() // hold the last frame a moment so the file does not end mid-fade
      requestAnimationFrame(frame)
    }
    requestAnimationFrame(frame)
  }).finally(() => recorder.stop())
  await stopped
  return { blob: new Blob(chunks, { type: format.mime.split(';')[0] }), ext: format.ext }
}
