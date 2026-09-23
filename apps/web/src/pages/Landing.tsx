import { useGSAP } from '@gsap/react'
import { ArrowRightIcon } from '@phosphor-icons/react'
import gsap from 'gsap'
import { useRef } from 'react'
import { AgentPresence } from '../components/AgentPresence'
import { useReveal } from '../lib/motion'
import { hero, personas, reportParts, run, safety, steps } from '../content'
import { Asset, btnGhost, btnPrimary, Closing, Faq, Footer, h2, lead, Nav, Pricing, Words } from '../components/Shared'

// Final landing page. Base: Silver. Borrowed: quote (Porcelain), report stays Silver,
// test users (Graphite), safety band (Mist). History of the variants: see DESIGN.md.
export default function Landing() {
  const root = useRef<HTMLDivElement>(null)
  useReveal(root)
  useGSAP(
    () => {
      gsap.matchMedia().add('(prefers-reduced-motion: no-preference)', () => {
        // The timeline draws itself as you read the four steps.
        gsap.fromTo('.time-line', { scaleY: 0 }, { scaleY: 1, ease: 'none', scrollTrigger: { trigger: '.timeline', start: 'top 70%', end: 'bottom 60%', scrub: true } })
      })
    },
    { scope: root },
  )

  return (
    <div ref={root} className="min-h-[100dvh] bg-bg text-ink">
      <Nav />
      <main id="main">
        <section className="mx-auto max-w-7xl px-5 pt-20 md:px-10 md:pt-24">
          <h1 className="max-w-[23ch] text-5xl leading-[1.04] font-extralight tracking-[-0.035em] md:text-7xl">
            <Words text={hero.title} />
          </h1>
          <div className="mt-14 grid gap-12 lg:grid-cols-[1fr_1.7fr]">
            <div>
              <p className="hero-fade max-w-[40ch] text-lg leading-relaxed text-muted">{hero.sub}</p>
              <div className="hero-fade mt-10 flex flex-wrap gap-3">
                <a href="#scan" className={btnPrimary}>{hero.primary} <ArrowRightIcon weight="light" className="size-4" /></a>
                <a href="#report" className={btnGhost}>{hero.secondary}</a>
              </div>
            </div>
            <div className="hero-fade">
              <Asset name="hero-product.png" eager ratio="2400 / 1373" label="Browser window: a site with the Walkthru side panel open mid-run" />
              <AgentPresence activity="Watching the flow" state="observing" className="mt-5 justify-end sm:flex" phase={0.08} />
            </div>
          </div>
        </section>

        <section id="how" className="mx-auto grid max-w-7xl scroll-mt-16 gap-16 px-5 py-32 md:px-10 lg:grid-cols-[1.3fr_1fr]">
          <div>
            <h2 className={`${h2} reveal`}>Your browser clicks. Our agent thinks.</h2>
            <ol className="timeline relative mt-16 max-w-3xl space-y-14 pl-12">
              <span className="time-line absolute top-2 left-[11px] h-[calc(100%-1rem)] w-px origin-top bg-ink/40" aria-hidden />
              {steps.map((s) => (
                <li key={s.title} className="reveal relative">
                  <span className="absolute top-0 -left-12 grid size-6 place-items-center rounded-full border border-line bg-bg">
                    <s.icon weight="light" className="size-3.5 text-accent" />
                  </span>
                  <h3 className="text-xl font-light">{s.title}</h3>
                  <p className="mt-2 max-w-[56ch] leading-relaxed text-muted">{s.body}</p>
                </li>
              ))}
            </ol>
          </div>
          <div className="reveal lg:sticky lg:top-28 lg:self-start">
            <Asset name="agent-eye.jpg" ratio="3 / 2" label="Close-up of an eye with desktop icons floating over it" />
          </div>
        </section>

        {/* Full-bleed band: breaks the run of split sections. The photo fades into the page on the left for the quote. */}
        <section className="relative isolate overflow-hidden border-y border-line bg-surface">
          <img src="/assets/reading.jpg" alt="" loading="lazy" className="absolute inset-y-0 right-0 -z-10 h-full w-full object-cover object-[70%_40%] md:w-3/5" />
          <div className="absolute inset-0 -z-10 bg-gradient-to-r from-surface via-surface/95 to-surface/10 md:via-surface/80" />
          <figure className="reveal mx-auto max-w-7xl px-5 py-32 md:px-10 md:py-40">
            <blockquote className="max-w-[18ch] text-3xl leading-snug font-extralight tracking-tight md:text-5xl">&ldquo;{run[3].thought}&rdquo;</blockquote>
            <figcaption className="mt-8 text-sm text-muted">The busy owner, trying to sign up on a sample invoicing app</figcaption>
          </figure>
        </section>

        <section id="report" className="mx-auto grid max-w-7xl scroll-mt-16 gap-16 px-5 py-32 md:px-10 lg:grid-cols-[1fr_1.4fr]">
          <div className="lg:sticky lg:top-28 lg:self-start">
            <h2 className={`${h2} reveal`}>One report. Everything a first visitor would tell you.</h2>
            <ul className="reveal mt-10 space-y-6">
              {reportParts.map((r) => (
                <li key={r.title} className="border-t border-line pt-5">
                  <h3 className="font-light">{r.title}</h3>
                  <p className="mt-1 text-sm leading-relaxed text-muted">{r.body}</p>
                </li>
              ))}
            </ul>
          </div>
          <div className="space-y-8">
            {reportParts.map((r) => (
              <div key={r.img} className="reveal">
                <Asset name={r.img} label={`${r.title} from the report`} />
              </div>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-7xl border-t border-line px-5 py-32 md:px-10">
          <h2 className={`${h2} reveal`}>Different people get stuck in different places.</h2>
          <p className={`${lead} reveal`}>Each test user acts like a real kind of visitor.</p>
          <div className="mt-14 grid gap-10 sm:grid-cols-2 lg:grid-cols-5">
            {personas.map((p) => (
              <article key={p.name} className="reveal">
                <Asset name={p.img} ratio="3 / 4" label={`Portrait: ${p.name.toLowerCase()}`} className="grayscale" />
                <h3 className="mt-5 font-light">{p.name}</h3>
                <p className="mt-1 text-sm text-muted">{p.catches}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="border-y border-line bg-surface">
          <div className="mx-auto max-w-7xl px-5 py-20 md:px-10">
            <h2 className={`${h2} reveal`}>Tests your dashboard without your password.</h2>
            <div className="mt-12 grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
              {safety.map((s) => (
                <div key={s.title} className="reveal">
                  <s.icon weight="light" className="size-6 text-accent" />
                  <h3 className="mt-4 font-light">{s.title}</h3>
                  <p className="mt-1 text-sm leading-relaxed text-muted">{s.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <Pricing />
        <Faq />
        <Closing />
      </main>
      <Footer />
    </div>
  )
}
