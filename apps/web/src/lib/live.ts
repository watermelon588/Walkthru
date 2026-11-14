/** In-app live runs: test users that walk a site in Walkthru's browser (apps/api/app/cloud.py). Pure helpers here are
 *  tested in tests/live.test.ts; they import types only, so they run without the browser client. */
import type { OrbState } from 'thinking-orbs'
import type { Step } from './runs'

/** Each built-in test user keeps one orb motion everywhere in live runs, so it reads as the same character. */
export const PERSONA_ORB: Record<string, OrbState> = { first_timer: 'breathing', phone_user: 'connecting', buyer: 'shaping', skeptic: 'searching' }
export const personaOrb = (key: string): OrbState => PERSONA_ORB[key] ?? 'composing'
/** One short line per built-in test user, from the Docs descriptions. */
export const PERSONA_HINT: Record<string, string> = {
  first_timer: 'Skims, gets impatient fast',
  phone_user: 'Small screen, big targets',
  buyer: 'Looks for price and proof',
  skeptic: 'Reads errors, distrusts vague copy',
}

export type LiveStatus = 'queued' | 'running' | 'finished' | 'failed' | 'blocked' | 'stopped'
export type LiveCard = {
  id: string
  persona: string
  status: LiveStatus
  error: string | null
  run_id: string | null
  run_status?: string
  ahead?: number
  created_at: string
  updated_at: string
  steps: Step[]
  report_ready: boolean
}
export type LiveTest = { group_id: string; site: string; goal: string; runs: LiveCard[] }

export const MAX_LIVE_PERSONAS = 3
export const isActive = (card: Pick<LiveCard, 'status'>) => card.status === 'queued' || card.status === 'running'
export const anyActive = (test: LiveTest) => test.runs.some(isActive)
/** Reports are written after the browser closes. Keep polling until each journey that produced a run has one. */
export const reportsPending = (test: LiveTest) => !anyActive(test) && test.runs.some((card) => card.run_id && !card.report_ready)

/** One line under a test user's name. Queue position and reasons are stated plainly; nothing is estimated. */
export function cardLine(card: LiveCard, now = Date.now()): string {
  const steps = `${card.steps.length} ${card.steps.length === 1 ? 'step' : 'steps'}`
  if (card.status === 'queued') return card.ahead ? `Queued, ${card.ahead} ahead of you` : 'Queued, starting next'
  if (card.status === 'running') {
    const seconds = Math.max(0, Math.round((now - Date.parse(card.created_at)) / 1000))
    return card.run_id || card.steps.length ? `Walking the site · ${steps}` : seconds < 90 ? 'Opening the site' : 'Still opening the site'
  }
  if (card.status === 'finished') return `${endedEarly(card) ? 'Stopped early' : 'Finished'} · ${steps}`
  if (card.status === 'stopped') return `Stopped · ${steps}`
  return card.status === 'blocked' ? 'Could not run' : 'Ended early'
}

/** The journey ran but the test user did not reach the goal: it gave up, got lost, ran out of steps or was stopped. */
export const endedEarly = (card: Pick<LiveCard, 'run_status'>) => !!card.run_status && card.run_status !== 'done' && card.run_status !== 'running'

/** The agent's own marker on a final step: the test user believed it was finished, but the automatic check found no proof. */
export const UNCONFIRMED = 'could not confirm the requested outcome'
export const believedDone = (card: Pick<LiveCard, 'run_status' | 'steps'>) =>
  card.run_status === 'agent_lost' && !!card.steps.at(-1)?.thought.includes(UNCONFIRMED)

/** General goals, shown only when the site's own navigation could not be read. */
export const GOAL_IDEAS = [
  'Work out what this site offers and who it is for',
  'Find the pricing and what each plan includes',
  'Find a way to get in touch',
  'Open one project or product and find out more about it',
]

/** Present tense for the pill shown while the cursor is on its way. */
export function inProgress(label: string | undefined, action: Step['action']): string {
  if (label?.startsWith('Clicked')) return `Clicking${label.slice('Clicked'.length)}`
  if (label?.startsWith('Typed in')) return `Typing in${label.slice('Typed in'.length)}`
  if (label?.startsWith('Scrolled')) return `Scrolling${label.slice('Scrolled'.length)}`
  return label ?? ({ click: 'Clicking', type: 'Typing', scroll: 'Scrolling', wait: 'Waiting', back: 'Going back', done: 'Finishing', give_up: 'Stopping' })[action]
}

/** Where the cursor rests at a step: the latest measured target at or before it. Never invented for a step without one. */
export function cursorAt(steps: Step[], index: number): { x: number; y: number } | null {
  for (let i = Math.min(index, steps.length - 1); i >= 0; i--) {
    const point = steps[i]?.evidence?.pointer
    if (point) return point
  }
  return null
}

export function framePaths(steps: Step[]): string[] {
  return [...new Set(steps.flatMap((step) => [step.evidence?.aim_path, step.evidence?.screenshot_path]).filter((path): path is string => !!path))]
}

/** Accepts yoursite.com as well as a full address. */
export function siteUrl(raw: string): string | null {
  const value = raw.trim()
  if (!value) return null
  try {
    const url = new URL(/^https?:\/\//i.test(value) ? value : `https://${value}`)
    return url.hostname.includes('.') ? url.toString() : null
  } catch {
    return null
  }
}

/** One thing the viewer sees: a page, and what the test user said on seeing it. Stored steps pair a thought with the
 *  action it led to and the page that followed, so showing a step as stored puts "I will click X" beside the page
 *  after X. A moment pairs each page with the thought the test user had while looking at it: the next step's. */
export type Moment = {
  label: string
  url: string
  frame?: string
  /** The view just before the action that led here, when it differs from the previous moment (the target was scrolled into view). */
  aim?: string
  pointer?: { x: number; y: number }
  regions?: NonNullable<Step['evidence']>['regions']
  width: number
  height: number
  thought: string
  confusion: number
  action?: Step['action']
  note?: string
  /** Live only: the action the test user is carrying out right now from this page. */
  doing?: string
  /** The journey ended on this page. */
  ended?: 'done' | 'give_up'
}

const ACTED: Record<Step['action'], string> = { click: 'Clicked', type: 'Typed', scroll: 'Scrolled', wait: 'Waited', back: 'Went back', done: 'Finished', give_up: 'Stopped' }
export const landingFrame = (runId: string) => `${runId}/step-00.jpg`

export function moments(steps: Step[], runId?: string | null): Moment[] {
  if (steps.length === 0) return []
  const first = steps.find((step) => step.evidence)?.evidence
  const size = { width: first?.width ?? 1280, height: first?.height ?? 900 }
  // Runs made before the landing frame existed fall back to the first aim frame, which shows the same page.
  const out: Moment[] = [{ label: 'Landed on the page', url: steps[0].url, frame: runId ? landingFrame(runId) : steps[0].evidence?.aim_path, ...size, thought: steps[0].thought, confusion: steps[0].confusion }]
  steps.forEach((step, i) => {
    const here = out[out.length - 1]
    if (step.action === 'done' || step.action === 'give_up') {
      here.ended = step.action // its thought is already this page's commentary; there is no new page
      return
    }
    const evidence = step.evidence
    if (!evidence) {
      if (i === steps.length - 1) here.doing = inProgress(undefined, step.action) // still happening
      return
    }
    const next = steps[i + 1]
    out.push({
      label: evidence.label ?? ACTED[step.action], url: evidence.result_url, frame: evidence.screenshot_path, aim: evidence.aim_path, pointer: evidence.pointer,
      regions: evidence.regions, width: evidence.width, height: evidence.height, action: step.action, note: evidence.note,
      thought: next?.thought ?? '', confusion: next?.confusion ?? step.confusion,
    })
  })
  return out
}

export const momentPaths = (list: Moment[]): string[] => [...new Set(list.flatMap((m) => [m.aim, m.frame]).filter((path): path is string => !!path))]

/** Where the cursor rests at a moment: the latest measured target at or before it. */
export function restingPoint(list: Moment[], index: number): { x: number; y: number } | null {
  for (let i = Math.min(index, list.length - 1); i >= 0; i--) if (list[i]?.pointer) return list[i].pointer!
  return null
}
