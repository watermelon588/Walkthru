import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import type { RefObject } from 'react'

gsap.registerPlugin(useGSAP, ScrollTrigger)

/** Shared entrance: headline words rise, .reveal blocks fade up as they enter. Skipped for reduced motion. */
export function useReveal(scope: RefObject<HTMLElement | null>) {
  useGSAP(
    () => {
      gsap.matchMedia().add('(prefers-reduced-motion: no-preference)', () => {
        gsap.from('.word', { yPercent: 110, duration: 1.3, ease: 'expo.out', stagger: 0.05, delay: 0.15 })
        gsap.from('.hero-fade', { y: 18, autoAlpha: 0, duration: 1.2, ease: 'expo.out', stagger: 0.12, delay: 0.55 })
        gsap.utils.toArray<HTMLElement>('.reveal').forEach((el) =>
          gsap.from(el, { y: 32, autoAlpha: 0, duration: 1.2, ease: 'expo.out', scrollTrigger: { trigger: el, start: 'top 88%' } }),
        )
      })
    },
    { scope },
  )
}
