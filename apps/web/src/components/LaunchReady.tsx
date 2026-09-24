import { GaugeIcon } from '@phosphor-icons/react'
import { useState } from 'react'
import { copyText } from '../lib/clipboard'
import { API, type Report } from '../lib/runs'

type Score = NonNullable<Report['launch_ready']>

const AREAS: { id: keyof Score['areas']; label: string; weight: number }[] = [
  { id: 'ux', label: 'Can a stranger get in', weight: 30 },
  { id: 'security', label: 'Security hygiene', weight: 20 },
  { id: 'geo', label: 'AI search readiness', weight: 20 },
  { id: 'seo', label: 'SEO', weight: 15 },
  { id: 'speed', label: 'Speed and accessibility', weight: 15 },
]

// Same bands as the badge (app/agent/score.py `band`).
function band(score: number): { label: string; tone: string } {
  if (score >= 85) return { label: 'Launch ready', tone: 'text-accent' }
  if (score >= 60) return { label: 'Almost ready', tone: 'text-ink' }
  return { label: 'Needs work', tone: 'text-danger' }
}

/** One number for the whole report, the areas behind it, and the badge for public reports. */
export function LaunchReady({ score, runId, isPublic, isScan, isOwner }: { score: Score; runId: string; isPublic: boolean; isScan: boolean; isOwner: boolean }) {
  if (score.score === null) return null
  const b = band(score.score)
  return (
    <section aria-labelledby="launch-ready-title" className="report-print-section mt-10">
      <div className="mt-2 grid gap-6 border-y border-line py-5 md:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
        <div>
          <h2 id="launch-ready-title" className="text-xl font-light tracking-tight flex items-center gap-2">
            <GaugeIcon weight="light" className="size-5 shrink-0 text-accent" aria-hidden />Launch Ready score</h2>
          <p className="mt-4 flex items-baseline gap-3">
            <span className="text-6xl leading-none font-extralight tracking-[-0.03em] tabular-nums">{score.score}</span>
            <span className="text-sm text-muted">of 100</span>
            <span className={`text-sm font-medium ${b.tone}`}>{b.label}</span>
          </p>
          <p className="mt-3 max-w-[48ch] text-sm leading-relaxed text-muted">
            Only what this {isScan ? 'scan' : 'test'} measured counts. An area that was not measured is left out and its weight goes to the others. Ignored findings still count.
          </p>
        </div>
        <dl className="grid content-start gap-3">
          {AREAS.map((a) => {
            const value = score.areas[a.id]
            return (
              <div key={a.id} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-1 text-sm">
                <dt>
                  {a.label} <span className="text-xs text-muted">({a.weight}%)</span>
                </dt>
                <dd className="font-mono text-xs text-muted">{value ?? 'Not measured'}</dd>
                <dd className="col-span-2 h-1 overflow-hidden rounded-full bg-line" aria-hidden="true">
                  {value != null && <div className="h-full rounded-full bg-ink" style={{ width: `${value}%` }} />}
                </dd>
              </div>
            )
          })}
        </dl>
      </div>
      {isOwner && <BadgeEmbed runId={runId} isPublic={isPublic} score={score.score} />}
    </section>
  )
}

function BadgeEmbed({ runId, isPublic, score }: { runId: string; isPublic: boolean; score: number }) {
  const [copied, setCopied] = useState<string | null>(null)
  if (!isPublic) {
    return (
      <p className="no-print mt-4 text-sm text-muted">
        Share this report to get a live badge for your site. It always shows your latest shared score for this site.
      </p>
    )
  }
  const img = `${API}/badge/${runId}.svg`
  const link = `${API}/badge/${runId}`
  const alt = `Walkthru Launch Ready score: ${score} of 100`
  const snippets = {
    HTML: `<a href="${link}"><img src="${img}" alt="${alt}" height="20"></a>`,
    Markdown: `[![${alt}](${img})](${link})`,
  }
  async function copy(kind: string, text: string) {
    setCopied((await copyText(text)) ? kind : `${kind} failed`)
  }
  return (
    <div className="no-print mt-5 grid gap-4 rounded-2xl border border-line p-5 md:grid-cols-[auto_minmax(0,1fr)] md:items-start">
      <div>
        <p className="text-sm font-medium">Your badge</p>
        <img src={img} alt={alt} height={20} className="mt-3" />
      </div>
      <div className="min-w-0">
        <p className="max-w-[60ch] text-sm leading-relaxed text-muted">
          Put it in your footer or README. It links to your latest shared report for this site and updates when you rerun and share again.
        </p>
        <pre className="mt-3 overflow-x-auto rounded-xl bg-surface px-3 py-2 font-mono text-xs text-muted"><code>{snippets.HTML}</code></pre>
        <div className="mt-3 flex flex-wrap gap-2">
          {Object.entries(snippets).map(([kind, text]) => (
            <button key={kind} type="button" onClick={() => copy(kind, text)} className="rounded-full border border-line px-4 py-1.5 text-sm transition hover:bg-surface">
              Copy {kind}
            </button>
          ))}
        </div>
        <p role="status" aria-live="polite" className="mt-2 min-h-5 text-xs text-muted">
          {copied?.endsWith('failed') ? 'Copy failed. Select the code in your browser instead.' : copied ? `${copied} copied.` : ''}
        </p>
      </div>
    </div>
  )
}
