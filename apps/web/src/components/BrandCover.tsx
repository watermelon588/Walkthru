import { PERSONA_LABEL, type Brand, type Run } from '../lib/runs'
import { band } from '../lib/score'

const host = (site: string) => {
  try {
    return new URL(site).host.replace(/^www\./, '')
  } catch {
    return site
  }
}
const longDate = (iso: string) => new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'long', year: 'numeric' })

function Mark({ brand, large }: { brand: Brand; large?: boolean }) {
  return brand.logo
    ? <img src={brand.logo} alt={brand.name} className={large ? 'brand-cover-logo' : 'brand-close-logo'} />
    : <span className={large ? 'brand-cover-monogram' : 'brand-close-monogram'} aria-hidden="true">{brand.name.trim()[0]?.toUpperCase()}</span>
}

/** Plus, printed report only: a full cover page in the owner's branding, in place of Walkthru's header (P4.3). */
export function BrandCover({ run, brand }: { run: Run; brand: Brand }) {
  const r = run.report
  const score = r?.launch_ready?.score ?? null
  const counts = { high: 0, medium: 0, low: 0 }
  for (const f of r?.findings ?? []) counts[f.severity]++
  const isScan = run.kind !== 'test'
  return (
    <section className="print-only brand-cover" aria-label="Report cover">
      <header className="brand-cover-top">
        <Mark brand={brand} large />
        {!brand.logo && <span className="brand-cover-name">{brand.name}</span>}
      </header>

      <div className="brand-cover-title">
        <p className="brand-cover-kicker">Launch readiness report</p>
        <h1>{host(run.site)}</h1>
        <p className="brand-cover-goal">{isScan ? 'Homepage scan: search, AI search readiness and security' : `Goal: ${run.goal}`}</p>
        {!isScan && <p className="brand-cover-meta">Test user: {PERSONA_LABEL[run.persona] ?? run.persona}</p>}
      </div>

      <div className="brand-cover-facts">
        <div>
          <p className="brand-cover-label">Launch Ready score</p>
          <p className="brand-cover-score">{score ?? 'N/A'}<span>{score === null ? '' : ' / 100'}</span></p>
          <p className="brand-cover-band">{score === null ? 'Not enough was measured for a score' : band(score).label}</p>
        </div>
        <div>
          <p className="brand-cover-label">Findings</p>
          <p className="brand-cover-count">{r?.findings.length ?? 0}</p>
          <p className="brand-cover-band">{counts.high} high, {counts.medium} medium, {counts.low} low</p>
        </div>
      </div>

      <footer className="brand-cover-foot">
        <span>Prepared by {brand.name} · {longDate(run.created_at)}</span>
        {brand.footer && <span>{brand.footer}</span>}
      </footer>
    </section>
  )
}

/** Plus, printed report only: who prepared the report and how it was made, on the last page. */
export function BrandClosing({ brand, scan }: { brand: Brand; scan: boolean }) {
  return (
    <section className="print-only brand-close" aria-label="About this report">
      <Mark brand={brand} />
      <div>
        <p className="brand-close-name">{brand.name}</p>
        <p>
          {scan
            ? 'The site was read the way search engines, AI search and browsers read it, and checked for search, AI search readiness, security hygiene, speed and accessibility.'
            : 'Automated test users worked through the site in a real browser, and every page they reached was checked for search, AI search readiness, security hygiene, speed and accessibility.'}
          {' '}Each finding cites the step, page or header it comes from.
        </p>
        {brand.footer && <p>{brand.footer}</p>}
      </div>
    </section>
  )
}
