import { supabase } from './supabase'

export type Step = {
  thought: string
  action: 'click' | 'type' | 'scroll' | 'back' | 'done' | 'give_up'
  target_id: number | null
  text: string | null
  confusion: number
  url: string
}

export type Run = {
  id: string
  site: string
  goal: string
  persona: string
  status: 'running' | 'done' | 'gave_up' | 'budget' | 'stuck' | 'captcha'
  steps: Step[]
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
}

const COLUMNS = 'id, site, goal, persona, status, steps, created_at, updated_at'

/** Reads go straight to Supabase; row-level security limits them to the signed-in user's runs. */
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

export function timeAgo(iso: string): string {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000)
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)} min ago`
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`
  return `${Math.floor(s / 86400)} d ago`
}
