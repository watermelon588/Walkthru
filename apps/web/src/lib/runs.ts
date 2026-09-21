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
  kind: 'ux' | 'accessibility' | 'performance' | 'seo' | 'security'
  severity: 'high' | 'medium' | 'low'
  title: string
  detail: string
  fix: string
  evidence: string | null
}

export type Report = {
  summary: string
  first_impression: { what: string; who: string; first_click: string; trust: string[]; clarity: number } | null
  findings: Finding[]
  top_fixes: string[]
  verified: boolean
  tokens: number
  checks?: Partial<Record<'accessibility' | 'performance' | 'seo' | 'security', 'complete' | 'unavailable'>>
}

export type Run = {
  id: string
  site: string
  goal: string
  persona: string
  kind: 'test' | 'scan'
  status: 'running' | 'done' | 'gave_up' | 'budget' | 'stuck' | 'captcha'
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
}

export const PERSONA_LABEL: Record<string, string> = {
  first_timer: 'First-time visitor',
  phone_user: 'Phone user',
  buyer: 'Small-business buyer',
  skeptic: 'Skeptical developer',
  stranger: 'Stranger, five seconds',
}

export const KIND_LABEL: Record<Finding['kind'], string> = { ux: 'UX', accessibility: 'Accessibility', performance: 'Performance', seo: 'SEO', security: 'Security' }

const API = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000'
const COLUMNS = 'id, site, goal, persona, kind, status, steps, report, public, created_at, updated_at'

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
async function api<T>(path: string, body?: unknown, auth = true): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (auth) {
    const token = (await supabase?.auth.getSession())?.data.session?.access_token
    if (!token) throw new Error('Sign in first')
    headers.Authorization = `Bearer ${token}`
  }
  const res = await fetch(API + path, { method: 'POST', headers, body: JSON.stringify(body ?? {}) })
  if (!res.ok) {
    const detail = (await res.json().catch(() => ({}))) as { detail?: string }
    throw new Error(detail.detail ?? `Request failed (${res.status})`)
  }
  return res.json()
}

export const instantScan = (site: string, email?: string) => api<{ run_id: string; url: string; report: Report }>('/scans', { site, email: email || null }, false)
export const shareRun = (id: string) => api<{ url: string }>(`/runs/${id}/share`)
export const emailRun = (id: string) => api<{ sent: boolean; to: string }>(`/runs/${id}/email`)

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
