import { useState } from 'react'
import { Link } from 'react-router'
import { timeAgo } from '../../lib/runs'
import { describe, getActivity, type Overview as Data, type TeamEvent } from '../../lib/teams'
import { AccountAvatar } from '../AccountAvatar'

const host = (url: string) => url.replace(/^https?:\/\//, '').replace(/\/$/, '')

/** The workspace home: what needs fixing, each site's latest score, who is here and what happened. */
export function Overview({ team }: { team: Data }) {
  const base = `/app/team/${team.team.id}`
  const f = team.findings
  // The latest events come with the overview (and refresh with it); older pages are added on request.
  const [earlier, setEarlier] = useState<TeamEvent[]>([])
  const [more, setMore] = useState<boolean | null>(null)
  const oldest = team.activity.at(-1)?.id ?? 0
  const events = [...team.activity, ...earlier.filter((e) => e.id < oldest)]

  async function older() {
    const page = await getActivity(team.team.id, events.at(-1)?.id).catch(() => null)
    if (!page) return
    setEarlier((current) => [...current, ...page.events])
    setMore(page.has_more)
  }

  const steps = [
    { done: team.members.length > 1, text: 'Invite your team or your client', to: `${base}/members` },
    { done: team.reports > 0, text: 'Share a report (or turn on auto-share)', to: `${base}/settings` },
    { done: events.some((e) => e.type.startsWith('finding.')), text: 'Give a finding a status and an owner', to: `${base}/findings` },
  ]
  const stats = [
    { label: 'To fix', value: f.open + f.in_progress, to: `${base}/findings` },
    { label: 'High, still open', value: f.high_open, to: `${base}/findings`, danger: f.high_open > 0 },
    { label: 'Assigned to you', value: f.mine, to: `${base}/findings` },
    { label: 'Found again after a fix', value: f.seen_again, to: `${base}/findings`, danger: f.seen_again > 0 },
    { label: 'Reports shared', value: team.reports, to: `${base}/reports` },
  ]

  return (
    <div className="grid gap-12">
      {steps.some((s) => !s.done) && (
        <section aria-labelledby="start-heading" className="rounded-2xl border border-line px-5 py-5">
          <h2 id="start-heading" className="text-lg font-light">Set up the workspace</h2>
          <ol className="mt-3 grid gap-2 text-sm">
            {steps.map((s, i) => (
              <li key={s.text} className="flex items-center gap-3">
                <span className={`grid size-6 shrink-0 place-items-center rounded-full border font-mono text-[11px] ${s.done ? 'border-accent text-accent' : 'border-line text-muted'}`} aria-hidden>{s.done ? '✓' : i + 1}</span>
                {s.done ? <span className="text-muted line-through decoration-line">{s.text}</span> : <Link to={s.to} className="text-ink underline decoration-line underline-offset-4 hover:decoration-ink">{s.text}</Link>}
                <span className="sr-only">{s.done ? '(done)' : '(to do)'}</span>
              </li>
            ))}
          </ol>
        </section>
      )}

      <section aria-label="Findings at a glance" className="grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-line bg-line sm:grid-cols-3 lg:grid-cols-5">
        {stats.map((s) => (
          <Link key={s.label} to={s.to} className="bg-bg px-5 py-4 transition hover:bg-surface/60">
            <p className="text-xs text-muted">{s.label}</p>
            <p className={`mt-1 text-2xl font-light ${s.danger ? 'text-danger' : 'text-ink'}`}>{s.value}</p>
          </Link>
        ))}
      </section>

      <div className="grid gap-12 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,0.7fr)]">
        <section aria-labelledby="sites-heading" className="min-w-0">
          <h2 id="sites-heading" className="text-xl font-light">Sites</h2>
          {team.sites.length === 0 ? (
            <p className="mt-4 rounded-2xl border border-line px-5 py-4 text-sm text-muted">No reports shared yet. Each site shows here with its latest Launch Ready score.</p>
          ) : (
            <ul className="mt-4 divide-y divide-line rounded-2xl border border-line">
              {team.sites.map((s) => (
                <li key={s.origin}>
                  <Link to={`${base}/runs/${s.run_id}`} className="flex items-center justify-between gap-4 px-5 py-4 transition hover:bg-surface/60">
                    <span className="min-w-0">
                      <span className="block truncate font-mono text-sm text-ink">{host(s.origin)}</span>
                      <span className="mt-0.5 block text-xs text-muted">
                        {s.findings.high} high, {s.findings.medium} medium, {s.findings.low} low · {s.reports} report{s.reports === 1 ? '' : 's'} · latest {timeAgo(s.created_at)}
                      </span>
                    </span>
                    <span className="shrink-0 text-right">
                      <span className="block text-2xl font-light">{s.score ?? 'N/A'}</span>
                      <span className="block text-[11px] text-muted">Launch Ready</span>
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section aria-labelledby="people-heading" className="min-w-0">
          <h2 id="people-heading" className="text-xl font-light">People</h2>
          <ul className="mt-4 grid gap-3">
            {team.members.map((m) => (
              <li key={m.user_id} className="flex items-center gap-3 text-sm">
                <span className="relative">
                  <AccountAvatar name={m.name} />
                  {m.online && <span className="absolute -right-0.5 -bottom-0.5 size-2.5 rounded-full border-2 border-bg bg-accent" aria-hidden />}
                </span>
                <span className="min-w-0">
                  <span className="block truncate text-ink">{m.name}{m.user_id === team.me.user_id ? ' (you)' : ''}</span>
                  <span className="block text-xs text-muted">{m.online ? 'Here now' : m.last_seen_at ? `Seen ${timeAgo(m.last_seen_at)}` : 'Not here yet'}</span>
                </span>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <section aria-labelledby="activity-heading">
        <h2 id="activity-heading" className="text-xl font-light">Activity</h2>
        {events.length === 0 ? (
          <p className="mt-4 text-sm text-muted">Nothing yet.</p>
        ) : (
          <ol className="mt-4 border-t border-line">
            {events.map((e) => (
              <li key={e.id} className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-b border-line py-3 text-sm">
                <p className="min-w-0 text-muted"><span className="text-ink">{e.actor_name || 'Someone'}</span> {describe(e)}</p>
                <time dateTime={e.created_at} className="shrink-0 text-xs text-muted">{timeAgo(e.created_at)}</time>
              </li>
            ))}
          </ol>
        )}
        {(more ?? team.activity.length === 15) && <button type="button" onClick={older} className="mt-4 text-sm text-ink underline decoration-line underline-offset-4 hover:decoration-ink">Show earlier activity</button>}
      </section>
    </div>
  )
}
