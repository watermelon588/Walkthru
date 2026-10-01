import type { Session } from '@supabase/supabase-js'
import { useEffect, useState } from 'react'
import { supabase } from './supabase'
import { disconnectExtension, signingOutExtension } from './extension'
import { authSessionId, sameLogin } from './sessionHandoff'
import { toast } from './toast'

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

let signOutTask: Promise<void> | undefined
export function signOut(): Promise<void> {
  if (!signOutTask) signOutTask = disconnectAndSignOut().finally(() => { signOutTask = undefined })
  return signOutTask
}

async function disconnectAndSignOut() {
  if (!supabase) return
  signingOutExtension(true)
  try {
    const { data, error: readError } = await supabase.auth.getSession()
    if (readError) throw readError
    if (!data.session) return
    if (data.session && !await disconnectExtension(data.session)) disconnectWarning()
    const refreshed = await supabase.auth.getSession()
    if (refreshed.error) throw refreshed.error
    const current = refreshed.data.session
    if (current && !sameLogin(data.session, current)) {
      throw new Error('Your account changed while signing out. Sign out again if that was intended.')
    }
    if (!current) return
    const { error } = await supabase.auth.signOut()
    if (error) throw error
  } finally {
    signingOutExtension(false)
  }
}

/** One listener per app, including other-tab logout and account changes. Never call Auth methods inside its callback. */
export function useExtensionDisconnect() {
  useEffect(() => {
    if (!supabase) return
    let previous: Session | null = null
    const { data } = supabase.auth.onAuthStateChange((_event, session) => {
      const old = previous
      previous = session
      if (old && (old.user.id !== session?.user.id
        || authSessionId(old.access_token) !== authSessionId(session?.access_token ?? ''))) {
        void disconnectExtension(old).then((ok) => { if (!ok) disconnectWarning() })
      }
    })
    return () => data.subscription.unsubscribe()
  }, [])
}

let warnedAt = 0
function disconnectWarning() {
  if (Date.now() - warnedAt < 1000) return
  warnedAt = Date.now()
  toast({ title: 'Extension disconnect could not be confirmed', body: 'If Walkthru is installed, disable it in Chrome until you reconnect.', tone: 'danger' })
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
