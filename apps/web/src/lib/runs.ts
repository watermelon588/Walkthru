import { supabase } from './supabase'

export type Step = {
  thought: string
  action: 'click' | 'type' | 'scroll' | 'back' | 'done' | 'give_up'
  target_id: number | null
  text: string | null
  confusion: number
  url: string
  provider?: 'jev' | 'llm'
  decision_confidence?: number
  fallback_reason?: string
  interrupted?: boolean
  evidence?: StepEvidence
  diagnostics?: BrowserDiagnostics
}

export type AccessibilityIssue = {
  rule: string
  severity: 'high' | 'medium' | 'low'
  message: string
  target?: string
}

export type BrowserDiagnostics = {
  captured_at: string
  accessibility: {
    status: 'complete' | 'unavailable'
    total: number
    issues: AccessibilityIssue[]
  }
  web_vitals: {
    lcp_ms?: number
    cls?: number
    inp_ms?: number
  }
}

export type StepEvidence = {
  screenshot_path: string
  captured_at: string
  result_url: string
  width: number
  height: number
  note?: string
}

export type Finding = {
  kind: 'ux' | 'accessibility' | 'performance' | 'seo' | 'security' | 'geo'
  severity: 'high' | 'medium' | 'low'
  title: string
  detail: string
  fix: string
  evidence: string | null
}

export type Compared = { kind: Finding['kind']; severity: Finding['severity']; title: string; fingerprint: string }

export type Report = {
  summary: string
  first_impression: { what: string; who: string; first_click: string; trust: string[]; clarity: number } | null
  findings: Finding[]
  top_fixes: string[]
  verified: boolean
  tokens: number
  checks?: Partial<Record<'accessibility' | 'performance' | 'seo' | 'security' | 'geo', 'complete' | 'unavailable'>>
  geo?: { score: number; band: 'critical' | 'foundation' | 'good' | 'excellent'; categories: { id: string; label: string; earned: number; max: number }[]; ai_words: number; ai_view: string; notes: string[] } | null
  comparison?: { previous_run_id: string; previous_at: string; fixed: Compared[]; still_broken: Compared[]; new: Compared[] } | null
  site_audit?: {
    pages_scanned: number
    page_limit: number
    duration_ms: number
    truncated: boolean
    urls: string[]
    robots_respected: boolean
  } | null
}

export type Run = {
  evidence_purged_at?: string | null
  id: string
  site: string
  goal: string
  persona: string
  kind: 'test' | 'scan'
  status: 'running' | 'done' | 'gave_up' | 'budget' | 'stuck' | 'captcha' | 'stopped' | 'safe_stop' | 'looping'
  steps: Step[]
  report: Report | null
  public: boolean
  created_at: string
  updated_at: string
}

export const STATUS_LABEL: Record<Run['status'], string> = {
  running: 'Running',
  done: 'Reached the goal',
  gave_up: 'Gave up',
  budget: 'Ran out of steps',
  stuck: 'Got stuck',
  captcha: 'Stopped at a CAPTCHA',
  stopped: 'Ended early',
  safe_stop: 'Stopped before sending',
  looping: 'Stopped going in circles',
}

export const PERSONA_LABEL: Record<string, string> = {
  first_timer: 'First-time visitor',
  phone_user: 'Phone user',
  buyer: 'Small-business buyer',
  skeptic: 'Skeptical developer',
  stranger: 'Stranger, five seconds',
}

export const KIND_LABEL: Record<Finding['kind'], string> = { ux: 'UX', accessibility: 'Accessibility', performance: 'Performance', seo: 'SEO', security: 'Security', geo: 'GEO' }

const API = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8010'
const COLUMNS = 'id, site, goal, persona, kind, status, steps, report, public, created_at, updated_at, evidence_purged_at'

/** Keep in sync with EVIDENCE_RETENTION_DAYS on the API (apps/api/app/retention.py). */
export const EVIDENCE_RETENTION_DAYS = 30

/** Reads go straight to Supabase; row-level security limits them to the signed-in user's runs (or public ones). */
export async function listRuns(): Promise<Run[]> {
  if (!supabase) throw new Error('Supabase is not configured')
  const { data, error } = await supabase.from('runs').select(COLUMNS).order('created_at', { ascending: false }).limit(50)
  if (error) throw error
  return data as Run[]
}

export async function getRun(id: string): Promise<Run | null> {
  if (!supabase) throw new Error('Supabase is not configured')
  const { data, error } = await supabase.from('runs').select(COLUMNS).eq('id', id).maybeSingle()
  if (error) throw error
  return data as Run | null
}

export async function evidenceUrls(paths: string[]): Promise<Record<string, string>> {
  const client = supabase
  if (!client || paths.length === 0) return {}
  const unique = [...new Set(paths)]
  const entries = await Promise.all(unique.map(async (path) => {
    const { data, error } = await client.storage.from('run-evidence').createSignedUrl(path, 60 * 60)
    return [path, error ? '' : data.signedUrl] as const
  }))
  return Object.fromEntries(entries.filter((entry) => entry[1]))
}

/** Writes go through the API. */
async function api<T>(path: string, body?: unknown, auth = true, method: 'GET' | 'POST' | 'DELETE' = 'POST'): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (auth) {
    const token = (await supabase?.auth.getSession())?.data.session?.access_token
    if (!token) throw new Error('Sign in first')
    headers.Authorization = `Bearer ${token}`
  }
  const res = await fetch(API + path, { method, headers, body: method === 'POST' ? JSON.stringify(body ?? {}) : undefined })
  if (!res.ok) {
    const detail = (await res.json().catch(() => ({}))) as { detail?: string }
    throw new Error(detail.detail ?? `Request failed (${res.status})`)
  }
  return res.json()
}

export const instantScan = (site: string, email?: string) => api<{ run_id: string; url: string; report: Report }>('/scans', { site, email: email || null }, false)
export const shareRun = (id: string) => api<{ url: string }>(`/runs/${id}/share`)
export const emailRun = (id: string) => api<{ sent: boolean; to: string }>(`/runs/${id}/email`)
export const deleteRun = (id: string) => api<{ deleted: string }>(`/runs/${id}`, undefined, true, 'DELETE')
export const exportAccount = () => api<Record<string, unknown>>('/account/export', undefined, true, 'GET')
/** The server decides the plan (apps/api/app/plans.py). */
export type PlanSummary = { plan: 'free' | 'launch' | 'pro' | 'plus'; runs_allowed: number; runs_left: number; expires_at: string | null; max_steps: number; logged_in: boolean; personas: string[]; sites: number; sites_used: string[] }
export const getPlan = () => api<PlanSummary>('/me/plan', undefined, true, 'GET')
/** Same rule as fingerprint() in apps/api/app/agent/compare.py: kind plus title, ignoring case, spacing and counts. */
export function fingerprint(f: Pick<Finding, 'kind' | 'title'>): string {
  return `${f.kind}:${f.title.toLowerCase().replace(/\d+/g, '#').split(/\s+/).filter(Boolean).join(' ')}`
}

function siteOrigin(url: string): string {
  try {
    return new URL(url).origin.toLowerCase()
  } catch {
    return url
  }
}

/** Findings the owner accepted for this site (fingerprint to reason). Read under RLS: only the owner's own rows. */
export async function ignoredFindings(site: string): Promise<Record<string, string>> {
  if (!supabase) return {}
  const { data, error } = await supabase.from('finding_states').select('fingerprint, reason').eq('origin', siteOrigin(site))
  if (error) throw new Error(error.message)
  return Object.fromEntries((data ?? []).map((row) => [row.fingerprint as string, row.reason as string]))
}

export const ignoreFinding = (runId: string, fp: string, reason: string) => api<{ ignored: string }>(`/runs/${runId}/findings/ignore`, { fingerprint: fp, reason })
export const unignoreFinding = (runId: string, fp: string) =>
  api<{ cleared: string }>(`/runs/${runId}/findings/ignore?fingerprint=${encodeURIComponent(fp)}`, undefined, true, 'DELETE')
export const getVerification = () => api<{ token: string; meta: string; file: string }>('/verification', undefined, true, 'GET')
export const deleteAccount = (confirm: string) => api<{ deleted: boolean }>('/account/delete', { confirm })
export const stopRun = (id: string) => api<{ run_id: string; status: 'stopped'; steps: Step[]; report_status: 'generating' | 'ready' }>(`/runs/${id}/stop`)

export function findingsCsv(run: Run): string {
  const esc = (v: string | null) => `"${(v ?? '').replace(/"/g, '""')}"`
  const rows = (run.report?.findings ?? []).map((f) => [f.kind, f.severity, f.title, f.detail, f.fix, f.evidence].map(esc).join(','))
  return ['kind,severity,title,detail,fix,evidence', ...rows].join('\n')
}

export function timeAgo(iso: string): string {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000)
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)} min ago`
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`
  return `${Math.floor(s / 86400)} d ago`
}
