import type { ReactNode } from 'react'

/** The report and dashboard card, matching the landing page mock-ups: a lighter surface, one hairline, no shadow. */
export function Card({ children, className = '', as: Tag = 'section', ...rest }: { children: ReactNode; className?: string; as?: 'section' | 'div' | 'aside' } & Record<string, unknown>) {
  return <Tag className={`rounded-2xl border border-line bg-card ${className}`} {...rest}>{children}</Tag>
}

export type Tone = 'ok' | 'bad' | 'neutral'
const TONE: Record<Tone, string> = {
  ok: 'bg-accent/10 text-accent',
  bad: 'bg-danger/10 text-danger',
  neutral: 'bg-surface text-muted',
}

/** A status pill ("Missing on 4 pages", "Found", "Not checked"). Tone is never the only signal: the words carry it. */
export function Pill({ tone, children }: { tone: Tone; children: ReactNode }) {
  return <span className={`inline-flex shrink-0 items-center rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap tabular-nums ${TONE[tone]}`}>{children}</span>
}
