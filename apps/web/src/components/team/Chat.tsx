import { useCallback, useEffect, useRef, useState, type FormEvent, type KeyboardEvent, type ReactNode } from 'react'
import { deleteMessage, editMessage, listMessages, markRead, postMessage, type Member, type Message } from '../../lib/teams'
import { AccountAvatar } from '../AccountAvatar'

type State = { kind: 'loading' } | { kind: 'ready' } | { kind: 'error'; message: string }

const time = (iso: string) => new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
const box = 'w-full rounded-xl border border-line bg-bg px-4 py-3 text-sm text-ink placeholder:text-muted focus:border-ink focus:outline-none'

/** Mentions are resolved from "@Name" in the text against the workspace's members, longest name first. */
function mentionsIn(text: string, members: Member[], me: string): string[] {
  const lower = text.toLowerCase()
  return [...members].sort((a, b) => b.name.length - a.name.length)
    .filter((m) => m.user_id !== me && m.name && lower.includes(`@${m.name.toLowerCase()}`))
    .map((m) => m.user_id)
}

/** Message text with links and @mentions marked. React escapes everything; links are http(s) only. */
function Body({ text, members }: { text: string; members: Member[] }) {
  const names = members.map((m) => m.name).filter(Boolean).sort((a, b) => b.length - a.length).map((n) => n.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  const pattern = new RegExp(`(https?://[^\\s<>"]+${names.length ? `|@(?:${names.join('|')})` : ''})`, 'gi')
  const parts: ReactNode[] = []
  let last = 0
  for (const match of text.matchAll(pattern)) {
    const at = match.index ?? 0
    parts.push(text.slice(last, at))
    const value = match[0]
    parts.push(value.startsWith('@')
      ? <span key={at} className="text-accent">{value}</span>
      : <a key={at} href={value} target="_blank" rel="noopener noreferrer nofollow" className="break-all text-ink underline decoration-line underline-offset-4 hover:decoration-ink">{value}</a>)
    last = at + value.length
  }
  parts.push(text.slice(last))
  return <p className="mt-1 text-sm leading-relaxed whitespace-pre-wrap break-words text-ink">{parts}</p>
}

/**
 * The workspace channel (thread "general") or a comment thread on a report ("run:<id>") or a finding ("finding:<key>").
 * New messages arrive through Supabase Realtime when it is connected (`live`), and by polling otherwise.
 */
type Props = {
  teamId: string; thread: string; me: string; members: Member[]; canChat: boolean; canModerate: boolean; live: boolean
  signal: number; title: string; empty: string; compact?: boolean
}

export function Chat(props: Props) {
  return <Thread key={`${props.teamId}:${props.thread}`} {...props} />  // fresh state per thread
}

function Thread({ teamId, thread, me, members, canChat, canModerate, live, signal, title, empty, compact = false }: Props) {
  const [messages, setMessages] = useState<Message[]>([])
  const [state, setState] = useState<State>({ kind: 'loading' })
  const [older, setOlder] = useState(false)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState<{ id: number; text: string } | null>(null)
  const list = useRef<HTMLOListElement>(null)
  const read = useRef(0)
  const nearBottom = useRef(true)

  const merge = useCallback((incoming: Message[]) => {
    setMessages((current) => {
      const byId = new Map(current.map((m) => [m.id, m]))
      for (const m of incoming) byId.set(m.id, m)
      return [...byId.values()].sort((a, b) => a.id - b.id)
    })
  }, [])

  const refresh = useCallback(() =>
    listMessages(teamId, thread)
      .then((page) => {
        merge(page.messages)
        setState({ kind: 'ready' })
        setOlder((o) => o || page.has_more)
      })
      .catch((e: Error) => setState((s) => (s.kind === 'ready' ? s : { kind: 'error', message: e.message }))), [teamId, thread, merge])

  useEffect(() => { refresh() }, [refresh])
  useEffect(() => { if (signal) refresh() }, [signal, refresh])  // a Realtime nudge from the page
  useEffect(() => {
    const timer = window.setInterval(() => { if (document.visibilityState === 'visible') refresh() }, live ? 30_000 : 5_000)
    return () => window.clearInterval(timer)
  }, [live, refresh])

  // Keep the newest message in view unless the reader scrolled up; mark the channel read while it is on screen.
  const newest = messages.at(-1)?.id ?? 0
  useEffect(() => {
    const el = list.current
    if (el && nearBottom.current) el.scrollTop = el.scrollHeight
    if (thread === 'general' && newest > read.current && document.visibilityState === 'visible') {
      read.current = newest
      markRead(teamId, newest).catch(() => { read.current = 0 })
    }
  }, [newest, teamId, thread])

  async function loadOlder() {
    const first = messages[0]?.id
    if (!first) return
    const el = list.current
    const height = el?.scrollHeight ?? 0
    try {
      const page = await listMessages(teamId, thread, { before: first })
      nearBottom.current = false
      merge(page.messages)
      setOlder(page.has_more)
      requestAnimationFrame(() => { if (el) el.scrollTop = el.scrollHeight - height })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load older messages.')
    }
  }

  async function send(event?: FormEvent) {
    event?.preventDefault()
    const body = text.trim()
    if (!body || busy) return
    setBusy(true)
    setError(null)
    try {
      const sent = await postMessage(teamId, body, thread, mentionsIn(body, members, me), crypto.randomUUID())
      nearBottom.current = true
      merge([sent])
      setText('')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not send. Your text is still here.')
    } finally {
      setBusy(false)
    }
  }

  function onKey(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      send()
    }
  }

  async function saveEdit() {
    if (!editing?.text.trim()) return
    try {
      merge([await editMessage(teamId, editing.id, editing.text.trim())])
      setEditing(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not save the edit.')
    }
  }

  async function remove(m: Message) {
    if (!window.confirm(m.author_id === me ? 'Delete your message?' : `Remove this message by ${m.author_name}? The removal is recorded in the activity log.`)) return
    try {
      await deleteMessage(teamId, m.id)
      merge([{ ...m, body: '', deleted: true, mentions: [] }])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not delete the message.')
    }
  }

  const insert = (name: string) => setText((current) => `${current}${current && !current.endsWith(' ') ? ' ' : ''}@${name} `)
  const others = members.filter((m) => m.user_id !== me && m.name)

  return (
    <section aria-label={title} className="grid min-w-0 gap-4">
      {state.kind === 'loading' && <div aria-busy="true" aria-label="Loading messages" className={`${compact ? 'h-24' : 'h-64'} animate-pulse rounded-2xl bg-surface motion-reduce:animate-none`} />}
      {state.kind === 'error' && (
        <div role="alert" className="rounded-2xl border border-line px-5 py-4">
          <p className="text-sm text-danger">Could not load messages: {state.message}</p>
          <button type="button" onClick={() => { setState({ kind: 'loading' }); refresh() }} className="mt-2 text-sm text-ink underline decoration-line underline-offset-4 hover:decoration-ink">Try again</button>
        </div>
      )}
      {state.kind === 'ready' && (
        <div className="rounded-2xl border border-line">
          <ol
            ref={list}
            role="log"
            aria-live="polite"
            aria-label={title}
            onScroll={(e) => { const el = e.currentTarget; nearBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80 }}
            className={`grid content-start gap-5 overflow-y-auto overscroll-contain px-5 py-5 ${compact ? 'max-h-80' : 'h-[min(60dvh,34rem)]'}`}
          >
            {older && (
              <li className="text-center">
                <button type="button" onClick={loadOlder} className="text-xs text-muted underline decoration-line underline-offset-4 hover:text-ink">Load earlier messages</button>
              </li>
            )}
            {messages.length === 0 && <li className="text-sm text-muted">{empty}</li>}
            {messages.map((m) => (
              <li key={m.id} className="flex gap-3">
                <AccountAvatar name={m.author_name} />
                <div className="min-w-0 flex-1">
                  <p className="flex flex-wrap items-baseline gap-x-2 text-xs text-muted">
                    <span className="text-sm text-ink">{m.author_name}</span>
                    <time dateTime={m.created_at}>{time(m.created_at)}</time>
                    {m.edited_at && !m.deleted && <span>(edited)</span>}
                  </p>
                  {m.deleted ? (
                    <p className="mt-1 text-sm text-muted italic">Message deleted</p>
                  ) : editing?.id === m.id ? (
                    <div className="mt-2 grid gap-2">
                      <label htmlFor={`edit-${m.id}`} className="sr-only">Edit message</label>
                      <textarea id={`edit-${m.id}`} value={editing.text} onChange={(e) => setEditing({ id: m.id, text: e.target.value })} rows={3} maxLength={4000} className={box} />
                      <span className="flex gap-4 text-xs">
                        <button type="button" onClick={saveEdit} className="text-ink underline decoration-line underline-offset-4 hover:decoration-ink">Save</button>
                        <button type="button" onClick={() => setEditing(null)} className="text-muted underline decoration-line underline-offset-4 hover:text-ink">Cancel</button>
                      </span>
                    </div>
                  ) : (
                    <Body text={m.body} members={members} />
                  )}
                  {!m.deleted && editing?.id !== m.id && (m.author_id === me || canModerate) && (
                    <span className="mt-1 flex gap-4 text-xs">
                      {m.author_id === me && canChat && <button type="button" onClick={() => setEditing({ id: m.id, text: m.body })} className="text-muted underline decoration-line underline-offset-4 hover:text-ink">Edit</button>}
                      <button type="button" onClick={() => remove(m)} className="text-muted underline decoration-line underline-offset-4 hover:text-danger">Delete</button>
                    </span>
                  )}
                </div>
              </li>
            ))}
          </ol>
          {canChat ? (
            <form onSubmit={send} className="border-t border-line px-5 py-4">
              <label htmlFor={`composer-${thread}`} className="sr-only">Message</label>
              <textarea
                id={`composer-${thread}`}
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={onKey}
                rows={compact ? 2 : 3}
                maxLength={4000}
                placeholder={thread === 'general' ? 'Write to the workspace. Enter sends, Shift+Enter adds a line.' : 'Add a comment. Enter sends.'}
                className={box}
              />
              <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                <span className="flex flex-wrap items-center gap-2 text-xs text-muted">
                  {others.length > 0 && <span>Mention</span>}
                  {others.slice(0, 8).map((m) => (
                    <button key={m.user_id} type="button" onClick={() => insert(m.name)} className="rounded-full border border-line px-2.5 py-1 transition hover:bg-surface hover:text-ink">@{m.name}</button>
                  ))}
                </span>
                <button type="submit" disabled={busy || !text.trim()} className="rounded-full bg-ink px-5 py-2 text-sm text-bg transition hover:opacity-85 disabled:opacity-50">{busy ? 'Sending' : 'Send'}</button>
              </div>
              {error && <p role="alert" className="mt-2 text-sm text-danger">{error}</p>}
            </form>
          ) : (
            <p className="border-t border-line px-5 py-4 text-sm text-muted">This workspace is read-only right now, so new messages are paused.</p>
          )}
        </div>
      )}
    </section>
  )
}
