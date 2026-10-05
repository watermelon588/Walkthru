import { useEffect, useMemo, useSyncExternalStore } from 'react'
import { NOTIFICATION_EVENT, type Notification } from './notifications'
import { listRunsPage } from './runs'
import { HistoryPager } from './runHistory'

/** A new login/token gets a new store immediately, so previous account rows never render. */
export function useRunHistory(identity: string, load = listRunsPage) {
  const pager = useMemo(() => new HistoryPager((cursor, signal) => load(cursor, signal, identity)), [identity, load])
  const state = useSyncExternalStore(pager.subscribe, pager.snapshot)
  useEffect(() => {
    if (!identity) return
    void pager.refresh()
    const onNote = (event: Event) => {
      if ((event as CustomEvent<Notification>).detail?.section === 'runs') void pager.refresh()
    }
    window.addEventListener(NOTIFICATION_EVENT, onNote)
    return () => { pager.dispose(); window.removeEventListener(NOTIFICATION_EVENT, onNote) }
  }, [identity, pager])
  return { state, refresh: () => pager.refresh(), more: () => pager.more() }
}
