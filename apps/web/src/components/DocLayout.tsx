import { CaretDownIcon } from '@phosphor-icons/react'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { brand } from '../brand'
import { useReveal } from '../lib/motion'
import { Footer, Nav, Words } from './Shared'

export type DocSection = { id: string; title: string; body: ReactNode }

/** Long-form reading page: docs, privacy, terms, security. Title, lead, an "On this page" index and prose sections. */
export function DocLayout({ title, lead, updated, sections }: { title: string; lead: string; updated?: string; sections: DocSection[] }) {
  const root = useRef<HTMLDivElement>(null)
  const [active, setActive] = useState(sections[0]?.id)
  useReveal(root)

  // Highlight the section being read. The band sits in the upper third of the viewport.
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => entries.forEach((e) => e.isIntersecting && setActive(e.target.id)),
      { rootMargin: '-15% 0px -70% 0px' },
    )
    sections.forEach((s) => { const el = document.getElementById(s.id); if (el) observer.observe(el) })
    return () => observer.disconnect()
  }, [sections])

  const links = (onPick?: (e: React.MouseEvent<HTMLAnchorElement>) => void) => (
    <ol className="grid border-l border-line text-sm">
      {sections.map((s) => (
        <li key={s.id}>
          <a
            href={`#${s.id}`}
            onClick={onPick}
            aria-current={active === s.id ? 'location' : undefined}
            className={`-ml-px flex min-h-9 items-center border-l py-1 pl-4 transition-colors ${active === s.id ? 'border-ink text-ink' : 'border-transparent text-muted hover:text-ink'}`}
          >
            {s.title}
          </a>
        </li>
      ))}
    </ol>
  )

  return (
    <div ref={root} className="min-h-[100dvh] bg-bg text-ink">
      <title>{`${title} · ${brand.name}`}</title>
      <Nav />
      <main id="main" className="mx-auto max-w-7xl px-5 pt-16 pb-28 md:px-10 md:pt-24">
        <header className="max-w-3xl">
          <h1 className="text-4xl leading-[1.05] font-extralight tracking-[-0.035em] md:text-6xl"><Words text={title} /></h1>
          <p className="hero-fade mt-6 max-w-[58ch] text-lg leading-relaxed text-muted">{lead}</p>
          {updated && (
            <p className="hero-fade mt-6 text-sm text-muted">
              Last updated <time dateTime={updated}>{new Date(`${updated}T00:00:00`).toLocaleDateString('en', { day: 'numeric', month: 'long', year: 'numeric' })}</time>
            </p>
          )}
        </header>

        <div className="mt-12 grid gap-10 border-t border-line pt-10 md:mt-16 lg:grid-cols-[14rem_minmax(0,1fr)] lg:gap-20 lg:pt-14">
          <nav aria-label="On this page" className="lg:sticky lg:top-28 lg:self-start">
            <details className="group rounded-2xl border border-line px-5 lg:hidden">
              <summary className="flex min-h-12 cursor-pointer list-none items-center justify-between text-sm text-ink [&::-webkit-details-marker]:hidden">
                On this page
                <CaretDownIcon weight="light" className="size-4 text-muted transition group-open:rotate-180 motion-reduce:transition-none" />
              </summary>
              <div className="pb-4">{links((e) => e.currentTarget.closest('details')?.removeAttribute('open'))}</div>
            </details>
            <div className="hidden lg:block">
              <p className="mb-4 text-sm text-ink">On this page</p>
              {links()}
            </div>
          </nav>

          <div className="prose-doc max-w-[68ch]">
            {sections.map((s) => (
              <section key={s.id} id={s.id} aria-labelledby={`${s.id}-title`}>
                <h2 id={`${s.id}-title`}>{s.title}</h2>
                {s.body}
              </section>
            ))}
          </div>
        </div>
      </main>
      <Footer />
    </div>
  )
}
