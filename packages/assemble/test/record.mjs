// Record a rebuild as a frame-exact 30 fps video. Usage: node test/record.mjs <out.mp4> <url> [maxSeconds] [speed]
// Needs ffmpeg on PATH and a fresh `npm run build`. The engine is stepped by hand, one frame per screenshot,
// and the page is scrolled whenever the crew has finished what is in view.
import { spawn } from 'node:child_process'
import { BUNDLE, launch, sleep } from './cdp.mjs'

const [out, url, maxSeconds = '45', speed = '1'] = process.argv.slice(2)
if (!out || !url) throw new Error('usage: record.mjs <out.mp4> <url> [maxSeconds] [speed]')

const b = await launch()
const ffmpeg = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', '30', '-i', '-', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2', out], { stdio: ['pipe', 'inherit', 'inherit'] })
const frame = async () => ffmpeg.stdin.write(Buffer.from(await b.shot('jpeg'), 'base64'))

try {
  await b.go(url)
  await b.js(`document.fonts.ready.then(() => scrollTo(0, 0))`)
  await sleep(4000)
  await b.js(BUNDLE() + ';0')
  for (let i = 0; i < 20; i++) await frame() // two thirds of a second of the real page first
  await b.js(`window.__h = Assemble.assemble(document.body, { autoplay: false, scroll: 'tour', speed: ${Number(speed)}, seed: 11 }); 0`)
  let s
  for (let i = 0; i < Number(maxSeconds) * 30; i++) {
    s = await b.js(`(() => { __h.step(1000 / 30); const s = __h.stats(); return { phase: s.phase, built: s.built, total: s.total, agents: s.agents } })()`)
    await frame()
    if (s.phase === 'finished') break
  }
  // the finale: move a pretend mouse in a loop so the flock has something to follow
  for (let i = 0; i < 150; i++) {
    await b.js(`(() => { const t = ${i} / 30; dispatchEvent(new PointerEvent('pointermove', { clientX: innerWidth / 2 + Math.cos(t * 1.6) * 380, clientY: innerHeight / 2 + Math.sin(t * 2.3) * 220 })); __h.step(1000 / 30) })()`)
    await frame()
  }
  await b.js(`__h.destroy()`)
  for (let i = 0; i < 15; i++) await frame()
  console.log(out, s)
} finally {
  ffmpeg.stdin.end()
  await new Promise((r) => ffmpeg.on('close', r))
  b.close()
}
