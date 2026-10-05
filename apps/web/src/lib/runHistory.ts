/** Exact stored timestamp precision is preserved; do not normalize microseconds through Date. */
export type RunCursor = { v: 1; created_at: string; id: string }
export const HISTORY_PAGE_SIZE = 50
export const RUN_SUMMARY_COLUMNS = 'id,site,goal,persona,kind,status,public,created_at,updated_at,group_id'
const runId = /^[a-f0-9]{32}$/
const timestamp = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/
function validTimestamp(value: string): boolean {
  const match = timestamp.exec(value)
  if (!match || !Number.isFinite(Date.parse(value))) return false
  const [year, month, day, hour, minute, second] = match.slice(1).map(Number)
  const leap = year! % 4 === 0 && (year! % 100 !== 0 || year! % 400 === 0)
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
  return year! >= 1 && month! >= 1 && month! <= 12 && day! >= 1 && day! <= days[month! - 1]! && hour! < 24 && minute! < 60 && second! < 60
}

export function encodeRunCursor(row: { created_at: string; id: string }): string {
  return btoa(JSON.stringify({ v: 1, created_at: row.created_at, id: row.id })).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

export function decodeRunCursor(cursor: string): RunCursor {
  try {
    if (!/^[a-zA-Z0-9_-]{1,256}$/.test(cursor)) throw new Error()
    const value = JSON.parse(atob(cursor.replace(/-/g, '+').replace(/_/g, '/'))) as RunCursor
    if (value.v !== 1 || !validTimestamp(value.created_at) || !runId.test(value.id)
      || Object.keys(value).sort().join(',') !== 'created_at,id,v') throw new Error()
    return value
  } catch { throw new Error('Invalid run history cursor. Refresh your history.') }
}

export function runCursorFilter(cursor: string): string {
  const { created_at, id } = decodeRunCursor(cursor)
  return `created_at.lt.${created_at},and(created_at.eq.${created_at},id.lt.${id})`
}

export type HistoryPage<T> = { runs: T[]; next_cursor: string | null }
export type HistoryState<T> = { kind: 'loading' } | { kind: 'error'; message: string }
  | { kind: 'ready'; runs: T[]; nextCursor: string | null; loadingMore: boolean; moreError: string | null }

/** One mounted account owns one pager. Refresh discards its old continuation, including pending replies. */
export class HistoryPager<T extends { id: string }> {
  private state: HistoryState<T> = { kind: 'loading' }
  private listeners = new Set<() => void>()
  private generation = 0
  private request: AbortController | null = null
  private load: (cursor: string | undefined, signal: AbortSignal) => Promise<HistoryPage<T>>

  constructor(load: (cursor: string | undefined, signal: AbortSignal) => Promise<HistoryPage<T>>) { this.load = load }
  snapshot = () => this.state
  subscribe = (listener: () => void) => { this.listeners.add(listener); return () => { this.listeners.delete(listener) } }
  private update(state: HistoryState<T>) { this.state = state; this.listeners.forEach((listener) => listener()) }
  dispose() { this.generation++; this.request?.abort(); this.request = null }

  async refresh() {
    this.dispose()
    this.update({ kind: 'loading' })
    await this.fetchPage()
  }

  async more() {
    if (this.state.kind !== 'ready' || this.state.loadingMore || !this.state.nextCursor) return
    const previous = this.state
    this.update({ ...previous, loadingMore: true, moreError: null })
    await this.fetchPage(previous)
  }

  private async fetchPage(previous?: Extract<HistoryState<T>, { kind: 'ready' }>) {
    const generation = ++this.generation
    const controller = new AbortController()
    this.request = controller
    try {
      const page = await this.load(previous?.nextCursor ?? undefined, controller.signal)
      if (generation !== this.generation || controller.signal.aborted) return
      const rows = new Map((previous?.runs ?? []).map((run) => [run.id, run]))
      page.runs.forEach((run) => rows.set(run.id, run))
      this.update({ kind: 'ready', runs: [...rows.values()], nextCursor: page.next_cursor, loadingMore: false, moreError: null })
    } catch (error) {
      if (generation !== this.generation || controller.signal.aborted) return
      const message = error instanceof Error ? error.message : 'Could not load runs.'
      this.update(previous ? { ...previous, loadingMore: false, moreError: message } : { kind: 'error', message })
    } finally { if (this.request === controller) this.request = null }
  }
}
