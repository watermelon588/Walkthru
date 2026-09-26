import { createContext, useContext } from 'react'

/** The sidebar sections that can carry a count (apps/api/app/notify.py SECTIONS). */
export type Section = 'runs' | 'team' | 'compare' | 'watch' | 'billing'
export type Counts = Record<Section, number>
export type Notification = { id: number; section: Section; kind: string; title: string; body: string; link: string; created_at: string }

export const EMPTY: Counts = { runs: 0, team: 0, compare: 0, watch: 0, billing: 0 }
/** Fired on window when a notification arrives, so an open page can refresh itself (detail: Notification). */
export const NOTIFICATION_EVENT = 'walkthru:notification'

export const NotificationCounts = createContext<Counts>(EMPTY)
export const useNotificationCounts = () => useContext(NotificationCounts)

/** Which section a page belongs to; opening it marks that section's notifications read. */
export function sectionFor(pathname: string): Section | null {
  if (pathname === '/app' || pathname.startsWith('/app/runs/')) return 'runs'
  if (pathname.startsWith('/app/team')) return 'team'
  if (pathname.startsWith('/app/compare')) return 'compare'
  if (pathname.startsWith('/app/watch')) return 'watch'
  if (pathname.startsWith('/app/billing')) return 'billing'
  return null
}
