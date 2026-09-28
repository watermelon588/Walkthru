import { useGSAP } from '@gsap/react'
import { ArrowRightIcon, CheckIcon, LockSimpleIcon, MinusIcon, PaperPlaneTiltIcon, PlusIcon, ReceiptIcon, SealCheckIcon } from '@phosphor-icons/react'
import gsap from 'gsap'
import { Fragment, useRef } from 'react'
import { brand } from '../brand'
import { Orb, Skeleton } from '../components/Loading'
import { btnGhost, btnPrimary, Footer, h2, lead, Nav, Words } from '../components/Shared'
import { billingFaqs, planMatrix, plans } from '../content'
import { useReveal } from '../lib/motion'

const flow = [
  { icon: PaperPlaneTiltIcon, title: 'Request a plan', body: 'Pick a plan in your dashboard and say what you are testing.' },
  { icon: SealCheckIcon, title: 'Get a private offer', body: 'We confirm your spot and send an offer that holds for 24 hours.' },
  { icon: ReceiptIcon, title: 'Pay once', body: 'One payment for 30 days. It never renews on its own.' },
]

/** /pricing: the four plans, what each includes, and how paying works until online checkout opens at launch. */
export default function Pricing() {
  const root = useRef<HTMLDivElement>(null)
  useReveal(root)
  useGSAP(() => {
    gsap.matchMedia().add('(prefers-reduced-motion: no-preference)', () => {
      gsap.from('.plan-card', { y: 60, rotateX: -12, autoAlpha: 0, transformPerspective: 900, transformOrigin: '50% 100%', duration: 1.3, ease: 'expo.out', stagger: 0.09, delay: 0.5 })
      gsap.to('.pricing-orb', { yPercent: 35, ease: 'none', scrollTrigger: { trigger: '.pricing-hero', start: 'top top', end: 'bottom top', scrub: true } })
      gsap.from('.matrix-row', { x: -16, autoAlpha: 0, duration: 0.8, ease: 'expo.out', stagger: 0.03, scrollTrigger: { trigger: '.matrix', start: 'top 80%' } })
    })
  }, { scope: root })

  return (
    <div ref={root} className="min-h-[100dvh] bg-bg text-ink">
      <title>{`Pricing · ${brand.name}`}</title>
      <Nav />
      <main id="main">
        <section className="pricing-hero relative isolate overflow-hidden">
          <div aria-hidden className="pricing-orb pointer-events-none absolute inset-x-0 -top-10 -z-10 flex justify-center opacity-20">
            <Orb size={560} state="breathing" speed={0.5} className="max-md:scale-[0.7]" />
          </div>
          <div aria-hidden className="pointer-events-none absolute top-24 -left-24 -z-10 hidden opacity-25 lg:block"><Orb size={300} state="weaving" speed={0.6} /></div>
          <div aria-hidden className="pointer-events-none absolute top-40 -right-20 -z-10 hidden opacity-25 lg:block"><Orb size={260} state="connecting" speed={0.6} /></div>
          <div className="mx-auto max-w-7xl px-5 pt-20 pb-16 text-center md:px-10 md:pt-28">
            <p className="hero-fade mx-auto inline-flex items-center gap-2 rounded-full border border-line bg-bg/70 px-4 py-1.5 text-xs text-muted backdrop-blur">
              <span className="size-1.5 rounded-full bg-accent" aria-hidden /> Online checkout opens at launch
            </p>
            <h1 className="mx-auto mt-8 max-w-[18ch] text-5xl leading-[1.04] font-extralight tracking-[-0.035em] md:text-7xl">
              <Words text="Free to start. One pass when it counts." />
            </h1>
            <p className="hero-fade mx-auto mt-6 max-w-[52ch] text-lg leading-relaxed text-muted">
              Scan any homepage for free. Buy 30 days of AI test users when you are testing the real product. Nothing renews on its own.
            </p>
          </div>
        </section>

        <section aria-label="Plans" className="mx-auto max-w-7xl px-5 md:px-10">
          <div className="grid gap-4 [perspective:1200px] md:grid-cols-2 lg:grid-cols-4">
            {plans.map((p) => {
              const dark = !!p.highlight
              return (
                <article key={p.name} className={`plan-card group relative flex flex-col overflow-hidden rounded-2xl p-7 transition-[translate,box-shadow] duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] hover:-translate-y-1.5 ${dark ? 'bg-ink text-bg shadow-[0_40px_80px_-40px_rgba(27,27,31,0.7)]' : 'border border-line bg-bg hover:shadow-[0_30px_60px_-40px_rgba(27,27,31,0.35)]'}`}>
                  {dark && <div aria-hidden className="pointer-events-none absolute -right-16 -bottom-16 opacity-30 invert"><Orb size={240} state="working" speed={0.7} /></div>}
                  <div className="flex items-baseline justify-between">
                    <h2 className="text-sm">{p.name}</h2>
                    {dark && <span className="rounded-full bg-bg/15 px-2.5 py-0.5 text-[11px]">Most picked</span>}
                  </div>
                  <p className="mt-8 text-6xl font-extralight tracking-[-0.03em]">{p.price}</p>
                  <p className={`mt-2 min-h-10 text-sm ${dark ? 'text-bg/70' : 'text-muted'}`}>{p.per}</p>
                  <ul className={`mt-6 flex-1 space-y-3 border-t pt-6 text-sm ${dark ? 'border-bg/15 text-bg/85' : 'border-line text-muted'}`}>
                    {p.features.map((f) => (
                      <li key={f} className="flex gap-2.5"><CheckIcon weight="bold" className={`mt-0.5 size-3.5 shrink-0 ${dark ? 'text-bg' : 'text-accent'}`} aria-hidden />{f}</li>
                    ))}
                  </ul>
                  <a href={'href' in p ? p.href : '/#scan'} className={`mt-8 justify-center ${dark ? 'inline-flex items-center gap-2 rounded-full bg-bg px-6 py-3 text-sm text-ink transition hover:opacity-90 active:scale-[0.98]' : 'href' in p ? btnGhost : btnPrimary}`}>
                    {p.cta} <ArrowRightIcon weight="light" className="size-4" />
                  </a>
                </article>
              )
            })}
          </div>
          <p className="reveal mt-6 text-center text-sm text-muted">Prices in US dollars. Founding prices hold for the first 50 paying customers.</p>
        </section>

        <section aria-labelledby="checkout-title" className="mx-auto mt-28 max-w-7xl px-5 md:px-10">
          <div className="reveal relative isolate grid gap-12 overflow-hidden rounded-2xl border border-line bg-surface/50 p-7 md:p-12 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
            <div>
              <h2 id="checkout-title" className={h2}>Checkout is on its way.</h2>
              <p className={lead}>
                Card payments switch on at launch, when our payment provider goes live on our own domain. Until then, paid plans open by request, so we can keep costs honest while the first customers arrive.
              </p>
              <ol className="mt-10 grid gap-6 sm:grid-cols-3">
                {flow.map((s) => (
                  <li key={s.title}>
                    <s.icon weight="light" className="size-6 text-accent" aria-hidden />
                    <h3 className="mt-3 text-sm font-medium">{s.title}</h3>
                    <p className="mt-1 text-sm leading-relaxed text-muted">{s.body}</p>
                  </li>
                ))}
              </ol>
              <a href="/app/billing" className={`${btnPrimary} mt-10`}>Request access <ArrowRightIcon weight="light" className="size-4" /></a>
            </div>

            {/* A checkout card still being built: honest placeholder, nothing here takes a payment. */}
            <div aria-hidden className="relative mx-auto w-full max-w-sm">
              <div className="pointer-events-none absolute -inset-16 -z-10 grid place-items-center opacity-50"><Orb size={420} state="shaping" speed={0.5} /></div>
              <div className="rounded-2xl border border-line bg-bg p-6 shadow-[0_40px_80px_-50px_rgba(27,27,31,0.5)]">
                <div className="flex items-center justify-between">
                  <span className="text-sm">Pro pass, 30 days</span>
                  <span className="text-sm tabular-nums">$19.00</span>
                </div>
                <div className="mt-6 grid gap-3">
                  <Skeleton className="h-11 rounded-xl" />
                  <div className="grid grid-cols-2 gap-3"><Skeleton className="h-11 rounded-xl" /><Skeleton className="h-11 rounded-xl" /></div>
                  <Skeleton className="h-11 rounded-xl" />
                </div>
                <div className="mt-6 flex h-12 items-center justify-center gap-2 rounded-full bg-ink/80 text-sm text-bg">
                  <LockSimpleIcon weight="light" className="size-4" /> Opens at launch
                </div>
              </div>
            </div>
          </div>
        </section>

        <section aria-labelledby="matrix-title" className="mx-auto mt-28 max-w-7xl px-5 md:px-10">
          <h2 id="matrix-title" className={`${h2} reveal`}>Every plan, line by line.</h2>
          <div className="matrix reveal mt-12 overflow-x-auto" role="region" aria-label="Plan comparison table" tabIndex={0}>
            <table className="w-full min-w-[46rem] border-collapse text-sm">
              <thead>
                <tr className="border-b border-ink">
                  <th scope="col" className="w-[34%] py-4 pr-4 text-left font-normal text-muted">Feature</th>
                  {plans.map((p) => (
                    <th key={p.name} scope="col" className="py-4 pr-4 text-left align-bottom font-normal">
                      <span className="block text-ink">{p.name}</span>
                      <span className="block text-xs text-muted">{p.price}</span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {planMatrix.map((g) => (
                  <Fragment key={g.group}>
                    <tr><th scope="colgroup" colSpan={5} className="pt-10 pb-3 text-left text-xs font-medium tracking-wide text-accent">{g.group}</th></tr>
                    {g.rows.map(([label, ...cells]) => (
                      <tr key={label} className="matrix-row border-b border-line transition-colors hover:bg-surface/50">
                        <th scope="row" className="py-3.5 pr-4 text-left font-normal">{label}</th>
                        {cells.map((c, i) => (
                          <td key={i} className="py-3.5 pr-4">
                            {c === true ? <CheckIcon weight="bold" className="size-4 text-ink" aria-label="Included" />
                              : c === false ? <MinusIcon weight="light" className="size-4 text-line" aria-label="Not included" />
                              : <span className="text-ink">{c}</span>}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section aria-labelledby="billing-faq" className="mx-auto mt-28 grid max-w-7xl gap-12 px-5 pb-28 md:px-10 lg:grid-cols-[1fr_2fr]">
          <h2 id="billing-faq" className={`${h2} reveal`}>Paying, plainly.</h2>
          <div className="reveal border-t border-line">
            {billingFaqs.map((f) => (
              <details key={f.q} className="group border-b border-line py-6">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-6 text-lg font-light text-ink">
                  {f.q}
                  <PlusIcon weight="light" className="size-5 shrink-0 text-muted transition duration-300 group-open:rotate-45" />
                </summary>
                <p className="mt-4 max-w-[62ch] leading-relaxed text-muted">{f.a}</p>
              </details>
            ))}
          </div>
        </section>
      </main>
      <Footer />
    </div>
  )
}
