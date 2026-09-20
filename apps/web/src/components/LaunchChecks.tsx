import { CheckCircleIcon, MagnifyingGlassIcon, WarningCircleIcon } from '@phosphor-icons/react'
import type { Finding } from '../lib/runs'

const checks = [
  { kind: 'seo' as const, label: 'Search readiness', description: 'Titles, descriptions, headings, links and crawl basics.', icon: MagnifyingGlassIcon },
  { kind: 'security' as const, label: 'Security hygiene', description: 'Passive headers and verified-domain exposure checks.', icon: WarningCircleIcon },
]

export function LaunchChecks({ findings, verified }: { findings: Finding[]; verified: boolean }) {
  return (
    <section aria-labelledby="launch-checks-title" className="report-print-section print-break-before mt-14">
      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Technical launch checks</p>
      <div className="mt-2 flex flex-wrap items-end justify-between gap-3">
        <h2 id="launch-checks-title" className="text-2xl font-light tracking-tight">Catch what the journey cannot see</h2>
        <p className="text-xs text-muted">{verified ? 'Verified-domain checks included' : 'Passive public checks only'}</p>
      </div>
      <div className="mt-5 grid gap-px overflow-hidden rounded-2xl bg-line sm:grid-cols-2">
        {checks.map(({ kind, label, description, icon: Icon }) => {
          const items = findings.filter((finding) => finding.kind === kind)
          const urgent = items.filter((finding) => finding.severity === 'high').length
          return (
            <article key={kind} className="bg-bg px-5 py-5">
              <div className="flex items-start justify-between gap-4">
                <Icon className={items.length ? 'size-5 text-danger' : 'size-5 text-accent'} weight="light" />
                <span className="font-mono text-xs text-muted">{items.length ? `${items.length} issue${items.length === 1 ? '' : 's'}` : 'clear'}</span>
              </div>
              <h3 className="mt-5 font-medium">{label}</h3>
              <p className="mt-1 text-sm leading-relaxed text-muted">{description}</p>
              <p className="mt-4 flex items-center gap-2 text-xs">
                {items.length ? <WarningCircleIcon className="size-4 text-danger" /> : <CheckCircleIcon className="size-4 text-accent" />}
                {items.length ? `${urgent} high priority` : 'No issues found in this scope'}
              </p>
            </article>
          )
        })}
      </div>
    </section>
  )
}
