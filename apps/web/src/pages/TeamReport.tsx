import { ArrowLeftIcon, ChatCircleIcon } from '@phosphor-icons/react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'
import { AppShell } from '../components/AppShell'
import { ReportView } from '../components/ReportView'
import { btnGhost } from '../components/Shared'
import { Chat } from '../components/team/Chat'
import { getRun, type Run } from '../lib/runs'
import { getMembers, useTeamLive, type Members } from '../lib/teams'
import { SkeletonReport } from '../components/Loading'
import type { Cell } from '../lib/export'
import { ExportBar } from '../components/ExportBar'

const findingsRows = (run: Run): Cell[][] => [['kind', 'severity', 'title', 'detail', 'fix', 'evidence'], ...(run.report?.findings ?? []).map((f) => [f.kind, f.severity, f.title, f.detail, f.fix, f.evidence])]

type State = { kind: 'loading' } | { kind: 'ready'; run: Run; team: Members } | { kind: 'missing' } | { kind: 'error'; message: string }

/** A report shared into a workspace, read-only for members, with the team's comment thread under it. The run is read
 *  through row-level security (members of a workspace it is shared into may read it and its screenshots). */
export default function TeamReport() {
  const { id = '', runId = '' } = useParams()
  const [state, setState] = useState<State>({ kind: 'loading' })
  const [signal, setSignal] = useState(0)
  const live = useTeamLive(id, (table) => { if (table === 'team_messages') setSignal((n) => n + 1) })

  useEffect(() => {
    let timer: number | undefined
    const load = () =>
      Promise.all([getRun(runId), getMembers(id)])
        .then(([run, team]) => {
          setState(run ? { kind: 'ready', run, team } : { kind: 'missing' })
          if (run && (run.status === 'running' || !run.report)) timer = window.setTimeout(load, 5000)
        })
        .catch((e: Error) => setState(/not a member|No workspace/i.test(e.message) ? { kind: 'missing' } : { kind: 'error', message: e.message }))
    load()
    return () => window.clearTimeout(timer)
  }, [id, runId])

  return (
    <AppShell title="Shared report">
      <Link to={`/app/team/${id}/reports`} className="no-print inline-flex items-center gap-1.5 text-sm text-muted hover:text-ink">
        <ArrowLeftIcon className="size-4" /> Workspace reports
      </Link>

      {state.kind === 'loading' && <SkeletonReport label="Loading the report" className="mt-8" />}
      {state.kind === 'missing' && <p role="status" className="mt-8 text-muted">This report is not shared in this workspace, or you are not a member.</p>}
      {state.kind === 'error' && <p role="alert" className="mt-8 text-sm text-danger">Could not load the report: {state.message}</p>}

      {state.kind === 'ready' && (
        <div className="mt-6">
          <div className="no-print mb-8 flex flex-wrap items-center gap-2">
            <a href="#comments" className={btnGhost}><ChatCircleIcon weight="light" className="size-4" /> Comments</a>
            <ExportBar filename={`walkthru-${state.run.id.slice(0, 8)}`} csv={() => findingsRows(state.run)} />
          </div>
          <ReportView run={state.run} />
          <section id="comments" aria-labelledby="comments-heading" className="no-print mt-16 scroll-mt-24 border-t border-line pt-10">
            <h2 id="comments-heading" className="text-2xl font-light tracking-tight">Team comments</h2>
            <p className="mt-2 mb-6 max-w-[60ch] text-sm leading-relaxed text-muted">Only members of this workspace see these. Mention someone with @ to get their attention.</p>
            <Chat teamId={id} thread={`run:${runId}`} me={state.team.me.user_id} members={state.team.members} canChat={state.team.me.can.chat}
              canModerate={state.team.me.can.manage_members} live={live} signal={signal} title="Comments on this report" empty="No comments yet. Point at a step, a screenshot or a finding." compact />
          </section>
        </div>
      )}
    </AppShell>
  )
}
