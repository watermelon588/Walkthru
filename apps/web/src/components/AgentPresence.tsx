import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import { useRef } from 'react'
import { AgentBird } from './AgentBird'

gsap.registerPlugin(useGSAP)

export type AgentPresenceState = 'ready' | 'observing' | 'complete' | 'stopped'

const stateTone: Record<AgentPresenceState, string> = {
  ready: 'text-ink',
  observing: 'text-accent',
  complete: 'text-accent',
  stopped: 'text-danger',
}

type AgentPresenceProps = {
  activity: string
  state?: AgentPresenceState
  className?: string
  phase?: number
  onActivate?: () => void
  actionLabel?: string
  expanded?: boolean
}

export function AgentPresence({ activity, state = 'ready', className = '', phase = 0, onActivate, actionLabel, expanded }: AgentPresenceProps) {
  const root = useRef<HTMLElement>(null)
  const activityRef = useRef<HTMLSpanElement>(null)

  useGSAP(() => {
    const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches
    gsap.fromTo(
      activityRef.current,
      { autoAlpha: reduce ? 1 : 0.35, y: reduce ? 0 : 3 },
      { autoAlpha: 1, y: 0, duration: reduce ? 0 : 0.2, ease: 'power2.out', overwrite: 'auto' },
    )
  }, { dependencies: [activity, state], scope: root })

  const content = (
    <>
      <AgentBird
        variant="solid"
        className="size-14 shrink-0 overflow-visible"
        phase={phase}
        title="Scout, the Walkthru test agent"
      />
      <span className="min-w-0 leading-tight">
        <strong className="block font-mono text-[10px] uppercase tracking-[0.2em] text-ink">Scout</strong>
        <span ref={activityRef} aria-live="polite" className="mt-1 block text-xs text-muted">{activity}</span>
      </span>
    </>
  )

  const classes = `inline-flex items-center gap-3 text-left transition-colors duration-200 motion-reduce:transition-none ${stateTone[state]} ${className}`
  if (onActivate) {
    return (
      <button
        ref={(node) => { root.current = node }}
        type="button"
        onClick={onActivate}
        aria-expanded={expanded}
        aria-label={actionLabel ?? `Scout. ${activity}`}
        className={`${classes} rounded-xl focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent`}
      >
        {content}
      </button>
    )
  }
  return <aside ref={root} aria-label={`Scout. ${activity}`} className={classes}>{content}</aside>
}
