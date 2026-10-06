// Variant 2, Darkroom: a cinematic dark page. Black and white photography, one red signal, a WebGL scanner in the
// hero, a headline whose letters widen under the pointer, pinned steps, a transcript that lights up as you read and
// a sideways pan through the real report.
import { useGSAP } from '@gsap/react'
import { ArrowRightIcon, ArrowUpRightIcon, PlusIcon } from '@phosphor-icons/react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { SplitText } from 'gsap/SplitText'
import { useEffect, useId, useRef } from 'react'
import { brand } from '../brand'
import { checks, faqs, hero, personas, plans, reportParts, run, safety, steps } from '../content'
import { reduced, scrollToId, useScan, useSmoother } from './shared'
import './darkroom.css'

gsap.registerPlugin(SplitText)

const stepShots = [
  { src: 'work-cap.jpg', alt: 'Someone at a cafe table with a laptop, hand on their head, studying a page' },
  { src: 'desk-face.jpg', alt: 'A face seen through a screen full of desktop icons' },
  { src: 'trackpad.jpg', alt: 'A hand resting on a laptop trackpad' },
  { src: 'work-train.jpg', alt: 'Hands typing on a laptop on a train' },
]
const transcript = `${run[2].thought} ${run[3].thought}`
const lastLine = 'I would leave now.'

export default function Darkroom() {
  const wrapper = useRef<HTMLDivElement>(null)
  const content = useRef<HTMLDivElement>(null)
  useSmoother(wrapper, content, 1.3)
  const scope = useRef<HTMLDivElement>(null)
  const peek = useRef<HTMLImageElement>(null)

  useGSAP(() => {
    const mm = gsap.matchMedia()
    mm.add('(prefers-reduced-motion: no-preference)', () => {
      // Red reading line down the left edge: how far through the page you are.
      gsap.fromTo('.dr-progress', { scaleY: 0 }, { scaleY: 1, ease: 'none', scrollTrigger: { start: 0, end: 'max', scrub: true } })

      // Hero: characters snap open from condensed to normal width, the red bar wipes in behind "built with AI".
      const split = SplitText.create('.dr-h1', { type: 'words,chars', charsClass: 'dr-char', mask: 'words' })
      gsap.from(split.chars, { '--s': 62, yPercent: 100, duration: 1.2, ease: 'expo.out', stagger: 0.018, delay: 0.25 })
      gsap.fromTo('.dr-mark', { '--mark': 0 }, { '--mark': 1, duration: 0.9, ease: 'expo.inOut', delay: 1.1 })
      gsap.from('.dr-hero-fade', { y: 20, autoAlpha: 0, duration: 1, ease: 'expo.out', stagger: 0.1, delay: 0.9 })
      gsap.to('.dr-hero-copy', { yPercent: -30, autoAlpha: 0, ease: 'none', scrollTrigger: { trigger: '.dr-hero', start: 'top top', end: 'bottom top', scrub: true } })

      // Letters widen as the pointer passes over them.
      const chars = split.chars as HTMLElement[]
      const setters = chars.map((c) => gsap.quickTo(c, '--s', { duration: 0.6, ease: 'power3' }))
      const h1 = document.querySelector<HTMLElement>('.dr-h1')
      const onMove = (e: PointerEvent) => chars.forEach((c, i) => {
        const r = c.getBoundingClientRect()
        const d = Math.hypot(e.clientX - (r.left + r.width / 2), e.clientY - (r.top + r.height / 2))
        setters[i](100 + 25 * Math.max(0, 1 - d / 220))
      })
      const onLeave = () => setters.forEach((s) => s(100))
      h1?.addEventListener('pointermove', onMove)
      h1?.addEventListener('pointerleave', onLeave)

      // The eye opens: the clip widens and the photo settles as it reaches the middle of the screen.
      gsap.fromTo('.dr-eye', { clipPath: 'inset(22% 30% 22% 30%)' }, { clipPath: 'inset(0% 0% 0% 0%)', ease: 'none', scrollTrigger: { trigger: '.dr-eye-wrap', start: 'top 80%', end: 'center center', scrub: true } })
      gsap.fromTo('.dr-eye img', { scale: 1.35 }, { scale: 1, ease: 'none', scrollTrigger: { trigger: '.dr-eye-wrap', start: 'top bottom', end: 'bottom top', scrub: true } })

      // Transcript: words light up one by one, the last sentence in red.
      const words = gsap.utils.toArray<HTMLElement>('.dr-word')
      gsap.timeline({ scrollTrigger: { trigger: '.dr-read', start: 'top top', end: '+=1400', pin: true, scrub: 0.5 } })
        .to(words, { color: (_i: number, el: HTMLElement) => (el.dataset.red ? 'var(--dr-red)' : 'var(--dr-ink)'), stagger: 0.1, duration: 0.3 })

      // Rows and headings slide in.
      gsap.utils.toArray<HTMLElement>('.dr-rise').forEach((el) =>
        gsap.from(el, { y: 70, autoAlpha: 0, duration: 1.2, ease: 'expo.out', scrollTrigger: { trigger: el, start: 'top 88%' } }))

      // Closing: the giant words stretch to full width as they arrive.
      gsap.fromTo('.dr-close-word', { fontStretch: '62%', letterSpacing: '0.1em' }, { fontStretch: '125%', letterSpacing: '-0.03em', ease: 'none', scrollTrigger: { trigger: '.dr-close', start: 'top bottom', end: 'center center', scrub: true } })

      return () => { h1?.removeEventListener('pointermove', onMove); h1?.removeEventListener('pointerleave', onLeave) }
    })

    // Steps (desktop): pinned, each scroll length hands the light to the next step.
    mm.add('(prefers-reduced-motion: no-preference) and (min-width: 1024px)', () => {
      const items = gsap.utils.toArray<HTMLElement>('.dr-step')
      const shots = gsap.utils.toArray<HTMLElement>('.dr-shot')
      const tl = gsap.timeline({ scrollTrigger: { trigger: '.dr-steps', start: 'top top', end: () => `+=${window.innerHeight * 3}`, pin: true, scrub: 0.8 } })
      gsap.set(items.slice(1), { color: 'var(--dr-faint)' })
      gsap.set(items.slice(1).map((i) => i.querySelector('p')), { autoAlpha: 0, height: 0 })
      gsap.set(shots.slice(1), { clipPath: 'inset(100% 0% 0% 0%)' })
      for (let i = 1; i < items.length; i++) {
        tl.to(items[i - 1], { color: 'var(--dr-faint)', duration: 0.4 }, i)
          .to(items[i - 1].querySelector('p'), { autoAlpha: 0, height: 0, duration: 0.4 }, i)
          .to(items[i], { color: 'var(--dr-ink)', duration: 0.4 }, i)
          .to(items[i].querySelector('p'), { autoAlpha: 1, height: 'auto', duration: 0.4 }, i)
          .to(shots[i], { clipPath: 'inset(0% 0% 0% 0%)', duration: 0.8, ease: 'power2.inOut' }, i - 0.2)
          .to('.dr-frame', { xPercent: [0, 18, -6, 10][i], yPercent: [0, 30, 60, 12][i], duration: 0.8, ease: 'power2.inOut' }, i - 0.2)
      }
    })

    // Report: vertical scroll pans the captures sideways.
    mm.add('(prefers-reduced-motion: no-preference) and (min-width: 768px)', () => {
      const track = document.querySelector<HTMLElement>('.dr-track')
      if (!track) return
      const distance = () => track.scrollWidth - window.innerWidth
      gsap.to(track, { x: () => -distance(), ease: 'none', scrollTrigger: { trigger: '.dr-pan', start: 'top top', end: () => `+=${distance()}`, pin: true, scrub: 1, invalidateOnRefresh: true } })
    })

    // A portrait follows the pointer over the test-user rows.
    mm.add('(hover: hover) and (min-width: 768px)', () => {
      const img = peek.current
      if (!img) return
      const x = gsap.quickTo(img, 'x', { duration: 0.5, ease: 'power3' })
      const y = gsap.quickTo(img, 'y', { duration: 0.5, ease: 'power3' })
      const list = document.querySelector<HTMLElement>('.dr-people')
      const move = (e: PointerEvent) => { const r = list!.getBoundingClientRect(); x(e.clientX - r.left); y(e.clientY - r.top) }
      list?.addEventListener('pointermove', move)
      return () => list?.removeEventListener('pointermove', move)
    })
    // The pinned sections were created out of page order (media-query groups): measure them top to bottom.
    ScrollTrigger.sort()
    ScrollTrigger.refresh()
  }, { scope })

  const show = (src: string | null) => {
    const img = peek.current
    if (!img) return
    if (src) img.src = `/assets/${src}`
    gsap.to(img, { autoAlpha: src ? 1 : 0, scale: src ? 1 : 0.85, rotate: src ? -3 : 0, duration: reduced() ? 0 : 0.35, ease: 'power3.out' })
  }
  const go = (id: string) => (e: React.MouseEvent) => { e.preventDefault(); scrollToId(id) }

  return (
    <div ref={scope} className="dr dr-grain">
      <span aria-hidden className="dr-progress fixed top-0 left-0 z-[60] h-full w-[3px] origin-top bg-(--dr-red)" />
      <header className="fixed inset-x-0 top-0 z-50 border-b border-(--dr-line) bg-(--dr-bg)/70 backdrop-blur-md">
        <nav aria-label="Main" className="mx-auto flex h-16 max-w-[1440px] items-center justify-between gap-6 px-5 md:px-10">
          <a href="#top" onClick={go('top')} className="flex items-center gap-2.5 text-sm font-semibold tracking-wide uppercase"><img src={brand.mark} alt="" className="size-6 invert" />{brand.name}</a>
          <div className="dr-mono hidden items-center gap-8 text-(--dr-muted) md:flex">
            <a href="#how" onClick={go('how')} className="hover:text-(--dr-ink)">How it works</a>
            <a href="#report" onClick={go('report')} className="hover:text-(--dr-ink)">Report</a>
            <a href="#pricing" onClick={go('pricing')} className="hover:text-(--dr-ink)">Pricing</a>
            <a href="#faq" onClick={go('faq')} className="hover:text-(--dr-ink)">FAQ</a>
          </div>
          <a href="#scan" onClick={go('scan')} className="dr-btn !px-4 !py-2.5 !text-sm">{hero.primary}</a>
        </nav>
      </header>

      <div ref={wrapper}>
        <div ref={content} className="dr-content">
          <main id="main">
            {/* Hero: the scanner */}
            <section id="top" className="dr-hero relative isolate flex min-h-[100dvh] flex-col justify-end overflow-hidden px-5 pt-28 pb-12 md:px-10">
              <ScannerCanvas />
              <div className="dr-hero-copy mx-auto w-full max-w-[1440px]">
                <h1 className="dr-display dr-h1 max-w-[16ch] text-[clamp(3rem,8.4vw,9.4rem)]">
                  The launch check for apps <span className="dr-mark inline-block">built with AI.</span>
                </h1>
                <div className="mt-10 grid items-end gap-8 border-t border-(--dr-line) pt-8 md:grid-cols-[1fr_1fr] lg:grid-cols-[1.2fr_1fr]">
                  <p className="dr-hero-fade max-w-[44ch] text-lg leading-relaxed text-(--dr-muted)">AI test users try your signup and dashboard in your own browser. One report adds SEO, AI search and security, fixes ranked.</p>
                  <ScanForm className="dr-hero-fade" />
                </div>
              </div>
            </section>

            {/* The eye opens */}
            <section id="how" className="dr-eye-wrap relative px-5 py-24 md:px-10 md:py-32">
              <div className="mx-auto max-w-[1440px]">
                <div className="dr-eye relative ml-auto aspect-[16/10] overflow-hidden md:w-[68%]">
                  <img src="/variants/dark/eye.jpg" alt="A close-up of an eye with desktop icons floating over the skin" loading="lazy" className="dr-photo absolute inset-0 h-full w-full object-cover" />
                  <div className="absolute inset-0 bg-gradient-to-t from-(--dr-bg) via-transparent to-transparent" />
                </div>
                <h2 className="dr-display dr-rise relative -mt-[0.6em] max-w-[14ch] text-[clamp(2.6rem,7vw,7.5rem)]">Your browser clicks. <span className="text-(--dr-red)">Our agent thinks.</span></h2>
              </div>
            </section>

            {/* Steps: pinned on desktop */}
            <section className="dr-steps relative px-5 md:px-10 lg:flex lg:h-[100dvh] lg:items-center">
              <div className="mx-auto grid w-full max-w-[1440px] gap-12 lg:grid-cols-[1fr_1fr] lg:gap-20">
                <ol className="grid content-center gap-6">
                  {steps.map((s, i) => (
                    <li key={s.title} className="dr-step">
                      <div className="flex items-baseline gap-5">
                        <span className="dr-mono text-(--dr-red)">{String(i + 1).padStart(2, '0')}</span>
                        <h3 className="dr-title text-[clamp(2.2rem,4.4vw,4.4rem)]">{s.title}</h3>
                      </div>
                      <p className="mt-3 max-w-[46ch] overflow-hidden pl-12 leading-relaxed text-(--dr-muted)">{s.body}</p>
                    </li>
                  ))}
                </ol>
                <div className="relative aspect-[4/5] max-h-[78dvh] w-full overflow-hidden bg-(--dr-panel)">
                  {stepShots.map((s, i) => (
                    <img key={s.src} src={`/variants/dark/${s.src}`} alt={s.alt} loading="lazy" className={`dr-shot dr-photo absolute inset-0 h-full w-full object-cover ${i ? 'max-lg:hidden' : ''}`} />
                  ))}
                  <span aria-hidden className="dr-frame absolute top-[14%] left-[16%] h-[34%] w-[46%] border-2 border-(--dr-red) mix-blend-screen" />
                </div>
              </div>
            </section>

            {/* Checks: a quiet index, not a marquee */}
            <section aria-label="What every scan checks" className="px-5 py-28 md:px-10">
              <div className="mx-auto max-w-[1440px]">
                <p className="dr-mono text-(--dr-red)">Every scan checks</p>
                <ul className="dr-rise mt-8 columns-2 gap-10 text-lg leading-[2.1] text-(--dr-muted) md:columns-3 lg:columns-4">
                  {checks.map((c) => <li key={c} className="break-inside-avoid transition-colors hover:text-(--dr-ink)">{c}</li>)}
                </ul>
              </div>
            </section>

            {/* The transcript */}
            <section className="dr-read relative flex min-h-[100dvh] items-center overflow-hidden px-5 md:px-10">
              <img src="/variants/dark/walkers.jpg" alt="" loading="lazy" className="dr-photo absolute inset-0 -z-0 h-full w-full object-cover opacity-20" />
              <figure className="relative mx-auto max-w-[1300px]">
                <blockquote className="dr-title text-[clamp(2.2rem,5.6vw,6rem)] leading-[0.98]">
                  {transcript.split(' ').map((w, i, all) => {
                    const red = i >= all.length - lastLine.split(' ').length
                    return <span key={i}><span className="dr-word" data-red={red || undefined}>{w}</span> </span>
                  })}
                </blockquote>
                <figcaption className="dr-mono mt-10 text-(--dr-muted)">A test user signing up on quickinvoice.app, a made-up invoicing app</figcaption>
              </figure>
            </section>

            {/* Report: sideways pan */}
            <section id="report" className="dr-pan relative overflow-hidden py-24 md:flex md:h-[100dvh] md:flex-col md:justify-center md:py-0">
              <h2 className="dr-display px-5 text-[clamp(2.4rem,5.4vw,5.6rem)] md:px-10">One report. <span className="text-(--dr-muted)">Four reads.</span></h2>
              <p className="mt-4 px-5 text-lg text-(--dr-muted) md:px-10">Journeys, SEO, AI search readiness and security, with the fixes ranked.</p>
              <div className="dr-track mt-10 flex flex-col gap-10 px-5 md:w-max md:flex-row md:gap-8 md:px-10">
                {reportParts.map((r, i) => (
                  <figure key={r.img} className="md:w-[min(46rem,50vw)]">
                    <div className="overflow-hidden border border-(--dr-line) bg-(--dr-ink) p-2">
                      <img src={`/assets/${r.img}`} alt={`${r.title}, from a real Walkthru report`} loading="lazy" className="block aspect-[16/9] w-full object-cover object-left-top" />
                    </div>
                    <figcaption className="mt-5 grid grid-cols-[3rem_1fr] gap-x-2">
                      <span className="dr-mono pt-1 text-(--dr-red)">{String(i + 1).padStart(2, '0')}</span>
                      <span><span className="block text-xl font-semibold">{r.title}</span><span className="mt-1 block max-w-[56ch] text-(--dr-muted)">{r.body}</span></span>
                    </figcaption>
                  </figure>
                ))}
                <div aria-hidden className="hidden w-[8vw] shrink-0 md:block" />
              </div>
            </section>

            {/* Test users */}
            <section className="px-5 py-28 md:px-10">
              <div className="mx-auto max-w-[1440px]">
                <div className="dr-rise relative overflow-hidden">
                  <img src="/variants/dark/crowd.jpg" alt="A cinema crowd in 3D glasses, one figure cut out in red" loading="lazy" className="aspect-[21/9] w-full object-cover" />
                </div>
                <h2 className="dr-display dr-rise mt-12 max-w-[18ch] text-[clamp(2.4rem,5.4vw,5.6rem)]">Different people get stuck in different places.</h2>
                <ul className="dr-people relative mt-14" onPointerLeave={() => show(null)}>
                  <img ref={peek} alt="" aria-hidden className="dr-photo pointer-events-none absolute top-0 left-0 z-10 hidden w-56 -translate-x-1/2 -translate-y-1/2 opacity-0 md:block" style={{ aspectRatio: '3 / 4', objectFit: 'cover' }} />
                  {personas.map((p) => (
                    <li key={p.name} onPointerEnter={() => show(p.img)} className="dr-row group grid gap-2 py-7 md:grid-cols-[1.4fr_1fr] md:items-center md:gap-10">
                      <h3 className="dr-title text-[clamp(2rem,4.4vw,4.4rem)] transition-colors duration-300 group-hover:text-(--dr-red)">{p.name.replace(/^The /, '')}</h3>
                      <div className="flex items-start gap-4">
                        <img src={`/assets/${p.img}`} alt="" loading="lazy" className="dr-photo size-16 shrink-0 object-cover md:hidden" />
                        <p className="text-(--dr-muted)"><span className="text-(--dr-ink)">{p.who}</span> Catches {p.catches.charAt(0).toLowerCase() + p.catches.slice(1)}</p>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            </section>

            {/* Safety */}
            <section className="px-5 pb-28 md:px-10">
              <div className="mx-auto grid max-w-[1440px] gap-12 lg:grid-cols-[1fr_1.1fr] lg:gap-20">
                <div className="dr-rise relative overflow-hidden">
                  <img src="/variants/dark/red-book.jpg" alt="A man in a suit reading a red book in a wire chair" loading="lazy" className="aspect-square w-full object-cover" data-speed="0.92" />
                </div>
                <div className="flex flex-col justify-center">
                  <h2 className="dr-display dr-rise max-w-[12ch] text-[clamp(2.4rem,4.6vw,4.8rem)]">Tests your dashboard without your password.</h2>
                  <dl className="mt-12 grid gap-x-10 gap-y-8 sm:grid-cols-2">
                    {safety.map((s) => (
                      <div key={s.title} className="dr-rise border-t-2 border-(--dr-red) pt-5">
                        <dt className="flex items-center gap-3 text-lg font-semibold"><s.icon weight="light" className="size-5 text-(--dr-red)" />{s.title}</dt>
                        <dd className="mt-2 leading-relaxed text-(--dr-muted)">{s.body}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
              </div>
            </section>

            {/* Pricing */}
            <section id="pricing" className="border-t border-(--dr-line) px-5 py-28 md:px-10">
              <div className="mx-auto max-w-[1440px]">
                <h2 className="dr-display dr-rise text-[clamp(2.4rem,5.4vw,5.6rem)]">Free to start.<br /><span className="text-(--dr-muted)">One-time passes to launch.</span></h2>
                <div className="mt-14 grid gap-px bg-(--dr-line) sm:grid-cols-2 lg:grid-cols-4">
                  {plans.map((p) => (
                    <article key={p.name} className={`dr-rise flex flex-col bg-(--dr-bg) p-8 ${p.highlight ? 'shadow-[inset_0_3px_0_var(--dr-red)]' : ''}`}>
                      <h3 className="dr-mono text-(--dr-muted)">{p.name}</h3>
                      <p className={`dr-display mt-6 text-7xl ${p.highlight ? 'text-(--dr-red)' : ''}`}>{p.price}</p>
                      <p className="mt-3 text-sm text-(--dr-muted)">{p.per}</p>
                      <ul className="mt-8 mb-10 grid flex-1 content-start gap-3 text-sm">
                        {p.features.map((f) => <li key={f} className="border-b border-(--dr-line) pb-3">{f}</li>)}
                      </ul>
                      <a href={p.href ?? '#scan'} onClick={p.href ? undefined : go('scan')} className={`dr-btn ${p.highlight ? '' : 'dr-btn--ghost'}`}>{p.cta}<ArrowUpRightIcon className="size-4" /></a>
                    </article>
                  ))}
                </div>
              </div>
            </section>

            {/* FAQ */}
            <section id="faq" className="px-5 py-28 md:px-10">
              <div className="mx-auto grid max-w-[1440px] gap-12 lg:grid-cols-[1fr_1.4fr]">
                <h2 className="dr-display dr-rise text-[clamp(2.4rem,5.4vw,5.6rem)] lg:sticky lg:top-28 lg:self-start">Asked often.</h2>
                <div>
                  {faqs.map((f) => (
                    <details key={f.q} className="dr-faq dr-row py-6">
                      <summary className="flex items-center justify-between gap-6 text-xl">{f.q}<PlusIcon weight="light" className="dr-plus size-6 shrink-0" /></summary>
                      <p className="mt-4 max-w-[62ch] leading-relaxed text-(--dr-muted)">{f.a}</p>
                    </details>
                  ))}
                </div>
              </div>
            </section>

            {/* Closing */}
            <section id="scan" className="dr-close relative overflow-hidden px-5 pt-20 pb-32 md:px-10">
              <img src="/variants/dark/collage.jpg" alt="" loading="lazy" className="dr-photo absolute inset-y-0 right-0 h-full w-1/2 object-cover opacity-40 max-md:hidden" />
              <div className="relative mx-auto max-w-[1440px]">
                <p className="dr-display dr-close-word text-[clamp(2.4rem,8.4vw,12rem)] whitespace-nowrap" aria-hidden>Scan my site</p>
                <div className="mt-12 grid gap-10 md:grid-cols-[1fr_1fr]">
                  <h2 className="max-w-[24ch] text-2xl leading-snug">SEO, AI search readiness and security in about 20 seconds. No install, no card.</h2>
                  <ScanForm />
                </div>
              </div>
            </section>
          </main>

          <footer className="border-t border-(--dr-line) px-5 py-12 md:px-10">
            <div className="dr-mono mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-6 text-(--dr-muted)">
              <span className="flex items-center gap-2"><img src={brand.mark} alt="" className="size-5 invert" />{brand.name}, {brand.year}</span>
              <span className="flex flex-wrap gap-6">
                <a href="/docs" className="hover:text-(--dr-ink)">Docs</a><a href="/pricing" className="hover:text-(--dr-ink)">Pricing</a><a href="/privacy" className="hover:text-(--dr-ink)">Privacy</a><a href="/terms" className="hover:text-(--dr-ink)">Terms</a><a href="/security" className="hover:text-(--dr-ink)">Security</a><a href="/login" className="hover:text-(--dr-ink)">Sign in</a>
              </span>
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
      <label htmlFor={id} className="dr-mono text-(--dr-muted)">Your website</label>
      <div className="mt-1 flex flex-col gap-4 sm:flex-row sm:items-end">
        <input id={id} name="url" type="text" inputMode="url" placeholder="yoursite.com" disabled={busy} aria-invalid={!!error} aria-describedby={`${id}-error`} className="dr-input" />
        <button type="submit" disabled={busy} className="dr-btn disabled:opacity-60">{busy ? 'Scanning...' : hero.primary}<ArrowRightIcon className="size-4" /></button>
      </div>
      <p id={`${id}-error`} role="status" className="mt-2 min-h-5 text-sm text-(--dr-red)">{error}</p>
    </form>
  )
}

/** The hero scanner: a black and white photo through a WebGL shader. A red band sweeps down the frame like a reader
 *  going over the page, the pointer bends the image like a lens, film grain on top. Paused off screen; one still
 *  frame for reduced motion; a plain photo when WebGL is unavailable. */
function ScannerCanvas() {
  const ref = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    const canvas = ref.current
    const gl = canvas?.getContext('webgl', { antialias: false, alpha: false })
    if (!canvas || !gl) return
    const vs = 'attribute vec2 p; varying vec2 v; void main(){ v = p * .5 + .5; gl_Position = vec4(p, 0., 1.); }'
    const fs = `precision mediump float;
      uniform sampler2D t; uniform vec2 res; uniform vec2 img; uniform float time; uniform vec2 mouse; uniform float fade;
      varying vec2 v;
      float rnd(vec2 c){ return fract(sin(dot(c, vec2(12.9898, 78.233))) * 43758.5453); }
      void main(){
        float rs = res.x / res.y, ri = img.x / img.y;
        vec2 s = rs > ri ? vec2(1., ri / rs) : vec2(rs / ri, 1.);
        vec2 d = v - mouse; d.x *= rs;
        float lens = smoothstep(.3, 0., length(d));
        vec2 uv = (v - .5) * s * .92 + .5 - (v - mouse) * lens * .07;
        float y = 1. - fract(time * .07);
        float band = smoothstep(.16, 0., abs(v.y - y));
        float off = .002 + band * .012;
        vec3 c = vec3(texture2D(t, uv + vec2(off, 0.)).r, texture2D(t, uv).g, texture2D(t, uv - vec2(off, 0.)).b);
        float l = pow(dot(c, vec3(.299, .587, .114)), 1.2) * .62;
        vec3 col = mix(vec3(l), vec3(1., .23, .13) * (l * 1.9 + .1), band * .9);
        col += (rnd(v * res + fract(time)) - .5) * .1;
        col *= smoothstep(1.25, .35, length(v - .5)) * fade;
        gl_FragColor = vec4(col, 1.);
      }`
    const sh = (type: number, src: string) => { const s = gl.createShader(type)!; gl.shaderSource(s, src); gl.compileShader(s); return s }
    const prog = gl.createProgram()!
    gl.attachShader(prog, sh(gl.VERTEX_SHADER, vs))
    gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, fs))
    gl.linkProgram(prog)
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) return
    gl.useProgram(prog)
    gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer())
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW)
    const p = gl.getAttribLocation(prog, 'p')
    gl.enableVertexAttribArray(p)
    gl.vertexAttribPointer(p, 2, gl.FLOAT, false, 0, 0)
    const u = (n: string) => gl.getUniformLocation(prog, n)
    const mouse = { x: 0.5, y: 0.5, tx: 0.5, ty: 0.5 }
    let fade = 0
    let frame = 0
    let visible = true
    let ready = false
    let size = [1, 1]

    const resize = () => {
      const dpr = Math.min(1.5, devicePixelRatio || 1)
      canvas.width = Math.round(canvas.clientWidth * dpr)
      canvas.height = Math.round(canvas.clientHeight * dpr)
      gl.viewport(0, 0, canvas.width, canvas.height)
    }
    const draw = (now: number) => {
      mouse.x += (mouse.tx - mouse.x) * 0.06
      mouse.y += (mouse.ty - mouse.y) * 0.06
      fade = Math.min(1, fade + 0.02)
      gl.uniform2f(u('res'), canvas.width, canvas.height)
      gl.uniform2f(u('img'), size[0], size[1])
      gl.uniform1f(u('time'), now / 1000)
      gl.uniform2f(u('mouse'), mouse.x, mouse.y)
      gl.uniform1f(u('fade'), fade)
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4)
    }
    const loop = (now: number) => { draw(now); frame = requestAnimationFrame(loop) }
    const sync = () => { cancelAnimationFrame(frame); if (ready && visible && document.visibilityState !== 'hidden') frame = requestAnimationFrame(loop) }

    const image = new Image()
    image.onload = () => {
      size = [image.naturalWidth, image.naturalHeight]
      gl.bindTexture(gl.TEXTURE_2D, gl.createTexture())
      gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true)
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, gl.RGB, gl.UNSIGNED_BYTE, image)
      for (const [k, val] of [[gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE], [gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE], [gl.TEXTURE_MIN_FILTER, gl.LINEAR], [gl.TEXTURE_MAG_FILTER, gl.LINEAR]]) gl.texParameteri(gl.TEXTURE_2D, k, val)
      resize()
      ready = true
      if (reduced()) { fade = 1; draw(4200); return }
      sync()
    }
    image.src = '/variants/dark/walkers.jpg'

    const onMove = (e: PointerEvent) => { const r = canvas.getBoundingClientRect(); mouse.tx = (e.clientX - r.left) / r.width; mouse.ty = 1 - (e.clientY - r.top) / r.height }
    const io = new IntersectionObserver(([e]) => { visible = e.isIntersecting; sync() })
    io.observe(canvas)
    const ro = new ResizeObserver(() => { resize(); if (reduced() && ready) draw(4200) })
    ro.observe(canvas)
    window.addEventListener('pointermove', onMove)
    document.addEventListener('visibilitychange', sync)
    return () => { cancelAnimationFrame(frame); io.disconnect(); ro.disconnect(); window.removeEventListener('pointermove', onMove); document.removeEventListener('visibilitychange', sync) }
  }, [])
  return (
    <>
      <img src="/variants/dark/walkers.jpg" alt="" className="dr-photo absolute inset-0 -z-20 h-full w-full object-cover opacity-50" />
      <canvas ref={ref} aria-hidden className="absolute inset-0 -z-10 h-full w-full" />
      <div aria-hidden className="absolute inset-x-0 bottom-0 -z-10 h-2/3 bg-gradient-to-t from-(--dr-bg) via-(--dr-bg)/70 to-transparent" />
    </>
  )
}
