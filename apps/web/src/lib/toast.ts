/** A tiny toast store: call `toast()` from anywhere, `<Toaster />` renders it (mounted once in App). */

export type Toast = { id: number; title: string; body?: string; href?: string; tone?: 'default' | 'danger' }
type Listener = (toasts: Toast[]) => void

const MAX = 3 // older ones leave when a fourth arrives
let toasts: Toast[] = []
let next = 1
const listeners = new Set<Listener>()

function emit() {
  for (const listener of listeners) listener(toasts)
}

export function toast(input: Omit<Toast, 'id'>): number {
  const id = next++
  toasts = [...toasts, { ...input, id }].slice(-MAX)
  emit()
  return id
}

export function dismiss(id: number) {
  toasts = toasts.filter((t) => t.id !== id)
  emit()
}

export function subscribe(listener: Listener): () => void {
  listeners.add(listener)
  listener(toasts)
  return () => { listeners.delete(listener) }
}
