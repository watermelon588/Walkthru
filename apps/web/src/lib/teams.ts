import { useEffect, useRef, useState } from 'react'
import { api, type Finding } from './runs'
import { supabase } from './supabase'

/** Plus team workspaces (apps/api/app/teams.py, docs/team-collaboration.md). Every call goes through the API, which
 *  checks membership and role on each request. Supabase Realtime only nudges the page to refetch. */

export type Role = 'owner' | 'admin' | 'member' | 'viewer'
export type Status = 'open' | 'in_progress' | 'fixed' | 'wont_fix'
export type Can = { chat: boolean; share: boolean; triage: boolean; invite: boolean; manage_members: boolean; rename: boolean; manage_admins: boolean; transfer: boolean; delete: boolean }

export type TeamSummary = { id: string; name: string; role: Role; active: boolean; unread: number; mentions: number; created_at: string }
export type Invitation = { id: string; team: { id: string; name: string }; role: Role; invited_by_name: string; expires_at: string }
export type TeamList = { teams: TeamSummary[]; invitations: Invitation[]; plus: boolean; can_create: boolean; owned: number; max_owned: number; seats: number }

export type Member = { user_id: string; name: string; email: string; role: Role; joined_at: string; last_seen_at: string | null; online: boolean }
export type TeamEvent = { id: number; type: string; actor_id: string | null; actor_name: string; detail: Record<string, unknown>; created_at: string }
export type Counts = { high: number; medium: number; low: number }
export type Site = { origin: string; site: string; run_id: string; kind: string; status: string; created_at: string; score: number | null; findings: Counts; reports: number }
export type Overview = {
  team: { id: string; name: string; owner_id: string; created_at: string; active: boolean; seats: number }
  me: { user_id: string; role: Role; auto_share: boolean; last_read_message_id: number; can: Can }
  members: Member[]
  sites: Site[]
  findings: Record<Status, number> & { high_open: number; seen_again: number; mine: number }
  reports: number
  activity: TeamEvent[]
  unread: number
  mentions: number
}

export type Invite = { id: string; kind: 'email' | 'link'; email: string | null; email_domain: string | null; role: Role; max_uses: number; uses: number; invited_by_name: string; created_at: string; expires_at: string }
export type Members = { members: Member[]; invites: Invite[]; seats: number; seats_used: number; me: { user_id: string; role: Role; can: Can } }

export type SharedRun = {
  run_id: string; site: string; goal: string; persona: string; kind: string; status: string; created_at: string; score: number | null
  findings: Counts; owner_id: string | null; shared_by: string | null; shared_by_name: string; shared_at: string; comments: number
}

export type BoardItem = {
  origin: string; fingerprint: string; thread: string; kind: Finding['kind']; severity: Finding['severity']; title: string; detail: string; fix: string
  evidence: string | null; site: string; run_id: string; first_seen: string; last_seen: string; reports: number; status: Status
  assignee_id: string | null; assignee_name: string | null; updated_at: string | null; updated_by_name: string | null; seen_again: boolean; comments: number
}
export type Board = { findings: BoardItem[]; assignees: { user_id: string; name: string }[]; can_triage: boolean }

export type Message = { id: number; thread: string; author_id: string | null; author_name: string; bot: boolean; body: string; mentions: string[]; created_at: string; edited_at: string | null; deleted: boolean }
export type Preview = { team: { id: string; name: string }; role: Role; kind: 'email' | 'link'; invited_by_name: string; expires_at: string; member: boolean; problem: string | null }

const t = (id: string) => `/teams/${encodeURIComponent(id)}`

export const listTeams = () => api<TeamList>('/teams', undefined, true, 'GET')
export const createTeam = (name: string) => api<{ id: string; name: string }>('/teams', { name })
export const getTeam = (id: string) => api<Overview>(t(id), undefined, true, 'GET')
export const renameTeam = (id: string, name: string) => api<{ id: string; name: string }>(t(id), { name })
export const deleteTeam = (id: string, confirm: string) => api<{ deleted: string }>(`${t(id)}/delete`, { confirm })
export const transferTeam = (id: string, userId: string) => api<{ owner_id: string; active: boolean }>(`${t(id)}/transfer`, { user_id: userId })
export const setAutoShare = (id: string, autoShare: boolean) => api<{ auto_share: boolean }>(`${t(id)}/me`, { auto_share: autoShare })

export const getMembers = (id: string) => api<Members>(`${t(id)}/members`, undefined, true, 'GET')
export const changeRole = (id: string, userId: string, role: Role) => api<{ user_id: string; role: Role }>(`${t(id)}/members/${userId}/role`, { role })
export const removeMember = (id: string, userId: string) => api<{ removed?: string; left?: string }>(`${t(id)}/members/${userId}`, undefined, true, 'DELETE')
export const inviteByEmail = (id: string, email: string, role: Role) => api<{ invite: Invite; link: string; code: string; emailed: boolean }>(`${t(id)}/invites`, { email, role })
export const createLink = (id: string, body: { role: Role; days: number; max_uses: number; email_domain: string | null }) =>
  api<{ invite: Invite; link: string; code: string }>(`${t(id)}/links`, body)
export const revokeInvite = (id: string, inviteId: string) => api<{ revoked: string }>(`${t(id)}/invites/${inviteId}`, undefined, true, 'DELETE')

export const previewInvite = (code: string) => api<Preview>('/invites/preview', { code })
export const acceptInvite = (code: string) => api<{ team_id: string; joined: boolean }>('/invites/accept', { code })
export const acceptListedInvite = (inviteId: string) => api<{ team_id: string; joined: boolean }>(`/invites/${inviteId}/accept`)
export const declineInvite = (inviteId: string) => api<{ declined: string }>(`/invites/${inviteId}/decline`)

export const sharedRuns = (id: string, before?: string) =>
  api<{ runs: SharedRun[]; has_more: boolean }>(`${t(id)}/runs${before ? `?before=${encodeURIComponent(before)}` : ''}`, undefined, true, 'GET')
export const shareRun = (id: string, runId: string) => api<{ shared: string }>(`${t(id)}/runs`, { run_id: runId })
export const unshareRun = (id: string, runId: string) => api<{ unshared: string }>(`${t(id)}/runs/${runId}`, undefined, true, 'DELETE')
export const runTeams = (runId: string) => api<{ teams: { id: string; name: string; shared: boolean }[] }>(`/runs/${runId}/teams`, undefined, true, 'GET')

export const getBoard = (id: string) => api<Board>(`${t(id)}/findings`, undefined, true, 'GET')
export const triage = (id: string, item: Pick<BoardItem, 'origin' | 'fingerprint'>, change: { status?: Status; assignee_id?: string | null }) =>
  api<BoardItem>(`${t(id)}/findings`, { origin: item.origin, fingerprint: item.fingerprint, ...change })

export function listMessages(id: string, thread: string, page: { after?: number; before?: number } = {}) {
  const q = new URLSearchParams({ thread })
  if (page.after !== undefined) q.set('after', String(page.after))
  if (page.before !== undefined) q.set('before', String(page.before))
  return api<{ messages: Message[]; has_more: boolean }>(`${t(id)}/messages?${q}`, undefined, true, 'GET')
}
export const postMessage = (id: string, body: string, thread: string, mentions: string[], clientId: string) =>
  api<Message>(`${t(id)}/messages`, { body, thread, mentions, client_id: clientId })
export const editMessage = (id: string, messageId: number, body: string) => api<Message>(`${t(id)}/messages/${messageId}`, { body })
export const deleteMessage = (id: string, messageId: number) => api<{ deleted: number }>(`${t(id)}/messages/${messageId}`, undefined, true, 'DELETE')
export const markRead = (id: string, messageId: number) => api<{ last_read_message_id: number }>(`${t(id)}/read`, { message_id: messageId })
export const getActivity = (id: string, before?: number) =>
  api<{ events: TeamEvent[]; has_more: boolean }>(`${t(id)}/activity${before ? `?before=${before}` : ''}`, undefined, true, 'GET')

export const ROLE_LABEL: Record<Role, string> = { owner: 'Owner', admin: 'Admin', member: 'Member', viewer: 'Viewer' }
export const ROLE_HELP: Record<Role, string> = {
  owner: 'Everything. The workspace runs on their Plus plan; they can hand it over or delete it.',
  admin: 'Invites people, manages members and viewers, renames the workspace.',
  member: 'Shares reports, triages findings, chats and comments.',
  viewer: 'Reads reports and findings, chats and comments. Good for clients.',
}
export const ROLE_A: Record<Role, string> = { owner: 'the owner', admin: 'an admin', member: 'a member', viewer: 'a viewer' }
export const STATUS_TEXT: Record<Status, string> = { open: 'Open', in_progress: 'In progress', fixed: 'Fixed', wont_fix: "Won't fix" }

/** One sentence per activity event. Unknown types fall back to a neutral line, so older clients never break. */
export function describe(e: TeamEvent): string {
  const d = e.detail as Record<string, string | number | boolean | null | undefined>
  const host = (url: unknown) => (typeof url === 'string' ? url.replace(/^https?:\/\//, '').replace(/\/$/, '') : 'a site')
  switch (e.type) {
    case 'team.created': return 'created the workspace'
    case 'team.renamed': return `renamed the workspace to ${d.new}`
    case 'team.transferred': return `handed the workspace to ${d.to_name}`
    case 'member.joined': return `joined as ${String(d.role ?? 'member')}`
    case 'member.left': return 'left the workspace'
    case 'member.removed': return `removed ${d.member_name}`
    case 'member.role': return `made ${d.member_name} ${d.new === 'admin' ? 'an admin' : `a ${String(d.new)}`}`
    case 'invite.sent': return `invited ${d.email}`
    case 'invite.revoked': return 'withdrew an invitation'
    case 'invite.declined': return 'declined an invitation'
    case 'link.created': return `made an invite link for ${d.email_domain ? `@${d.email_domain} ` : ''}${String(d.role)}s`
    case 'run.shared': return `shared a report on ${host(d.site)}${d.auto ? ' (auto-share)' : ''}`
    case 'run.unshared': return `removed a report on ${host(d.site)}`
    case 'finding.status': return `marked "${d.title}" ${STATUS_TEXT[d.new as Status]?.toLowerCase() ?? String(d.new)}`
    case 'finding.assigned': return d.assignee_name ? `assigned "${d.title}" to ${d.assignee_name}` : `unassigned "${d.title}"`
    case 'message.removed': return `removed a message by ${d.author_name}`
    default: return 'made a change'
  }
}

/** Realtime nudges for one workspace. Calls `onChange(table)` when a row changes; returns whether the socket is up,
 *  so pages poll quickly only when it is not. Row-level security decides which changes this browser may see. */
export function useTeamLive(teamId: string, onChange: (table: string) => void): boolean {
  const [live, setLive] = useState(false)
  const handler = useRef(onChange)
  useEffect(() => { handler.current = onChange })
  useEffect(() => {
    const client = supabase
    if (!client || !teamId) return
    const channel = client.channel(`team:${teamId}:${Math.random().toString(36).slice(2)}`)
    for (const table of ['team_messages', 'team_events', 'team_runs', 'team_findings', 'team_members']) {
      channel.on('postgres_changes', { event: '*', schema: 'public', table, filter: `team_id=eq.${teamId}` }, () => handler.current(table))
    }
    channel.subscribe((status) => setLive(status === 'SUBSCRIBED'))
    return () => {
      setLive(false)
      void client.removeChannel(channel)
    }
  }, [teamId])
  return live
}

/** A join code waiting for the sign-in to finish (the invitee was signed out when they opened the link). */
const PENDING = 'walkthru.join'
export function savePendingJoin(code: string) {
  try { localStorage.setItem(PENDING, JSON.stringify({ code, at: Date.now() })) } catch { /* storage can be blocked */ }
}
export function pendingJoin(): string | null {
  try {
    const saved = JSON.parse(localStorage.getItem(PENDING) ?? 'null') as { code: string; at: number } | null
    if (saved && Date.now() - saved.at < 3_600_000 && typeof saved.code === 'string') return saved.code
    localStorage.removeItem(PENDING)
  } catch { /* ignore */ }
  return null
}
export function clearPendingJoin() {
  try { localStorage.removeItem(PENDING) } catch { /* ignore */ }
}
