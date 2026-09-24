import { ListNumbersIcon, QuotesIcon } from '@phosphor-icons/react'
import { useState } from 'react'
import { EVIDENCE_RETENTION_DAYS, fingerprint, KIND_LABEL, PERSONA_LABEL, STATUS_LABEL, type Finding, type Run } from '../lib/runs'
import { AgentPresence, type AgentPresenceState } from './AgentPresence'
import { Card } from './Card'
import { CheckCards } from './CheckCards'
import { EvidenceTimeline } from './EvidenceTimeline'
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

// The report's headline says what happened, the way the landing page mock-up does ("0 of 3 test users reached the goal").
const OUTCOME: Record<Run['status'], string> = {
  running: 'The test user is still working',
  done: 'The test user reached the goal',
  gave_up: 'The test user gave up',
  budget: 'The test user ran out of steps',
  stuck: 'The test user got stuck',
  captcha: 'The test stopped at a CAPTCHA',
  stopped: 'The test ended early',
  safe_stop: 'Everything worked up to the send button',
  looping: 'Walkthru stopped a test user going in circles',
}

function Chip({ children }: { children: React.ReactNode }) {
  return <span className="rounded-full border border-line px-3 py-1 text-xs text-muted">{children}</span>
}

function hostOf(site: string): string {
  try {
    return new URL(site).host
  } catch {
    return site
  }
}

/** The report body. Shared by the signed-in report page and the public share page. */
export function ReportView({ run, ignore }: { run: Run; ignore?: IgnoreControls }) {
  const r = run.report
  const steps = run.steps ?? []
  const peak = Math.max(0, ...steps.map((s) => s.confusion))
  const isScan = run.kind === 'scan'
  const counts = { high: 0, medium: 0, low: 0 }
  for (const f of r?.findings ?? []) counts[f.severity]++
  const stopped = ['gave_up', 'budget', 'stuck', 'captcha', 'stopped'].includes(run.status)
  const agentState: AgentPresenceState = stopped ? 'stopped' : r ? 'complete' : 'observing'
  const agentActivity = stopped ? STATUS_LABEL[run.status] : r ? 'Report ready' : isScan ? 'Scanning this site' : 'Testing this flow'
  const host = hostOf(run.site)

  return (
    <article className="report-root">
      <header className="report-cover flex flex-wrap items-end justify-between gap-6">
        <div className="min-w-0">
          <p className="report-kicker hidden print:block">Launch readiness report</p>
          <p className="text-sm text-muted">Report for <span className="text-ink">{host}</span></p>
          <h1 className="mt-2 max-w-[22ch] text-3xl font-extralight tracking-[-0.03em] md:text-5xl">{isScan ? `Instant Scan of ${host}` : OUTCOME[run.status]}</h1>
          <div className="mt-4 flex flex-wrap gap-2">
            {!isScan && <Chip>Goal: {run.goal}</Chip>}
            {!isScan && <Chip>{PERSONA_LABEL[run.persona] ?? run.persona}</Chip>}
            {!isScan && steps.length > 0 && <Chip>{steps.length} step{steps.length === 1 ? '' : 's'}, peak confusion {peak} of 3</Chip>}
            {r && <Chip>{counts.high} high, {counts.medium} medium, {counts.low} low</Chip>}
            <Chip><time dateTime={run.created_at}>{new Date(run.created_at).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })}</time></Chip>
          </div>
          {r?.model && <p className="mt-3 text-xs text-muted">Test user and report: {r.model}</p>}
        </div>
        <AgentPresence activity={agentActivity} state={agentState} phase={0.32} />
      </header>

      {r ? (
        <div className="mt-10 grid gap-10 lg:grid-cols-[minmax(0,1fr)_20rem] lg:items-start">
          <div className="min-w-0">
            <p className="max-w-[64ch] text-lg leading-relaxed">{r.summary}</p>

            {/* The first thing a rerun owner wants to know. */}
            {r.comparison && <RerunComparison comparison={r.comparison} linkPrevious={!!ignore} />}

            {run.status === 'safe_stop' && (
              <p className="no-print mt-6 max-w-[64ch] rounded-2xl border border-line px-5 py-4 text-sm leading-relaxed text-muted">
                The test user stopped at the send button, so nothing was sent. Walkthru only sends on a verified domain, once per run, after the owner approves.{' '}
                <a href="/docs#verify" className="text-ink underline decoration-line underline-offset-4 transition hover:decoration-ink">Verify your domain</a> to test the full flow.
              </p>
            )}

            {r.first_impression && (
              <Card className="report-print-section mt-10 p-6" aria-label="First impression">
                <h2 className="flex items-center gap-2 text-sm font-medium"><QuotesIcon weight="light" className="size-5 text-accent" aria-hidden />First impression, five seconds in</h2>
                <p className="mt-4 max-w-[40ch] text-2xl leading-snug font-extralight tracking-tight">{r.first_impression.what}</p>
                <dl className="mt-5 grid gap-x-8 gap-y-4 text-sm sm:grid-cols-3">
                  <Item term="Who it is for" desc={r.first_impression.who} />
                  <Item term="What they would click first" desc={r.first_impression.first_click} />
                  <Item term="Trust signals" desc={r.first_impression.trust.join(', ') || 'None noticed'} />
                </dl>
              </Card>
            )}

            {!isScan && steps.length > 0 && <EvidenceTimeline steps={steps} />}
            {!isScan && steps.length > 0 && <RetentionNote run={run} />}

            {r.geo && <GeoReadiness geo={r.geo} findings={r.findings.filter((f) => f.kind === 'geo')} />}
            <CheckCards report={r} />
            {r.site_audit && <SiteAuditCoverage audit={r.site_audit} />}

            {ignore && r.findings.length > 0 && (
              <FixPrompt runId={run.id} paid={ignore.canIgnore} count={r.findings.filter((f) => !ignore.ignored[fingerprint(f)]).length} />
            )}

            <section aria-labelledby="all-findings-title" className="report-print-section mt-12">
              <h2 id="all-findings-title" className="text-xl font-light tracking-tight">All findings</h2>
              {r.findings.length === 0 ? (
                <p role="status" className="mt-4 text-sm text-muted">Nothing to report. Nice.</p>
              ) : (
                <ul className="mt-4 border-t border-line">
                  {r.findings.map((f, i) => <FindingRow key={i} f={f} ignore={ignore} />)}
                </ul>
              )}
            </section>
          </div>

          <aside className="grid gap-4 lg:sticky lg:top-24" aria-label="Scores and priorities">
            {/* `ignore` is only passed on the owner's page, so strangers on /r/ see the score but not the badge code. */}
            {r.launch_ready && <LaunchReady score={r.launch_ready} runId={run.id} isPublic={run.public} isOwner={!!ignore} />}
            {r.top_fixes.length > 0 && (
              <Card className="report-print-section p-6" aria-labelledby="top-fixes-title">
                <h2 id="top-fixes-title" className="flex items-center gap-2 text-sm font-medium"><ListNumbersIcon weight="light" className="size-5 text-accent" aria-hidden />Fix these first</h2>
                <ol className="mt-4 grid gap-3 text-sm leading-relaxed">
                  {r.top_fixes.map((f, i) => (
                    <li key={i} className="grid grid-cols-[1.5rem_1fr] gap-2">
                      <span className="text-muted tabular-nums">{i + 1}.</span>
                      <span>{f}</span>
                    </li>
                  ))}
                </ol>
              </Card>
            )}
          </aside>
        </div>
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
  const fp = fingerprint(f)
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

function Item({ term, desc }: { term: string; desc: string }) {
  return (
    <div>
      <dt className="text-xs text-muted">{term}</dt>
      <dd className="mt-1 leading-relaxed">{desc}</dd>
    </div>
  )
}
