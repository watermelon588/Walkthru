import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { useLocation } from 'react-router'
import { useSession } from '../lib/auth'
import { EMPTY, NOTIFICATION_EVENT, NotificationCounts, sectionFor, type Counts, type Notification } from '../lib/notifications'
import { api } from '../lib/runs'
import { supabase } from '../lib/supabase'
import { toast } from '../lib/toast'

/** Live counts per section. New notifications arrive over Supabase Realtime (row-level security: only your own rows)
 *  and show a toast; counts also refresh on focus, and poll slowly in case the socket is down. */
export function NotificationsProvider({ children }: { children: ReactNode }) {
  const { session } = useSession()
  const uid = session?.user.id ?? null
  const [state, setState] = useState<{ uid: string | null; counts: Counts }>({ uid: null, counts: EMPTY })
  const counts = state.uid === uid && uid ? state.counts : EMPTY
  const { pathname } = useLocation()
  const later = useRef<number | undefined>(undefined)

  const refresh = useCallback(() => {
    if (!uid) return
    api<{ counts: Counts }>('/me/notifications', undefined, true, 'GET')
      .then((r) => setState({ uid, counts: { ...EMPTY, ...r.counts } }))
      .catch(() => { /* counts are a courtesy; the next focus or poll tries again */ })
  }, [uid])
  const refreshSoon = useCallback(() => {
    window.clearTimeout(later.current)
    later.current = window.setTimeout(refresh, 400)
  }, [refresh])

  useEffect(() => {
    if (!uid) return
    refresh()
    const visible = () => { if (document.visibilityState === 'visible') refresh() }
    window.addEventListener('focus', refresh)
    document.addEventListener('visibilitychange', visible)
    const poll = window.setInterval(visible, 60_000)
    return () => {
      window.removeEventListener('focus', refresh)
      document.removeEventListener('visibilitychange', visible)
      window.clearInterval(poll)
    }
  }, [uid, refresh])

  useEffect(() => {
    const client = supabase
    if (!client || !uid) return
    const channel = client
      .channel(`notifications:${uid}:${Math.random().toString(36).slice(2)}`)
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'notifications', filter: `user_id=eq.${uid}` }, (payload) => {
        const n = payload.new as Notification
        toast({ title: n.title, body: n.body || undefined, href: n.link || undefined })
        window.dispatchEvent(new CustomEvent(NOTIFICATION_EVENT, { detail: n }))
        refreshSoon()
      })
      // Workspace chat counts toward the Team badge; row-level security only delivers your workspaces' messages.
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'team_messages' }, refreshSoon)
      // Reading a workspace chat moves your read marker; the Team badge drops as soon as that lands.
      .on('postgres_changes', { event: 'UPDATE', schema: 'public', table: 'team_members', filter: `user_id=eq.${uid}` }, refreshSoon)
      .subscribe()
    return () => { void client.removeChannel(channel) }
  }, [uid, refreshSoon])

  // Opening a section's page reads its notifications. Team chat stays unread until the chat itself is opened.
  const section = sectionFor(pathname)
  const waiting = section ? counts[section] : 0
  useEffect(() => {
    if (!uid || !section || waiting === 0) return
    api('/me/notifications/read', { section }).then(refreshSoon).catch(() => {})
  }, [uid, section, waiting, refreshSoon])

  return <NotificationCounts.Provider value={counts}>{children}</NotificationCounts.Provider>
}
