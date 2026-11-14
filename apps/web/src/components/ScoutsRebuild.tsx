import { assembleImage } from 'assemble'
import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'

const reducedMotion = () => typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches

/** Wraps a picture of a page. The first time it is on screen, a crew of scouts (packages/assemble, image mode)
 *  rebuilds the picture block by block over itself, once, then leaves it exactly as it was. Never loops; a quiet
 *  Replay button runs it again. Visitors who asked for reduced motion just see the picture. */
export function ScoutsRebuild({ src, children }: { src: string; children: ReactNode }) {
  const host = useRef<HTMLDivElement>(null)
  const fx = useRef<HTMLDivElement>(null) // the scouts draw in here; React never puts anything inside it
  const run = useRef<{ destroy(): void } | null>(null)
  const [done, setDone] = useState(false)

  const play = useCallback(() => {
    if (!fx.current) return
    run.current?.destroy()
    setDone(false)
    const ink = getComputedStyle(document.documentElement).getPropertyValue('--ink').trim() || undefined
    // Calmer than the engine's image default (speed 1.5, 5-9 scouts): a hero visitor should be able to follow one scout.
    run.current = assembleImage(fx.current, src, { outline: ink, speed: 0.75, agents: { min: 3, max: 5 }, onDone: () => setDone(true) })
  }, [src])

  useEffect(() => {
    const el = host.current
    if (!el || reducedMotion()) return
    let timer = 0
    const seen = new IntersectionObserver((entries) => {
      if (!entries.some((entry) => entry.isIntersecting)) return
      seen.disconnect()
      timer = window.setTimeout(play, 1200) // after the page's own entrance has settled
    }, { threshold: 0.5 })
    seen.observe(el)
    return () => { seen.disconnect(); window.clearTimeout(timer); run.current?.destroy() }
  }, [play])

  return (
    <div ref={host} className="relative">
      {children}
      <div ref={fx} aria-hidden className="pointer-events-none absolute inset-0" />
      {done && !reducedMotion() && (
        <button type="button" onClick={play} aria-label="Replay the scouts rebuilding this screen"
          className="absolute right-3 bottom-3 rounded-full border border-line bg-bg/90 px-3 py-1 text-xs text-muted transition-colors duration-150 hover:text-ink">
          Replay
        </button>
      )}
    </div>
  )
}
