import { useState } from 'react'
import type { CitationAnswer, CitationView } from '../lib/runs'
import { citationLabel, citationMetrics } from '../lib/citationMetrics'
import { Working } from './Loading'

const day = (iso: string) => new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
const coverageReason: Record<string, string> = {
  not_applicable: 'Mentions only. This answer did not use web search.',
  unresolved: 'Citation attribution is incomplete. Unmatched references or redirect destinations are not counted.',
  unavailable: 'No usable search evidence was returned.',
  legacy: 'Older measurement: citation evidence was not retained. Run a new check to measure citations.',
}

export function CitationResults({ view }: { view: CitationView }) {
  const [engine, setEngine] = useState('all')
  const [group, setGroup] = useState('all')
  const labels = [...new Set(view.answers.map(citationLabel))]
  const selected = view.answers.filter((a) => (engine === 'all' || citationLabel(a) === engine) && (group === 'all' || a.result?.prompt_group === group))
  const stats = citationMetrics(selected)
  const mine = stats.voice.find((b) => b.you)
  return <div className="mt-8 grid gap-8">
    <section aria-label="Engine coverage" className="rounded-2xl border border-line p-5">
      <h3 className="text-sm font-medium">What is measured</h3>
      <p className="mt-2 text-sm leading-relaxed text-muted">These are sampled API answers, which can differ from consumer apps. Gemini with Google Search is a Gemini answer, not a Google AI Overview or AI Mode result.</p>
      <p className="mt-2 text-sm leading-relaxed text-muted">Not measured: {view.not_measured.join(', ')}.</p>
      <p className="mt-2 text-xs text-muted">An unmeasured engine has no visibility score. One sample per prompt and engine is a snapshot, not a stable ranking.</p>
    </section>
    {!!view.capacity?.length && <section aria-label="Queue capacity" className="border-y border-line py-5">
      <h3 className="text-sm font-medium">Shared provider capacity</h3>
      <ul className="mt-3 grid gap-2 text-xs leading-relaxed text-muted">{view.capacity.map((c) => <li key={c.engine}>
        {c.label}: {c.configured ? `${c.remaining} of ${c.daily_limit} attempts left today · ${c.queued} queued across the service` : 'Provider is not configured'}
        {c.configured && c.queued > 0 && <> · {c.quota_windows === null ? 'paused at the current limit' : `about ${c.quota_windows} daily quota window${c.quota_windows === 1 ? '' : 's'} at current capacity`}</>}
      </li>)}</ul>
      <p className="mt-3 text-xs text-muted">Limits reset at midnight UTC. Retries also use quota. These are capacity estimates; provider limits and outages can delay answers.</p>
    </section>}
    {view.answers.length === 0 ? view.status.queued > 0
      ? <Working state="listening" every={7000} title={`Asking AI ${view.status.queued} question${view.status.queued === 1 ? '' : 's'}`} steps={['Waiting for free provider capacity', 'Asking each answer engine', 'Reading which brands the answer names', 'Matching citations to your pages']} />
      : <p className="text-sm text-muted">No answers yet. Check now, or wait for the scheduled check.</p> : <>
      <div className="flex flex-wrap gap-5">
        <label className="grid max-w-full gap-2 text-xs text-muted">Answer engine
          <select value={engine} onChange={(e) => setEngine(e.target.value)} className="max-w-full rounded-xl border border-line bg-bg px-3 py-2 text-ink">
            <option value="all">All sampled engines</option>{labels.map((l) => <option key={l}>{l}</option>)}
          </select>
        </label>
        <label className="grid gap-2 text-xs text-muted">Prompt type
          <select value={group} onChange={(e) => setGroup(e.target.value)} className="rounded-xl border border-line bg-bg px-3 py-2 text-ink">
            <option value="all">All prompts</option><option value="unbranded">Does not name your brand</option><option value="branded">Names your brand</option>
          </select>
        </label>
      </div>
      <section aria-label="Sample summary" className="grid gap-px overflow-hidden rounded-2xl bg-line sm:grid-cols-4">
        <Stat label="Named you" value={stats.done.length ? `${stats.named} of ${stats.done.length}` : 'N/A'} note="completed answers in this selection" />
        <Stat label="Cited you" value={stats.citationAnswers ? `${stats.cited} of ${stats.citationAnswers}` : 'N/A'} note="answers with resolved citation evidence" />
        <Stat label="Share of mentions" value={stats.hasMentions ? `${mine?.share ?? 0}%` : 'N/A'} note="your mentions among tracked brands" />
        <Stat label="Batch progress" value={`${view.status.done} complete`} note={`${view.status.queued} queued · ${view.status.failed} failed`} />
      </section>
      <p className="text-xs leading-relaxed text-muted">{stats.done.length - stats.citationAnswers} completed answers in this selection are excluded from citation measurement. Prompts naming your brand can raise mention rates. Mention order and source order are not search rankings.</p>
      {stats.voice.length > 1 && <section aria-labelledby="sov-heading">
        <h3 id="sov-heading" className="text-xl font-light">Share of mentions</h3>
        <ul className="mt-4 grid gap-3">{stats.voice.map((b, i) => <li key={i} className="grid grid-cols-[minmax(5rem,1fr)_2fr_auto] items-center gap-3 text-sm">
          <span className="truncate">{b.name}{b.you ? ' (you)' : ''}</span>
          <span aria-hidden className="h-2 rounded-full bg-surface"><span className={`block h-2 rounded-full ${b.you ? 'bg-ink' : 'bg-muted/50'}`} style={{ width: `${b.share}%` }} /></span>
          <span className="text-xs text-muted tabular-nums">{b.share}% · {b.mentions}</span>
        </li>)}</ul>
      </section>}
      <section aria-labelledby="answers-heading">
        <h3 id="answers-heading" className="text-xl font-light">Answers and evidence</h3>
        {!selected.length && <p className="mt-4 text-sm text-muted">No answers match these filters.</p>}
        <ul className="mt-5 grid gap-3">{selected.map((a) => <li key={a.id}><Answer answer={a} /></li>)}</ul>
      </section>
      {view.trend.length > 1 && <section aria-labelledby="trend-heading">
        <h3 id="trend-heading" className="text-xl font-light">Batch history</h3>
        <p className="mt-2 text-xs text-muted">All engines and prompts in each batch. Changes in prompts, modes and completed samples can affect these counts.</p>
        <ol className="mt-4 grid gap-2 text-sm text-muted">{view.trend.map((t) => <li key={t.at}>
          {day(t.at)}: named in {t.mentioned} of {t.answers}; {t.citation_answers ? `cited in ${t.cited} of ${t.citation_answers} measurable answers` : 'citations not measured'}
        </li>)}</ol>
        {view.history_limited && <p className="mt-2 text-xs text-muted">History is limited to the most recent 5,000 checks.</p>}
      </section>}
    </>}
  </div>
}

function Answer({ answer: a }: { answer: CitationAnswer }) {
  const you = a.result?.brands?.find((b) => b.you)
  const status = a.result?.citation_status ?? 'legacy'
  const sources = a.sources ?? []
  const reason = coverageReason[status]
  return <details className="group rounded-xl border border-line p-4">
    <summary className="cursor-pointer text-sm">
      <span className="block text-ink">{a.prompt}</span>
      <span className="mt-2 block text-xs text-muted">{citationLabel(a)} · {a.status === 'done' ? `${you?.mentioned ? 'Named you' : 'Did not name you'} · ${you?.cited ? 'Cited your site' : status === 'measured' ? 'Not cited' : 'Citations N/A'}` : a.status === 'queued' ? 'Queued' : 'Failed'}</span>
    </summary>
    <div className="mt-4 grid gap-4 border-t border-line pt-4">
      {a.status !== 'done' ? <p role="status" className="text-sm text-muted">{a.last_error || a.answer || 'Waiting for available provider capacity.'}{a.status === 'queued' && a.next_attempt_at ? ` Eligible to retry after ${new Date(a.next_attempt_at).toLocaleString()}.` : ''}</p> : <>
        <p className="text-xs text-muted">{a.model || 'Model not recorded'} · {a.checked_at ? new Date(a.checked_at).toLocaleString() : 'Date unavailable'} · {a.result?.prompt_group === 'branded' ? 'Prompt names your brand' : a.result?.prompt_group === 'unbranded' ? 'Prompt does not name your brand' : 'Prompt type not recorded'}</p>
        <p className="text-sm leading-relaxed whitespace-pre-line break-words">{a.result?.raw_answer || a.answer}</p>
        {reason && <p className="text-xs leading-relaxed text-muted">{reason}</p>}
        {!!sources.length && <div><h4 className="text-sm font-medium">Sources and attribution</h4>
          <ol className="mt-3 grid gap-4">{sources.map((s, i) => <li key={`${s.url}-${i}`} className="min-w-0 text-xs text-muted">
            <p>{s.cited ? 'Referenced in answer' : 'Retrieved only'}{!s.domain && ' · destination unresolved'}</p>
            <a href={safeLink(s.url)} target="_blank" rel="noopener noreferrer nofollow" className="mt-1 block break-all text-ink underline decoration-line underline-offset-4">{s.title || s.domain || s.url}</a>
            <span className="mt-1 block break-all">{s.url}</span>
            {s.evidence?.map((e, j) => <p key={j} className="mt-2 break-words">Evidence: {e.quote ? `“${e.quote}”` : e.reference}</p>)}
          </li>)}</ol>
        </div>}
      </>}
    </div>
  </details>
}

function safeLink(raw: string) {
  try { const u = new URL(raw); return ['http:', 'https:'].includes(u.protocol) && !u.username && !u.password ? u.href : undefined } catch { return undefined }
}

function Stat({ label, value, note }: { label: string; value: string; note: string }) {
  return <div className="bg-bg px-5 py-4"><p className="text-xs text-muted">{label}</p><p className="mt-1 text-2xl font-extralight tabular-nums">{value}</p><p className="mt-2 text-xs text-muted">{note}</p></div>
}
