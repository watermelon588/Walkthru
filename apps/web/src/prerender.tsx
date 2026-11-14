import { StrictMode } from 'react'
import { prerender } from 'react-dom/static'
import { StaticRouter } from 'react-router'
import { AppRoutes } from './App'

export { faqs } from './content'

/** Public pages written as HTML at build time (scripts/prerender.mjs), so crawlers, link previews and AI assistants
 *  read real copy without running JavaScript. Each needs its own title and description; the home page keeps index.html's. */
export const PAGES: Record<string, { title?: string; description: string }> = {
  '/': { description: 'The launch check for apps built with AI: AI test users try your signup and dashboard, plus SEO, AI search readiness and passive security in one ranked report.' },
  '/pricing': { description: 'Walkthru pricing: a free plan with Instant Scan, a $9 one-time Launch Pack, Pro at $19 a month and Plus at $49 a month. No card is needed for Free.' },
  '/docs': { description: 'How Walkthru works: Instant Scan, the browser extension, test users, the fix prompt and the MCP server.' },
  '/security': { description: 'How Walkthru protects your site and data: passive checks only, extension permissions, where test users may act and how to report a vulnerability.' },
  '/privacy': { description: 'What Walkthru collects, why, how long it keeps it and how to delete your data.' },
  '/terms': { description: 'The terms for using Walkthru, its plans and its reports.' },
  '/bot': { description: 'WalkthruBot: what it fetches, how it identifies itself, how it respects robots.txt and how to contact us about it.' },
}

/** The same tree the browser renders, waiting for lazy pages, so hydration matches. */
export async function render(path: string): Promise<string> {
  const { prelude } = await prerender(<StrictMode><StaticRouter location={path}><AppRoutes /></StaticRouter></StrictMode>)
  return new Response(prelude).text()
}
