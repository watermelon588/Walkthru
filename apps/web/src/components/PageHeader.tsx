import type { ReactNode } from 'react'

/** The Settings page header, shared by the other workspace pages so they read as one set. */
export function PageHeader({ kicker, title, children, aside }: { kicker: string; title: string; children: ReactNode; aside?: ReactNode }) {
  return (
    <header className="grid gap-6 border-b border-line pb-10 sm:grid-cols-[1fr_auto] sm:items-end">
      <div>
        <p className="font-mono text-xs uppercase tracking-[0.16em] text-accent">{kicker}</p>
        <h1 className="mt-3 text-4xl font-extralight tracking-tight md:text-5xl">{title}</h1>
        <p className="mt-4 max-w-[58ch] leading-relaxed text-muted">{children}</p>
      </div>
      {aside}
    </header>
  )
}

/** The locked state for a feature outside the caller's plan. */
export function Locked({ children }: { children: ReactNode }) {
  return (
    <div className="mt-14 rounded-2xl border border-line px-5 py-5">
      <p className="text-sm text-ink">{children}</p>
      <p className="mt-1 text-sm text-muted"><a href="/#pricing" className="text-ink underline decoration-line underline-offset-4 hover:decoration-ink">See the plans</a></p>
    </div>
  )
}
