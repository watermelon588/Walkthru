// Browser checks against the built bundle. Usage: node test/browser.mjs [extra page url...]
// Run `npm run build` first. The fixture is always tested; extra URLs get the fidelity check only.
import assert from 'node:assert/strict'
import { pathToFileURL } from 'node:url'
import { join } from 'node:path'
import { BUNDLE, HERE, launch, sleep } from './cdp.mjs'

const FIXTURE = pathToFileURL(join(HERE, 'fixture.html')).href
const bundle = BUNDLE()
// reduced motion keeps the host pages still between screenshots; the engine is told to run anyway
const b = await launch({ reducedMotion: true })

async function open(url) {
  await b.go(url)
  await b.js(`document.fonts.ready.then(() => scrollTo(0, 0))`)
  // wait for preloaders and entrance animations: two identical screenshots in a row
  let still = false
  for (let i = 0, prev = ''; i < 12 && !still; i++) {
    await sleep(600)
    const now = await b.shot()
    still = now === prev
    prev = now
  }
  await b.js(bundle + ';0')
  return still
}

// Run to the end with manual stepping; returns what the engine reports plus leftovers on the page.
const RUN = (opts) => `(() => {
  const h = window.__h = Assemble.assemble(document.body, { autoplay: false, scroll: 'none', hud: false, respectReducedMotion: false, ...${JSON.stringify(opts)} })
  let mid = null, steps = 0
  while (!['done', 'finished'].includes(h.stats().phase) && steps++ < 40000) {
    h.step(1000 / 60)
    const s = h.stats()
    if (!mid && s.phase === 'build') mid = { hidden: document.querySelectorAll('[data-asm="0"]').length, total: s.total }
  }
  const s = h.stats()
  return { ...s, mid, steps, tagged: document.querySelectorAll('[data-asm]').length, styles: document.querySelectorAll('[style*="clip-path"]').length, hosts: document.querySelectorAll('[data-asm-host]').length }
})()`

const results = []
try {
  // ---- T1: the fixture turns into the layers we expect
  await open(FIXTURE)
  const layers = await b.js(`Assemble.fromDOM(document.body).map((l) => ({ id: l.el.id, cls: l.el.className, kind: l.kind, fill: !!l.fill, parent: l.parent }))`)
  const by = Object.fromEntries(layers.map((l, i) => [l.id, { ...l, i }]))
  assert.equal(by.headline.kind, 'text', 'a headline split into word spans is one text layer')
  assert.ok(!layers.some((l) => l.cls === 'word'), 'word spans are not layers of their own')
  assert.equal(by.para.kind, 'text')
  assert.deepEqual([by.button.kind, by.button.fill], ['text', true], 'a button is a painted label')
  assert.equal(by.img.kind, 'media')
  assert.equal(by.inline.kind, 'text')
  assert.equal(by.rule.kind, 'line', 'a rule is a pen line')
  // T5/T6: one-sided borders are lines; alike rows are one original plus copies
  const shape = await b.js(`(() => { const s = Assemble.snapshot(document.body); const of = (id) => s.layers.filter((l) => l.el.closest('#' + id)); return {
    band: s.layers.find((l) => l.el.id === 'band').kind + ':' + s.layers.find((l) => l.el.id === 'band').sides,
    row: s.layers.find((l) => l.el.id === 'r1').kind + ':' + s.layers.find((l) => l.el.id === 'r1').sides,
    copies: s.copies.map((c) => c.el.id + '<' + c.from.id),
    r1: of('r1').map((l) => [l.copy, l.master >= 0]), r3: of('r3').map((l) => l.copy), card: of('card').map((l) => l.copy) } })()`)
  assert.equal(shape.band, 'line:t', 'a section with only a top border is a line along its top')
  assert.equal(shape.row, 'line:b')
  assert.deepEqual(shape.copies, ['r2<r1', 'r3<r1', 'r4<r1'], 'rows two to four are copies of row one')
  assert.deepEqual(shape.r1, [[-1, true], [-1, true], [-1, true]], 'row one is the original: its border and two texts')
  assert.deepEqual(shape.r3, [1, 1, 1])
  assert.deepEqual(shape.card, [-1, -1, -1], 'a one-off card is not a copy')
  assert.equal(by.card.kind, 'box')
  assert.equal(by.title.parent, by.card.i, 'card content waits for the card')
  assert.equal(by.body.parent, by.card.i)
  assert.equal(by.swatch.kind, 'box')
  assert.ok(!by.later && !by.gone, 'opacity 0 and display none are skipped')
  assert.equal(by.belowText.kind, 'text', 'faded out below the fold is a scroll reveal, so it is built')

  // ---- T7/T8/T9: tour mode with rulers, a guide and the HUD, on a window too short to show the whole fixture
  await b.send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 420, deviceScaleFactor: 1, mobile: false })
  await open(FIXTURE)
  const plain = await b.js(`Assemble.assemble(document.body, { autoplay: false, scroll: 'none', hud: false, respectReducedMotion: false }).stats().total`)
  await open(FIXTURE)
  const stuck = await b.js(RUN({ scroll: 'follow', hud: true }).replace('40000', '3000'))
  assert.equal(stuck.phase, 'build', 'follow mode waits for the visitor to scroll')
  assert.ok(stuck.built < stuck.total && stuck.ready === 0 && stuck.active === 0)
  const hint = await b.js(`document.querySelector('[data-asm-host]').shadowRoot.querySelector('.hud').textContent`)
  assert.match(hint, /scroll to keep building/)
  await b.js(`__h.destroy()`)
  await open(FIXTURE)
  const tour = await b.js(RUN({ scroll: 'tour', hud: true }))
  assert.equal(tour.total, plain + 1, 'rulers add one guide task for the shared left edge')
  assert.equal(tour.phase, 'finished', 'with a HUD the run ends on the summary pill')
  assert.equal(tour.built, tour.total)
  assert.deepEqual([tour.tagged, tour.styles, tour.hosts], [0, 0, 1], 'page is clean, only our pill is left')
  assert.ok(await b.js(`scrollY > 0`), 'tour scrolled the page')
  // T10: after the summary the scouts flock to the mouse; the page stays whole while they do
  const flock = await b.js(`(() => {
    dispatchEvent(new PointerEvent('pointermove', { clientX: 300, clientY: 200 }))
    for (let i = 0; i < 240; i++) __h.step(1000 / 60)
    const c = document.querySelector('[data-asm-host]').shadowRoot.querySelector('canvas')
    const near = c.getContext('2d').getImageData(200 * (c.width / innerWidth), 100 * (c.height / innerHeight), 200 * (c.width / innerWidth), 200 * (c.height / innerHeight)).data
    let drawn = 0
    for (let i = 3; i < near.length; i += 4) if (near[i]) drawn++
    return { phase: __h.stats().phase, drawn, tagged: document.querySelectorAll('[data-asm]').length }
  })()`)
  assert.deepEqual([flock.phase, flock.tagged], ['finished', 0])
  assert.ok(flock.drawn > 200, `scouts should gather round the mouse, drew ${flock.drawn} px there`)
  const pill = await b.js(`(() => { const r = document.querySelector('[data-asm-host]').shadowRoot; const t = r.querySelector('.hud').textContent; r.querySelector('[data-k="replay"]').click(); return t })()`)
  assert.match(pill, /Rebuilt by \d+ scouts in [\d.]+s/)
  assert.equal(await b.js(`__h.stats().phase`), 'intro', 'Replay starts a fresh run')
  // T11: the Sound button turns audio on mid-run without breaking anything
  const sound = await b.js(`(() => { const btn = document.querySelector('[data-asm-host]').shadowRoot.querySelector('[data-k="sound"]'); btn.click(); for (let i = 0; i < 120; i++) __h.step(16.7); return [btn.getAttribute('aria-pressed'), __h.stats().phase] })()`)
  assert.deepEqual(sound, ['true', 'build'])
  const closed = await b.js(`(() => { for (let i = 0; i < 60; i++) __h.step(16.7); document.querySelector('[data-asm-host]').shadowRoot.querySelector('[data-k="close"]').click(); return [__h.stats().phase, document.querySelectorAll('[data-asm],[data-asm-host]').length] })()`)
  assert.deepEqual(closed, ['done', 0], 'close mid-run restores the page')
  await b.send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false })

  // ---- T12: <assemble-stage> rebuilds its own content and leaves it as it was
  await open(FIXTURE)
  const element = await b.js(`(() => {
    const el = document.createElement('assemble-stage')
    const card = document.getElementById('card')
    card.replaceWith(el)
    el.append(card)
    const defined = !!customElements.get('assemble-stage')
    // inline styles are re-serialised by the browser when touched, so compare structure and text, not the raw string
    const shape = () => el.querySelectorAll('*').length + '|' + el.textContent + '|' + el.querySelectorAll('[style*=clip-path]').length
    const before = shape()
    const run = el.play()
    // play() reads attributes only, so hand the test options to a second run
    run.destroy()
    const h = Assemble.assemble(el, { autoplay: false, respectReducedMotion: false })
    let steps = 0, hidden = 0
    while (h.stats().phase !== 'done' && steps++ < 20000) { h.step(1000 / 60); hidden = Math.max(hidden, el.querySelectorAll('[data-asm="0"]').length) }
    return { defined, total: h.stats().total, hidden, same: shape() === before, outside: document.querySelectorAll('[data-asm],[data-asm-host]').length, display: getComputedStyle(el).display }
  })()`)
  assert.ok(element.defined, 'loading the bundle defines <assemble-stage>')
  assert.deepEqual([element.total, element.same, element.outside, element.display], [3, true, 0, 'block'], 'card box and its two texts, restored exactly')
  assert.ok(element.hidden > 0)

  // ---- image mode: rebuild a screenshot inside a stage, as the live-run player does
  await open(FIXTURE)
  const picture = 'data:image/png;base64,' + (await b.shot())
  await b.go(pathToFileURL(join(HERE, 'stage.html')).href)
  await b.js(bundle + ';0')
  await b.js(`new Promise((done) => { const i = document.getElementById('frame'); i.onload = done; i.src = ${JSON.stringify(picture)} })`)
  const before = await b.shot()
  const image = await b.js(`new Promise((done) => {
    const host = document.getElementById('stage')
    const h = Assemble.assembleImage(host, ${JSON.stringify(picture)}, { autoplay: false, respectReducedMotion: false, onStart(tiles) {
      const kinds = [...host.querySelectorAll('[data-asm-kind]')].map((t) => t.getAttribute('data-asm-kind'))
      const box = host.getBoundingClientRect()
      let steps = 0, hidden = 0, outside = 0
      while (h.stats().phase !== 'done' && steps++ < 20000) {
        h.step(1000 / 60)
        hidden = Math.max(hidden, host.querySelectorAll('[data-asm="0"]').length)
        outside += document.querySelectorAll('#says[data-asm]').length
      }
      done({ tiles, kinds: [...new Set(kinds)].sort(), built: h.stats().built, total: h.stats().total, steps, hidden, outside, box: [box.width, box.height],
        kids: host.children.length, left: document.querySelectorAll('[data-asm],[data-asm-kind],[data-asm-host]').length })
    } })
  })`)
  assert.ok(image.tiles >= 6, `screenshot should split into several blocks, got ${image.tiles}`)
  assert.ok(image.kinds.includes('text') && image.kinds.length >= 2, `expected text and boxes, got ${image.kinds}`)
  assert.equal(image.built, image.total)
  assert.ok(image.hidden > 0, 'tiles were hidden, then built')
  assert.equal(image.outside, 0, 'nothing outside the stage is touched')
  assert.deepEqual([image.kids, image.left], [1, 0], 'the stage is left with just its own image')
  await sleep(100)
  const afterImage = await b.shot()
  const imageDiff = await b.diff(before, afterImage)
  assert.ok(imageDiff < 0.05, `stage differs after image mode by ${imageDiff}%`)
  results.push({ url: 'image mode (stage.html)', layers: image.total, frames: image.steps, diffPct: imageDiff })

  // ---- T2/T3/T4 on the fixture, then fidelity on any extra pages
  for (const url of [FIXTURE, ...process.argv.slice(2)]) {
    const still = await open(url)
    const real = await b.shot()
    const t0 = Date.now()
    const run = await b.js(RUN({ seed: 7 }))
    const wall = Date.now() - t0
    await sleep(150)
    const after = await b.shot()
    assert.equal(run.phase, 'done', `${url}: run did not finish`)
    assert.equal(run.built, run.total, `${url}: every task built`)
    assert.equal(run.mid.hidden > 0, true, `${url}: page was blanked`)
    assert.deepEqual([run.tagged, run.styles, run.hosts], [0, 0, 0], `${url}: nothing left behind on the page`)

    let again = null
    let fast = null
    if (url === FIXTURE) {
      await open(url)
      again = await b.js(RUN({ seed: 7 }))
      assert.deepEqual(again.log, run.log, 'same seed gives the same event log')
      await open(url)
      const other = await b.js(RUN({ seed: 8 }))
      assert.notDeepEqual(other.log, run.log, 'a different seed gives a different run')
      await open(url)
      fast = await b.js(RUN({ seed: 7, speed: 2 }))
      const ratio = fast.steps / run.steps
      assert.ok(Math.abs(ratio - 0.5) < 0.05, `2x speed should halve the frames, got ${ratio.toFixed(3)}`)
    }
    // A live site that animates by itself cannot be compared pixel for pixel; say so instead of failing on its motion.
    const pct = still || url === FIXTURE ? await b.diff(real, after) : 'page keeps moving, not compared'
    if (typeof pct === 'number') assert.ok(pct < 0.05, `${url}: page after the run differs from the real page by ${pct}%`)
    results.push({ url: url.slice(0, 60), layers: run.total, simSeconds: +(run.time / 1000).toFixed(1), agents: run.agents, diffPct: pct, frames: run.steps, msPerFrame: +(wall / run.steps).toFixed(2), speed2xRatio: fast ? +(fast.steps / run.steps).toFixed(3) : '' })
  }
} finally {
  b.close()
}
console.table(results)
console.log('browser checks passed')
