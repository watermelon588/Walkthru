import { useState } from 'react'
import { EVIDENCE_RETENTION_DAYS, ignoredKey, KIND_LABEL, PERSONA_LABEL, STATUS_LABEL, type Brand, type Finding, type Run } from '../lib/runs'
import { BrandClosing, BrandCover } from './BrandCover'
import { AgentPresence, type AgentPresenceState } from './AgentPresence'
import { EvidenceTimeline } from './EvidenceTimeline'
import { SkeletonReport, Working } from './Loading'
import { LaunchReady } from './LaunchReady'
import { FixPrompt } from './FixPrompt'
import { AgentReadiness } from './AgentReadiness'
import { GeoReadiness } from './GeoReadiness'
import { KeywordMap } from './KeywordMap'
import { RerunComparison } from './RerunComparison'
import { SiteAuditCoverage } from './SiteAuditCoverage'
import { TestUsersCompared } from './TestUsersCompared'
import { FindingAssessment, ReportScope } from './ReportAssessment'
import { ChapterContents, ChapterPrompt, ChapterSection, CrossLinks, NextActions } from './ReportChapters'
import { PerformanceEvidence } from './PerformanceEvidence'
import { alsoAffects, CHAPTER_TITLE, chapterOf, chapters, findingIds, issueAnchor, nextActions } from '../lib/reportChapters'
import { OUTCOME_LABEL, reportProblem, type ReportAssessment, type ReportIssue } from '../lib/reportContract'

// What the server does while the report is pending, in its real order. Paced on a timer, not tied to server progress.
const RUNNING_STEPS = ['Reading the page like a stranger', 'Choosing the next click', 'Noting what feels confusing', 'Saving a screenshot of each important screen']
const REPORT_STEPS = ['Reading every step the test user took', 'Matching screenshots to moments of confusion', 'Checking SEO and AI search basics', 'Checking security headers', 'Ranking the fixes', 'Writing the summary']
const SCAN_STEPS = ['Fetching your homepage', 'Reading titles, links and sitemaps', 'Checking what AI crawlers can read', 'Checking security headers', 'Scoring Launch Ready', 'Writing the report']

/** Owner-only controls for accepting ("won't fix") findings. The public share page passes none. */
export type IgnoreControls = {
  ignored: Record<string, string>
  canIgnore: boolean
  onIgnore: (fp: string, reason: string) => Promise<void>
  onClear: (fp: string) => Promise<void>
}

/** The report body. Shared by the signed-in report page and the public share page. `brand` (Plus, owner only) prints
 *  the report in the owner's branding: their cover and color, no Walkthru marks. The screen view does not change. */
export function ReportView({ run, ignore, brand }: { run: Run; ignore?: IgnoreControls; brand?: Brand | null }) {
  const r = run.report
  const problem = reportProblem(r)
  if (problem) return <article className="report-root"><p role="alert" className="text-sm text-danger">{problem}</p></article>
  const assessment = r?.version === 2 ? r.assessment : null
  const ignored = ignore?.ignored ?? {}
  const chapterList = r ? chapters(r, run.kind, run.status, ignored) : []
  const ids = r ? findingIds(r.findings) : []
  const titles = Object.fromEntries(ids.map((id, i) => [id, r!.findings[i].title]))
  const steps = run.steps ?? []
  const peak = Math.max(0, ...steps.map((s) => s.confusion))
  const stuckAt = steps.findIndex((s) => s.confusion >= 2)
  const isScan = run.kind !== 'test'  // scans, watch checks and comparison parts have no journey
  const counts = { high: 0, medium: 0, low: 0 }
  for (const f of r?.findings ?? []) counts[f.severity]++
  const stopped = run.status !== 'running' && run.status !== 'done'
  const agentState: AgentPresenceState = stopped ? 'stopped' : r ? 'complete' : 'observing'
  const agentActivity = stopped
    ? STATUS_LABEL[run.status]
    : r
      ? 'Report ready'
      : isScan
        ? 'Scanning this homepage'
        : 'Testing this flow'

  return (
    <article className="report-root min-w-0 [overflow-wrap:anywhere]" data-branded={brand ? '' : undefined} style={brand ? ({ '--brand': brand.color } as React.CSSProperties) : undefined}>
      {brand && <BrandCover run={run} brand={brand} />}
      <header className="report-cover grid gap-6 sm:grid-cols-[1fr_auto] sm:items-end">
        <div>
          <p className="report-kicker font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Launch readiness report</p>
          <p className="mt-3 font-mono text-xs text-muted">{run.site}</p>
          <h1 className="mt-2 text-3xl font-extralight tracking-tight md:text-5xl">{isScan ? 'Instant Scan' : run.goal}</h1>
          <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted">
            <span>{PERSONA_LABEL[run.persona] ?? run.persona}</span>
            {!isScan && (assessment ? <span>{OUTCOME_LABEL[assessment.outcome]}</span> : <StatusPill status={run.status} />)}
            <time dateTime={run.created_at}>{new Date(run.created_at).toLocaleString()}</time>
            {r?.model && <span>Test user and report: {r.model}</span>}
          </div>
        </div>
        <AgentPresence activity={agentActivity} state={agentState} phase={0.32} />
      </header>

      {r ? (
        <>
          {assessment && <ReportScope assessment={assessment} />}
          <p className="mt-8 max-w-[64ch] text-lg leading-relaxed">{r.summary}</p>

          {!assessment && !isScan && stopped && <JourneyCoverage run={run} />}

          <NextActions actions={nextActions(r, ignored)} />
          <ChapterContents chapters={chapterList} />

          <section aria-label="Summary" className="report-summary mt-8 grid gap-px overflow-hidden rounded-2xl bg-line sm:grid-cols-3">
            <Stat label="Findings" value={String(r.findings.length)} note={`${counts.high} high / ${counts.medium} medium / ${counts.low} low`} />
            {isScan ? (
              <Stat label="First impression clarity" value={r.first_impression ? `${3 - r.first_impression.clarity} of 3` : 'Not judged'} note={r.first_impression ? '3 = instantly clear' : 'no readable text before JavaScript runs'} />
            ) : (
              <Stat label="Outcome" value={assessment ? OUTCOME_LABEL[assessment.outcome] : STATUS_LABEL[run.status]} note={`${steps.length} steps`} />
            )}
            <Stat label={isScan ? 'Security scan' : 'Peak confusion'} value={isScan ? (r.verified ? 'Full' : 'Headers only') : `${peak} of 3`} note={isScan ? (r.verified ? 'domain verified' : 'verify your domain for exposed files and secrets') : stuckAt >= 0 ? `first at step ${stuckAt + 1}` : 'no confusion recorded'} />
          </section>

          {/* `ignore` is only passed on the owner's page, so strangers on /r/ see the score but not the badge code. */}
          {r.launch_ready && <LaunchReady score={r.launch_ready} runId={run.id} isPublic={run.public} isScan={isScan} isOwner={!!ignore} />}

          {r.funnel && <FunnelNumbers funnel={r.funnel} />}

          {/* The first thing a rerun owner wants to know. */}
          {r.comparison && <RerunComparison comparison={r.comparison} linkPrevious={!!ignore} />}

          {run.status === 'safe_stop' && (
            <p className="no-print mt-6 max-w-[64ch] rounded-2xl border border-line px-5 py-4 text-sm leading-relaxed text-muted">
              {assessment ? 'An action was prevented by safety rules. Review recorded outcomes; the stopped action does not confirm completion or a website defect.' : 'The test user stopped at the send button, so nothing was sent. Walkthru only sends on a verified domain, once per run, after the owner approves.'}{' '}
              <a href="/docs#verify" className="text-ink underline decoration-line underline-offset-4 transition hover:decoration-ink">Verify your domain</a> to test the full flow.
            </p>
          )}
          {ignore && r.findings.length > 0 && (
            <FixPrompt runId={run.id} paid={ignore.canIgnore} count={r.findings.filter((f) => !ignore.ignored[ignoredKey(f, ignore.ignored)]).length} />
          )}

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

          {chapterList.map((c) => (
            <ChapterSection key={c.key} chapter={c}>
              {c.key === 'journey' && (
                <>
                  {!isScan && steps.length > 0 && <EvidenceTimeline steps={steps} branded={!!brand} />}
                  {!isScan && steps.length > 0 && <RetentionNote run={run} />}
                  {run.group_id && <TestUsersCompared run={run} owner={!!ignore} />}
                  {r.first_impression && (
                    <section aria-label="First impression" className="mt-10">
                      <h3 className="text-xl font-light tracking-tight">First impression, five seconds in</h3>
                      <dl className="mt-4 grid gap-4 sm:grid-cols-2">
                        <Item term="What this site does" desc={r.first_impression.what} />
                        <Item term="Who it is for" desc={r.first_impression.who} />
                        <Item term="What they would click first" desc={r.first_impression.first_click} />
                        <Item term="Trust signals" desc={r.first_impression.trust.join(', ') || 'none noticed'} />
                      </dl>
                    </section>
                  )}
                </>
              )}
              {c.key === 'performance' && <PerformanceEvidence measurements={r.site_audit?.mobile_vitals} />}
              {c.key === 'geo' && r.geo && <GeoReadiness geo={r.geo} />}
              {c.key === 'geo' && r.agent_ready && <AgentReadiness agent={r.agent_ready} />}
              {c.key === 'citations' && ignore && (
                <p className="no-print mt-4 text-sm"><a href="/app/visibility" className="text-ink underline decoration-line underline-offset-4 transition hover:decoration-ink">Open AI answers</a> for dated samples and their sources.</p>
              )}
              {c.key === 'keywords' && r.opportunities && r.opportunities.pages.length > 0 && <KeywordMap map={r.opportunities} />}
              {c.key === 'evidence' && r.site_audit && <SiteAuditCoverage audit={r.site_audit} />}
              {c.issue_ids.length > 0 && (
                <ul className="mt-6 border-t border-line">
                  {r.findings.map((f, i) => chapterOf(f) === c.key && (
                    <FindingRow key={i} id={ids[i]} f={f} ignore={ignore} assessment={assessment ?? undefined} issue={assessment?.issues.find((item) => item.finding_index === i)} />
                  ))}
                </ul>
              )}
              <CrossLinks ids={c.cross_links} titles={titles} />
              {ignore?.canIgnore && c.status === 'issues' && <ChapterPrompt runId={run.id} chapter={c} />}
            </ChapterSection>
          ))}
          {brand && <BrandClosing brand={brand} scan={isScan} />}
        </>
      ) : (
        <>
          {run.status === 'running'
            ? <Working className="mt-8" state="searching" every={6000} title="The test user is still working through the site" steps={RUNNING_STEPS} />
            : <Working className="mt-8" state="composing" title="Writing the report" steps={isScan ? SCAN_STEPS : REPORT_STEPS} />}
          {run.status !== 'running' && <SkeletonReport label="" className="mt-10 opacity-60" />}
          {!isScan && steps.length > 0 && <EvidenceTimeline steps={steps} />}
        </>
      )}
    </article>
  )
}

function JourneyCoverage({ run }: { run: Run }) {
  const actions = (run.steps ?? []).filter((step) => step.action !== 'done' && step.action !== 'give_up')
  const interrupted = actions.filter((step) => step.interrupted).length
  return (
    <section aria-label="Journey coverage" className="mt-5 max-w-[64ch] rounded-2xl border border-line px-5 py-4 text-sm leading-relaxed text-muted">
      <p className="font-medium text-ink">Partial journey: {STATUS_LABEL[run.status]}</p>
      <p className="mt-1">
        {actions.length === 0
          ? 'No journey actions were recorded. The requested flow was not verified.'
          : `${actions.length} ${actions.length === 1 ? 'action record is' : 'action records are'} available. The full requested flow was not verified.`}
        {interrupted > 0 && ` ${interrupted} ${interrupted === 1 ? 'action ended' : 'actions ended'} before the result was confirmed.`}
      </p>
      <p className="mt-1">Findings describe the recorded evidence and technical checks. An early stop does not establish a defect in the site.</p>
    </section>
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

function FindingRow({ id, f, ignore, assessment, issue }: { id: string; f: Finding; ignore?: IgnoreControls; assessment?: ReportAssessment; issue?: ReportIssue }) {
  const tone = f.severity === 'high' ? 'text-danger' : f.severity === 'medium' ? 'text-ink' : 'text-muted'
  const fp = ignoredKey(f, ignore?.ignored ?? {})
  const reason = ignore?.ignored[fp]
  const also = alsoAffects(f)
  return (
    <li id={issueAnchor(id)} className={`grid scroll-mt-24 gap-2 border-b border-line py-5 sm:grid-cols-[7rem_1fr] ${reason ? 'opacity-60' : ''}`}>
      <div className="flex gap-2 text-xs sm:flex-col sm:gap-1">
        <span className={`font-medium ${tone}`}>{f.severity}</span>
        <span className="text-muted">{KIND_LABEL[f.kind]}</span>
      </div>
      <div className="min-w-0">
        <h3 className="font-medium">{f.title}</h3>
        <p className="mt-1 font-mono text-[11px] text-muted">id: {id}</p>
        {also.length > 0 && (
          <p className="mt-1 text-xs text-muted">Also affects {also.map((key, i) => (
            <span key={key}>{i > 0 && ', '}<a href={`#chapter-${key}`} className="text-ink underline decoration-line underline-offset-4 transition hover:decoration-ink">{CHAPTER_TITLE[key]}</a></span>
          ))}</p>
        )}
        <p className="mt-1 leading-relaxed text-muted">{f.detail}</p>
        <p className="mt-2 leading-relaxed"><span className="text-muted">Fix: </span>{f.fix}</p>
        {f.evidence && (
          <>
            <details className="no-print mt-3 text-xs text-muted">
              <summary className="w-fit cursor-pointer py-1 text-ink">View evidence</summary>
              <p className="mt-2 whitespace-pre-wrap font-mono leading-relaxed [overflow-wrap:anywhere]">{f.evidence}</p>
            </details>
            <p className="print-only mt-3 whitespace-pre-wrap font-mono text-xs leading-relaxed text-muted [overflow-wrap:anywhere]">{f.evidence}</p>
          </>
        )}
        {ignore && <IgnoreControl fp={fp} reason={reason} controls={ignore} />}
        {assessment && issue && <FindingAssessment assessment={assessment} issue={issue} />}
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
  const tone = status === 'done' || status === 'safe_stop' ? 'text-accent' : ['running', 'looping', 'agent_lost', 'bot_wall', 'captcha'].includes(status) ? 'text-muted' : 'text-danger'
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
