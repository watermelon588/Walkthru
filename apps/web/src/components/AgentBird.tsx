import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import { useRef } from 'react'

gsap.registerPlugin(useGSAP)

export type AgentBirdVariant = 'solid' | 'outline'

type AgentBirdProps = {
  variant: AgentBirdVariant
  phase?: number
  className?: string
  title: string
}

const bodyPath = 'M76 117c11 7 23 11 36 11 22 1 39-8 47-24 9-19 5-43 1-62l30-4q7-1 2-6L165 10c-12-10-28-9-37 1-8 9-9 21-13 32-10 26-23 49-38 65l-1 9Z'
const tailPath = 'M96 126 40 42q-2-4-7-2L13 50q-6 3-2 9c18 22 41 44 65 58l18 9Z'
const frontLegPath = 'M108 115 97 158 72 169 56 189M72 169l-5 20m5-20 5 18m-5-18-13 11'
const backLegPath = 'M124 115 146 155l6 29m0 0-1 12m1-12 11 10m-11-10 17 5'

export function AgentBird({ variant, phase = 0, className = '', title }: AgentBirdProps) {
  const svg = useRef<SVGSVGElement>(null)
  const outline = variant === 'outline'
  const fill = outline ? 'var(--bg)' : 'currentColor'
  const strokeWidth = outline ? 5 : 0

  useGSAP(() => {
    const root = svg.current
    if (!root) return

    const rig = root.querySelector<SVGGElement>('.agent-bird__rig')
    const body = root.querySelector<SVGGElement>('.agent-bird__body')
    const eye = root.querySelector<SVGGElement>('.agent-bird__eye')
    const tail = root.querySelector<SVGPathElement>('.agent-bird__tail')
    const frontLeg = root.querySelector<SVGPathElement>('.agent-bird__leg--front')
    const backLeg = root.querySelector<SVGPathElement>('.agent-bird__leg--back')
    if (!rig || !body || !eye || !tail || !frontLeg || !backLeg) return

    gsap.set([rig, body, eye, tail, frontLeg, backLeg], { clearProps: 'transform' })

    const media = gsap.matchMedia()
    media.add('(prefers-reduced-motion: no-preference)', () => {
      gsap.set(rig, { svgOrigin: '120 184' })
      gsap.set(body, { svgOrigin: '112 124' })
      gsap.set(eye, { svgOrigin: '145 22' })
      gsap.set(tail, { svgOrigin: '80 113' })
      gsap.set(frontLeg, { svgOrigin: '108 119' })
      gsap.set(backLeg, { svgOrigin: '124 119' })

      const blink = gsap.timeline({ repeat: -1, repeatDelay: 4.4 })
        .to(eye, { scaleY: 0.12, duration: 0.1, ease: 'power1.inOut' })
        .to(eye, { scaleY: 1, duration: 0.14, ease: 'power1.inOut' })

      const observe = gsap.timeline({ repeat: -1, repeatDelay: 0.7, defaults: { ease: 'power2.inOut' } })
        .to(rig, { rotation: 1.6, y: 1, duration: 1.8 }, 0)
        .to(tail, { rotation: -3, duration: 1.8 }, 0)
        .to(rig, { rotation: -0.7, y: 0, duration: 1.5 }, '+=0.35')
        .to(tail, { rotation: 2, duration: 1.5 }, '<')
        .to(rig, { rotation: 0, duration: 1.2 }, '+=0.2')
        .to(tail, { rotation: 0, duration: 1.2 }, '<')

      observe.progress(phase)
      blink.progress(phase)
    })

    return () => media.revert()
  }, { dependencies: [phase], scope: svg, revertOnUpdate: true })

  return (
    <svg ref={svg} viewBox="0 0 200 200" role="img" aria-label={title} className={`agent-bird ${className}`}>
      <g className="agent-bird__rig">
        <path
          className="agent-bird__tail"
          d={tailPath}
          fill={fill}
          stroke="currentColor"
          strokeLinejoin="round"
          strokeWidth={strokeWidth}
        />
        <path
          className="agent-bird__leg agent-bird__leg--back"
          d={backLegPath}
          fill="none"
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="4"
        />
        <path
          className="agent-bird__leg agent-bird__leg--front"
          d={frontLegPath}
          fill="none"
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="4"
        />

        <g className="agent-bird__body">
          <path
            d={bodyPath}
            fill={fill}
            stroke="currentColor"
            strokeLinejoin="round"
            strokeWidth={strokeWidth}
          />
          <g className="agent-bird__eye">
            <circle cx="145" cy="22" r="7" fill="var(--bg)" />
            <circle cx="145" cy="22" r="3" fill="currentColor" />
          </g>
        </g>
      </g>
    </svg>
  )
}
