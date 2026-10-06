// /variants: three alternative home pages to compare, with a floating switcher. Preview only; the live home page
// (pages/Landing.tsx) is untouched. Remove this folder, public/variants and the one route in App.tsx to revoke.
import { lazy, Suspense, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router'
import { Preloader } from '../components/preloader/Preloader'

const looks = [
  { id: 'fresh', name: 'Fresh Eyes', page: lazy(() => import('./FreshEyes')) },
  { id: 'darkroom', name: 'Darkroom', page: lazy(() => import('./Darkroom')) },
  { id: 'markup', name: 'Markup', page: lazy(() => import('./Markup')) },
] as const

export default function Variants() {
  const [params, setParams] = useSearchParams()
  const look = looks.find((l) => l.id === params.get('v')) ?? looks[0]
  const Page = look.page
  useEffect(() => { window.scrollTo(0, 0); document.title = `${look.name} · Walkthru home variant` }, [look])
  return (
    <>
      <Suspense fallback={<Preloader />}>
        <Page key={look.id} />
      </Suspense>
      <nav aria-label="Home page variants" className="fixed bottom-[max(1rem,env(safe-area-inset-bottom))] left-1/2 z-[70] flex -translate-x-1/2 items-center gap-1 rounded-full border border-white/15 bg-[#121214]/85 p-1 text-[13px] text-white/70 shadow-[0_18px_40px_-16px_rgba(0,0,0,0.6)] backdrop-blur-xl">
        <Link to="/" className="rounded-full px-3.5 py-2 transition-colors hover:text-white">Current</Link>
        <span aria-hidden className="mx-0.5 h-4 w-px bg-white/15" />
        {looks.map((l, i) => (
          <button
            key={l.id}
            type="button"
            aria-pressed={l.id === look.id}
            onClick={() => setParams({ v: l.id })}
            className={`rounded-full px-3.5 py-2 whitespace-nowrap transition-[background-color,color,scale] duration-200 active:scale-[0.96] ${l.id === look.id ? 'bg-white text-[#121214]' : 'hover:text-white'}`}
          >
            <span className="font-mono text-[11px] sm:opacity-50">{i + 1}</span><span className="max-sm:sr-only"> {l.name}</span>
          </button>
        ))}
      </nav>
    </>
  )
}
