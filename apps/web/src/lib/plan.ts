import { useEffect, useState } from 'react'
import { useSession } from './auth'
import { getPlan, type PlanSummary } from './runs'

// One request per signed-in user, shared by the sidebar and the dashboard. Keyed by user so a new sign-in never
// shows the previous account's numbers.
let cache: { user: string; plan: Promise<PlanSummary> } | null = null

export type PlanState = { kind: 'loading' } | { kind: 'ready'; plan: PlanSummary } | { kind: 'error' }

export function usePlan(): PlanState {
  const { session } = useSession()
  const user = session?.user.id
  const [state, setState] = useState<PlanState>({ kind: 'loading' })
  useEffect(() => {
    if (!user) return
    if (cache?.user !== user) cache = { user, plan: getPlan() }
    let live = true
    cache.plan
      .then((plan) => live && setState({ kind: 'ready', plan }))
      .catch(() => {
        cache = null // try again on the next page
        if (live) setState({ kind: 'error' })
      })
    return () => { live = false }
  }, [user])
  return state
}
