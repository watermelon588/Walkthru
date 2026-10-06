// Variant 3, Markup: the page reads like a reviewer's proof sheet. Real captures get circled and annotated in ink,
// the checklist ticks itself, Scout walks the steps along a drawn path, the safety promises land as rubber stamps.
import { useGSAP } from '@gsap/react'
import { ArrowRightIcon, PlusIcon } from '@phosphor-icons/react'
import gsap from 'gsap'
import { DrawSVGPlugin } from 'gsap/DrawSVGPlugin'
import { MotionPathPlugin } from 'gsap/MotionPathPlugin'
import { SplitText } from 'gsap/SplitText'
import { useId, useRef } from 'react'
import { brand } from '../brand'
import { checks, faqs, hero, personas, plans, reportParts, run, safety, steps } from '../content'
import { scrollToId, useScan, useSmoother } from './shared'
import './markup.css'

gsap.registerPlugin(DrawSVGPlugin, MotionPathPlugin, SplitText)

/** A hand-drawn loop around (cx, cy): a little more than one turn, the radius wobbling so the ends never meet. */
function scribble(cx: number, cy: number, rx: number, ry: number, seed = 1) {
  const pts: string[] = []
  for (let i = 0; i <= 72; i++) {
    const t = (i / 72) * Math.PI * 2.2 + seed
    const w = 1 + Math.sin(t * 3 + seed) * 0.035 + (i / 72) * 0.07
    pts.push(`${(cx + Math.cos(t) * rx * w).toFixed(1)} ${(cy + Math.sin(t) * ry * w).toFixed(1)}`)
  }
  return `M${pts.join(' L')}`
}

const stepArt = [
  { src: 'line-laptop.jpg', alt: 'Line drawing of someone sitting on the floor with a laptop' },
  { src: 'line-walk.jpg', alt: 'Line drawing of someone walking while checking a phone' },
  { src: 'line-monitor.jpg', alt: 'Line drawing of someone leaning in to read a monitor' },
  { src: 'line-juggle.jpg', alt: 'Line drawing of someone handling a laptop, phone and parcels at once' },
]
const reportNotes = ['the step, and their own words', 'one score out of 100', 'what crawlers can read', 'passive checks only']

export default function Markup() {
  const wrapper = useRef<HTMLDivElement>(null)
  const content = useRef<HTMLDivElement>(null)
  useSmoother(wrapper, content, 1.1)
  const scope = useRef<HTMLDivElement>(null)

  useGSAP(() => {
    const mm = gsap.matchMedia()
    mm.add('(prefers-reduced-motion: no-preference)', () => {
      // Hero: lines rise, the highlighter sweeps, then the reviewer marks up the capture.
      const split = SplitText.create('.mk-h1', { type: 'lines', mask: 'lines' })
      gsap.from(split.lines, { yPercent: 105, duration: 1.1, ease: 'expo.out', stagger: 0.09, delay: 0.2 })
      gsap.fromTo('.mk-h1 .mk-hl', { '--hl': '0%' }, { '--hl': '100%', duration: 0.8, ease: 'power2.inOut', delay: 0.85 })
      gsap.from('.mk-hero-fade', { y: 18, autoAlpha: 0, duration: 0.9, ease: 'expo.out', stagger: 0.08, delay: 0.6 })
      gsap.from('.mk-proof', { y: 40, rotate: 0, autoAlpha: 0, duration: 1.2, ease: 'expo.out', delay: 0.35 })
      const marks = gsap.timeline({ delay: 1.3 })
      gsap.utils.toArray<SVGPathElement>('.mk-proof .mk-ink').forEach((p, i) => marks.from(p, { drawSVG: 0, duration: 0.7, ease: 'power1.inOut' }, i * 0.35))
      marks.from('.mk-proof .mk-note', { autoAlpha: 0, y: 6, duration: 0.5, stagger: 0.35 }, 0.3)

      // The checklist ticks itself as you read down it.
      gsap.from('.mk-check path', { drawSVG: 0, ease: 'none', stagger: 0.12, scrollTrigger: { trigger: '.mk-checks', start: 'top 70%', end: 'bottom 55%', scrub: 0.6 } })

      // Steps: the path draws itself and Scout walks it.
      gsap.timeline({ scrollTrigger: { trigger: '.mk-steps', start: 'top 55%', end: 'bottom 70%', scrub: 0.8 } })
        .from('.mk-route', { drawSVG: 0, ease: 'none' }, 0)
        .to('.mk-walker', { motionPath: { path: '.mk-route', align: '.mk-route', alignOrigin: [0.5, 0.5] }, ease: 'none' }, 0)

      // Field report: rows arrive, the last one is circled and highlighted.
      gsap.timeline({ scrollTrigger: { trigger: '.mk-log', start: 'top 65%' } })
        .from('.mk-log-row', { y: 24, autoAlpha: 0, duration: 0.6, ease: 'expo.out', stagger: 0.15 })
        .fromTo('.mk-log .mk-hl', { '--hl': '0%' }, { '--hl': '100%', duration: 0.7, ease: 'power2.inOut' })
        .from('.mk-log .mk-ink', { drawSVG: 0, duration: 0.8, ease: 'power1.inOut' }, '-=0.2')
        .from('.mk-log .mk-note', { autoAlpha: 0, rotate: -12, duration: 0.5 })

      // Report captures: crop marks and the reviewer's note draw in as each sheet arrives.
      gsap.utils.toArray<HTMLElement>('.mk-shot').forEach((el) =>
        gsap.timeline({ scrollTrigger: { trigger: el, start: 'top 70%' } })
          .from(el.querySelectorAll('.mk-ink'), { drawSVG: 0, duration: 0.5, stagger: 0.08 })
          .from(el.querySelector('.mk-note'), { autoAlpha: 0, x: -10, duration: 0.5 }, '-=0.2'))

      // Safety: stamps thud onto the page.
      gsap.timeline({ scrollTrigger: { trigger: '.mk-stamps', start: 'top 70%' } })
        .from('.mk-stamp', { scale: 2.4, autoAlpha: 0, duration: 0.32, ease: 'power4.in', stagger: 0.28 })
        .from('.mk-stamp-body', { autoAlpha: 0, y: 8, duration: 0.4, stagger: 0.1 }, '-=0.4')

      gsap.utils.toArray<HTMLElement>('.mk-rise').forEach((el) =>
        gsap.from(el, { y: 40, autoAlpha: 0, duration: 1, ease: 'expo.out', scrollTrigger: { trigger: el, start: 'top 88%' } }))
    })
    // Index cards fan out from one pile.
    mm.add('(prefers-reduced-motion: no-preference) and (min-width: 1024px)', () => {
      gsap.from('.mk-person', { x: (i) => (2 - i) * 260, y: 40, rotate: (i) => (i - 2) * -7, ease: 'none', scrollTrigger: { trigger: '.mk-people', start: 'top 85%', end: 'top 35%', scrub: 0.8 } })
    })
  }, { scope })

  const go = (id: string) => (e: React.MouseEvent) => { e.preventDefault(); scrollToId(id, 90) }

  return (
    <div ref={scope} className="mk">
      <header className="fixed inset-x-0 top-0 z-50 border-b border-(--mk-line) bg-(--mk-paper)/85 backdrop-blur-md">
        <nav aria-label="Main" className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-6 px-5 md:px-10">
          <a href="#top" onClick={go('top')} className="flex items-center gap-2 font-semibold"><img src={brand.mark} alt="" className="size-7" />{brand.name}</a>
          <div className="mk-mono hidden items-center gap-7 text-(--mk-muted) md:flex">
            <a href="#how" onClick={go('how')} className="hover:text-(--mk-ink)">How it works</a>
            <a href="#report" onClick={go('report')} className="hover:text-(--mk-ink)">Report</a>
            <a href="#pricing" onClick={go('pricing')} className="hover:text-(--mk-ink)">Pricing</a>
            <a href="#faq" onClick={go('faq')} className="hover:text-(--mk-ink)">FAQ</a>
          </div>
          <a href="#scan" onClick={go('scan')} className="mk-btn !py-2.5 !text-sm">{hero.primary}</a>
        </nav>
      </header>

      <div ref={wrapper}>
        <div ref={content} className="mk-content">
          <main id="main">
            {/* Hero: a marked-up proof of the real dashboard */}
            <section id="top" className="mx-auto grid min-h-[100dvh] max-w-7xl items-center gap-14 px-5 pt-28 pb-20 md:px-10 lg:grid-cols-[0.9fr_1.1fr] lg:gap-12">
              <div>
                <h1 className="mk-display mk-h1 text-[clamp(2.7rem,5vw,4.9rem)]">The <span className="mk-hl">launch check</span> for apps built with AI.</h1>
                <p className="mk-hero-fade mt-7 max-w-[40ch] text-lg leading-relaxed text-(--mk-muted)">AI test users try your signup and dashboard in your own browser. One report marks up what to fix first.</p>
                <ScanForm className="mk-hero-fade mt-9 max-w-lg" />
              </div>
              <figure className="mk-proof relative rotate-[-1.2deg] pb-24">
                <div className="mk-sheet relative p-2.5">
                  <span aria-hidden className="mk-tape -top-3 left-10 rotate-[-4deg]" />
                  <span aria-hidden className="mk-tape -top-3 right-12 rotate-[5deg]" />
                  <div className="relative overflow-hidden rounded-[0.3rem]">
                    <img src="/assets/hero-dashboard.webp" width={2160} height={1275} alt="The real Walkthru dashboard: plan and runs left, and the launch-readiness pipeline across recent runs" fetchPriority="high" className="block h-auto w-full" />
                    <svg viewBox="0 0 1000 590" className="absolute inset-0 h-full w-full overflow-visible" aria-hidden>
                      <path className="mk-ink" d="M196 186 C 260 178, 330 192, 420 180" />
                      <path className="mk-ink" d={scribble(292, 357, 112, 54, 0.6)} />
                      <path className="mk-ink" d="M232 590 C 236 520, 250 470, 268 418 M252 432 L268 416 L276 438" />
                      <path className="mk-ink mk-ink--lime" d="M196 494 L186 494 L186 580 L196 580 M964 494 L974 494 L974 580 L964 580" />
                    </svg>
                    <p className="mk-note mk-hand absolute top-[17%] left-[47%] rotate-[-4deg] text-[clamp(1rem,1.9vw,1.6rem)]">the promise, up front</p>
                  </div>
                </div>
                <p className="mk-note mk-hand absolute bottom-7 left-[6%] rotate-[-3deg] text-[clamp(1.1rem,1.8vw,1.6rem)]">runs left, always in view</p>
                <p className="mk-note mk-hand absolute right-[3%] bottom-1 rotate-[2deg] text-[clamp(1.1rem,1.8vw,1.6rem)]">four layers of proof</p>
                <figcaption className="sr-only">A real capture of the Walkthru dashboard, annotated.</figcaption>
              </figure>
            </section>

            {/* Inspection checklist */}
            <section className="mk-checks mx-auto max-w-7xl px-5 py-24 md:px-10">
              <div className="mk-sheet grid gap-10 p-7 md:p-12 lg:grid-cols-[0.8fr_1.2fr]">
                <div>
                  <h2 className="mk-display mk-rise text-[clamp(2.2rem,4vw,3.6rem)]">Every scan checks {checks.length} things.</h2>
                  <p className="mk-rise mt-5 max-w-[36ch] leading-relaxed text-(--mk-muted)">The free Instant Scan reads your public pages in about 20 seconds. No install, no account.</p>
                  <img src="/variants/markup/spotlight.jpg" alt="A line drawing of a crowd of faces caught in a lime spotlight" loading="lazy" className="mk-rise mt-8 aspect-[16/10] w-full max-w-sm object-cover object-[50%_72%] mix-blend-multiply" />
                </div>
                <ul className="grid content-start gap-x-8 gap-y-3.5 sm:grid-cols-2 xl:grid-cols-3">
                  {checks.map((c) => (
                    <li key={c} className="flex items-start gap-3 text-[0.95rem] leading-snug">
                      <span className="mk-box mt-px" aria-hidden><svg viewBox="0 0 17 15" className="mk-check size-3.5 overflow-visible"><path className="mk-ink" d="M2 8 L6.5 12.5 L15 2" /></svg></span>{c}
                    </li>
                  ))}
                </ul>
              </div>
            </section>

            {/* Steps along a drawn path */}
            <section id="how" className="mx-auto max-w-7xl px-5 py-24 md:px-10">
              <h2 className="mk-display mk-rise max-w-[16ch] text-[clamp(2.4rem,5vw,4.4rem)]">Your browser clicks. <span className="mk-hl">Our agent thinks.</span></h2>
              <div className="mk-steps relative mt-16 grid gap-14 lg:grid-cols-[1fr_140px_1fr] lg:gap-x-6 lg:gap-y-4">
                <svg viewBox="0 0 100 1000" preserveAspectRatio="none" aria-hidden className="pointer-events-none absolute top-0 left-1/2 hidden h-full w-[140px] -translate-x-1/2 overflow-visible lg:block">
                  <path className="mk-ink opacity-30" strokeDasharray="2 9" d="M50 0 C 95 120, 5 250, 50 375 S 95 625, 50 750 S 5 900, 50 1000" />
                  <path className="mk-route mk-ink" d="M50 0 C 95 120, 5 250, 50 375 S 95 625, 50 750 S 5 900, 50 1000" />
                </svg>
                <img src={brand.mark} alt="" aria-hidden className="mk-walker pointer-events-none absolute top-0 left-0 z-10 hidden size-12 lg:block" />
                {steps.map((s, i) => (
                  <article key={s.title} className={`mk-rise mk-sheet relative grid gap-5 self-start p-6 sm:grid-cols-[1fr_9rem] md:p-8 ${i % 2 ? 'lg:col-start-3 lg:mt-24' : 'lg:col-start-1'}`}>
                    <div>
                      <p className="mk-mono text-(--mk-muted)">{String(i + 1).padStart(2, '0')}</p>
                      <h3 className="mk-display mt-2 text-3xl">{s.title}</h3>
                      <p className="mt-3 leading-relaxed text-(--mk-muted)">{s.body}</p>
                    </div>
                    <img src={`/variants/markup/${stepArt[i].src}`} alt={stepArt[i].alt} loading="lazy" className="aspect-square w-full object-contain mix-blend-multiply" />
                  </article>
                ))}
              </div>
            </section>

            {/* Field report: one real-looking run, marked up */}
            <section className="mk-log mx-auto max-w-7xl px-5 py-24 md:px-10">
              <h2 className="mk-display mk-rise max-w-[18ch] text-[clamp(2.4rem,5vw,4.4rem)]">Read along as a stranger signs up.</h2>
              <p className="mk-rise mt-4 max-w-[52ch] text-(--mk-muted)">A sample run on quickinvoice.app, a made-up invoicing app.</p>
              <ol className="mk-sheet mt-10 overflow-hidden">
                {run.map((r, i) => {
                  const last = i === run.length - 1
                  return (
                    <li key={r.action} className="mk-log-row relative grid gap-2 border-b border-(--mk-line) px-6 py-6 last:border-b-0 md:grid-cols-[3rem_1fr_1.6fr] md:items-baseline md:gap-6 md:px-10">
                      <span className="mk-mono text-(--mk-muted)">{String(i + 1).padStart(2, '0')}</span>
                      <span className="font-medium">{r.action}</span>
                      <span className="text-lg leading-snug">&ldquo;{last ? <span className="mk-hl">{r.thought}</span> : r.thought}&rdquo;</span>
                      {last && (
                        <>
                          <svg viewBox="0 0 100 40" preserveAspectRatio="none" aria-hidden className="pointer-events-none absolute inset-x-[2%] inset-y-[8%] hidden h-[84%] w-[96%] overflow-visible md:block"><path className="mk-ink" d={scribble(50, 20, 49, 19, 2.2)} /></svg>
                          <span className="mk-note mk-hand absolute -bottom-9 right-8 rotate-[-4deg] text-2xl md:text-3xl">this is where they leave</span>
                        </>
                      )}
                    </li>
                  )
                })}
              </ol>
            </section>

            {/* Report */}
            <section id="report" className="mx-auto grid max-w-7xl gap-14 px-5 pt-28 pb-24 md:px-10 lg:grid-cols-[0.85fr_1.15fr]">
              <div className="lg:sticky lg:top-28 lg:self-start">
                <h2 className="mk-display mk-rise text-[clamp(2.4rem,4.6vw,4.2rem)]">One report. Journeys, SEO, AI search and security.</h2>
                <ol className="mt-10 grid gap-6">
                  {reportParts.map((r, i) => (
                    <li key={r.title} className="mk-rise grid grid-cols-[2rem_1fr] gap-3">
                      <span className="mk-mono pt-1 text-(--mk-muted)">{String(i + 1).padStart(2, '0')}</span>
                      <span><span className="block text-lg font-semibold">{r.title}</span><span className="mt-1 block text-sm leading-relaxed text-(--mk-muted)">{r.body}</span></span>
                    </li>
                  ))}
                </ol>
              </div>
              <div className="grid gap-16">
                {reportParts.map((r, i) => (
                  <figure key={r.img} className="mk-shot relative">
                    <div className={`mk-sheet relative p-2.5 ${i % 2 ? 'rotate-[0.8deg]' : 'rotate-[-0.8deg]'}`}>
                      <img src={`/assets/${r.img}`} alt={`${r.title}, from a real Walkthru report`} loading="lazy" className="block h-auto w-full rounded-[0.3rem]" />
                      <svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden className="pointer-events-none absolute -inset-3 h-[calc(100%+1.5rem)] w-[calc(100%+1.5rem)] overflow-visible">
                        <path className="mk-ink" d="M0 7 L0 0 L5 0 M95 0 L100 0 L100 7 M100 93 L100 100 L95 100 M5 100 L0 100 L0 93" />
                      </svg>
                    </div>
                    <figcaption className="mk-note mk-hand mt-5 flex items-center gap-2 pl-2 text-2xl"><ArrowRightIcon weight="bold" className="size-5 rotate-[-25deg]" />{reportNotes[i]}</figcaption>
                  </figure>
                ))}
              </div>
            </section>

            {/* Test users: index cards fanned out */}
            <section className="mk-people mx-auto max-w-7xl px-5 py-24 md:px-10">
              <h2 className="mk-display mk-rise max-w-[18ch] text-[clamp(2.4rem,5vw,4.4rem)]">Different people get stuck in different places.</h2>
              <div className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-5">
                {personas.map((p, i) => (
                  <article key={p.name} className="mk-person mk-sheet relative p-3 pb-5" style={{ rotate: `${[-2, 1.5, -1, 2, -1.5][i]}deg` }}>
                    <span aria-hidden className="mk-tape -top-3 left-1/2 -translate-x-1/2 rotate-[-3deg]" />
                    <img src={`/assets/${p.img}`} alt={`Portrait for ${p.name.toLowerCase()}`} loading="lazy" className="aspect-[4/5] w-full rounded-[0.3rem] object-cover grayscale" />
                    <h3 className="mk-hand mt-4 px-1 text-[1.65rem]">{p.name}</h3>
                    <p className="mt-1 px-1 text-sm leading-snug text-(--mk-muted)">Catches {p.catches.charAt(0).toLowerCase() + p.catches.slice(1)}</p>
                  </article>
                ))}
              </div>
            </section>

            {/* Safety stamps */}
            <section className="mx-auto max-w-7xl px-5 py-24 md:px-10">
              <div className="mk-sheet p-7 md:p-12">
                <h2 className="mk-display mk-rise max-w-[16ch] text-[clamp(2.4rem,5vw,4.4rem)]">Tests your dashboard without your password.</h2>
                <div className="mk-stamps mt-14 grid gap-12 sm:grid-cols-2 lg:grid-cols-4">
                  {safety.map((s, i) => (
                    <div key={s.title}>
                      <p className="mk-stamp" style={{ rotate: `${[-6, 4, -3, 7][i]}deg` }}><span className="flex items-center gap-2"><s.icon weight="bold" className="size-4" />{s.title}</span></p>
                      <p className="mk-stamp-body mt-6 leading-relaxed text-(--mk-muted)">{s.body}</p>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            {/* Pricing */}
            <section id="pricing" className="mx-auto max-w-7xl px-5 py-24 md:px-10">
              <h2 className="mk-display mk-rise text-[clamp(2.4rem,5vw,4.4rem)]">Start free. <span className="mk-hl">Pay once</span> to launch.</h2>
              <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
                {plans.map((p) => (
                  <article key={p.name} className="mk-rise mk-sheet relative flex flex-col p-7">
                    {p.highlight && <span aria-hidden className="mk-tape -top-3 right-6 rotate-[4deg]" />}
                    <h3 className="mk-mono text-(--mk-muted)">{p.name}</h3>
                    <p className="mk-display mt-5 text-6xl"><span className={p.highlight ? 'mk-hl' : ''}>{p.price}</span></p>
                    <p className="mt-2 text-sm text-(--mk-muted)">{p.per}</p>
                    <ul className="mt-6 mb-8 grid flex-1 content-start text-sm">
                      {p.features.map((f) => <li key={f} className="border-b border-dashed border-(--mk-line) py-2.5">{f}</li>)}
                    </ul>
                    <a href={p.href ?? '#scan'} onClick={p.href ? undefined : go('scan')} className={`mk-btn ${p.highlight ? '' : 'mk-btn--line'}`}>{p.cta}</a>
                  </article>
                ))}
              </div>
            </section>

            {/* FAQ */}
            <section id="faq" className="mx-auto max-w-4xl px-5 py-24 md:px-10">
              <h2 className="mk-display mk-rise text-[clamp(2.4rem,5vw,4.4rem)]">Questions in the margin.</h2>
              <div className="mk-sheet mt-10 px-6 md:px-10">
                {faqs.map((f) => (
                  <details key={f.q} className="mk-faq border-b border-(--mk-line) py-6 last:border-b-0">
                    <summary className="flex items-center justify-between gap-6 text-lg font-semibold"><span>{f.q}</span><PlusIcon weight="bold" className="mk-plus size-5 shrink-0" /></summary>
                    <p className="mt-3 max-w-[62ch] leading-relaxed text-(--mk-muted)">{f.a}</p>
                  </details>
                ))}
              </div>
            </section>

            {/* Closing */}
            <section id="scan" className="mx-auto max-w-7xl px-5 pt-12 pb-32 md:px-10">
              <div className="mk-sheet relative grid items-center gap-10 overflow-hidden p-8 md:p-14 lg:grid-cols-[1.2fr_0.8fr]">
                <div>
                  <h2 className="mk-display text-[clamp(2.8rem,6vw,5.6rem)]">Get a <span className="mk-hl">second reading.</span></h2>
                  <p className="mt-5 max-w-[42ch] text-lg text-(--mk-muted)">SEO, AI search readiness and security in about 20 seconds. Free, no card.</p>
                  <ScanForm className="mt-9 max-w-lg" />
                </div>
                <img src="/variants/markup/figures.jpg" alt="Loose ink doodles of small curious figures" loading="lazy" className="mx-auto max-h-96 w-auto mix-blend-multiply" />
              </div>
            </section>
          </main>

          <footer className="border-t border-(--mk-line) px-5 py-12 md:px-10">
            <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-6 text-sm text-(--mk-muted)">
              <span className="flex items-center gap-2 text-(--mk-ink)"><img src={brand.mark} alt="" className="size-6" />{brand.name}<span className="text-(--mk-muted)">{brand.tagline}</span></span>
              <span className="mk-mono flex flex-wrap gap-6">
                <a href="/docs" className="hover:text-(--mk-ink)">Docs</a><a href="/pricing" className="hover:text-(--mk-ink)">Pricing</a><a href="/privacy" className="hover:text-(--mk-ink)">Privacy</a><a href="/terms" className="hover:text-(--mk-ink)">Terms</a><a href="/security" className="hover:text-(--mk-ink)">Security</a><a href="/login" className="hover:text-(--mk-ink)">Sign in</a>
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
      <label htmlFor={id} className="mk-mono text-(--mk-muted)">Website to check</label>
      <div className="mt-2 flex flex-col gap-3 sm:flex-row">
        <input id={id} name="url" type="text" inputMode="url" placeholder="yoursite.com" disabled={busy} aria-invalid={!!error} aria-describedby={`${id}-error`} className="mk-input" />
        <button type="submit" disabled={busy} className="mk-btn disabled:opacity-60">{busy ? 'Scanning...' : hero.primary}<ArrowRightIcon weight="bold" className="size-4" /></button>
      </div>
      <p id={`${id}-error`} role="status" className="mt-2 min-h-5 text-sm font-medium text-[#a3261b]">{error}</p>
    </form>
  )
}
