import { CheckIcon, CopyIcon } from '@phosphor-icons/react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { getVerification } from '../lib/runs'

type State = { kind: 'loading' } | { kind: 'ready'; meta: string; token: string; file: string; txt_name: string; txt_value: string } | { kind: 'error'; message: string }

/** Shows the owner's verification tag. One token per account verifies every site that carries it. */
export function DomainVerification() {
  const [state, setState] = useState<State>({ kind: 'loading' })
  const fetchTag = () =>
    getVerification()
      .then((v) => setState({ kind: 'ready', ...v }))
      .catch((e: Error) => setState({ kind: 'error', message: e.message }))
  const retry = () => {
    setState({ kind: 'loading' })
    fetchTag()
  }
  useEffect(() => { fetchTag() }, [])

  return (
    <section id="verify" aria-labelledby="verify-heading" className="mt-14 scroll-mt-24 border-t border-line pt-10">
      <div className="grid gap-10 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
        <div>
          <h2 id="verify-heading" className="text-xl font-light">Verify your domain</h2>
          <p className="mt-2 max-w-[48ch] text-sm leading-relaxed text-muted">
            Prove you own a site to unlock the full security check and let test users fill in forms, sign in and send what you approve. Until then Walkthru tests the site as a visitor. Add any one option below, then run a new scan or test.
          </p>
          <Link to="/docs#verify" className="mt-4 inline-block text-sm text-ink underline decoration-line underline-offset-4 transition hover:decoration-ink">How verification works</Link>
        </div>

        <div aria-live="polite" className="min-w-0">
          {state.kind === 'loading' && <div aria-busy="true" aria-label="Loading your verification tag" className="h-40 animate-pulse rounded-2xl bg-surface motion-reduce:animate-none" />}
          {state.kind === 'error' && (
            <div role="alert" className="rounded-2xl border border-line px-5 py-5">
              <p className="text-sm text-danger">Could not load your verification tag: {state.message}</p>
              <button type="button" onClick={retry} className="mt-3 text-sm text-ink underline decoration-line underline-offset-4 hover:decoration-ink">Try again</button>
            </div>
          )}
          {state.kind === 'ready' && (
            <div className="grid gap-5">
              <Snippet label="Option 1: add this tag inside the <head> of your homepage" value={state.meta} />
              <Snippet label={`Option 2: or put only this token in a file at ${state.file}`} value={state.token} />
              <div className="grid gap-3">
                <Snippet label="Option 3: or add a DNS TXT record. Name (host):" value={state.txt_name} />
                <Snippet label="Value:" value={state.txt_value} />
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}

export function Snippet({ label, value }: { label: string; value: string }) {
  const [copied, setCopied] = useState(false)
  async function copy() {
    try {
      await navigator.clipboard.writeText(value)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      // Clipboard can be blocked; the value stays selectable.
    }
  }
  return (
    <div>
      <p className="text-xs text-muted">{label}</p>
      <div className="mt-2 flex items-start gap-2 rounded-xl border border-line bg-surface py-2 pr-2 pl-4">
        <code className="min-w-0 flex-1 py-1.5 font-mono text-xs leading-relaxed break-all text-ink select-all">{value}</code>
        <button type="button" onClick={copy} aria-label={copied ? 'Copied' : 'Copy'} className="grid size-8 shrink-0 place-items-center rounded-full text-muted transition hover:bg-bg hover:text-ink">
          {copied ? <CheckIcon weight="light" className="size-4 text-accent" /> : <CopyIcon weight="light" className="size-4" />}
        </button>
      </div>
    </div>
  )
}
