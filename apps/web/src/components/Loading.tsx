import { useEffect, useRef, useState, type CSSProperties } from 'react'
import type { OrbState } from 'thinking-orbs'
import { MODE_DRAWS, resolvePreset } from 'thinking-orbs/engine'

const reduced = () => typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches

/** The thinking-orbs blob at any size. The library's component ships 20 and 64 px only; this draws its engine directly,
 *  pauses off screen and in hidden tabs, and holds one still frame for reduced motion. */
export function Orb({ size, state = 'working', speed = 1, className = '', style, label }: { size: number; state?: OrbState; speed?: number; className?: string; style?: CSSProperties; label?: string }) {
  const ref = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    const canvas = ref.current
    const ctx = canvas?.getContext('2d')
    if (!canvas || !ctx) return
    const dpr = Math.min(2, devicePixelRatio || 1)
    canvas.width = Math.round(size * dpr)
    canvas.height = Math.round(size * dpr)
    const { mode, speed: base, opts } = resolvePreset(state, 64)
    const draw = MODE_DRAWS[mode]
    const paint = (t: number) => {
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      ctx.clearRect(0, 0, size, size)
      draw(ctx, size, t, false, opts)
    }
    if (reduced()) { paint(0.6); return }
    let frame = 0
    let visible = true
    const loop = () => { paint((performance.now() / 1000) * base * speed); frame = requestAnimationFrame(loop) }
    const sync = () => { cancelAnimationFrame(frame); if (visible && document.visibilityState !== 'hidden') frame = requestAnimationFrame(loop) }
    const io = new IntersectionObserver(([e]) => { visible = e.isIntersecting; sync() })
    io.observe(canvas)
    document.addEventListener('visibilitychange', sync)
    paint((performance.now() / 1000) * base * speed)
    return () => { cancelAnimationFrame(frame); io.disconnect(); document.removeEventListener('visibilitychange', sync) }
  }, [size, state, speed])
  return <canvas ref={ref} role={label ? 'img' : undefined} aria-label={label} aria-hidden={label ? undefined : true} className={className} style={{ width: size, height: size, display: 'block', ...style }} />
}

/** One shimmering placeholder block. Size it with classes. */
export function Skeleton({ className = '', style }: { className?: string; style?: CSSProperties }) {
  return <span aria-hidden className={`skeleton block rounded-md ${className}`} style={style} />
}

/** A list of rows shaped like the content that will replace them. */
export function SkeletonRows({ label, rows = 3, className = '' }: { label: string; rows?: number; className?: string }) {
  return (
    <div role={label ? 'status' : undefined} aria-busy={label ? true : undefined} aria-label={label || undefined} className={`grid gap-px overflow-hidden rounded-2xl border border-line bg-line ${className}`}>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex items-center justify-between gap-6 bg-bg px-5 py-4">
          <div className="grid flex-1 gap-2">
            <Skeleton className={`h-3.5 ${['w-3/5', 'w-1/2', 'w-2/3'][i % 3]}`} />
            <Skeleton className={`h-3 ${['w-2/5', 'w-1/3', 'w-1/2'][i % 3]}`} />
          </div>
          <Skeleton className="h-6 w-16 rounded-full" />
        </div>
      ))}
    </div>
  )
}

/** A page section while it loads: a heading line, a paragraph and a block. */
export function SkeletonPanel({ label, className = '' }: { label: string; className?: string }) {
  return (
    <div role="status" aria-busy="true" aria-label={label} className={`grid gap-4 rounded-2xl border border-line p-6 ${className}`}>
      <Skeleton className="h-5 w-1/3" />
      <Skeleton className="h-3 w-2/3" />
      <Skeleton className="h-3 w-1/2" />
      <div className="mt-2 grid gap-px overflow-hidden rounded-xl bg-line sm:grid-cols-3">
        {[0, 1, 2].map((i) => <div key={i} className="grid gap-3 bg-bg p-4"><Skeleton className="h-3 w-1/2" /><Skeleton className="h-7 w-2/3" /></div>)}
      </div>
    </div>
  )
}

/** A report while it loads: cover, summary line, the three summary cells, then the findings list. */
export function SkeletonReport({ label = 'Loading the report', className = '' }: { label?: string; className?: string }) {
  return (
    <div role={label ? 'status' : undefined} aria-busy={label ? true : undefined} aria-label={label || undefined} className={`grid gap-8 ${className}`}>
      <div className="flex items-end justify-between gap-6">
        <div className="grid flex-1 gap-3"><Skeleton className="h-3 w-40" /><Skeleton className="h-3 w-56" /><Skeleton className="h-12 w-3/4 max-w-xl" /><Skeleton className="h-3 w-72" /></div>
        <Skeleton className="size-16 rounded-full" />
      </div>
      <div className="grid max-w-[64ch] gap-2.5"><Skeleton className="h-4" /><Skeleton className="h-4 w-11/12" /><Skeleton className="h-4 w-3/5" /></div>
      <div className="grid gap-px overflow-hidden rounded-2xl border border-line bg-line sm:grid-cols-3">
        {[0, 1, 2].map((i) => <div key={i} className="grid gap-3 bg-bg p-5"><Skeleton className="h-3 w-1/3" /><Skeleton className="h-9 w-1/2" /><Skeleton className="h-3 w-2/3" /></div>)}
      </div>
      <SkeletonRows label="" rows={3} />
    </div>
  )
}

/** Long work in progress (a report being written, sites being scanned): the orb, what is happening now, and the
 *  steps so far. Steps advance on a timer as honest pacing, never as a claim about server progress. */
export function Working({ title, steps, state = 'working', every = 4200, className = '' }: { title: string; steps: string[]; state?: OrbState; every?: number; className?: string }) {
  const [at, setAt] = useState(0)
  useEffect(() => {
    const timer = window.setInterval(() => setAt((n) => Math.min(n + 1, steps.length - 1)), every)
    return () => window.clearInterval(timer)
  }, [steps.length, every])
  return (
    <section role="status" aria-live="polite" aria-busy="true" className={`no-print relative isolate overflow-hidden rounded-2xl border border-line bg-surface/40 px-6 py-8 sm:px-10 ${className}`}>
      <Orb size={260} state={state} className="pointer-events-none absolute -top-16 -right-16 -z-10 opacity-40" />
      <div className="flex items-center gap-5">
        <Orb size={64} state={state} className="shrink-0" />
        <div className="min-w-0">
          <p className="text-xl font-light tracking-tight">{title}</p>
          <p key={at} className="working-line mt-1 text-sm text-muted">{steps[at]}</p>
        </div>
      </div>
      <ol className="mt-7 flex gap-1.5" aria-hidden>
        {steps.map((s, i) => <li key={s} className={`h-1 flex-1 rounded-full transition-colors duration-700 ${i < at ? 'bg-ink' : i === at ? 'working-bar bg-muted/40' : 'bg-line'}`} />)}
      </ol>
    </section>
  )
}
