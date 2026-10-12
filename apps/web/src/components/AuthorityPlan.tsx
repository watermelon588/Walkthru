import type { AuthorityPlan as Plan, AuthorityTactic } from '../lib/runs'

const STATE: Record<AuthorityTactic['state'], { label: string; tone: string }> = {
  advisory: { label: 'Advisory brief', tone: 'text-accent' },
  prerequisite_missing: { label: 'Needs input', tone: 'text-ink' },
  not_applicable: { label: 'Not applicable', tone: 'text-muted' },
  not_recommended: { label: 'Not recommended', tone: 'text-danger' },
}

const path = (url: string) => {
  try {
    const u = new URL(url)
    return u.pathname + u.search || '/'
  } catch {
    return url
  }
}

/** Authority and backlinks, prelaunch advisory mode (R-S17a): twelve link tactics with their state. Briefs build only on
 *  audited pages; tactics needing outside evidence say what is needed. No link data, so no counts, and nothing is sent. */
export function AuthorityPlan({ plan }: { plan: Plan }) {
  const briefs = plan.tactics.filter((t) => t.state === 'advisory')
  const rest = plan.tactics.filter((t) => t.state !== 'advisory')
  return (
    <div className="mt-6">
      <p className="max-w-[72ch] rounded-2xl border border-line px-5 py-4 text-sm leading-relaxed text-muted">
        <span className="font-medium text-ink">Advisory, no link data. </span>{plan.basis} {plan.rules.join(' ')}
      </p>
      {briefs.length > 0 && (
        <ol className="mt-6 grid gap-4">
          {briefs.map((t) => (
            <li key={t.id} className="rounded-2xl border border-line px-5 py-5">
              <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
                <h3 className="font-medium">{t.title}</h3>
                <span className={`text-xs ${STATE[t.state].tone}`}>{STATE[t.state].label}{t.effort ? `, ${t.effort} effort` : ''}</span>
              </div>
              <p className="mt-2 text-sm leading-relaxed [overflow-wrap:anywhere]">{t.brief}</p>
              <p className="mt-2 text-sm leading-relaxed text-muted">{t.reader_benefit}</p>
              <details className="mt-3 text-sm">
                <summary className="w-fit cursor-pointer py-1 text-ink">Source, what it needs and how to measure</summary>
                <dl className="mt-3 space-y-3 border-l border-line pl-4">
                  {t.source && <div><dt className="font-medium">Built from</dt><dd className="mt-1 text-muted [overflow-wrap:anywhere]">{path(t.source.url)}, {t.source.observed}</dd></div>}
                  <div><dt className="font-medium">Before acting</dt><dd className="mt-1 text-muted"><ul className="list-disc pl-5">{t.prerequisites.map((p) => <li key={p}>{p}</li>)}</ul></dd></div>
                  {t.measurement && <div><dt className="font-medium">Measure</dt><dd className="mt-1 text-muted">{t.measurement}</dd></div>}
                </dl>
              </details>
            </li>
          ))}
        </ol>
      )}
      <ul className="mt-6 divide-y divide-line border-y border-line text-sm">
        {rest.map((t) => (
          <li key={t.id} className="py-4">
            <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
              <h3 className="font-medium">{t.title}</h3>
              <span className={`text-xs ${STATE[t.state].tone}`}>{STATE[t.state].label}</span>
            </div>
            <p className="mt-1 leading-relaxed text-muted">{t.reader_benefit}</p>
            {t.missing.length > 0 && <p className="mt-1 leading-relaxed"><span className="text-muted">Needs: </span>{t.missing.join(' ')}</p>}
            {t.policy && <p className="mt-1 leading-relaxed">{t.policy} <a href={plan.policy_source} target="_blank" rel="noreferrer" className="text-ink underline decoration-line underline-offset-4 hover:decoration-ink">Google&rsquo;s link spam policy</a>.</p>}
          </li>
        ))}
      </ul>
      <div className="mt-6 grid gap-2 text-sm text-muted">
        <h3 className="font-medium text-ink">Kept separate</h3>
        <p>{plan.separate.backlinks}</p>
        <p>{plan.separate.geo_readiness}</p>
        <p>{plan.separate.ai_citations}</p>
      </div>
    </div>
  )
}
