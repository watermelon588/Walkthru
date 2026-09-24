import { SparkleIcon } from '@phosphor-icons/react'
import { useState } from 'react'
import { copyText } from '../lib/clipboard'
import type { Report } from '../lib/runs'

type Geo = NonNullable<Report['geo']>

const BAND: Record<Geo['band'], { label: string; tone: string }> = {
  critical: { label: 'Critical', tone: 'text-danger' },
  foundation: { label: 'Needs a foundation', tone: 'text-ink' },
  good: { label: 'Good', tone: 'text-accent' },
  excellent: { label: 'Excellent', tone: 'text-accent' },
}

/** AI search readiness (GEO): can ChatGPT, Claude, Perplexity and Google's AI answers read and quote the site? */
export function GeoReadiness({ geo }: { geo: Geo }) {
  const band = BAND[geo.band]
  return (
    <section aria-labelledby="geo-title" className="report-print-section mt-12">
      <div className="mt-2 grid gap-6 border-y border-line py-5 md:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
        <div>
          <h2 id="geo-title" className="text-xl font-light tracking-tight flex items-center gap-2">
            <SparkleIcon weight="light" className="size-5 shrink-0 text-accent" aria-hidden />AI search readiness</h2>
          <p className="mt-3 flex items-baseline gap-3">
            <span className="text-5xl font-extralight tracking-[-0.03em]">{geo.score}</span>
            <span className="text-sm text-muted">of 100</span>
            <span className={`text-sm font-medium ${band.tone}`}>{band.label}</span>
          </p>
          <p className="mt-3 max-w-[48ch] text-sm leading-relaxed text-muted">
            Readiness, not rankings: whether assistants can fetch, understand and quote your pages. Fixes are in the findings below, marked GEO.
          </p>
        </div>
        <dl className="grid content-start gap-3">
          {geo.categories.map((c) => (
            <div key={c.id} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-1 text-sm">
              <dt>{c.label}</dt>
              <dd className="font-mono text-xs text-muted">{c.earned}/{c.max}</dd>
              <dd className="col-span-2 h-1 overflow-hidden rounded-full bg-line" aria-hidden="true">
                <div className="h-full rounded-full bg-ink" style={{ width: `${Math.round((100 * c.earned) / c.max)}%` }} />
              </dd>
            </div>
          ))}
        </dl>
      </div>

      <figure className="mt-5 rounded-2xl border border-line px-5 py-4">
        <figcaption className="text-xs text-muted">
          What AI search sees on your homepage, before JavaScript runs: {geo.ai_words} word{geo.ai_words === 1 ? '' : 's'}
        </figcaption>
        <blockquote className="mt-2 max-w-[72ch] font-mono text-sm leading-relaxed">
          {geo.ai_view ? `${geo.ai_view}${geo.ai_words > 60 ? ' ...' : ''}` : 'Nothing. The page is empty until JavaScript runs, and most AI crawlers do not run it.'}
        </blockquote>
      </figure>

      {(geo.fixes?.length ?? 0) > 0 && <FixPack fixes={geo.fixes ?? []} total={geo.fixes_total ?? 0} />}

      {geo.notes.length > 0 && (
        <ul className="mt-4 grid gap-1 text-xs leading-relaxed text-muted">
          {geo.notes.map((n) => <li key={n}>{n}</li>)}
        </ul>
      )}
    </section>
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
