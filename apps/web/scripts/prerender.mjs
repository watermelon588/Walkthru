// After `vite build`: write the public pages as real HTML (src/prerender.tsx), plus the files Cloudflare Pages
// routes by (public/_redirects): shell.html for app routes, 404.html for unknown paths. Also writes sitemap.xml and
// llms-full.txt from the same pages, so they never drift from the site.
import { readFileSync, rmSync, writeFileSync } from 'node:fs'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { build } from 'vite'

const SITE = 'https://trywalkthru.com'
const root = fileURLToPath(new URL('..', import.meta.url))
const dist = `${root}dist/`
const ssr = `${root}node_modules/.prerender/`

await build({ root, logLevel: 'warn', publicDir: false, build: { ssr: 'src/prerender.tsx', outDir: ssr, emptyOutDir: true } })
const { PAGES, faqs, render } = await import(pathToFileURL(`${ssr}prerender.js`).href)
const template = readFileSync(`${dist}index.html`, 'utf8')
if (!template.includes('<div id="root"></div>')) throw new Error('dist/index.html has no empty #root to fill')

const esc = (s) => s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;')
const noindex = template.replace('</head>', '    <meta name="robots" content="noindex" />\n  </head>')
writeFileSync(`${dist}shell.html`, noindex) // app routes: rendered in the browser after sign-in
writeFileSync(`${dist}404.html`, noindex) // unknown paths: Pages answers 404 with this, the app shows Not found

const ORG = { '@type': 'Organization', '@id': `${SITE}/#org`, name: 'Walkthru', url: `${SITE}/`, logo: `${SITE}/apple-touch-icon.png` }
const LD = { '@context': 'https://schema.org', '@graph': [
  ORG,
  { '@type': 'WebSite', '@id': `${SITE}/#site`, name: 'Walkthru', url: `${SITE}/`, description: PAGES['/'].description, inLanguage: 'en', publisher: { '@id': `${SITE}/#org` } },
  // FAQPage, not SoftwareApplication: that one needs reviews or a rating we do not have.
  { '@type': 'FAQPage', '@id': `${SITE}/#faq`, mainEntity: faqs.map((f) => ({ '@type': 'Question', name: f.q, acceptedAnswer: { '@type': 'Answer', text: f.a } })) },
] }

const text = (html) => html.replace(/<(script|style|svg)[\s\S]*?<\/\1>/g, ' ').replace(/<[^>]+>/g, ' ')
  .replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#x27;|&#39;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>')
  .replace(/\s+/g, ' ').trim()
const full = []
for (const [path, meta] of Object.entries(PAGES)) {
  let body = await render(path)
  // React 19 hoists a page's <title> and resource preloads to the start of its output; they belong in <head>.
  let title = template.match(/<title>([\s\S]*?)<\/title>/)[1]
  const hoisted = body.match(/^(?:<title>[\s\S]*?<\/title>|<link [^>]*\/?>)*/)[0]
  body = body.slice(hoisted.length)
  const preloads = hoisted.replace(/<title>([\s\S]*?)<\/title>/, (_, t) => { title = t; return '' })
  const url = `${SITE}${path === '/' ? '/' : path}`
  const head = [
    `<link rel="canonical" href="${url}" />`,
    `<meta property="og:url" content="${url}" />`,
    ...(preloads ? [preloads] : []),
    ...(path === '/' ? [`<script type="application/ld+json">${JSON.stringify(LD).replace(/</g, '\\u003c')}</script>`] : []),
  ].map((l) => `    ${l}\n`).join('')
  const html = template
    .replace(/<title>[\s\S]*?<\/title>/, `<title>${title}</title>`)
    .replace(/(<meta name="description" content=")[^"]*/, `$1${esc(meta.description)}`)
    .replace(/(<meta property="og:title" content=")[^"]*/, `$1${title}`)
    .replace(/(<meta property="og:description" content=")[^"]*/, `$1${esc(meta.description)}`)
    .replace('</head>', `${head}  </head>`)
    .replace('<div id="root"></div>', `<div id="root">${body}</div>`)
  writeFileSync(`${dist}${path === '/' ? 'index' : path.slice(1)}.html`, html)
  full.push(`# ${text(title)}\nURL: ${url}\n\n${text(body)}\n`)
  console.log(`prerendered ${path} (${Math.round(html.length / 1024)} kB)`)
}

const day = new Date().toISOString().slice(0, 10)
writeFileSync(`${dist}sitemap.xml`, `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${
  Object.keys(PAGES).map((p) => `  <url><loc>${SITE}${p}</loc><lastmod>${day}</lastmod></url>`).join('\n')}\n</urlset>\n`)
writeFileSync(`${dist}llms-full.txt`, `# Walkthru\n\n> ${PAGES['/'].description}\n\nThe full text of every public page, generated at build time on ${day}.\n\n${full.join('\n')}`)
rmSync(ssr, { recursive: true, force: true })
