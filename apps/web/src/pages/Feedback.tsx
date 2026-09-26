import { useState, type FormEvent } from 'react'
import { AppShell } from '../components/AppShell'
import { PageHeader } from '../components/PageHeader'
import { btnPrimary } from '../components/Shared'
import { sendFeedback } from '../lib/runs'
import { toast } from '../lib/toast'

type State = { kind: 'idle' } | { kind: 'sending' } | { kind: 'error'; message: string }

/** A note straight to the founder. Stored server-side for the admin panel; nobody else can read it. */
export default function Feedback() {
  const [message, setMessage] = useState('')
  const [state, setState] = useState<State>({ kind: 'idle' })

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setState({ kind: 'sending' })
    try {
      await sendFeedback(message.trim(), document.referrer ? new URL(document.referrer).pathname : '')
      setMessage('')
      setState({ kind: 'idle' })
      toast({ title: 'Thanks, your message reached the founder', body: 'We read every one. If you left something to fix, watch this space.' })
    } catch (e) {
      setState({ kind: 'error', message: e instanceof Error ? e.message : 'Could not send your message' })
    }
  }

  return (
    <AppShell title="Feedback">
      <PageHeader kicker="Feedback" title="Tell us what to fix">
        Something confusing, broken or missing? It goes straight to the founder, who reads every message.
      </PageHeader>

      <form onSubmit={submit} className="mt-10 grid max-w-[60ch] gap-4">
        <label htmlFor="feedback" className="grid gap-2 text-sm text-muted">
          Your message
          <textarea id="feedback" required minLength={3} maxLength={2000} rows={6} value={message} onChange={(e) => setMessage(e.target.value)}
            placeholder="The report was great, but I could not find where to..." className="w-full rounded-xl border border-line bg-bg px-4 py-3 text-sm text-ink placeholder:text-muted focus:border-ink focus:outline-none" />
        </label>
        <div className="flex flex-wrap items-center gap-4">
          <button type="submit" disabled={state.kind === 'sending' || message.trim().length < 3} className={`${btnPrimary} disabled:opacity-50`}>
            {state.kind === 'sending' ? 'Sending' : 'Send'}
          </button>
          <p aria-live="polite" className="text-sm">
            {state.kind === 'error' && <span role="alert" className="text-danger">{state.message}</span>}
          </p>
        </div>
      </form>
    </AppShell>
  )
}
