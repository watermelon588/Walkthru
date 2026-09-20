import type { Session } from '@supabase/supabase-js'
import { useEffect, useState } from 'react'
import { supabase } from './supabase'

export type SessionState = { loading: true; session: null } | { loading: false; session: Session | null }
export type AccountType = 'individual' | 'business'
export type AccountProfile = {
  account_type: AccountType
  full_name: string
  company_name: string
  company_role: string
  company_size: string
  website: string
}

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

function text(value: unknown) {
  return typeof value === 'string' ? value : ''
}

export function accountProfile(session: Session | null): AccountProfile {
  const metadata = session?.user.user_metadata ?? {}
  return {
    account_type: metadata.account_type === 'business' ? 'business' : 'individual',
    full_name: text(metadata.full_name) || text(metadata.name),
    company_name: text(metadata.company_name),
    company_role: text(metadata.company_role),
    company_size: text(metadata.company_size),
    website: text(metadata.website),
  }
}

export function accountAvatar(session: Session | null) {
  const metadata = session?.user.user_metadata ?? {}
  return text(metadata.avatar_url) || text(metadata.picture)
}

export async function updateAccountProfile(session: Session, profile: AccountProfile) {
  if (!supabase) throw new Error('Sign-in is not configured')
  const { error } = await supabase.auth.updateUser({
    data: { ...session.user.user_metadata, ...profile },
  })
  if (error) throw error
}
