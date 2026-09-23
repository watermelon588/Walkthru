import { ArrowRightIcon } from '@phosphor-icons/react'
import { useRef } from 'react'
import { useLocation } from 'react-router'
import { brand } from '../brand'
import { AgentPresence } from '../components/AgentPresence'
import { btnGhost, btnPrimary, Footer, Nav, Words } from '../components/Shared'
import { useReveal } from '../lib/motion'

export default function NotFound() {
  const root = useRef<HTMLDivElement>(null)
  const { pathname } = useLocation()
  useReveal(root)
  return (
    <div ref={root} className="flex min-h-[100dvh] flex-col bg-bg text-ink">
      <title>{`Page not found · ${brand.name}`}</title>
      <Nav />
      <main id="main" className="mx-auto flex w-full max-w-7xl flex-1 flex-col justify-center px-5 py-24 md:px-10">
        <AgentPresence activity="Could not find this page" state="stopped" className="hero-fade mb-10" phase={0.4} />
        <h1 className="max-w-[16ch] text-5xl leading-[1.04] font-extralight tracking-[-0.035em] md:text-7xl">
          <Words text="A stranger would get stuck here." />
        </h1>
        <p className="hero-fade mt-6 max-w-[52ch] text-lg leading-relaxed text-muted">
          There is nothing at <span className="font-mono text-base break-all text-ink">{pathname}</span>. The link may be old, or the report may have been deleted.
        </p>
        <div className="hero-fade mt-10 flex flex-wrap gap-3">
          <a href="/" className={btnPrimary}>Back to home <ArrowRightIcon weight="light" className="size-4" /></a>
          <a href="/docs" className={btnGhost}>Read the docs</a>
        </div>
      </main>
      <Footer />
    </div>
  )
}
