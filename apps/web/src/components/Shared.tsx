import { ListIcon, PlusIcon, XIcon } from '@phosphor-icons/react'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { useRef, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'
import { brand } from '../brand'
import { faqs, footer, hero, navLinks, plans } from '../content'

export const btnPrimary =
  'inline-flex items-center gap-2 rounded-full bg-ink px-6 py-3 text-sm whitespace-nowrap text-bg transition hover:opacity-85 active:scale-[0.98]'
export const btnGhost =
  'inline-flex items-center gap-2 rounded-full border border-line px-6 py-3 text-sm whitespace-nowrap text-ink transition hover:bg-surface active:scale-[0.98]'
export const h2 = 'text-3xl font-light tracking-tight md:text-5xl'
export const lead = 'mt-5 max-w-[58ch] leading-relaxed text-muted'

/**
 * Image from public/assets. Photos (.jpg) are cropped to `ratio`. Screenshots (.png) keep their natural shape,
 * get a small radius matching the mock window corners and a soft ink-tinted shadow.
 * Until a file exists it renders a labelled slot so layout stays true.
 */
export function Asset({ name, label, ratio, className = '', quiet = false, eager = false }: { name: string; label: string; ratio?: string; className?: string; quiet?: boolean; eager?: boolean }) {
  const [missing, setMissing] = useState(false)
  const shot = name.endsWith('.png')
  if (missing)
    return (
      <div style={{ aspectRatio: ratio ?? '16 / 10' }} className={`grid place-items-center rounded-2xl border border-dashed border-line bg-surface p-6 text-center ${className}`}>
        <div className={quiet ? 'sr-only' : ''}>
          <p className="font-mono text-xs text-muted">public/assets/{name}</p>
          <p className="mt-2 max-w-[34ch] text-sm text-muted">{label}</p>
        </div>
      </div>
    )
  return (
    <img
      src={`/assets/${name}`}
      alt={label}
      loading={eager ? 'eager' : 'lazy'}
      onError={() => setMissing(true)}
      onLoad={() => ScrollTrigger.refresh()}
      style={ratio ? { aspectRatio: ratio } : undefined}
      className={`w-full ${shot ? 'h-auto rounded-lg shadow-[0_30px_70px_-40px_rgba(27,27,31,0.35)]' : 'rounded-2xl object-cover'} ${className}`}
    />
  )
}

/** Headline split into words so GSAP can lift them in one by one (.word). */
export function Words({ text }: { text: string }) {
  return (
    <>
      {text.split(' ').map((w, i) => (
        <span key={i} className="inline-block overflow-hidden pb-[0.12em] align-bottom">
          <span className="word inline-block">{w}&nbsp;</span>
        </span>
      ))}
    </>
  )
}

/** Brand mark, optionally with the name. Everything comes from src/brand.ts. */
export function Logo({ withName = true, className = '' }: { withName?: boolean; className?: string }) {
  return (
    <a href="/" aria-label={`${brand.name} home`} className={`flex items-center gap-2.5 text-[15px] tracking-tight text-ink ${className}`}>
      <img src={brand.mark} alt="" width={32} height={32} className="size-8" />
      {withName && <span>{brand.name}</span>}
    </a>
  )
}

/** First focusable element on every page: jumps keyboard users past the navigation. */
export function SkipLink() {
  return (
    <a href="#main" className="sr-only z-50 rounded-full bg-ink px-4 py-2 text-sm text-bg focus:not-sr-only focus:fixed focus:top-3 focus:left-3">
      Skip to content
    </a>
  )
}

/** Signed in? Reads Supabase's saved session key directly, so marketing pages need not load the Supabase library. */
function hasSession(): boolean {
  try {
    const url = import.meta.env.VITE_SUPABASE_URL as string | undefined
    return !!url && !!localStorage.getItem(`sb-${new URL(url).hostname.split('.')[0]}-auth-token`)
  } catch {
    return false
  }
}

export function Nav() {
  const menu = useRef<HTMLDetailsElement>(null)
  const [account] = useState(() => (hasSession() ? { label: 'Dashboard', href: '/app' } : { label: 'Sign in', href: '/login' }))
  const close = () => menu.current?.removeAttribute('open')
  return (
    <header className="sticky top-0 z-20 border-b border-line/70 bg-bg/80 backdrop-blur-md">
      <SkipLink />
      <nav className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5 md:px-10" aria-label="Main">
        <Logo withName={false} />
        <div className="hidden items-center gap-9 text-sm text-muted md:flex">
          {navLinks.map((l) => <a key={l.href} href={l.href} className="transition hover:text-ink">{l.label}</a>)}
        </div>
        <div className="flex items-center gap-3 sm:gap-5">
          <a href={account.href} className="hidden text-sm text-ink transition hover:opacity-70 sm:block">{account.label}</a>
          <a href="/#scan" className={btnPrimary.replace('px-6 py-3', 'px-5 py-2.5')}>{hero.primary}</a>
          <details ref={menu} className="group md:hidden">
            <summary aria-label="Menu" className="grid size-10 cursor-pointer list-none place-items-center rounded-full border border-line transition hover:bg-surface [&::-webkit-details-marker]:hidden">
              <ListIcon weight="light" className="size-4 group-open:hidden" />
              <XIcon weight="light" className="hidden size-4 group-open:block" />
            </summary>
            <div onClick={close} className="absolute inset-x-0 top-16 border-y border-line bg-bg px-5 pb-6 shadow-[0_24px_40px_-32px_rgba(27,27,31,0.4)]">
              <ul className="grid text-lg font-light">
                {[...navLinks, account].map((l) => (
                  <li key={l.href} className="border-b border-line last:border-b-0">
                    <a href={l.href} className="flex min-h-12 items-center py-2 text-ink">{l.label}</a>
                  </li>
                ))}
              </ul>
            </div>
          </details>
        </div>
      </nav>
    </header>
  )
}

export function Pricing() {
  return (
    <section id="pricing" className="mx-auto max-w-7xl scroll-mt-16 px-5 py-28 md:px-10">
      <h2 className={`${h2} reveal`}>Free to start. Pay when you test the real product.</h2>
      <div className="reveal mt-14 grid gap-px overflow-hidden rounded-2xl border border-line bg-line md:grid-cols-2 lg:grid-cols-4">
        {plans.map((p) => (
          <div key={p.name} className="flex flex-col bg-bg p-8">
            <div className="flex items-baseline justify-between">
              <h3 className="text-sm text-ink">{p.name}</h3>
              {p.highlight && <span className="text-xs text-accent">Most picked</span>}
            </div>
            <p className="mt-6 text-5xl font-extralight tracking-tight text-ink">{p.price}</p>
            <p className="mt-1 text-sm text-muted">{p.per}</p>
            <ul className="mt-8 flex-1 space-y-3 text-sm text-muted">
              {p.features.map((f) => <li key={f}>{f}</li>)}
            </ul>
            <a href="#scan" className={`mt-10 self-start ${p.highlight ? btnPrimary : btnGhost}`}>{p.cta}</a>
          </div>
        ))}
      </div>
    </section>
  )
}

export function Faq() {
  return (
    <section id="faq" className="mx-auto grid max-w-7xl scroll-mt-16 gap-12 px-5 pb-28 md:px-10 lg:grid-cols-[1fr_2fr]">
      <h2 className={`${h2} reveal`}>Questions</h2>
      <div className="reveal border-t border-line">
        {faqs.map((f) => (
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
  )
}

/** Front end only: validates, then confirms. Wired to the Instant Scan API in task T11. */
export function ScanForm() {
  const navigate = useNavigate()
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const data = new FormData(e.currentTarget)
    const raw = String(data.get('url')).trim()
    let site: string
    try {
      const u = new URL(raw.startsWith('http') ? raw : `https://${raw}`)
      if (!u.hostname.includes('.') && !u.hostname.startsWith('127.')) throw new Error()
      site = u.href
    } catch {
      setError('Enter a full website address, like yoursite.com')
      return
    }
    setError('')
    setBusy(true)
    try {
      // Loaded on submit so the landing page does not ship the Supabase client.
      const { instantScan } = await import('../lib/runs')
      const { run_id } = await instantScan(site)
      navigate(`/r/${run_id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The scan failed. Try again in a minute.')
      setBusy(false)
    }
  }

  const input = 'w-full rounded-xl border border-line bg-bg px-4 py-3 text-sm text-ink placeholder:text-muted focus:border-ink focus:outline-none disabled:opacity-60'
  return (
    <form onSubmit={submit} noValidate aria-busy={busy} className="grid gap-4 sm:grid-cols-[1fr_auto] sm:items-end">
      <div className="grid gap-2">
        <label htmlFor="url" className="text-sm text-muted">Website</label>
        <input id="url" name="url" type="text" inputMode="url" placeholder="yoursite.com" disabled={busy} className={input} aria-invalid={!!error} aria-describedby="url-error" />
      </div>
      <button type="submit" disabled={busy} className={`${btnPrimary} disabled:opacity-60`}>{busy ? 'Scanning...' : hero.primary}</button>
      <p id="url-error" role="status" className="min-h-5 text-sm sm:col-span-2">
        {error ? <span className="text-danger">{error}</span> : busy ? <span className="text-muted">Reading your pages, checking SEO, AI search and security, writing the report. About 20 seconds.</span> : ''}
      </p>
    </form>
  )
}

export function Closing({ title = 'Your next visitor is a stranger. Test like one.' }: { title?: string }) {
  return (
    <section id="scan" className="scroll-mt-16 border-t border-line bg-surface">
      <div className="mx-auto grid max-w-7xl items-center gap-14 px-5 py-28 md:px-10 lg:grid-cols-[0.8fr_1.2fr]">
        <div className="reveal">
          <Asset name="workspace.jpg" ratio="4 / 5" label="Someone working by a window" />
        </div>
        <div>
          <h2 className={`${h2} reveal max-w-[18ch]`}>{title}</h2>
          <p className={`${lead} reveal`}>Start with a free Instant Scan. No install, about 20 seconds.</p>
          <div className="reveal mt-12">
            <ScanForm />
          </div>
        </div>
      </div>
    </section>
  )
}

export function Footer() {
  return (
    <footer className="border-t border-line">
      <div className="mx-auto grid max-w-7xl gap-12 px-5 pt-16 pb-10 md:px-10 lg:grid-cols-[1.4fr_1fr_1fr_1fr]">
        <div>
          <Logo />
          <p className="mt-5 text-sm text-ink">{brand.tagline}</p>
          <p className="mt-3 max-w-[42ch] text-sm leading-relaxed text-muted">{brand.description}</p>
          <p className="mt-5 text-sm text-ink">The Chrome extension is in beta. Install it from the docs.</p>
        </div>
        {footer.columns.map((c) => (
          <nav key={c.title} aria-label={c.title}>
            <h2 className="text-sm text-ink">{c.title}</h2>
            <ul className="mt-5 space-y-3 text-sm text-muted">
              {c.links.map((l) => (
                <li key={l.label}><a href={l.href} className="transition hover:text-ink">{l.label}</a></li>
              ))}
            </ul>
          </nav>
        ))}
      </div>
      <div className="mx-auto flex max-w-7xl flex-col justify-between gap-3 border-t border-line px-5 py-6 text-xs text-muted sm:flex-row md:px-10">
        <p>© {brand.year} {brand.name}</p>
        <p>Test users are AI. Findings are suggestions, not guarantees.</p>
      </div>
    </footer>
  )
}
