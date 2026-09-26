import type { CitationAnswer, CitationBrand, CitationView } from '../lib/runs'

const day = (iso: string) => new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })

/** What AI said about the site: the headline numbers, share of voice, and each prompt's answers with their sources. */
export function CitationResults({ view }: { view: CitationView }) {
  const done = view.answers.filter((a) => a.status === 'done')
  const you = (a: CitationAnswer) => a.result.brands?.find((b) => b.you)
  const named = done.filter((a) => you(a)?.mentioned).length
  const cited = done.filter((a) => you(a)?.cited).length
  const mine = view.share_of_voice.find((s) => s.you)
  const prompts = [...new Set(view.answers.map((a) => a.prompt))]
  const engines = view.engines.filter((e) => view.answers.some((a) => a.engine === e.engine))

  if (view.answers.length === 0) {
    return <p className="mt-8 text-sm text-muted">No answers yet. Check now, or wait for the weekly check.</p>
  }

  return (
    <div className="mt-8 grid gap-12">
      <section aria-label="Summary" className="grid gap-px overflow-hidden rounded-2xl bg-line sm:grid-cols-4">
        <Stat label="Named you" value={`${named} of ${done.length}`} note="answers that say your name" />
        <Stat label="Cited you" value={`${cited} of ${done.length}`} note="answers that link your pages" />
        <Stat label="Share of voice" value={mine ? `${mine.share}%` : '-'} note="of brand mentions, you vs competitors" />
        <Stat
          label={view.status.queued ? 'Checking' : 'Last checked'}
          value={view.status.queued ? `${view.status.queued} left` : done[0]?.checked_at ? day(done[0].checked_at) : '-'}
          note={view.status.queued ? 'answers arrive over the next minutes' : view.site.next_check_at ? `next check ${day(view.site.next_check_at)}` : 'checks when you ask'}
        />
      </section>

      {view.share_of_voice.length > 1 && (
        <section aria-labelledby="sov-heading">
          <h2 id="sov-heading" className="text-xl font-light">Share of voice</h2>
          <p className="mt-2 max-w-[60ch] text-sm leading-relaxed text-muted">How often each brand is named across these {done.length} answers. Counted in code from the answer text, never by another AI.</p>
          <ul className="mt-5 grid gap-3">
            {view.share_of_voice.map((s) => (
              <li key={s.name} className="grid grid-cols-[minmax(7rem,12rem)_1fr_auto] items-center gap-4 text-sm">
                <span className={`truncate ${s.you ? 'text-ink' : 'text-muted'}`}>{s.name}{s.you && <span className="sr-only"> (you)</span>}</span>
                <span className="h-2 overflow-hidden rounded-full bg-surface" aria-hidden>
                  <span className={`block h-full rounded-full ${s.you ? 'bg-ink' : 'bg-muted/50'}`} style={{ width: `${Math.max(s.share, s.mentions ? 2 : 0)}%` }} />
                </span>
                <span className="text-right text-xs whitespace-nowrap text-muted tabular-nums">{s.share}% · {s.mentions} named{s.citations ? `, ${s.citations} cited` : ''}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section aria-labelledby="answers-heading">
        <h2 id="answers-heading" className="text-xl font-light">Answers by prompt</h2>
        <p className="mt-2 max-w-[60ch] text-sm leading-relaxed text-muted">
          {engines.map((e) => `${e.label}${e.cites ? '' : ' (mentions only, no sources)'}`).join('. ')}. {view.not_measured.join(' and ')}: not measured yet.
        </p>
        <ul className="mt-5 divide-y divide-line border-y border-line">
          {prompts.map((prompt) => (
            <li key={prompt} className="grid gap-3 py-5">
              <p className="text-sm text-ink">{prompt}</p>
              <div className="grid gap-2">
                {engines.map((e) => {
                  const a = view.answers.find((x) => x.prompt === prompt && x.engine === e.engine)
                  return a ? <Answer key={e.engine} answer={a} label={e.label} /> : null
                })}
              </div>
            </li>
          ))}
        </ul>
      </section>

      {view.trend.length > 1 && (
        <section aria-labelledby="trend-heading">
          <h2 id="trend-heading" className="text-xl font-light">Over time</h2>
          <ol className="mt-4 grid gap-1 text-sm text-muted">
            {view.trend.map((t) => (
              <li key={t.at} className="tabular-nums"><span className="inline-block w-20 text-ink">{day(t.at)}</span> named in {t.mentioned} of {t.answers}, cited in {t.cited}</li>
            ))}
          </ol>
        </section>
      )}
    </div>
  )
}

function Answer({ answer, label }: { answer: CitationAnswer; label: string }) {
  const you = answer.result.brands?.find((b) => b.you)
  const others = (answer.result.brands ?? []).filter((b) => !b.you && b.mentioned)
  return (
    <details className="group rounded-xl border border-line px-4 py-3">
      <summary className="flex cursor-pointer list-none flex-wrap items-center gap-x-3 gap-y-1 text-xs">
        <span className="text-muted">{label}</span>
        {answer.status === 'queued' && <span className="text-muted">Waiting for its turn</span>}
        {answer.status === 'failed' && <span className="text-danger">{answer.answer || 'No answer'}</span>}
        {answer.status === 'done' && you && <Verdict brand={you} />}
        {answer.status === 'done' && others.length > 0 && <span className="text-muted">Also named: {others.map((b) => b.name).join(', ')}</span>}
        <span aria-hidden className="ml-auto text-muted transition-transform group-open:rotate-90 motion-reduce:transition-none">›</span>
      </summary>
      {answer.status === 'done' && (
        <div className="mt-3 grid gap-3 border-t border-line pt-3">
          <p className="text-sm leading-relaxed whitespace-pre-line text-ink">{answer.answer}</p>
          {answer.sources.length > 0 && (
            <ol className="grid gap-1 text-xs text-muted">
              {answer.sources.map((s, i) => (
                <li key={s.url} className="truncate">
                  {i + 1}. <a href={s.url} target="_blank" rel="noopener noreferrer nofollow" className="text-ink underline decoration-line underline-offset-4 hover:decoration-ink">{s.domain}</a> {s.title}
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </details>
  )
}

function Verdict({ brand }: { brand: CitationBrand }) {
  return (
    <>
      <span className={brand.mentioned ? 'text-ink' : 'text-muted'}>{brand.mentioned ? `Named you${brand.mention_rank ? ` (#${brand.mention_rank})` : ''}` : 'Did not name you'}</span>
      <span className={brand.cited ? 'text-accent' : 'text-muted'}>{brand.cited ? `Cited your site (source #${brand.source_rank})` : 'Not cited'}</span>
    </>
  )
}

function Stat({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <div className="bg-bg px-5 py-4">
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-1 text-2xl font-extralight tracking-tight tabular-nums">{value}</p>
      <p className="mt-1 text-xs text-muted">{note}</p>
    </div>
  )
}
