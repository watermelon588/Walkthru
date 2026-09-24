import { GaugeIcon } from '@phosphor-icons/react'
import { useState } from 'react'
import { copyText } from '../lib/clipboard'
import { API, type Report } from '../lib/runs'
import { Card } from './Card'

type Score = NonNullable<Report['launch_ready']>

const AREAS: { id: keyof Score['areas']; label: string }[] = [
  { id: 'ux', label: 'Can a stranger get in' },
  { id: 'security', label: 'Security hygiene' },
  { id: 'geo', label: 'AI search readiness' },
  { id: 'seo', label: 'SEO' },
  { id: 'speed', label: 'Speed and accessibility' },
]

// Same bands as the badge (app/agent/score.py `band`).
function band(score: number): { label: string; tone: string } {
  if (score >= 85) return { label: 'Launch ready', tone: 'text-accent' }
  if (score >= 60) return { label: 'Almost ready', tone: 'text-ink' }
  return { label: 'Needs work', tone: 'text-danger' }
}

/** The report's Scores card, as in the landing page mock-up: one number, the areas behind it, and the owner's badge. */
export function LaunchReady({ score, runId, isPublic, isOwner }: { score: Score; runId: string; isPublic: boolean; isOwner: boolean }) {
  if (score.score === null) return null
  const b = band(score.score)
  return (
    <Card className="p-6" aria-labelledby="launch-ready-title">
      <h2 id="launch-ready-title" className="flex items-center gap-2 text-sm font-medium">
        <GaugeIcon weight="light" className="size-5 text-accent" aria-hidden />Launch Ready score
      </h2>
      <p className="mt-4 flex items-baseline gap-3">
        <span className={`text-6xl leading-none font-extralight tracking-[-0.03em] tabular-nums ${b.tone}`}>{score.score}</span>
        <span className="text-sm text-muted">{b.label}</span>
      </p>
      <dl className="mt-5">
        {AREAS.map((a) => {
          const value = score.areas[a.id]
          return (
            <div key={a.id} className="flex items-baseline justify-between gap-4 border-b border-line py-2.5 text-sm last:border-b-0">
              <dt>{a.label}</dt>
              <dd className={`tabular-nums ${value == null ? 'text-xs text-muted' : 'text-ink'}`}>{value ?? 'Not measured'}</dd>
            </div>
          )
        })}
      </dl>
      <p className="mt-3 text-xs leading-relaxed text-muted">Only measured areas count; ignored findings still count.</p>
      {isOwner && <BadgeEmbed runId={runId} isPublic={isPublic} score={score.score} />}
    </Card>
  )
}

function BadgeEmbed({ runId, isPublic, score }: { runId: string; isPublic: boolean; score: number }) {
  const [copied, setCopied] = useState<string | null>(null)
  if (!isPublic) {
    return <p className="no-print mt-4 border-t border-line pt-4 text-xs leading-relaxed text-muted">Share this report to get a live badge for your site.</p>
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
    <div className="no-print mt-4 border-t border-line pt-4">
      <p className="text-sm font-medium">Your badge</p>
      <img src={img} alt={alt} height={20} className="mt-3" />
      <p className="mt-3 text-xs leading-relaxed text-muted">For your footer or README. It follows your latest shared report for this site.</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {Object.entries(snippets).map(([kind, text]) => (
          <button key={kind} type="button" onClick={() => copy(kind, text)} className="rounded-full border border-line px-3 py-1 text-xs transition hover:bg-surface">
            Copy {kind}
          </button>
        ))}
      </div>
      <p role="status" aria-live="polite" className="mt-2 min-h-4 text-xs text-muted">
        {copied?.endsWith('failed') ? 'Copy failed. Copy it from here instead:' : copied ? `${copied} copied.` : ''}
      </p>
      {copied?.endsWith('failed') && <pre className="mt-1 overflow-x-auto rounded-lg bg-surface px-2 py-1.5 font-mono text-[11px] text-muted"><code>{snippets.HTML}</code></pre>}
    </div>
  )
}
