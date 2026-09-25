import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { fingerprint, groupRuns, PERSONA_LABEL, STATUS_LABEL, type Finding, type Run } from '../lib/runs'

type State = { kind: 'loading' } | { kind: 'ready'; runs: Run[] } | { kind: 'error' }

/** Same rule as `_same` in apps/api/app/agent/compare.py: equal fingerprints, or model-written UX titles that share
 *  most of their words (they vary between test users describing the same problem). */
function sameProblem(a: Finding, b: Finding): boolean {
  if (fingerprint(a) === fingerprint(b)) return true
  if (a.kind !== 'ux' || b.kind !== 'ux') return false
  const words = (t: string) => new Set((t.toLowerCase().match(/[a-z]+/g) ?? []).filter((w) => w.length > 3).map((w) => w.slice(0, 5)))
  const wa = words(a.title), wb = words(b.title)
  const shared = [...wa].filter((w) => wb.has(w)).length
  const union = new Set([...wa, ...wb]).size
  return union > 0 && shared / union >= 0.5
}

type Shared = { finding: Finding; who: string[] }

/** Problems from the journeys (UX findings) grouped across test users, most shared first. Code only, no model. */
function sharedProblems(runs: Run[]): Shared[] {
  const groups: Shared[] = []
  for (const run of runs) {
    const who = PERSONA_LABEL[run.persona] ?? run.persona
    for (const finding of run.report?.findings.filter((f) => f.kind === 'ux') ?? []) {
      const group = groups.find((g) => sameProblem(g.finding, finding))
      if (!group) groups.push({ finding, who: [who] })
      else if (!group.who.includes(who)) group.who.push(who)
    }
  }
  const rank = { high: 0, medium: 1, low: 2 }
  return groups.filter((g) => g.who.length > 1).sort((a, b) => b.who.length - a.who.length || rank[a.finding.severity] - rank[b.finding.severity])
}

/** Plus: several test users on one goal, side by side in every report of the set (P4.2). */
export function TestUsersCompared({ run, owner }: { run: Run; owner: boolean }) {
  const [state, setState] = useState<State>({ kind: 'loading' })
  const groupId = run.group_id
  useEffect(() => {
    if (!groupId) return
    groupRuns(groupId).then((runs) => setState({ kind: 'ready', runs })).catch(() => setState({ kind: 'error' }))
  }, [groupId, run.status, run.report])

  if (!groupId || state.kind === 'error') return null
  if (state.kind === 'loading') return <div aria-busy="true" aria-label="Loading the other test users" className="no-print mt-12 h-32 animate-pulse rounded-2xl bg-surface motion-reduce:animate-none" />
  const runs = state.runs
  if (runs.length < 2) return null
  const shared = sharedProblems(runs)
  const writing = runs.filter((r) => !r.report).length
  const link = (r: Run) => (owner ? `/app/runs/${r.id}` : r.public ? `/r/${r.id}` : null)

  return (
    <section aria-labelledby="test-users-compared" className="report-print-section print-break-before mt-14">
      <p className="report-kicker font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Several test users</p>
      <h2 id="test-users-compared" className="mt-2 text-2xl font-light tracking-tight">{runs.length} test users tried this goal</h2>
      <p className="mt-2 max-w-[64ch] text-sm leading-relaxed text-muted">Each started on the same page with the same goal. Where several of them got stuck on the same thing, fix that first.</p>

      <div className="mt-6 overflow-x-auto rounded-2xl border border-line">
        <table className="w-full min-w-[34rem] border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-line text-xs text-muted">
              <th scope="col" className="px-5 py-3 font-normal">Test user</th>
              <th scope="col" className="px-5 py-3 font-normal">Outcome</th>
              <th scope="col" className="px-5 py-3 font-normal">Steps</th>
              <th scope="col" className="px-5 py-3 font-normal">Peak confusion</th>
              <th scope="col" className="px-5 py-3 font-normal"><span className="sr-only">Report</span></th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => {
              const steps = r.steps ?? []
              const peak = Math.max(0, ...steps.map((s) => s.confusion))
              const here = r.id === run.id
              const to = link(r)
              return (
                <tr key={r.id} className={`border-b border-line last:border-b-0 ${here ? 'bg-surface' : ''}`}>
                  <th scope="row" className="px-5 py-3 font-normal text-ink">{PERSONA_LABEL[r.persona] ?? r.persona}</th>
                  <td className={`px-5 py-3 ${r.status === 'done' || r.status === 'safe_stop' ? 'text-accent' : r.status === 'running' || r.status === 'looping' ? 'text-muted' : 'text-danger'}`}>{STATUS_LABEL[r.status]}</td>
                  <td className="px-5 py-3 font-mono text-xs text-muted">{steps.length}</td>
                  <td className="px-5 py-3 font-mono text-xs text-muted">{peak} of 3</td>
                  <td className="px-5 py-3 text-right text-xs">
                    {here ? <span className="text-muted">This report</span> : to ? <Link to={to} className="no-print text-ink underline decoration-line underline-offset-4 hover:decoration-ink">Open report</Link> : null}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <h3 className="mt-8 text-lg font-light">Problems several test users hit</h3>
      {shared.length > 0 ? (
        <ul className="mt-3 border-t border-line">
          {shared.map(({ finding, who }) => (
            <li key={finding.title} className="grid gap-1 border-b border-line py-4 sm:grid-cols-[9rem_1fr]">
              <span className="font-mono text-xs text-muted">{who.length} of {runs.length} test users</span>
              <div className="min-w-0">
                <p className={finding.severity === 'high' ? 'text-danger' : 'text-ink'}>{finding.title}</p>
                <p className="mt-1 text-sm text-muted">{who.join(', ')}</p>
                <p className="mt-2 text-sm leading-relaxed"><span className="text-muted">Fix: </span>{finding.fix}</p>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-sm leading-relaxed text-muted">No problem was hit by more than one test user{writing ? ' so far' : ''}. Each report lists what its own test user ran into.</p>
      )}
      {writing > 0 && <p role="status" className="no-print mt-3 text-xs text-muted">{writing} report{writing > 1 ? 's are' : ' is'} still being written; this section fills in as they finish.</p>}
    </section>
  )
}
