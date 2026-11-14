// Headless Chrome over the DevTools protocol with Node's built-in WebSocket and fetch. No dependencies.
import { spawn } from 'node:child_process'
import { existsSync, mkdtempSync, readFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

export const HERE = dirname(fileURLToPath(import.meta.url))
export const BUNDLE = () => readFileSync(join(HERE, '..', 'dist', 'assemble.iife.js'), 'utf8')
export const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const CHROME = [process.env.CHROME_PATH, 'C:/Program Files/Google/Chrome/Application/chrome.exe', '/usr/bin/google-chrome', '/usr/bin/chromium'].find((p) => p && existsSync(p))

// Runs in about:blank: share of pixels where any channel differs by more than 16.
const DIFF = `(async (a, b) => {
  const load = (s) => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = 'data:image/png;base64,' + s })
  const [ia, ib] = await Promise.all([load(a), load(b)])
  const w = Math.min(ia.width, ib.width), h = Math.min(ia.height, ib.height)
  const px = (img) => { const c = new OffscreenCanvas(w, h).getContext('2d'); c.drawImage(img, 0, 0); return c.getImageData(0, 0, w, h).data }
  const da = px(ia), db = px(ib)
  let bad = 0
  for (let i = 0; i < da.length; i += 4) if (Math.max(Math.abs(da[i] - db[i]), Math.abs(da[i + 1] - db[i + 1]), Math.abs(da[i + 2] - db[i + 2])) > 16) bad++
  return +(bad / (w * h) * 100).toFixed(3)
})`

export async function launch({ width = 1440, height = 900, port = 9377, reducedMotion = false } = {}) {
  if (!CHROME) throw new Error('Chrome not found; set CHROME_PATH')
  const chrome = spawn(CHROME, ['--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${mkdtempSync(join(tmpdir(), 'assemble-'))}`, `--window-size=${width},${height}`, '--hide-scrollbars', '--no-first-run', 'about:blank'], { stdio: 'ignore' })
  let url
  for (let i = 0; i < 50 && !url; i++) {
    try {
      url = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find((t) => t.type === 'page')?.webSocketDebuggerUrl
    } catch {
      // chrome still starting
    }
    if (!url) await sleep(200)
  }
  if (!url) throw new Error('chrome did not start')
  const ws = new WebSocket(url)
  await new Promise((r) => ws.addEventListener('open', r, { once: true }))
  let seq = 0
  const pending = new Map()
  const waiters = new Map()
  ws.addEventListener('message', (e) => {
    const m = JSON.parse(e.data)
    if (m.id && pending.has(m.id)) {
      const { resolve, reject } = pending.get(m.id)
      pending.delete(m.id)
      if (m.error) reject(new Error(m.error.message))
      else resolve(m.result)
    } else if (m.method && waiters.has(m.method)) {
      waiters.get(m.method)()
      waiters.delete(m.method)
    }
  })
  const send = (method, params = {}) =>
    new Promise((resolve, reject) => {
      pending.set(++seq, { resolve, reject })
      ws.send(JSON.stringify({ id: seq, method, params }))
    })
  const js = async (expression) => {
    const r = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text)
    return r.result.value
  }
  const go = async (to) => {
    const loaded = new Promise((r) => waiters.set('Page.loadEventFired', r))
    await send('Page.navigate', { url: to })
    await loaded
  }
  await send('Page.enable')
  await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: false })
  if (reducedMotion) await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] })
  return {
    send,
    js,
    go,
    shot: async (format = 'png', full = false) => (await send('Page.captureScreenshot', { format, quality: 88, captureBeyondViewport: full })).data,
    /** percent of differing pixels between two base64 PNGs; navigates to about:blank */
    diff: async (a, b) => {
      await go('about:blank')
      return js(`${DIFF}(${JSON.stringify(a)}, ${JSON.stringify(b)})`)
    },
    close: () => chrome.kill(),
  }
}
