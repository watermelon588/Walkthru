import type { Report } from '../lib/runs'

type Audit = NonNullable<Report['site_audit']>

export function SiteAuditCoverage({ audit }: { audit: Audit }) {
  const duration = audit.duration_ms < 1000 ? `${audit.duration_ms} ms` : `${(audit.duration_ms / 1000).toFixed(1)} s`
  return (
    <section aria-labelledby="site-audit-title" className="report-print-section mt-12">
      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Crawl coverage</p>
      <div className="mt-2 grid gap-5 border-y border-line py-5 md:grid-cols-[minmax(0,1fr)_auto] md:items-start">
        <div>
          <h2 id="site-audit-title" className="text-xl font-light tracking-tight">
            {audit.pages_scanned} page{audit.pages_scanned === 1 ? '' : 's'} checked
          </h2>
          <p className="mt-2 max-w-[62ch] text-sm leading-relaxed text-muted">
            {audit.truncated
              ? `The audit reached its safe ${audit.page_limit}-page or time limit. The report covers the pages listed below, not the entire site.`
              : 'The audit checked every same-origin HTML page it discovered within this run.'}
          </p>
        </div>
        <dl className="grid grid-cols-2 gap-x-8 gap-y-3 text-xs md:min-w-64">
          <Stat term="Page limit" value={String(audit.page_limit)} />
          <Stat term="Duration" value={duration} />
          <Stat term="robots.txt" value={audit.robots_respected ? 'Respected' : 'Unavailable'} />
          <Stat term="Scope" value="Same origin" />
        </dl>
      </div>
      {audit.urls.length > 0 && (
        <ol className="mt-4 grid gap-2 text-xs text-muted sm:grid-cols-2">
          {audit.urls.map((url, index) => (
            <li key={url} className="min-w-0 rounded-xl border border-line px-3 py-2">
              <span className="mr-2 font-mono">{String(index + 1).padStart(2, '0')}</span>
              <span className="break-all font-mono">{url}</span>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}

function Stat({ term, value }: { term: string; value: string }) {
  return (
    <div>
      <dt className="text-muted">{term}</dt>
      <dd className="mt-0.5 text-ink">{value}</dd>
    </div>
  )
}
