// <assemble-stage>: the effect as a plain HTML element, for sites with no build step.
//   <assemble-stage auto> ...any content... </assemble-stage>      rebuilds its own content, once, when scrolled into view
//   <assemble-stage auto src="shot.png"><img src="shot.png"></assemble-stage>   rebuilds a picture (image mode)
// Attributes: auto, src, speed, seed, sound. Call .play() to run it again.
import { assemble, assembleImage, type Handle } from './index.ts'

export function define(name = 'assemble-stage') {
  if (typeof customElements === 'undefined' || customElements.get(name)) return
  customElements.define(
    name,
    class extends HTMLElement {
      run: Handle | null = null
      seen: IntersectionObserver | null = null

      connectedCallback() {
        if (getComputedStyle(this).display === 'inline') this.style.display = 'block'
        if (getComputedStyle(this).position === 'static') this.style.position = 'relative'
        if (!this.hasAttribute('auto')) return
        this.seen = new IntersectionObserver(
          (entries) => {
            if (!entries.some((e) => e.isIntersecting)) return
            this.seen?.disconnect()
            this.play()
          },
          { threshold: 0.4 },
        )
        this.seen.observe(this)
      }

      disconnectedCallback() {
        this.seen?.disconnect()
        this.run?.destroy()
      }

      play() {
        this.run?.destroy()
        const num = (k: string) => (this.hasAttribute(k) ? Number(this.getAttribute(k)) : undefined)
        const options = { speed: num('speed'), seed: num('seed'), sound: this.hasAttribute('sound') }
        const clean = Object.fromEntries(Object.entries(options).filter(([, v]) => v !== undefined))
        const src = this.getAttribute('src')
        this.run = src ? assembleImage(this, src, clean) : assemble(this, clean)
        return this.run
      }
    },
  )
}
