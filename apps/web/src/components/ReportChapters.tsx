import { useState, type ReactNode } from 'react'
import { copyText } from '../lib/clipboard'
import { CHAPTER_TITLE, issueAnchor, type Chapter, type NextAction } from '../lib/reportChapters'
import { getFixPrompt } from '../lib/runs'

const TONE: Record<Chapter['status'], string> = {
  issues: 'text-ink', clear: 'text-accent', unconfirmed: 'text-muted', not_measured: 'text-muted', not_tested: 'text-muted', separate: 'text-muted', reference: 'text-muted', advisory: 'text-muted',
}
const num = (n: number) => String(n).padStart(2, '0')

/** The first screen's answer to "what do I do now": the three most important open findings, linked to their detail. */
export function NextActions({ actions }: { actions: NextAction[] }) {
  return (
    <section aria-labelledby="next-actions-title" className="report-print-section mt-10">
      <h2 id="next-actions-title" className="text-2xl font-light tracking-tight">Start here</h2>
      {actions.length === 0 ? (
        <p role="status" className="mt-3 max-w-[64ch] text-sm leading-relaxed text-muted">No open findings within this report's measured scope. Check the chapters below for what was not measured.</p>
      ) : (
        <ol className="mt-4 grid gap-px overflow-hidden rounded-2xl border border-line bg-line">
          {actions.map((a, i) => (
            <li key={a.id} className="grid grid-cols-[2.5rem_1fr] gap-3 bg-bg px-5 py-4">
              <span className="pt-0.5 font-mono text-xs text-muted">{num(i + 1)}</span>
              <div className="min-w-0">
                <a href={`#${issueAnchor(a.id)}`} className="font-medium underline decoration-line underline-offset-4 transition hover:decoration-ink">{a.title}</a>
                <p className="mt-1 text-sm leading-relaxed text-muted">{a.fix}</p>
                <p className="mt-1 text-xs text-muted"><span className={a.severity === 'high' ? 'text-danger' : undefined}>{a.severity}</span> · {CHAPTER_TITLE[a.chapter]}</p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}

/** Contents: every chapter, its number and status, as keyboard-reachable anchors. */
export function ChapterContents({ chapters }: { chapters: Chapter[] }) {
  return (
    <nav aria-labelledby="contents-title" className="report-print-section mt-12">
      <h2 id="contents-title" className="text-2xl font-light tracking-tight">Contents</h2>
      <ol className="mt-4 grid gap-px overflow-hidden rounded-2xl border border-line bg-line sm:grid-cols-2">
        {chapters.map((c) => (
          <li key={c.key} className="bg-bg">
            <a href={`#chapter-${c.key}`} className="grid h-full grid-cols-[2rem_1fr] gap-x-3 px-5 py-3.5 transition-colors hover:bg-surface/60 focus-visible:bg-surface/60">
              <span className="pt-0.5 font-mono text-xs text-muted">{num(c.number)}</span>
              <span className="min-w-0">
                <span className="block">{c.title}</span>
                <span className={`block text-xs ${TONE[c.status]}`}>{c.label}</span>
              </span>
            </a>
          </li>
        ))}
      </ol>
    </nav>
  )
}

/** One numbered chapter: a prominent heading, its plain-language summary, then whatever the chapter holds. */
export function ChapterSection({ chapter: c, children }: { chapter: Chapter; children?: ReactNode }) {
  return (
    <section id={`chapter-${c.key}`} aria-labelledby={`chapter-${c.key}-title`} className="report-print-section mt-20 scroll-mt-24 border-t border-line pt-8">
      <p className="font-mono text-xs text-muted">{num(c.number)}</p>
      <div className="mt-1 flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
        <h2 id={`chapter-${c.key}-title`} className="text-3xl font-extralight tracking-tight md:text-4xl">{c.title}</h2>
        <p className={`text-sm ${TONE[c.status]}`}>{c.label}</p>
      </div>
      <p className="mt-3 max-w-[64ch] leading-relaxed text-muted">{c.summary}</p>
      {children}
    </section>
  )
}

/** Links to issues filed under another chapter that share a cause with this one. */
export function CrossLinks({ ids, titles }: { ids: string[]; titles: Record<string, string> }) {
  if (!ids.length) return null
  return (
    <p className="mt-6 text-sm text-muted">
      Related issues filed under other chapters:{' '}
      {ids.map((id, i) => (
        <span key={id}>{i > 0 && ', '}<a href={`#${issueAnchor(id)}`} className="text-ink underline decoration-line underline-offset-4 transition hover:decoration-ink">{titles[id] ?? id}</a></span>
      ))}
    </p>
  )
}

/** Paid owners: a fix prompt for this chapter only, smaller than the whole-report prompt. */
export function ChapterPrompt({ runId, chapter }: { runId: string; chapter: Chapter }) {
  const [status, setStatus] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const copy = async () => {
    setBusy(true)
    setStatus(null)
    try {
      if (!(await copyText(await getFixPrompt(runId, 'full', chapter.key)))) throw new Error('Could not copy. Use the whole-report download instead.')
      setStatus(`Copied the ${chapter.title} prompt. Paste it into your coding agent.`)
    } catch (e) {
      setStatus(e instanceof Error ? e.message : 'That did not work. Try again.')
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className="no-print mt-6 flex flex-wrap items-center gap-3">
      <button type="button" disabled={busy} onClick={copy} className="rounded-full border border-line px-4 py-2 text-sm transition hover:border-ink disabled:opacity-50">
        {busy ? 'Copying...' : 'Copy fix prompt for this chapter'}
      </button>
      {status && <p role="status" className="text-xs text-muted">{status}</p>}
    </div>
  )
}
