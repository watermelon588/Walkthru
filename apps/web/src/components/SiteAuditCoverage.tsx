import { TreeStructureIcon } from '@phosphor-icons/react'
import type { Report } from '../lib/runs'

type Audit = NonNullable<Report['site_audit']>

export function SiteAuditCoverage({ audit }: { audit: Audit }) {
  const duration = audit.duration_ms < 1000 ? `${audit.duration_ms} ms` : `${(audit.duration_ms / 1000).toFixed(1)} s`
  return (
    <section aria-labelledby="site-audit-title" className="report-print-section mt-12">
      <div className="mt-2 grid gap-5 border-y border-line py-5 md:grid-cols-[minmax(0,1fr)_auto] md:items-start">
        <div>
          <h2 id="site-audit-title" className="text-xl font-light tracking-tight flex items-center gap-2">
            <TreeStructureIcon weight="light" className="size-5 shrink-0 text-accent" aria-hidden />
            Crawl coverage: {audit.pages_scanned} page{audit.pages_scanned === 1 ? "" : "s"} checked
          </h2>
          <p className="mt-2 max-w-[62ch] text-sm leading-relaxed text-muted">
            {audit.truncated
              ? `The audit reached its safe ${audit.page_limit}-page or time limit. The report covers the pages listed below, not the entire site.`
              : audit.pages_scanned <= 1
                ? 'Only this page was found. The HTML the server sends links to no other pages on this site, which is typical when navigation is built by JavaScript.'
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
      {audit.urls.length > 10 ? (
        // Paid audits reach 50 pages; keep the list one click away instead of a wall of cards.
        <details className="mt-4">
          <summary className="cursor-pointer text-sm text-ink underline decoration-line underline-offset-4 hover:decoration-ink">
            Show all {audit.urls.length} pages checked
          </summary>
          <UrlList urls={audit.urls} />
        </details>
      ) : (
        audit.urls.length > 0 && <UrlList urls={audit.urls} />
      )}
    </section>
  )
}

function UrlList({ urls }: { urls: string[] }) {
  return (
    <ol className="mt-4 grid gap-2 text-xs text-muted sm:grid-cols-2">
      {urls.map((url, index) => (
        <li key={url} className="min-w-0 rounded-xl border border-line px-3 py-2">
          <span className="mr-2 font-mono">{String(index + 1).padStart(2, '0')}</span>
          <span className="break-all font-mono">{url}</span>
        </li>
      ))}
    </ol>
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
