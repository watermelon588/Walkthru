import { ArrowCounterClockwiseIcon, ArrowLeftIcon } from '@phosphor-icons/react'
import { useEffect, useRef, useState, type KeyboardEvent, type PointerEvent } from 'react'
import { AgentBird, type AgentBirdVariant } from '../components/AgentBird'
import { Logo, btnGhost } from '../components/Shared'

type BirdAgent = {
  id: string
  name: string
  activity: string
  variant: AgentBirdVariant
  phase: number
}

const agents: BirdAgent[] = [
  { id: 'scout', name: 'Scout', activity: 'Mapping the signup', variant: 'solid', phase: 0 },
  { id: 'scout-teal', name: 'Scout', activity: 'Reading the page', variant: 'solid', phase: 0.16 },
  { id: 'trace', name: 'Trace', activity: 'Checking the checkout', variant: 'outline', phase: 0.32 },
  { id: 'scout-rust', name: 'Scout', activity: 'Replaying a stuck step', variant: 'solid', phase: 0.48 },
  { id: 'scout-plum', name: 'Scout', activity: 'Writing your report', variant: 'solid', phase: 0.64 },
]

function MovableBird({ agent, resetKey }: { agent: BirdAgent; resetKey: number }) {
  const item = useRef<HTMLButtonElement>(null)
  const offset = useRef({ x: 0, y: 0 })
  const drag = useRef<{ pointerX: number; pointerY: number; startX: number; startY: number } | null>(null)
  const frame = useRef<number | null>(null)

  function move(x: number, y: number) {
    offset.current = { x, y }
    if (frame.current !== null) cancelAnimationFrame(frame.current)
    frame.current = requestAnimationFrame(() => {
      item.current?.style.setProperty('translate', `${x}px ${y}px`)
      frame.current = null
    })
  }

  function startDrag(event: PointerEvent<HTMLButtonElement>) {
    event.currentTarget.setPointerCapture(event.pointerId)
    drag.current = { pointerX: event.clientX, pointerY: event.clientY, startX: offset.current.x, startY: offset.current.y }
    event.currentTarget.dataset.dragging = 'true'
  }

  function continueDrag(event: PointerEvent<HTMLButtonElement>) {
    if (!drag.current) return
    move(
      drag.current.startX + event.clientX - drag.current.pointerX,
      drag.current.startY + event.clientY - drag.current.pointerY,
    )
  }

  function stopDrag(event: PointerEvent<HTMLButtonElement>) {
    drag.current = null
    event.currentTarget.dataset.dragging = 'false'
  }

  function moveWithKeys(event: KeyboardEvent<HTMLButtonElement>) {
    const step = event.shiftKey ? 24 : 8
    const direction = {
      ArrowLeft: [-step, 0],
      ArrowRight: [step, 0],
      ArrowUp: [0, -step],
      ArrowDown: [0, step],
    }[event.key]
    if (!direction) return
    event.preventDefault()
    move(offset.current.x + direction[0], offset.current.y + direction[1])
  }

  useEffect(() => {
    move(0, 0)
    return () => {
      if (frame.current !== null) cancelAnimationFrame(frame.current)
    }
  }, [resetKey])

  return (
    <button
      ref={item}
      type="button"
      className={`bird-agent bird-agent--${agent.id}`}
      aria-label={`${agent.name}. ${agent.activity}. Drag to move, or use the arrow keys.`}
      onPointerDown={startDrag}
      onPointerMove={continueDrag}
      onPointerUp={stopDrag}
      onPointerCancel={stopDrag}
      onKeyDown={moveWithKeys}
    >
      <AgentBird variant={agent.variant} phase={agent.phase} title={`${agent.name} bird`} className="bird-agent__mark" />
      <span className="bird-agent__name">{agent.name}</span>
      <span className="bird-agent__activity">{agent.activity}</span>
    </button>
  )
}

export default function AgentLab() {
  const [resetKey, setResetKey] = useState(0)

  return (
    <div className="min-h-[100dvh] overflow-x-clip bg-bg text-ink">
      <header className="relative z-20 border-b border-line bg-bg/90 backdrop-blur-md">
        <nav className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5 md:px-10" aria-label="Agent identity lab">
          <Logo />
          <a href="/" className={btnGhost.replace('px-6 py-3', 'px-4 py-2')}>
            <ArrowLeftIcon aria-hidden weight="light" className="size-4" />
            Back to site
          </a>
        </nav>
      </header>

      <main>
        <section className="bird-playground relative mx-auto min-h-[1550px] max-w-7xl overflow-hidden px-5 pt-16 md:min-h-[820px] md:px-10 md:pt-20" aria-labelledby="lab-title">
          <p className="font-mono text-xs tracking-[0.12em] text-accent uppercase">Bird bot playground</p>
          <h1 id="lab-title" className="mt-5 max-w-[15ch] text-5xl leading-[1.04] font-extralight tracking-[-0.035em] md:text-7xl">
            Five birds. One Walkthru identity.
          </h1>
          <p className="mt-6 max-w-[42ch] leading-relaxed text-muted">Drag any bird. Use arrow keys when focused.</p>
          <button type="button" onClick={() => setResetKey((key) => key + 1)} className="mt-6 inline-flex items-center gap-2 text-sm text-muted transition hover:text-ink active:scale-[0.98]">
            <ArrowCounterClockwiseIcon aria-hidden weight="light" className="size-4" />
            Reset positions
          </button>

          {agents.map((agent) => <MovableBird key={agent.id} agent={agent} resetKey={resetKey} />)}
        </section>
      </main>
    </div>
  )
}
