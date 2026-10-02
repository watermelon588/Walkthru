// Renders every diagram in diagrams.js to docs/diagrams/<name>.png with headless Edge.
// Usage: node docs/diagrams/render.cjs [name ...]   (needs Playwright; set PLAYWRIGHT_PATH if it is not resolvable)
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright');

(async () => {
  const url = 'file:///' + path.join(__dirname, 'sketch.html').replaceAll('\\', '/');
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1.5 });
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await page.goto(url);
  const names = process.argv.slice(2).length ? process.argv.slice(2) : await page.evaluate(() => Object.keys(DIAGRAMS));
  for (const name of names) {
    await page.goto(`${url}?d=${name}`);
    await page.waitForSelector('body[data-ready="1"]');
    await page.locator('#d').screenshot({ path: path.join(__dirname, `${name}.png`) });
    console.log('rendered', name);
  }
  await browser.close();
  if (errors.length) throw new Error(errors.join('\n'));
})();
