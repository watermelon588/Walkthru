import type { KeywordMap as Map } from '../lib/runs'

const path = (url: string) => {
  try {
    const u = new URL(url)
    return u.pathname + u.search || '/'
  } catch {
    return url
  }
}

/** Keywords and content, prelaunch advisory mode: one card per page with its quoted copy, the intent hypothesis,
 *  proposals built from its own words, internal links and the next action. No search data, so no numbers. */
export function KeywordMap({ map }: { map: Map }) {
  return (
    <div className="mt-6">
      <p className="max-w-[72ch] rounded-2xl border border-line px-5 py-4 text-sm leading-relaxed text-muted">
        <span className="font-medium text-ink">Advisory, no search data. </span>{map.basis} {map.measurement}
      </p>
      <ol className="mt-6 grid gap-4">
        {map.pages.map((page, i) => (
          <li key={page.url} className="rounded-2xl border border-line px-5 py-5">
            <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
              <h3 className="font-medium [overflow-wrap:anywhere]"><span className="mr-2 font-mono text-xs text-muted">{String(i + 1).padStart(2, '0')}</span>{path(page.url)}</h3>
              <span className="text-xs text-muted">{page.effort === 'low' ? 'Low effort' : 'Medium effort'}</span>
            </div>
            <p className="mt-2 text-sm leading-relaxed">
              <span className="text-muted">Intent hypothesis: </span>
              {page.primary_intent ? <>&ldquo;{page.primary_intent.text}&rdquo; <span className="text-muted">(from its {page.primary_intent.source === 'h1' ? 'main heading' : 'title'})</span></> : <span className="text-muted">none readable on this page</span>}
            </p>
            <p className="mt-2 text-sm leading-relaxed"><span className="text-muted">Next: </span>{page.next_action}</p>
            <details className="mt-3 text-sm">
              <summary className="w-fit cursor-pointer py-1 text-ink">Quoted copy, proposal and links</summary>
              <dl className="mt-3 space-y-3 border-l border-line pl-4">
                <div><dt className="font-medium">Current title</dt><dd className="mt-1 text-muted">{page.current.title ? `“${page.current.title}”` : 'None'}</dd></div>
                <div><dt className="font-medium">Current description</dt><dd className="mt-1 text-muted">{page.current.description ? `“${page.current.description}”` : 'None'}</dd></div>
                {page.supporting.length > 0 && <div><dt className="font-medium">Supporting topics (section headings)</dt><dd className="mt-1 text-muted">{page.supporting.map((s) => `“${s.text}”`).join(', ')}</dd></div>}
                {page.proposed.title && <div><dt className="font-medium">Proposed title</dt><dd className="mt-1">&ldquo;{page.proposed.title}&rdquo;</dd></div>}
                {page.proposed.description && <div><dt className="font-medium">Proposed description</dt><dd className="mt-1">&ldquo;{page.proposed.description}&rdquo;</dd></div>}
                {page.proposed.outline.length > 0 && <div><dt className="font-medium">Outline from its headings</dt><dd className="mt-1 text-muted"><ol className="list-decimal pl-5">{page.proposed.outline.map((h, j) => <li key={j}>{h}</li>)}</ol></dd></div>}
                <div><dt className="font-medium">Why these proposals</dt><dd className="mt-1 text-muted">{page.proposed.basis}</dd></div>
                {page.gaps.length > 0 && <div><dt className="font-medium">Gaps</dt><dd className="mt-1 text-muted"><ul className="list-disc pl-5">{page.gaps.map((g) => <li key={g}>{g}</li>)}</ul></dd></div>}
                <div><dt className="font-medium">Internal links</dt><dd className="mt-1 text-muted [overflow-wrap:anywhere]">
                  Linked from: {page.internal_links.inbound_from.map(path).join(', ') || 'no other audited page'}.
                  {page.internal_links.suggested_from.length > 0 && <> Suggested sources: {page.internal_links.suggested_from.map(path).join(', ')}.</>}
                </dd></div>
              </dl>
            </details>
          </li>
        ))}
      </ol>
      {map.overlaps.length > 0 && (
        <div className="mt-6 text-sm">
          <h3 className="font-medium">Pages with the same main topic</h3>
          <ul className="mt-2 space-y-2 text-muted">
            {map.overlaps.map((o) => <li key={o.intent} className="[overflow-wrap:anywhere]">&ldquo;{o.intent}&rdquo;: {o.pages.map(path).join(', ')}. {o.note}</li>)}
          </ul>
        </div>
      )}
      {map.excluded_noindex.length > 0 && <p className="mt-4 text-xs text-muted [overflow-wrap:anywhere]">Left out because they ask search engines not to index them: {map.excluded_noindex.map(path).join(', ')}.</p>}
    </div>
  )
}
