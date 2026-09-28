import { CheckIcon, CopyIcon } from '@phosphor-icons/react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { getVerification } from '../lib/runs'
import { SkeletonPanel } from './Loading'

type State = { kind: 'loading' } | { kind: 'ready'; meta: string; token: string; file: string; txt_name: string; txt_value: string } | { kind: 'error'; message: string }

/** Shows the owner's verification tag. One token per account verifies every site that carries it. */
export function DomainVerification() {
  const [state, setState] = useState<State>({ kind: 'loading' })
  const [domain, setDomain] = useState('')
  const [checking, setChecking] = useState(false)
  const [result, setResult] = useState<string | null>(null)
  let dnsName = '_walkthru'
  let dnsHost = '_walkthru'
  try {
    const host = new URL(domain.includes('://') ? domain : `https://${domain}`).hostname
    if (host) { dnsName = `_walkthru.${host}`; dnsHost = host }
  } catch { /* Keep generic instructions while an address is incomplete. */ }

  async function check(event: React.FormEvent) {
    event.preventDefault()
    setChecking(true)
    setResult(null)
    try {
      const response = await getVerification(domain)
      setResult(response.verified ? `Verified ${response.site}. You can now start an owner test. We recheck ownership when each run starts.` : `Proof not found for ${response.site}. Check the record name and value. DNS changes can take time to appear; try again after your provider has published them.`)
    } catch (e) { setResult(e instanceof Error ? e.message : 'Could not check this domain. Try again.') }
    finally { setChecking(false) }
  }
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
            Verify a live site without editing its source or deploying again: add a DNS TXT record at your domain provider. Ownership unlocks form testing, signed-in journeys and owner-only security checks.
          </p>
          <p className="mt-3 max-w-[48ch] text-sm leading-relaxed text-muted">Comparing public competitor pages does not require ownership. A scan confirmation cannot grant access to someone else's account or forms.</p>
          <Link to="/app/compare" className="mt-4 block text-sm underline decoration-line underline-offset-4">Compare public sites</Link>
          <Link to="/docs#verify" className="mt-4 inline-block text-sm text-ink underline decoration-line underline-offset-4 transition hover:decoration-ink">How verification works</Link>
        </div>

        <div aria-live="polite" className="min-w-0">
          {state.kind === 'loading' && <SkeletonPanel label="Loading your verification tag" />}
          {state.kind === 'error' && (
            <div role="alert" className="rounded-2xl border border-line px-5 py-5">
              <p className="text-sm text-danger">Could not load your verification tag: {state.message}</p>
              <button type="button" onClick={retry} className="mt-3 text-sm text-ink underline decoration-line underline-offset-4 hover:decoration-ink">Try again</button>
            </div>
          )}
          {state.kind === 'ready' && (
            <div className="grid gap-5">
              <form onSubmit={check} className="grid gap-4">
                <label htmlFor="verify-domain" className="grid gap-2 text-sm text-muted">Website to verify
                  <input id="verify-domain" required disabled={checking} value={domain} onChange={(e) => { setDomain(e.target.value); setResult(null) }} inputMode="url" autoCapitalize="none" spellCheck={false} placeholder="example.com or app.example.com" className="rounded-xl border border-line bg-bg px-4 py-3 text-ink" />
                </label>
                <div className="grid gap-3 rounded-2xl border border-line p-5">
                  <h3 className="text-sm font-medium">Recommended: DNS verification</h3>
                  <p className="text-xs leading-relaxed text-muted">In your DNS provider, add a TXT record. Keep your existing records. No source changes or redeploy needed.</p>
                  <Snippet label="Full record name" value={dnsName} />
                  <Snippet label="TXT value" value={state.txt_value} />
                  <p className="text-xs leading-relaxed text-muted">Some providers append your zone automatically. For example.com, enter _walkthru; for app.example.com in that zone, enter _walkthru.app. The final name must match the full record name above.{dnsHost !== '_walkthru' ? ` This verifies ${dnsHost} only.` : ''}</p>
                </div>
                <button type="submit" disabled={checking} className="justify-self-start rounded-full bg-ink px-5 py-3 text-sm text-bg hover:opacity-85 disabled:opacity-60">{checking ? 'Checking proof...' : 'Check verification'}</button>
                {result && <p role="status" className="text-sm leading-relaxed text-ink">{result}</p>}
              </form>
              <details className="border-t border-line pt-4"><summary className="cursor-pointer text-sm text-muted">Other ways to verify</summary><div className="mt-4 grid gap-5">
                <Snippet label="Add this tag inside the <head> of your homepage" value={state.meta} />
                <Snippet label={`Or put only this token in a file at ${state.file}`} value={state.token} />
                <p className="text-xs text-muted">On a hosted subdomain where you cannot manage DNS, use one of these methods or ask the site administrator to publish the proof.</p>
              </div></details>
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
