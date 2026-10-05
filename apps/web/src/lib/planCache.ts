import type { PlanSummary } from './runs'

type Login = { user: { id: string }; access_token: string } | null

/** Memory only. Tokens are never persisted, rendered or logged. A refresh is a new identity. */
export const accountIdentity = (session: Login) => session ? `${session.user.id}:${session.access_token}` : ''

export class PlanCache {
  private identity = ''
  private generation = 0
  private entry: { promise: Promise<PlanSummary>; expires: number } | null = null

  observe(identity: string) {
    if (identity !== this.identity) { this.clear(); this.identity = identity }
  }

  clear() { this.generation++; this.entry = null; this.identity = '' }

  read(identity: string, load: () => Promise<PlanSummary>, fresh = false, now = Date.now()): Promise<PlanSummary> {
    this.observe(identity)
    if (!identity) return Promise.reject(new Error('Sign in first'))
    if (!fresh && this.entry && this.entry.expires > now) return this.entry.promise
    const generation = ++this.generation
    const entry = { promise: null as unknown as Promise<PlanSummary>, expires: now + 60_000 }
    entry.promise = load().then((plan) => {
      if (generation !== this.generation || identity !== this.identity) throw new Error('Your account or plan changed. Try again.')
      return plan
    }).catch((error: unknown) => { if (this.entry === entry) this.entry = null; throw error })
    this.entry = entry
    return entry.promise
  }
}

export const planCache = new PlanCache()
