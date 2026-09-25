import { useState } from 'react'
import { EVIDENCE_RETENTION_DAYS, ignoredKey, KIND_LABEL, PERSONA_LABEL, STATUS_LABEL, type Finding, type Run } from '../lib/runs'
import { AgentPresence, type AgentPresenceState } from './AgentPresence'
import { EvidenceTimeline } from './EvidenceTimeline'
import { LaunchChecks } from './LaunchChecks'
import { LaunchReady } from './LaunchReady'
import { FixPrompt } from './FixPrompt'
import { GeoReadiness } from './GeoReadiness'
import { RerunComparison } from './RerunComparison'
import { SiteAuditCoverage } from './SiteAuditCoverage'

/** Owner-only controls for accepting ("won't fix") findings. The public share page passes none. */
export type IgnoreControls = {
  ignored: Record<string, string>
  canIgnore: boolean
  onIgnore: (fp: string, reason: string) => Promise<void>
  onClear: (fp: string) => Promise<void>
}

/** The report body. Shared by the signed-in report page and the public share page. */
export function ReportView({ run, ignore }: { run: Run; ignore?: IgnoreControls }) {
  const r = run.report
  const steps = run.steps ?? []
  const peak = Math.max(0, ...steps.map((s) => s.confusion))
  const stuckAt = steps.findIndex((s) => s.confusion >= 2)
  const isScan = run.kind !== 'test'  // scans, watch checks and comparison parts have no journey
  const counts = { high: 0, medium: 0, low: 0 }
  for (const f of r?.findings ?? []) counts[f.severity]++
  const stopped = ['gave_up', 'budget', 'stuck', 'captcha', 'stopped'].includes(run.status)
  const agentState: AgentPresenceState = stopped ? 'stopped' : r ? 'complete' : 'observing'
  const agentActivity = stopped
    ? STATUS_LABEL[run.status]
    : r
      ? 'Report ready'
      : isScan
        ? 'Scanning this homepage'
        : 'Testing this flow'

  return (
    <article className="report-root">
      <header className="report-cover grid gap-6 sm:grid-cols-[1fr_auto] sm:items-end">
        <div>
          <p className="report-kicker font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Launch readiness report</p>
          <p className="mt-3 font-mono text-xs text-muted">{run.site}</p>
          <h1 className="mt-2 text-3xl font-extralight tracking-tight md:text-5xl">{isScan ? 'Instant Scan' : run.goal}</h1>
          <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted">
            <span>{PERSONA_LABEL[run.persona] ?? run.persona}</span>
            {!isScan && <StatusPill status={run.status} />}
            <time dateTime={run.created_at}>{new Date(run.created_at).toLocaleString()}</time>
            {r?.model && <span>Test user and report: {r.model}</span>}
          </div>
        </div>
        <AgentPresence activity={agentActivity} state={agentState} phase={0.32} />
      </header>

      {r ? (
        <>
          <p className="mt-8 max-w-[64ch] text-lg leading-relaxed">{r.summary}</p>

          <section aria-label="Summary" className="report-summary mt-8 grid gap-px overflow-hidden rounded-2xl bg-line sm:grid-cols-3">
            <Stat label="Findings" value={String(r.findings.length)} note={`${counts.high} high / ${counts.medium} medium / ${counts.low} low`} />
            {isScan ? (
              <Stat label="First impression clarity" value={r.first_impression ? `${3 - r.first_impression.clarity} of 3` : 'Not judged'} note={r.first_impression ? '3 = instantly clear' : 'no readable text before JavaScript runs'} />
            ) : (
              <Stat label="Outcome" value={STATUS_LABEL[run.status]} note={`${steps.length} steps`} />
            )}
            <Stat label={isScan ? 'Security scan' : 'Peak confusion'} value={isScan ? (r.verified ? 'Full' : 'Headers only') : `${peak} of 3`} note={isScan ? (r.verified ? 'domain verified' : 'verify your domain for exposed files and secrets') : stuckAt >= 0 ? `first at step ${stuckAt + 1}` : 'never confused'} />
          </section>

          {/* `ignore` is only passed on the owner's page, so strangers on /r/ see the score but not the badge code. */}
          {r.launch_ready && <LaunchReady score={r.launch_ready} runId={run.id} isPublic={run.public} isScan={isScan} isOwner={!!ignore} />}

          {r.funnel && <FunnelNumbers funnel={r.funnel} />}

          {/* The first thing a rerun owner wants to know. */}
          {r.comparison && <RerunComparison comparison={r.comparison} linkPrevious={!!ignore} />}

          {run.status === 'safe_stop' && (
            <p className="no-print mt-6 max-w-[64ch] rounded-2xl border border-line px-5 py-4 text-sm leading-relaxed text-muted">
              The test user stopped at the send button, so nothing was sent. Walkthru only sends on a verified domain, once per run, after the owner approves.{' '}
              <a href="/docs#verify" className="text-ink underline decoration-line underline-offset-4 transition hover:decoration-ink">Verify your domain</a> to test the full flow.
            </p>
          )}
          {!isScan && steps.length > 0 && <EvidenceTimeline steps={steps} />}
          {!isScan && steps.length > 0 && <RetentionNote run={run} />}

          {r.first_impression && (
            <section aria-label="First impression" className="report-print-section mt-12">
              <h2 className="text-xl font-light tracking-tight">First impression, five seconds in</h2>
              <dl className="mt-4 grid gap-4 sm:grid-cols-2">
                <Item term="What this site does" desc={r.first_impression.what} />
                <Item term="Who it is for" desc={r.first_impression.who} />
                <Item term="What they would click first" desc={r.first_impression.first_click} />
                <Item term="Trust signals" desc={r.first_impression.trust.join(', ') || 'none noticed'} />
              </dl>
            </section>
          )}

          {ignore && r.findings.length > 0 && (
            <FixPrompt runId={run.id} paid={ignore.canIgnore} count={r.findings.filter((f) => !ignore.ignored[ignoredKey(f, ignore.ignored)]).length} />
          )}

          {r.geo && <GeoReadiness geo={r.geo} />}

          {r.site_audit && <SiteAuditCoverage audit={r.site_audit} />}

          <LaunchChecks findings={r.findings} verified={r.verified} states={r.checks} reasons={r.check_reasons} />

          {r.top_fixes.length > 0 && (
            <section aria-label="Top fixes" className="report-print-section print-break-before mt-14">
              <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Prioritized fixes</p>
              <h2 className="mt-2 text-2xl font-light tracking-tight">Fix these first</h2>
              <ol className="mt-5 overflow-hidden rounded-2xl border border-line bg-line">
                {r.top_fixes.map((f, i) => (
                  <li key={i} className="grid grid-cols-[3rem_1fr] gap-3 border-b border-line bg-bg px-5 py-4 leading-relaxed last:border-b-0">
                    <span className="font-mono text-xs text-muted pt-1">P{String(i + 1).padStart(2, '0')}</span>
                    <span>{f}</span>
                  </li>
                ))}
              </ol>
            </section>
          )}

          <section aria-label="All findings" className="report-print-section mt-12">
            <h2 className="text-xl font-light tracking-tight">All findings</h2>
            {r.findings.length === 0 ? (
              <p role="status" className="mt-4 text-sm text-muted">Nothing to report. Nice.</p>
            ) : (
              <ul className="mt-4 border-t border-line">
                {r.findings.map((f, i) => <FindingRow key={i} f={f} ignore={ignore} />)}
              </ul>
            )}
          </section>
        </>
      ) : (
        <>
          <p role="status" className="mt-8 text-muted">
            {run.status === 'running' ? 'The test user is still working through the site.' : 'Writing the report. This takes about half a minute.'}
          </p>
          {!isScan && steps.length > 0 && <EvidenceTimeline steps={steps} />}
        </>
      )}
    </article>
  )
}

function RetentionNote({ run }: { run: Run }) {
  const expires = new Date(new Date(run.created_at).getTime() + EVIDENCE_RETENTION_DAYS * 86_400_000)
  return (
    <p className="mt-3 text-xs text-muted">
      {run.evidence_purged_at
        ? `Screenshots were deleted on ${new Date(run.evidence_purged_at).toLocaleDateString()}, ${EVIDENCE_RETENTION_DAYS} days after the run. The steps and report are kept.`
        : `Screenshots are kept for ${EVIDENCE_RETENTION_DAYS} days and deleted automatically on ${expires.toLocaleDateString()}. The steps and report are kept until you delete the run.`}
    </p>
  )
}

function FindingRow({ f, ignore }: { f: Finding; ignore?: IgnoreControls }) {
  const tone = f.severity === 'high' ? 'text-danger' : f.severity === 'medium' ? 'text-ink' : 'text-muted'
  const fp = ignoredKey(f, ignore?.ignored ?? {})
  const reason = ignore?.ignored[fp]
  return (
    <li className={`grid gap-2 border-b border-line py-5 sm:grid-cols-[7rem_1fr] ${reason ? 'opacity-60' : ''}`}>
      <div className="flex gap-2 text-xs sm:flex-col sm:gap-1">
        <span className={`font-medium ${tone}`}>{f.severity}</span>
        <span className="text-muted">{KIND_LABEL[f.kind]}</span>
      </div>
      <div className="min-w-0">
        <h3 className="font-medium">{f.title}</h3>
        <p className="mt-1 leading-relaxed text-muted">{f.detail}</p>
        <p className="mt-2 leading-relaxed"><span className="text-muted">Fix: </span>{f.fix}</p>
        {f.evidence && <p className="mt-2 truncate font-mono text-xs text-muted">{f.evidence}</p>}
        {ignore && <IgnoreControl fp={fp} reason={reason} controls={ignore} />}
      </div>
    </li>
  )
}

function IgnoreControl({ fp, reason, controls }: { fp: string; reason?: string; controls: IgnoreControls }) {
  const [open, setOpen] = useState(false)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const run = async (action: () => Promise<void>) => {
    setBusy(true)
    setError(null)
    try {
      await action()
      setOpen(false)
      setText('')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'That did not work. Try again.')
    } finally {
      setBusy(false)
    }
  }
  const link = 'text-xs text-muted underline decoration-line underline-offset-4 transition hover:text-ink hover:decoration-ink disabled:opacity-50'
  if (reason) {
    return (
      <p className="no-print mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
        <span>Ignored: {reason}</span>
        <button type="button" className={link} disabled={busy} onClick={() => run(() => controls.onClear(fp))}>Stop ignoring</button>
        {error && <span role="alert" className="text-danger">{error}</span>}
      </p>
    )
  }
  if (!controls.canIgnore) return null
  if (!open) {
    return <button type="button" className={`no-print mt-3 ${link}`} onClick={() => setOpen(true)}>Ignore</button>
  }
  const field = `ignore-${fp}`
  return (
    <form className="no-print mt-3 grid gap-2 sm:max-w-md" onSubmit={(e) => { e.preventDefault(); if (text.trim()) void run(() => controls.onIgnore(fp, text.trim())) }}>
      <label htmlFor={field} className="text-xs text-muted">Why is this fine for your site? Reruns will leave it out.</label>
      <input id={field} value={text} onChange={(e) => setText(e.target.value)} maxLength={200} required autoFocus
        className="rounded-xl border border-line bg-bg px-3 py-2 text-sm text-ink" />
      <div className="flex gap-3">
        <button type="submit" className="text-xs font-medium text-ink disabled:opacity-50" disabled={busy || !text.trim()}>{busy ? 'Saving...' : 'Ignore this finding'}</button>
        <button type="button" className={link} onClick={() => setOpen(false)}>Cancel</button>
      </div>
      {error && <p role="alert" className="text-xs text-danger">{error}</p>}
    </form>
  )
}

export function StatusPill({ status }: { status: Run['status'] }) {
  // looping is Walkthru's own stop, never the site's fault, so it is not shown as a failure.
  const tone = status === 'done' || status === 'safe_stop' ? 'text-accent' : status === 'running' || status === 'looping' ? 'text-muted' : 'text-danger'
  return <span className={`rounded-full border border-line px-2.5 py-0.5 ${tone}`}>{STATUS_LABEL[status]}</span>
}

function Stat({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="bg-bg px-5 py-4">
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-1 text-lg font-light">{value}</p>
      {note && <p className="text-xs text-muted">{note}</p>}
    </div>
  )
}

function Item({ term, desc }: { term: string; desc: string }) {
  return (
    <div className="rounded-2xl border border-line px-5 py-4">
      <dt className="text-xs text-muted">{term}</dt>
      <dd className="mt-1 leading-relaxed">{desc}</dd>
    </div>
  )
}

/** Signup funnel numbers (paid runs), with the last run of the same goal alongside when there is one. */
function FunnelNumbers({ funnel }: { funnel: NonNullable<NonNullable<Run['report']>['funnel']> }) {
  const was = funnel.previous
  const show = (v: number | null, unit = '') => (v == null ? 'Not reached' : `${v}${unit}`)
  const note = (v: number | null | undefined, unit = '') => (was && v !== undefined ? `was ${v == null ? 'not reached' : `${v}${unit}`}` : undefined)
  const usefulNote = [funnel.seconds_to_first_useful == null ? 'time not measured' : `after ${funnel.seconds_to_first_useful} s`,
    was ? `was ${was.first_useful_step == null ? 'not reached' : `step ${was.first_useful_step}`}${was.seconds_to_first_useful == null ? '' : ` after ${was.seconds_to_first_useful} s`}` : null].filter(Boolean).join(' · ')
  return (
    <section aria-label="Signup funnel" className="report-summary mt-4 grid gap-px overflow-hidden rounded-2xl bg-line sm:grid-cols-3 lg:grid-cols-5">
      <Stat label="Steps to the goal" value={show(funnel.steps_to_goal)} note={note(was?.steps_to_goal)} />
      <Stat label="First useful screen" value={funnel.first_useful_step == null ? 'Not reached' : `Step ${funnel.first_useful_step}`} note={usefulNote} />
      <Stat label="Fields typed" value={String(funnel.fields_typed)} note={note(was?.fields_typed)} />
      <Stat label="Errors seen" value={String(funnel.errors_seen)} note={note(was?.errors_seen)} />
      <Stat label="Safe stops" value={String(funnel.safe_stops)} note={note(was?.safe_stops)} />
    </section>
  )
}
