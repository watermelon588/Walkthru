import { Link } from 'react-router'
import { PERSONA_LABEL, timeAgo, type RunSummary } from '../lib/runs'
import type { HistoryState } from '../lib/runHistory'
import { StatusPill } from './ReportView'
import { Orb, SkeletonRows } from './Loading'

const firstRun = [
  { title: 'Install the extension', body: 'Add Walkthru to Chrome and pin the bird to your toolbar.', link: 'How to install', href: '/docs#install' },
  { title: 'Connect it', body: 'Use Connect extension above so tests run as you.', link: 'Why it is safe', href: '/security#extension' },
  { title: 'Start a test', body: 'Open your site, click the bird and give the test user one goal.', link: 'Write a good goal', href: '/docs#goals' },
]

export function RunHistoryPanel({ runs, refresh, more, endRun, endingRun, runActionError }: {
  runs: HistoryState<RunSummary>
  refresh: () => void
  more: () => void
  endRun: (run: RunSummary) => void
  endingRun: string | null
  runActionError: string | null
}) {
  return (
      <section aria-labelledby="recent-runs-title" className="mt-14">
        <div className="mb-5 flex items-end justify-between gap-4">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">History</p>
            <h2 id="recent-runs-title" className="mt-2 text-2xl font-light tracking-tight">Recent runs</h2>
          </div>
          {runs.kind === 'ready' && <span className="font-mono text-xs text-muted">{runs.runs.length} loaded</span>}
        </div>
        {runs.kind === 'loading' && (
          <SkeletonRows label="Loading runs" rows={4} />
        )}
        {runs.kind === 'error' && (
          <div role="alert" className="text-sm text-danger">Could not load runs: {runs.message} <button type="button" onClick={refresh} className="ml-2 text-ink underline">Try again</button></div>
        )}
        {runs.kind === 'ready' && runs.runs.length === 0 && (
          <div role="status" className="relative isolate overflow-hidden rounded-2xl bg-surface px-6 py-12 text-center">
            <Orb size={420} state="connecting" speed={0.5} className="pointer-events-none absolute top-1/2 left-1/2 -z-10 -translate-x-1/2 -translate-y-1/2 opacity-25" />
            <p className="text-lg font-light">No runs yet.</p>
            <p className="mx-auto mt-2 max-w-[44ch] text-sm leading-relaxed text-muted">
              Connect the extension, open the site you want tested, click the Walkthru bird in the toolbar and start a test.
            </p>
            <ol className="mx-auto mt-8 grid max-w-3xl gap-px overflow-hidden rounded-2xl bg-line text-left sm:grid-cols-3">
              {firstRun.map((s, i) => (
                <li key={s.title} className="flex flex-col bg-bg px-5 py-5">
                  <span className="grid size-6 place-items-center rounded-full border border-line font-mono text-[11px] text-muted">{i + 1}</span>
                  <h3 className="mt-4 text-sm font-medium">{s.title}</h3>
                  <p className="mt-1 flex-1 text-xs leading-relaxed text-muted">{s.body}</p>
                  <Link to={s.href} className="mt-4 self-start text-xs text-ink underline decoration-line underline-offset-4 transition hover:decoration-ink">{s.link}</Link>
                </li>
              ))}
            </ol>
          </div>
        )}
        {runs.kind === 'ready' && runs.runs.length > 0 && (
          <>
          {runs.runs.some((run) => run.status === 'running') && (
            <p className="mb-4 max-w-[64ch] text-sm leading-relaxed text-muted">
              A run stays open when its browser tab or extension closes before the journey finishes. End it to preserve the completed steps and build a partial report.
            </p>
          )}
          {runActionError && <p role="alert" className="mb-4 text-sm text-danger">Could not end the run: {runActionError}</p>}
          <ol id="run-history-list" aria-busy={runs.loadingMore} className="grid gap-px overflow-hidden rounded-2xl bg-line">
            {runs.runs.map((r) => (
              <li key={r.id} className="grid bg-bg transition-colors hover:bg-surface sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
                <Link to={r.kind === 'compare' ? `/app/compare/${r.id}` : `/app/runs/${r.id}`} className="min-w-0 px-5 pt-4 pb-2 focus-visible:outline-2 focus-visible:outline-accent sm:py-4">
                  <div className="min-w-0">
                    <p className="truncate">{r.kind === 'scan' ? 'Instant Scan' : r.kind === 'watch' ? 'Weekly watch' : r.goal}</p>
                    <p className="mt-0.5 truncate font-mono text-xs text-muted">{r.site}</p>
                  </div>
                </Link>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-2 px-5 pb-4 text-xs text-muted sm:justify-end sm:py-4 sm:pl-0">
                    <span>{r.kind === 'test' ? PERSONA_LABEL[r.persona] ?? r.persona : r.kind === 'watch' ? 'Weekly watch' : r.kind === 'compare' ? 'Comparison' : 'Instant Scan'}</span>
                    {r.kind === 'test' && <StatusPill status={r.status} />}
                    <time dateTime={r.created_at}>{timeAgo(r.created_at)}</time>
                    {r.status === 'running' && (
                      <button
                        type="button"
                        onClick={() => endRun(r)}
                        disabled={endingRun !== null}
                        aria-label={`End ${r.goal} and build its partial report`}
                        className="rounded-full border border-line px-3 py-1.5 text-xs text-ink transition-colors hover:bg-bg disabled:opacity-50"
                      >
                        {endingRun === r.id ? 'Ending...' : 'End and report'}
                      </button>
                    )}
                </div>
              </li>
            ))}
          </ol>
          <div className="mt-5 flex flex-wrap items-center gap-3">
            {runs.nextCursor && <button type="button" onClick={more} disabled={runs.loadingMore} aria-controls="run-history-list" className="min-h-11 rounded-full border border-line px-5 py-2 text-sm text-ink hover:bg-surface disabled:opacity-50">{runs.loadingMore ? 'Loading more...' : runs.moreError ? 'Try loading more' : 'Load more'}</button>}
            {runs.moreError && <p role="alert" className="text-sm text-danger">Could not load more runs: {runs.moreError}</p>}
            <p role="status" aria-live="polite" className="text-xs text-muted">{runs.loadingMore ? 'Reading older runs.' : `${runs.runs.length} runs loaded.${runs.nextCursor ? '' : ' End of history.'}`}</p>
          </div>
          </>
        )}
      </section>
  )
}
