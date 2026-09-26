import { XIcon } from '@phosphor-icons/react'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { dismiss, subscribe, type Toast } from '../lib/toast'

const SHOW_MS = 6000
const LEAVE_MS = 150

/** Toasts, bottom right (full width on phones). Mounted once in App; `toast()` from lib/toast adds one. */
export function Toaster() {
  const [items, setItems] = useState<Toast[]>([])
  useEffect(() => subscribe(setItems), [])
  return (
    <section aria-label="Notifications" aria-live="polite" className="no-print pointer-events-none fixed inset-x-4 bottom-[max(1rem,env(safe-area-inset-bottom))] z-50 flex flex-col items-end gap-2 sm:left-auto sm:right-6 sm:bottom-6">
      {items.map((t) => <ToastCard key={t.id} toast={t} />)}
    </section>
  )
}

function ToastCard({ toast }: { toast: Toast }) {
  const [leaving, setLeaving] = useState(false)
  const paused = useRef(false)
  const left = useRef(SHOW_MS)

  const close = () => {
    setLeaving(true)
    window.setTimeout(() => dismiss(toast.id), LEAVE_MS)
  }

  // Counts down only while the page is visible and the toast is not hovered or focused, so nothing vanishes unread.
  useEffect(() => {
    let last = Date.now()
    const tick = window.setInterval(() => {
      const now = Date.now()
      if (!paused.current && document.visibilityState === 'visible') left.current -= now - last
      last = now
      if (left.current <= 0) {
        window.clearInterval(tick)
        setLeaving(true)
        window.setTimeout(() => dismiss(toast.id), LEAVE_MS)
      }
    }, 250)
    return () => window.clearInterval(tick)
  }, [toast.id])

  const hold = { onMouseEnter: () => { paused.current = true }, onMouseLeave: () => { paused.current = false }, onFocus: () => { paused.current = true }, onBlur: () => { paused.current = false } }

  return (
    <div
      role={toast.tone === 'danger' ? 'alert' : 'status'}
      {...hold}
      className={`pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-2xl border border-line bg-bg py-3 pr-2 pl-4 shadow-[0_16px_40px_-20px_rgba(27,27,31,0.35)] transition-[opacity,translate] ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:translate-y-0 ${leaving ? 'translate-y-1 opacity-0 duration-150' : 'translate-y-0 opacity-100 duration-200 starting:translate-y-2 starting:opacity-0'}`}
    >
      <span aria-hidden className={`mt-1.5 size-2 shrink-0 rounded-full ${toast.tone === 'danger' ? 'bg-danger' : 'bg-accent'}`} />
      <div className="min-w-0 flex-1">
        <p className="text-sm leading-snug text-ink">{toast.title}</p>
        {toast.body && <p className="mt-0.5 line-clamp-2 text-xs leading-relaxed text-muted">{toast.body}</p>}
        {toast.href && (
          <Link to={toast.href} onClick={close} className="mt-1.5 inline-block text-xs text-ink underline decoration-line underline-offset-4 transition-colors hover:decoration-ink">
            Open
          </Link>
        )}
      </div>
      <button type="button" onClick={close} aria-label="Dismiss" className="grid size-8 shrink-0 place-items-center rounded-full text-muted transition-[background-color,color,scale] hover:bg-surface hover:text-ink active:scale-[0.97]">
        <XIcon weight="light" className="size-3.5" />
      </button>
    </div>
  )
}
