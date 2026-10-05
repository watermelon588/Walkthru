import { useEffect, useState } from 'react'
import { useLocation } from 'react-router'
import { Orb } from '../Loading'
import './preloader.css'

const HOLD = 750 // ms on screen after a page change
const EXIT = 500 // ms fade out (preloader.css)

/** The preloader: the thinking-orbs Orb, centred. `overlay` covers the viewport and fades out when `leaving`;
 *  without it, it fills a page (a Suspense fallback). The Orb draws from the page clock, so an overlay fading off a
 *  fallback underneath shows no jump. */
export function Preloader({ overlay = false, leaving = false, label = 'Loading' }: { overlay?: boolean; leaving?: boolean; label?: string }) {
  return (
    <div role="status" aria-label={label} className={overlay ? 'pl-overlay' : 'pl-page'} data-leaving={leaving || undefined}>
      <div className="pl-content" aria-hidden>
        <Orb size={96} />
      </div>
    </div>
  )
}

/** Team tabs live in the path (/app/team/:id/:tab) but are one page: switching tabs is not a page change. */
const pageOf = (path: string) => path.replace(/^(\/app\/team\/[^/]+)\/[^/]+\/?$/, '$1')

/** Shows the preloader on first load and after every page change, then fades it out. Mount once inside the router. */
export function RouteLoader() {
  const page = pageOf(useLocation().pathname)
  const [shown, setShown] = useState({ page, phase: 'in' as 'in' | 'out' | 'off' })
  if (shown.page !== page) setShown({ page, phase: 'in' }) // during render, so the new page never paints uncovered
  useEffect(() => {
    const out = window.setTimeout(() => setShown((s) => ({ ...s, phase: 'out' })), HOLD)
    const off = window.setTimeout(() => setShown((s) => ({ ...s, phase: 'off' })), HOLD + EXIT)
    return () => { window.clearTimeout(out); window.clearTimeout(off) }
  }, [page])
  if (shown.phase === 'off') return null
  return <Preloader overlay leaving={shown.phase === 'out'} label="Loading page" />
}
