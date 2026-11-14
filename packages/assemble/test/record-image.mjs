// Record image mode: screenshot a page, show it in test/stage.html and rebuild it there.
// Usage: node test/record-image.mjs <out.mp4> <url>
import { spawn } from 'node:child_process'
import { join } from 'node:path'
import { pathToFileURL } from 'node:url'
import { BUNDLE, HERE, launch, sleep } from './cdp.mjs'

const [out, url] = process.argv.slice(2)
if (!out || !url) throw new Error('usage: record-image.mjs <out.mp4> <url>')
const b = await launch({ width: 1160, height: 760 })
const ffmpeg = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', '30', '-i', '-', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2', out], { stdio: ['pipe', 'inherit', 'inherit'] })
const frame = async () => ffmpeg.stdin.write(Buffer.from(await b.shot('jpeg'), 'base64'))
try {
  await b.send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false })
  await b.go(url)
  await sleep(4000)
  const picture = 'data:image/png;base64,' + (await b.shot())
  await b.send('Emulation.setDeviceMetricsOverride', { width: 1160, height: 760, deviceScaleFactor: 1, mobile: false })
  await b.go(pathToFileURL(join(HERE, 'stage.html')).href)
  await b.js(BUNDLE() + ';0')
  await b.js(`new Promise((done) => { const i = document.getElementById('frame'); i.onload = done; i.src = ${JSON.stringify(picture)} })`)
  for (let i = 0; i < 15; i++) await frame()
  const tiles = await b.js(`new Promise((done) => { window.__h = Assemble.assembleImage(document.getElementById('stage'), ${JSON.stringify(picture)}, { autoplay: false, onStart: done }) })`)
  let s
  for (let i = 0; i < 30 * 30; i++) {
    s = await b.js(`(() => { __h.step(1000 / 30); const s = __h.stats(); return { phase: s.phase, built: s.built, total: s.total, time: Math.round(s.time) } })()`)
    await frame()
    if (s.phase === 'done') break
  }
  for (let i = 0; i < 20; i++) await frame()
  console.log(out, { tiles, ...s })
} finally {
  ffmpeg.stdin.end()
  await new Promise((r) => ffmpeg.on('close', r))
  b.close()
}
