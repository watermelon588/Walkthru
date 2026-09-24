import { CaretDownIcon, GaugeIcon, MagnifyingGlassIcon, ShieldCheckIcon, type Icon } from '@phosphor-icons/react'
import { fingerprint, type Finding, type Report } from '../lib/runs'
import { Card, Pill, type Tone } from './Card'

type Kind = Finding['kind']
/** One line of a check card. `match` names the finding titles the scanners emit for this check (apps/api/app/scans). */
type Check = { label: string; kind: Kind; match: RegExp; pass: string; verifiedOnly?: boolean; needsFullCrawl?: boolean }

const SEO: Check[] = [
  { label: 'Page titles', kind: 'seo', match: /page title|^duplicate title/i, pass: 'Present' },
  { label: 'Meta descriptions', kind: 'seo', match: /meta description/i, pass: 'Present' },
  { label: 'One h1 per page', kind: 'seo', match: /h1 heading/i, pass: 'Present' },
  { label: 'Image alt text', kind: 'seo', match: /alt text/i, pass: 'Present' },
  { label: 'Mobile viewport', kind: 'seo', match: /viewport/i, pass: 'Set' },
  { label: 'Canonical URLs', kind: 'seo', match: /canonical/i, pass: 'Set' },
  { label: 'Indexable pages', kind: 'seo', match: /noindex/i, pass: 'Indexable' },
  { label: 'Sitemap and robots.txt', kind: 'seo', match: /sitemap|robots\.txt/i, pass: 'Found' },
  { label: 'Internal links', kind: 'seo', match: /broken internal link|server error on a linked page|redirect chain|has no links/i, pass: 'All working' },
  { label: 'Unique content', kind: 'seo', match: /duplicate (page content|meta description)|thin content/i, pass: 'Unique' },
  { label: 'Site structure', kind: 'seo', match: /orphan page|deep in the site/i, pass: 'Easy to reach', needsFullCrawl: true },
  { label: 'Social previews', kind: 'seo', match: /open graph/i, pass: 'Set' },
  { label: 'Crawler access', kind: 'seo', match: /crawler was blocked|rate limited/i, pass: 'Open' },
]

const SECURITY: Check[] = [
  { label: 'HTTPS everywhere', kind: 'security', match: /plain http|redirect to https/i, pass: 'On' },
  { label: 'Strict-Transport-Security header', kind: 'security', match: /hsts/i, pass: 'Set' },
  { label: 'Content-Security-Policy header', kind: 'security', match: /content-security-policy/i, pass: 'Set' },
  { label: 'Clickjacking protection', kind: 'security', match: /can be framed/i, pass: 'Set' },
  { label: 'X-Content-Type-Options header', kind: 'security', match: /x-content-type-options/i, pass: 'Set' },
  { label: 'Referrer-Policy header', kind: 'security', match: /referrer-policy/i, pass: 'Set' },
  { label: 'Server version hidden', kind: 'security', match: /reveals a version/i, pass: 'Hidden' },
  { label: 'Exposed files', kind: 'security', match: /publicly readable/i, pass: 'None found', verifiedOnly: true },
  { label: 'Secret keys in JavaScript', kind: 'security', match: /in a javascript bundle/i, pass: 'None found', verifiedOnly: true },
]

function problem(f: Finding, pages: number): string {
  const words: [RegExp, string][] = [
    [/plain http/i, 'Plain http'], [/redirect to https/i, 'No redirect'], [/^(missing|no )|can be framed/i, 'Missing'],
    [/too long/i, 'Too long'], [/too short/i, 'Too short'], [/duplicate/i, 'Duplicated'], [/blocked|rate limited/i, 'Blocked'],
    [/broken/i, 'Broken'], [/server error/i, 'Server error'], [/redirect chain/i, 'Redirect chain'], [/has no links/i, 'Dead end'],
    [/reveals a version|publicly readable/i, 'Exposed'], [/javascript bundle/i, 'Key found'], [/thin content/i, 'Thin'],
    [/orphan/i, 'Orphaned'], [/deep in the site/i, 'Too deep'], [/noindex/i, 'Noindex'], [/alt text/i, 'Missing'],
  ]
  const verb = words.find(([re]) => re.test(f.title))?.[1] ?? 'Needs a fix'
  return pages > 1 ? `${verb} on ${pages} pages` : verb
}

function Row({ check, report }: { check: Check; report: Report }) {
  const measured = (report.checks?.[check.kind as 'seo'] ?? 'complete') === 'complete'
  const hits = report.findings.filter((f) => f.kind === check.kind && check.match.test(f.title))
  const pages = hits.reduce((n, f) => Math.max(n, report.pages?.[fingerprint(f)]?.length ?? 1), 0)
  let tone: Tone = 'ok'
  let text = check.pass
  if (!measured) [tone, text] = ['neutral', 'Not measured']
  else if (hits.length) [tone, text] = [hits.some((f) => f.severity === 'high') ? 'bad' : 'neutral', problem(hits[0], pages)]
  else if (check.verifiedOnly && !report.verified) [tone, text] = ['neutral', 'Verify your domain']
  else if (check.needsFullCrawl && report.site_audit?.truncated) [tone, text] = ['neutral', 'Partly checked']

  const line = (
    <>
      <span className="min-w-0 text-sm text-ink">{check.label}</span>
      <span className="flex items-center gap-2">
        <Pill tone={tone}>{text}</Pill>
        {hits.length > 0 && <CaretDownIcon weight="bold" className="size-3 text-muted transition-transform group-open:rotate-180 motion-reduce:transition-none" aria-hidden />}
      </span>
    </>
  )
  if (!hits.length) return <li className="flex items-center justify-between gap-4 border-b border-line py-3 last:border-b-0">{line}</li>
  return (
    <li className="border-b border-line last:border-b-0">
      <details className="group">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-4 py-3 [&::-webkit-details-marker]:hidden">{line}</summary>
        <div className="grid gap-3 pb-4">
          {hits.map((f) => (
            <div key={f.title} className="text-sm leading-relaxed">
              <p className="text-ink">{f.title}</p>
              <p className="mt-1 text-muted">{f.detail}</p>
              <p className="mt-1"><span className="text-muted">Fix: </span>{f.fix}</p>
            </div>
          ))}
        </div>
      </details>
    </li>
  )
}

function Figure({ value, label, tone = 'text-ink' }: { value: string; label: string; tone?: string }) {
  return (
    <div>
      <p className={`text-4xl leading-none font-extralight tracking-[-0.02em] tabular-nums ${tone}`}>{value}</p>
      <p className="mt-2 text-xs text-muted">{label}</p>
    </div>
  )
}

function areaTone(v: number) {
  return v >= 85 ? 'text-accent' : v >= 60 ? 'text-ink' : 'text-danger'
}

function CheckCard({ title, icon: I, note, score, checks, report }: { title: string; icon: Icon; note: string; score?: number | null; checks: Check[]; report: Report }) {
  const issues = new Set(report.findings.filter((f) => checks.some((c) => c.kind === f.kind && c.match.test(f.title))).map((f) => f.title)).size
  return (
    <Card className="p-6" aria-label={title}>
      <div className="flex items-baseline justify-between gap-4">
        <h3 className="flex items-center gap-2 font-medium"><I weight="light" className="size-5 text-accent" aria-hidden />{title}</h3>
        <span className="text-xs text-muted">{note}</span>
      </div>
      <div className="mt-5 flex gap-10">
        {score != null && <Figure value={String(score)} label={`${title} score`} tone={areaTone(score)} />}
        <Figure value={String(issues)} label={issues === 1 ? 'Issue to fix' : 'Issues to fix'} tone={issues ? 'text-danger' : 'text-accent'} />
      </div>
      <ul className="mt-4">{checks.map((c) => <Row key={c.label} check={c} report={report} />)}</ul>
    </Card>
  )
}

/** Speed and accessibility have no fixed catalogue: list what was found, or say it was clear or not measured. */
function SpeedCard({ report }: { report: Report }) {
  const kinds = ['performance', 'accessibility'] as const
  const measured = kinds.some((k) => report.checks?.[k] === 'complete')
  const found = report.findings.filter((f) => (kinds as readonly string[]).includes(f.kind))
  const score = report.launch_ready?.areas.speed
  return (
    <Card className="p-6" aria-label="Speed and accessibility">
      <div className="flex items-baseline justify-between gap-4">
        <h3 className="flex items-center gap-2 font-medium"><GaugeIcon weight="light" className="size-5 text-accent" aria-hidden />Speed and accessibility</h3>
        <span className="text-xs text-muted">{measured ? 'Measured in the page' : 'Not measured for this run'}</span>
      </div>
      {measured && (
        <div className="mt-5 flex gap-10">
          {score != null && <Figure value={String(score)} label="Speed and accessibility score" tone={areaTone(score)} />}
          <Figure value={String(found.length)} label={found.length === 1 ? 'Issue to fix' : 'Issues to fix'} tone={found.length ? 'text-danger' : 'text-accent'} />
        </div>
      )}
      <ul className="mt-4">
        {kinds.map((k) => {
          const items = found.filter((f) => f.kind === k)
          const label = k === 'performance' ? 'Mobile speed' : 'Accessibility basics'
          if (report.checks?.[k] !== 'complete') return <li key={k} className="flex items-center justify-between gap-4 border-b border-line py-3 last:border-b-0"><span className="text-sm">{label}</span><Pill tone="neutral">Not measured</Pill></li>
          if (!items.length) return <li key={k} className="flex items-center justify-between gap-4 border-b border-line py-3 last:border-b-0"><span className="text-sm">{label}</span><Pill tone="ok">No issues</Pill></li>
          return items.map((f) => (
            <li key={f.title} className="flex items-center justify-between gap-4 border-b border-line py-3 last:border-b-0">
              <span className="min-w-0 text-sm">{f.title}</span>
              <Pill tone={f.severity === 'high' ? 'bad' : 'neutral'}>{f.severity === 'high' ? 'High' : f.severity === 'medium' ? 'Medium' : 'Low'}</Pill>
            </li>
          ))
        })}
      </ul>
    </Card>
  )
}

/** Technical checks, in the landing page's card style: every check that ran, passed or failed, with the details a click away. */
export function CheckCards({ report }: { report: Report }) {
  const pages = report.site_audit?.pages_scanned
  return (
    <section aria-labelledby="checks-title" className="report-print-section mt-12">
      <h2 id="checks-title" className="flex items-center gap-2 text-xl font-light tracking-tight">
        <ShieldCheckIcon weight="light" className="size-5 shrink-0 text-accent" aria-hidden />Technical launch checks
      </h2>
      <p className="mt-2 text-sm text-muted">{report.verified ? 'Includes the checks for verified domains.' : 'Passive public checks. Verify your domain to also check exposed files and leaked keys.'}</p>
      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <CheckCard title="SEO" icon={MagnifyingGlassIcon} note={pages ? `${pages} page${pages === 1 ? '' : 's'} checked` : 'Homepage'} score={report.launch_ready?.areas.seo} checks={SEO} report={report} />
        <CheckCard title="Security hygiene" icon={ShieldCheckIcon} note={report.verified ? 'Verified domain' : 'Passive checks'} score={report.launch_ready?.areas.security} checks={SECURITY} report={report} />
      </div>
      <div className="mt-4"><SpeedCard report={report} /></div>
    </section>
  )
}
