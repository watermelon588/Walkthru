// Variant 1, Fresh Eyes: the doodle zine. Cobalt and lemon on paper, stickers, a horizontal walk through the steps,
// a test user thinking out loud in speech bubbles, a sticky stack of real report captures and draggable polaroids.
import { useGSAP } from '@gsap/react'
import { ArrowRightIcon, PlusIcon } from '@phosphor-icons/react'
import gsap from 'gsap'
import { Draggable } from 'gsap/Draggable'
import { SplitText } from 'gsap/SplitText'
import { useId, useRef } from 'react'
import { brand } from '../brand'
import { checks, faqs, hero, personas, plans, reportParts, run, safety, steps } from '../content'
import { scrollToId, useScan, useSmoother } from './shared'
import './fresh.css'

gsap.registerPlugin(Draggable, SplitText)

const stickers = [
  { src: 'faces-cobalt.jpg', alt: 'Cobalt poster of nine doodled faces, each with a different expression', cls: 'left-[4%] top-[2%] w-[46%] aspect-[3/4] -rotate-6', depth: 0.6, speed: '1.25' },
  { src: 'cat-walk.jpg', alt: 'A long-legged doodle cat striding across a yellow page', cls: 'right-[2%] top-[0%] w-[38%] aspect-[3/4] rotate-[7deg]', depth: 1, speed: '0.85' },
  { src: 'people.jpg', alt: 'Hand-drawn portraits of strangers under the words I recognize people', cls: 'left-[22%] bottom-[0%] w-[40%] aspect-[4/5] rotate-[4deg]', depth: 1.4, speed: '1.1' },
  { src: 'rooster.jpg', alt: 'A loose blue and orange rooster doodle', cls: 'right-[6%] bottom-[6%] w-[30%] aspect-square -rotate-[9deg]', depth: 0.8, speed: '0.95' },
]
const stepArt = ['laptop.jpg', 'objects.jpg', 'trip.jpg', 'scout.jpg']
const stepAlt = ['A doodled person melting into a laptop', 'Blue doodles of everyday objects', 'A doodled figure tripping over a ball', 'A black doodle bird with one yellow eye, walking']
const spots = [
  { left: '1%', top: '6%', rotate: -8 }, { left: '20.5%', top: '22%', rotate: 5 }, { left: '40%', top: '2%', rotate: -3 },
  { left: '59.5%', top: '20%', rotate: 8 }, { left: '79%', top: '5%', rotate: -6 },
]

export default function FreshEyes() {
  const wrapper = useRef<HTMLDivElement>(null)
  const content = useRef<HTMLDivElement>(null)
  useSmoother(wrapper, content, 1.2)
  const scope = useRef<HTMLDivElement>(null)

  useGSAP(() => {
    const mm = gsap.matchMedia()
    mm.add('(prefers-reduced-motion: no-preference)', () => {
      // Hero: the headline bounces up word by word, stickers drop onto the table.
      const split = SplitText.create('.fx-h1', { type: 'words', mask: 'words' })
      gsap.from(split.words, { yPercent: 115, rotate: 6, duration: 1.1, ease: 'back.out(1.6)', stagger: 0.06, delay: 0.2 })
      gsap.from('.fx-squiggle path', { strokeDashoffset: 900, strokeDasharray: 900, duration: 1.1, ease: 'power2.inOut', delay: 0.9 })
      gsap.from('.fx-hero-fade', { y: 24, autoAlpha: 0, duration: 0.9, ease: 'expo.out', stagger: 0.1, delay: 0.6 })
      gsap.from('.fx-stick', { y: -140, rotate: () => gsap.utils.random(-30, 30), autoAlpha: 0, duration: 1.3, ease: 'elastic.out(1, 0.6)', stagger: 0.12, delay: 0.35 })

      // Each section heading rises as it arrives.
      gsap.utils.toArray<HTMLElement>('.fx-rise').forEach((el) =>
        gsap.from(el, { y: 60, autoAlpha: 0, duration: 1, ease: 'expo.out', scrollTrigger: { trigger: el, start: 'top 85%' } }))

      // Steps: vertical scroll walks the track sideways while the lemon bar fills.
      const track = document.querySelector<HTMLElement>('.fx-track')
      if (track && matchMedia('(min-width: 768px)').matches) {
        const distance = () => track.scrollWidth - window.innerWidth
        const tl = gsap.timeline({ scrollTrigger: { trigger: '.fx-steps', start: 'top top', end: () => `+=${distance()}`, pin: true, scrub: 1, invalidateOnRefresh: true } })
        tl.to(track, { x: () => -distance(), ease: 'none' }, 0).fromTo('.fx-steps-bar', { scaleX: 0 }, { scaleX: 1, ease: 'none' }, 0)
      }

      // The run: each thought pops in as you scroll, the last one with the crying face.
      const talk = gsap.timeline({ scrollTrigger: { trigger: '.fx-run', start: 'top top', end: '+=1800', pin: true, scrub: 0.6 } })
      gsap.utils.toArray<HTMLElement>('.fx-turn').forEach((el, i) => {
        talk.from(el.querySelector('.fx-action'), { x: -40, autoAlpha: 0, duration: 0.5 }, i)
          .from(el.querySelector('.fx-bubble'), { scale: 0.4, autoAlpha: 0, transformOrigin: '10% 100%', ease: 'back.out(2.2)', duration: 0.7 }, i + 0.2)
      })
      talk.from('.fx-cry', { scale: 0, rotate: -40, ease: 'back.out(2)', duration: 0.8 }, '-=0.3')

      // Report: real sticky stack. Each card settles back as the next one lands on it.
      const cards = gsap.utils.toArray<HTMLElement>('.fx-card')
      cards.forEach((card, i) => {
        if (i === cards.length - 1) return
        gsap.to(card, { scale: 0.9, rotate: i % 2 ? 2 : -2, autoAlpha: 0.6, ease: 'none', scrollTrigger: { trigger: cards[i + 1], start: 'top bottom', end: 'top 15%', scrub: true } })
      })

      // Closing: the skateboarding bird rolls in with the scroll.
      gsap.fromTo('.fx-skate', { xPercent: -160, rotate: -8 }, { xPercent: 40, rotate: 4, ease: 'none', scrollTrigger: { trigger: '.fx-close', start: 'top bottom', end: 'bottom bottom', scrub: 1 } })
    })

    // Stickers follow the pointer at different depths, pricing tickets tilt toward it.
    mm.add('(prefers-reduced-motion: no-preference) and (hover: hover)', () => {
      const movers = gsap.utils.toArray<HTMLElement>('.fx-stick').map((el) => ({ depth: Number(el.dataset.depth), x: gsap.quickTo(el, 'x', { duration: 0.8, ease: 'power3' }), y: gsap.quickTo(el, 'y', { duration: 0.8, ease: 'power3' }) }))
      const move = (e: PointerEvent) => {
        const dx = e.clientX / window.innerWidth - 0.5
        const dy = e.clientY / window.innerHeight - 0.5
        movers.forEach((m) => { m.x(dx * 40 * m.depth); m.y(dy * 30 * m.depth) })
      }
      window.addEventListener('pointermove', move)
      return () => window.removeEventListener('pointermove', move)
    })

    // Polaroids can be picked up and thrown around the table on desktop.
    mm.add('(min-width: 768px)', () => {
      let z = 10
      Draggable.create('.fx-polaroid', { bounds: '.fx-table', onPress() { gsap.set(this.target, { zIndex: ++z }) }, onDrag() { gsap.to(this.target, { rotate: gsap.utils.clamp(-14, 14, this.deltaX * 1.2), duration: 0.3 }) } })
    })
  }, { scope })

  const go = (id: string) => (e: React.MouseEvent) => { e.preventDefault(); scrollToId(id) }

  return (
    <div ref={scope} className="fx">
      <header className="fixed inset-x-0 top-0 z-50">
        <nav aria-label="Main" className="mx-auto mt-3 flex max-w-7xl items-center justify-between gap-4 rounded-full border-2 border-(--fx-ink) bg-(--fx-paper)/90 py-2 pr-2 pl-5 backdrop-blur-md md:mx-6 xl:mx-auto">
          <a href="#top" onClick={go('top')} className="flex items-center gap-2 font-semibold">
            <img src={brand.mark} alt="" className="size-7" /> {brand.name}
          </a>
          <div className="hidden items-center gap-1 text-sm font-medium md:flex">
            <a href="#how" onClick={go('how')} className="rounded-full px-4 py-2 hover:bg-(--fx-paper-2)">How it works</a>
            <a href="#report" onClick={go('report')} className="rounded-full px-4 py-2 hover:bg-(--fx-paper-2)">Report</a>
            <a href="#pricing" onClick={go('pricing')} className="rounded-full px-4 py-2 hover:bg-(--fx-paper-2)">Pricing</a>
            <a href="#faq" onClick={go('faq')} className="rounded-full px-4 py-2 hover:bg-(--fx-paper-2)">FAQ</a>
          </div>
          <a href="#scan" onClick={go('scan')} className="fx-btn fx-btn--lemon !py-2.5 !text-sm">{hero.primary}</a>
        </nav>
      </header>

      <div ref={wrapper}>
        <div ref={content} className="fx-content">
          <main id="main">
            {/* Hero */}
            <section id="top" className="relative mx-auto grid min-h-[100dvh] max-w-7xl items-center gap-10 px-5 pt-28 pb-16 md:px-10 lg:grid-cols-[1.05fr_1fr] lg:gap-6">
              <div>
                <h1 className="fx-display fx-h1 text-[clamp(3.2rem,8vw,7.6rem)]">
                  <span className="relative isolate inline-block">Fresh eyes<svg className="fx-squiggle" viewBox="0 0 600 40" preserveAspectRatio="none" aria-hidden><path d="M6 26 C 60 6, 110 38, 170 20 S 280 6, 340 24 S 460 38, 594 14" /></svg></span> for apps built with AI.
                </h1>
                <p className="fx-hero-fade mt-8 max-w-[34ch] text-lg leading-relaxed text-(--fx-muted) md:text-xl">AI test users try your signup and dashboard in your own browser. One report ranks every fix.</p>
                <ScanForm className="fx-hero-fade mt-9 max-w-lg" />
                <a href="#report" onClick={go('report')} className="fx-hero-fade mt-5 inline-flex items-center gap-1.5 text-sm font-semibold underline decoration-2 underline-offset-4 hover:decoration-(--fx-cobalt)">{hero.secondary} <ArrowRightIcon weight="bold" className="size-3.5" /></a>
              </div>
              <div className="relative mx-auto aspect-square w-full max-w-[560px]" aria-label="Doodles of curious people and a walking cat" role="img">
                {stickers.map((s) => (
                  <div key={s.src} className={`absolute ${s.cls}`} data-speed={s.speed}>
                    <div className="fx-stick h-full" data-depth={s.depth}>
                      <div className="fx-sticker h-full"><img src={`/variants/fresh/${s.src}`} alt={s.alt} /></div>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {/* The checks, drifting past on a tilted lemon band */}
            <section aria-label="What every scan checks" className="overflow-hidden py-10">
              <div className="fx-band py-5">
                <p className="sr-only">Every scan checks: {checks.join(', ')}.</p>
                <ul aria-hidden className="fx-marquee flex w-max gap-3 pr-3">
                  {[...checks, ...checks].map((c, i) => <li key={i} className="fx-chip">{c}</li>)}
                </ul>
              </div>
            </section>

            {/* How it works: pinned, scroll moves sideways */}
            <section id="how" className="fx-steps relative overflow-hidden py-20 md:flex md:min-h-[100dvh] md:flex-col md:justify-center md:py-0">
              <h2 className="fx-title fx-rise px-5 text-[clamp(2.4rem,5vw,4.5rem)] md:px-10">Your browser clicks.<br />Our agent thinks.</h2>
              <div className="fx-track mt-12 flex flex-col gap-5 px-5 md:w-max md:flex-row md:gap-6 md:px-10">
                {steps.map((s, i) => (
                  <article key={s.title} className={`grid w-full grid-rows-[auto_1fr] overflow-hidden rounded-[2rem] md:w-[min(30rem,80vw)] ${i % 2 ? 'bg-(--fx-lemon) text-(--fx-ink)' : 'bg-(--fx-cobalt) text-white'}`}>
                    <div className="p-7 md:p-9">
                      <p className="font-mono text-sm opacity-70">{String(i + 1).padStart(2, '0')}</p>
                      <h3 className="fx-title mt-3 text-4xl">{s.title}</h3>
                      <p className="mt-4 max-w-[38ch] leading-relaxed opacity-85">{s.body}</p>
                    </div>
                    <div className="mx-4 mb-4 overflow-hidden rounded-[1.4rem] bg-white">
                      <img src={`/variants/fresh/${stepArt[i]}`} alt={stepAlt[i]} loading="lazy" className="aspect-[16/10] w-full object-contain p-4" />
                    </div>
                  </article>
                ))}
                <div aria-hidden className="hidden w-[10vw] shrink-0 md:block" />
              </div>
              <div aria-hidden className="mx-10 mt-10 hidden h-2 overflow-hidden rounded-full bg-(--fx-paper-2) md:block"><div className="fx-steps-bar h-full origin-left rounded-full bg-(--fx-ink)" /></div>
            </section>

            {/* A test user thinking out loud */}
            <section className="fx-run relative flex min-h-[100dvh] items-center overflow-hidden bg-(--fx-cobalt) py-20 text-white">
              <div className="mx-auto grid w-full max-w-7xl gap-12 px-5 md:px-10 lg:grid-cols-[0.8fr_1.2fr]">
                <div>
                  <h2 className="fx-title text-[clamp(2.4rem,5vw,4.5rem)]">Hear a stranger think.</h2>
                  <p className="mt-5 max-w-[36ch] text-lg leading-relaxed text-white/80">A test user tries to sign up for quickinvoice.app, a made-up invoicing app, and says what it sees at every step.</p>
                  <img src="/variants/fresh/cry.jpg" alt="A doodled face with tears running down" loading="lazy" className="fx-cry mt-10 hidden w-44 rotate-[-6deg] rounded-[1.4rem] border-[6px] border-white lg:block" />
                </div>
                <ol className="grid gap-5">
                  {run.map((r, i) => (
                    <li key={r.action} className="fx-turn grid gap-2">
                      <span className="fx-action w-fit rounded-full bg-(--fx-cobalt-deep) px-3.5 py-1.5 font-mono text-xs text-white/85">{r.action}</span>
                      <p className={`fx-bubble text-lg leading-snug md:text-xl ${i === run.length - 1 ? 'fx-bubble--last font-semibold' : ''}`}>{r.thought}</p>
                    </li>
                  ))}
                </ol>
              </div>
            </section>

            {/* Report: sticky stack of real captures */}
            <section id="report" className="mx-auto max-w-7xl px-5 pt-28 md:px-10">
              <h2 className="fx-title fx-rise max-w-[16ch] text-[clamp(2.4rem,5vw,4.5rem)]">One report. Journeys, SEO, AI search and security.</h2>
              <div className="mt-14 pb-10">
                {reportParts.map((r, i) => (
                  <article key={r.img} className={`fx-card sticky top-24 mb-8 grid items-center gap-8 overflow-hidden rounded-[2rem] border-2 border-(--fx-ink) p-6 md:min-h-[70dvh] md:grid-cols-[0.8fr_1.2fr] md:p-10 ${['bg-white', 'bg-(--fx-lemon)', 'bg-(--fx-cobalt) text-white', 'bg-(--fx-paper-2)'][i]}`}>
                    <div>
                      <h3 className="fx-title text-3xl md:text-5xl">{r.title}</h3>
                      <p className={`mt-4 max-w-[40ch] leading-relaxed ${i === 2 ? 'text-white/85' : 'text-(--fx-muted)'}`}>{r.body}</p>
                    </div>
                    <div className="overflow-hidden rounded-[1.2rem] border-2 border-(--fx-ink) bg-white">
                      <img src={`/assets/${r.img}`} alt={`${r.title}, from a real Walkthru report`} loading="lazy" className="block h-auto w-full" />
                    </div>
                  </article>
                ))}
              </div>
            </section>

            {/* Test users: a table of polaroids you can push around */}
            <section className="mx-auto max-w-7xl px-5 py-24 md:px-10">
              <h2 className="fx-title fx-rise max-w-[18ch] text-[clamp(2.4rem,5vw,4.5rem)]">Different people get stuck in different places.</h2>
              <p className="fx-rise mt-5 max-w-[44ch] text-lg text-(--fx-muted)">Five kinds of visitor. <span className="hidden md:inline">Pick them up and move them around.</span></p>
              <div className="fx-table relative mt-12 flex snap-x snap-mandatory gap-5 overflow-x-auto pb-6 md:block md:h-[780px] md:overflow-visible md:pb-0">
                {personas.map((p, i) => (
                  <article key={p.name} className="fx-polaroid w-64 shrink-0 snap-center md:absolute md:w-[19%]" style={{ left: spots[i].left, top: spots[i].top, rotate: `${spots[i].rotate}deg` }}>
                    <div className={`fx-duo overflow-hidden rounded-[0.5rem] ${i % 2 ? 'fx-duo--cobalt' : ''}`}>
                      <img src={`/assets/${p.img}`} alt={`Portrait for ${p.name.toLowerCase()}`} loading="lazy" draggable={false} className="aspect-[3/4] w-full object-cover" />
                    </div>
                    <h3 className="fx-title mt-4 text-xl">{p.name}</h3>
                    <p className="mt-1 text-sm leading-snug text-(--fx-muted)">{p.who}</p>
                    <p className="mt-3 text-sm font-semibold">Catches: <span className="font-normal">{p.catches}</span></p>
                  </article>
                ))}
              </div>
            </section>

            {/* Safety bento */}
            <section className="mx-auto max-w-7xl px-5 pb-24 md:px-10">
              <div className="grid gap-4 md:grid-cols-4 md:grid-rows-2">
                <div className="fx-rise relative flex min-h-80 flex-col justify-end overflow-hidden rounded-[2rem] bg-(--fx-ink) p-8 text-(--fx-paper) md:col-span-2 md:row-span-2">
                  <img src="/variants/fresh/faces-bw.jpg" alt="" loading="lazy" className="absolute inset-0 h-full w-full object-cover opacity-25" />
                  <h2 className="fx-title relative max-w-[12ch] text-[clamp(2.2rem,4.4vw,4rem)]">Tests your dashboard without your password.</h2>
                </div>
                {safety.map((s, i) => (
                  <div key={s.title} className={`fx-rise rounded-[2rem] p-7 ${['bg-(--fx-lemon)', 'bg-white border-2 border-(--fx-ink)', 'bg-white border-2 border-(--fx-ink)', 'bg-(--fx-cobalt) text-white'][i]}`}>
                    <s.icon weight="bold" className="size-7" />
                    <h3 className="fx-title mt-6 text-2xl">{s.title}</h3>
                    <p className={`mt-2 text-sm leading-relaxed ${i === 3 ? 'text-white/85' : 'text-(--fx-muted)'}`}>{s.body}</p>
                  </div>
                ))}
              </div>
            </section>

            {/* Pricing tickets */}
            <section id="pricing" className="border-y-2 border-(--fx-ink) bg-(--fx-paper-2) py-24">
              <div className="mx-auto max-w-7xl px-5 md:px-10">
                <h2 className="fx-title fx-rise text-[clamp(2.4rem,5vw,4.5rem)]">Start free. Pay once when you launch.</h2>
                <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
                  {plans.map((p) => (
                    <article key={p.name} className={`fx-rise flex flex-col rounded-[2rem] border-2 border-(--fx-ink) p-7 transition-[translate,rotate] duration-300 hover:-translate-y-1.5 hover:-rotate-1 ${p.highlight ? 'bg-(--fx-cobalt) text-white' : 'bg-white'}`}>
                      <h3 className="font-semibold">{p.name}</h3>
                      <p className="fx-display mt-4 text-6xl">{p.price}</p>
                      <p className={`mt-2 text-sm ${p.highlight ? 'text-white/80' : 'text-(--fx-muted)'}`}>{p.per}</p>
                      <ul className="mt-6 mb-8 grid flex-1 content-start gap-2.5 text-sm">
                        {p.features.map((f) => <li key={f} className="flex gap-2"><span aria-hidden className={`mt-1.5 size-2 shrink-0 rounded-full ${p.highlight ? 'bg-(--fx-lemon)' : 'bg-(--fx-cobalt)'}`} />{f}</li>)}
                      </ul>
                      <a href={p.href ?? '#scan'} onClick={p.href ? undefined : go('scan')} className={`fx-btn justify-center ${p.highlight ? 'fx-btn--lemon' : 'fx-btn--ink'}`}>{p.cta}</a>
                    </article>
                  ))}
                </div>
              </div>
            </section>

            {/* FAQ */}
            <section id="faq" className="mx-auto max-w-4xl px-5 py-28 md:px-10">
              <h2 className="fx-title fx-rise text-[clamp(2.4rem,5vw,4.5rem)]">Questions, answered.</h2>
              <div className="mt-10 grid gap-3">
                {faqs.map((f) => (
                  <details key={f.q} className="fx-faq rounded-[1.6rem] border-2 border-(--fx-ink) bg-white px-6 py-5">
                    <summary className="flex items-center justify-between gap-6 text-lg font-semibold">{f.q}<span className="fx-plus grid size-9 shrink-0 place-items-center rounded-full border-2 border-(--fx-ink)"><PlusIcon weight="bold" className="size-4" /></span></summary>
                    <p className="mt-3 max-w-[62ch] leading-relaxed text-(--fx-muted)">{f.a}</p>
                  </details>
                ))}
              </div>
            </section>

            {/* Closing scan */}
            <section id="scan" className="fx-close relative overflow-hidden bg-(--fx-lemon) px-5 pt-24 pb-40 md:px-10">
              <div className="mx-auto max-w-5xl text-center">
                <h2 className="fx-display text-[clamp(3rem,9vw,8rem)]">See it with fresh eyes.</h2>
                <p className="mx-auto mt-6 max-w-[40ch] text-lg">A free Instant Scan checks SEO, AI search readiness and security in about 20 seconds.</p>
                <ScanForm className="mx-auto mt-10 max-w-xl text-left" />
              </div>
              <img src="/variants/fresh/skate-bird.jpg" alt="" loading="lazy" className="fx-skate absolute bottom-6 left-0 w-48 mix-blend-multiply md:w-64" />
            </section>
          </main>

          <footer className="bg-(--fx-ink) px-5 py-14 text-(--fx-paper) md:px-10">
            <div className="mx-auto flex max-w-7xl flex-wrap items-end justify-between gap-8">
              <div>
                <p className="flex items-center gap-2 text-lg font-semibold"><img src={brand.mark} alt="" className="size-7 invert" />{brand.name}</p>
                <p className="mt-2 max-w-[40ch] text-sm text-(--fx-paper)/60">{brand.tagline} Test users are AI, and their findings are an informed review, not a guarantee.</p>
              </div>
              <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-(--fx-paper)/75">
                <a href="/docs" className="hover:text-white">Docs</a><a href="/pricing" className="hover:text-white">Pricing</a><a href="/privacy" className="hover:text-white">Privacy</a><a href="/terms" className="hover:text-white">Terms</a><a href="/security" className="hover:text-white">Security</a><a href="/login" className="hover:text-white">Sign in</a>
              </div>
            </div>
          </footer>
        </div>
      </div>
    </div>
  )
}

function ScanForm({ className = '' }: { className?: string }) {
  const { submit, error, busy } = useScan()
  const id = useId()
  return (
    <form onSubmit={submit} noValidate aria-busy={busy} className={className}>
      <label htmlFor={id} className="mb-2 block text-sm font-semibold">Your website</label>
      <div className="flex flex-col gap-3 sm:flex-row">
        <input id={id} name="url" type="text" inputMode="url" placeholder="yoursite.com" disabled={busy} aria-invalid={!!error} aria-describedby={`${id}-error`} className="fx-input" />
        <button type="submit" disabled={busy} className="fx-btn fx-btn--cobalt justify-center disabled:opacity-60">{busy ? 'Scanning...' : hero.primary}<ArrowRightIcon weight="bold" className="size-4" /></button>
      </div>
      <p id={`${id}-error`} role="status" className="mt-2 min-h-5 text-sm font-semibold text-[#b3261e]">{error}</p>
    </form>
  )
}
