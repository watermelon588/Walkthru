import { CaretDownIcon, SparkleIcon } from '@phosphor-icons/react'
import { useState } from 'react'
import { copyText } from '../lib/clipboard'
import type { Finding, Report } from '../lib/runs'
import { Card, Pill, type Tone } from './Card'

type Geo = NonNullable<Report['geo']>

const BAND: Record<Geo['band'], { label: string; tone: string }> = {
  critical: { label: 'Critical', tone: 'text-danger' },
  foundation: { label: 'Needs a foundation', tone: 'text-ink' },
  good: { label: 'Good', tone: 'text-accent' },
  excellent: { label: 'Excellent', tone: 'text-accent' },
}

/** AI search readiness (GEO): can ChatGPT, Claude, Perplexity and Google's AI answers read and quote the site? */
export function GeoReadiness({ geo, findings }: { geo: Geo; findings: Finding[] }) {
  const band = BAND[geo.band]
  return (
    <Card className="report-print-section mt-10 p-6" aria-labelledby="geo-title">
      <div className="flex flex-wrap items-baseline justify-between gap-4">
        <h2 id="geo-title" className="flex items-center gap-2 font-medium">
          <SparkleIcon weight="light" className="size-5 shrink-0 text-accent" aria-hidden />AI search readiness
        </h2>
        <span className="text-xs text-muted">Can ChatGPT, Claude, Perplexity and Google AI read and quote you</span>
      </div>
      <div className="mt-5 flex gap-10">
        <div>
          <p className={`text-4xl leading-none font-extralight tracking-[-0.02em] tabular-nums ${band.tone}`}>{geo.score}</p>
          <p className="mt-2 text-xs text-muted">{band.label}, of 100</p>
        </div>
        <div>
          <p className={`text-4xl leading-none font-extralight tracking-[-0.02em] tabular-nums ${findings.length ? 'text-danger' : 'text-accent'}`}>{findings.length}</p>
          <p className="mt-2 text-xs text-muted">{findings.length === 1 ? 'Issue to fix' : 'Issues to fix'}</p>
        </div>
      </div>

      <ul className="mt-4">
        {geo.categories.map((c) => {
          const tone: Tone = c.earned >= c.max ? 'ok' : c.earned === 0 ? 'bad' : 'neutral'
          return (
            <li key={c.id} className="flex items-center justify-between gap-4 border-b border-line py-3">
              <span className="text-sm">{c.label}</span>
              <Pill tone={tone}>{c.earned} of {c.max} points</Pill>
            </li>
          )
        })}
        {findings.map((f) => (
          <li key={f.title} className="border-b border-line last:border-b-0">
            <details className="group">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 py-3 [&::-webkit-details-marker]:hidden">
                <span className="min-w-0 text-sm">{f.title}</span>
                <span className="flex items-center gap-2">
                  <Pill tone={f.severity === 'high' ? 'bad' : 'neutral'}>{f.severity === 'high' ? 'High' : f.severity === 'medium' ? 'Medium' : 'Low'}</Pill>
                  <CaretDownIcon weight="bold" className="size-3 text-muted transition-transform group-open:rotate-180 motion-reduce:transition-none" aria-hidden />
                </span>
              </summary>
              <div className="pb-4 text-sm leading-relaxed">
                <p className="text-muted">{f.detail}</p>
                <p className="mt-1"><span className="text-muted">Fix: </span>{f.fix}</p>
              </div>
            </details>
          </li>
        ))}
      </ul>

      <figure className="mt-5 rounded-xl bg-surface px-4 py-3">
        <figcaption className="text-xs text-muted">
          What AI search sees on your homepage before JavaScript runs: {geo.ai_words} word{geo.ai_words === 1 ? '' : 's'}
        </figcaption>
        <blockquote className="mt-2 max-w-[72ch] font-mono text-xs leading-relaxed text-ink">
          {geo.ai_view ? `${geo.ai_view}${geo.ai_words > 60 ? ' ...' : ''}` : 'Nothing. The page is empty until JavaScript runs, and most AI crawlers do not run it.'}
        </blockquote>
      </figure>

      {(geo.fixes?.length ?? 0) > 0 && <FixPack fixes={geo.fixes ?? []} total={geo.fixes_total ?? 0} />}

      {geo.notes.length > 0 && (
        <ul className="mt-4 grid gap-1 text-xs leading-relaxed text-muted">
          {geo.notes.map((n) => <li key={n}>{n}</li>)}
        </ul>
      )}
    </Card>
  )
}

type Fix = NonNullable<Geo['fixes']>[number]

/** Copy-paste fixes built from the site's own pages. Free reports show one, paid reports all of them. */
function FixPack({ fixes, total }: { fixes: Fix[]; total: number }) {
  const [copied, setCopied] = useState<string | null>(null)
  return (
    <div className="mt-6">
      <h3 className="text-sm font-medium">GEO fix pack</h3>
      <ol className="mt-3 grid gap-4">
        {fixes.map((fix) => (
          <li key={fix.id} className="rounded-2xl border border-line px-4 py-4">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <p className="text-sm font-medium">{fix.title}</p>
              <span className="font-mono text-xs text-muted">{fix.file}</span>
            </div>
            <p className="mt-1 text-xs leading-relaxed text-muted">{fix.note}</p>
            <pre className="mt-3 max-h-64 overflow-auto rounded-xl bg-surface px-3 py-2 font-mono text-xs leading-relaxed"><code>{fix.code}</code></pre>
            <button
              type="button"
              className="no-print mt-2 text-xs text-muted underline decoration-line underline-offset-4 transition hover:text-ink hover:decoration-ink"
              onClick={async () => setCopied((await copyText(fix.code)) ? fix.id : null)}
            >
              {copied === fix.id ? 'Copied' : 'Copy'}
            </button>
          </li>
        ))}
      </ol>
      {total > fixes.length && (
        <p className="mt-3 text-xs text-muted">{total - fixes.length} more ready-made fix{total - fixes.length === 1 ? '' : 'es'} for this site on Pro.</p>
      )}
    </div>
  )
}
