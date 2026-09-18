import type { Session } from '@supabase/supabase-js'
import { useEffect, useState } from 'react'
import { supabase } from './supabase'

export type SessionState = { loading: true; session: null } | { loading: false; session: Session | null }

/** Current Supabase session. `loading` until the first check completes. */
export function useSession(): SessionState {
  const [state, setState] = useState<SessionState>(() => (supabase ? { loading: true, session: null } : { loading: false, session: null }))
  useEffect(() => {
    if (!supabase) return
    supabase.auth.getSession().then(({ data }) => setState({ loading: false, session: data.session }))
    const { data } = supabase.auth.onAuthStateChange((_event, session) => setState({ loading: false, session }))
    return () => data.subscription.unsubscribe()
  }, [])
  return state
}

export async function signOut() {
  await supabase?.auth.signOut()
}
