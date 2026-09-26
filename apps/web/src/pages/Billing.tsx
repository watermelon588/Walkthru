import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router'
import { AppShell } from '../components/AppShell'
import { btnPrimary } from '../components/Shared'
import { plans as tiers } from '../content'
import { NOTIFICATION_EVENT, type Notification } from '../lib/notifications'
import { getBilling, requestAccess, startCheckout, type BillingOffer, type BillingStatus } from '../lib/runs'

const PLAN_NAME: Record<BillingOffer['plan'], string> = { launch: 'Launch Pack', pro: 'Pro', plus: 'Plus' }
// What each plan adds, from the pricing cards (content.ts), minus the run count shown above it.
const includes = (plan: BillingOffer['plan']) => tiers.find((t) => t.name === PLAN_NAME[plan])?.features.filter((f) => !/test runs|Opens after/.test(f)).join(', ')
const money = (cents: number, currency: string) => new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(cents / 100)
const day = (iso: string) => new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
const time = (iso: string) => new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })

type Load = { kind: 'loading' } | { kind: 'error'; message: string } | { kind: 'ready'; data: BillingStatus }

/** Paid access (payment.md): request, founder approval, then a one-time Dodo payment. The pass turns on only when
 *  Dodo's signed webhook reaches the API; returning here from checkout proves nothing, so this page just re-reads. */
export default function Billing() {
  const [params] = useSearchParams()
  const returnedFor = params.get('offer')
  const [load, setLoad] = useState<Load>({ kind: 'loading' })

  const refresh = useCallback(() => getBilling().then((data) => setLoad({ kind: 'ready', data })).catch((e: Error) => setLoad({ kind: 'error', message: e.message })), [])
  useEffect(() => { refresh() }, [refresh])
  // A grant, an offer or a payment arrives live (lib/notifications): show it without a reload.
  useEffect(() => {
    const onNote = (e: Event) => { if ((e as CustomEvent<Notification>).detail?.section === 'billing') refresh() }
    window.addEventListener(NOTIFICATION_EVENT, onNote)
    return () => window.removeEventListener(NOTIFICATION_EVENT, onNote)
  }, [refresh])

  // Back from Dodo: poll briefly while the webhook arrives. The server alone decides whether it was paid.
  const waiting = load.kind === 'ready' && returnedFor !== null && load.data.offers.some((o) => o.id === returnedFor && o.status === 'approved')
  useEffect(() => {
    if (!waiting) return
    let tries = 0
    const timer = window.setInterval(() => {
      if (++tries > 20) window.clearInterval(timer)
      else getBilling().then((data) => setLoad({ kind: 'ready', data })).catch(() => undefined)
    }, 3000)
    return () => window.clearInterval(timer)
  }, [waiting])

  return (
    <AppShell title="Billing">
      <header className="border-b border-line pb-10">
        <p className="font-mono text-xs uppercase tracking-[0.16em] text-accent">Plan</p>
        <h1 className="mt-3 text-4xl font-extralight tracking-tight md:text-5xl">Plan & billing</h1>
        <p className="mt-4 max-w-[60ch] leading-relaxed text-muted">
          Paid access opens in small groups while we watch real costs. Request a plan, we review it, and you get a private offer to pay here. Each pass is a one-time payment for 30 days and never renews on its own.
        </p>
      </header>

      <div aria-live="polite" className="mt-10">
        {load.kind === 'loading' && <div aria-busy="true" aria-label="Loading your plan" className="h-48 animate-pulse rounded-2xl bg-surface motion-reduce:animate-none" />}
        {load.kind === 'error' && (
          <div role="alert" className="rounded-2xl border border-line px-5 py-5">
            <p className="text-sm text-danger">Could not load your plan: {load.message}</p>
            <button type="button" onClick={() => { setLoad({ kind: 'loading' }); refresh() }} className="mt-3 text-sm text-ink underline decoration-line underline-offset-4 hover:decoration-ink">Try again</button>
          </div>
        )}
        {load.kind === 'ready' && <BillingContent data={load.data} returnedFor={returnedFor} waiting={waiting} onChange={refresh} />}
      </div>
    </AppShell>
  )
}

function BillingContent({ data, returnedFor, waiting, onChange }: { data: BillingStatus; returnedFor: string | null; waiting: boolean; onChange: () => void }) {
  const open = data.offers.filter((o) => o.open)
  const pending = data.requests.find((r) => r.status === 'pending')
  const returned = returnedFor ? data.offers.find((o) => o.id === returnedFor) : undefined
  const plan = data.plan

  return (
    <div className="grid gap-14">
      {returned && <ReturnNotice offer={returned} waiting={waiting} />}

      <section aria-labelledby="current-heading" className="grid gap-2">
        <h2 id="current-heading" className="text-xl font-light">Current plan</h2>
        <p className="text-3xl font-extralight tracking-tight">{plan.plan === 'free' ? 'Free' : PLAN_NAME[plan.plan]}</p>
        <p className="text-sm text-muted">
          {plan.runs_left} of {plan.runs_allowed} test runs left
          {plan.expires_at && (plan.plan === 'free' ? `, resets ${day(plan.expires_at)}` : `, pass ends ${day(plan.expires_at)}`)}
        </p>
      </section>

      {open.length > 0 && (
        <section aria-labelledby="offers-heading">
          <h2 id="offers-heading" className="text-xl font-light">Your approved offer</h2>
          <div className="mt-6 grid gap-px overflow-hidden rounded-2xl border border-line bg-line">
            {open.map((o) => <OfferRow key={o.id} offer={o} enabled={data.checkout_enabled} />)}
          </div>
        </section>
      )}

      {open.length === 0 && (pending
        ? (
          <section aria-labelledby="request-heading" className="rounded-2xl border border-line px-6 py-6">
            <h2 id="request-heading" className="text-xl font-light">Request received</h2>
            <p className="mt-2 max-w-[56ch] text-sm leading-relaxed text-muted">
              Your {PLAN_NAME[pending.plan]} request from {day(pending.created_at)} is waiting for review. When it is approved, a private offer appears on this page for 24 hours.
            </p>
          </section>
        )
        : <RequestForm prices={data.prices} renewing={plan.plan !== 'free'} onDone={onChange} />)}

      {data.passes.length > 0 && (
        <section aria-labelledby="history-heading">
          <h2 id="history-heading" className="text-xl font-light">Passes</h2>
          <ul className="mt-6 divide-y divide-line border-y border-line">
            {[...data.passes].reverse().map((p) => (
              <li key={`${p.starts_at}-${p.plan}`} className="flex flex-wrap items-baseline justify-between gap-2 py-4 text-sm">
                <span className="text-ink">{PLAN_NAME[p.plan]}, {p.runs_granted} runs</span>
                <span className="font-mono text-xs text-muted">
                  {day(p.starts_at)} to {day(p.expires_at)}{p.revoked_at ? `, ended (${p.revoked_reason ?? 'revoked'})` : ''}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}

function ReturnNotice({ offer, waiting }: { offer: BillingOffer; waiting: boolean }) {
  if (offer.status === 'paid') {
    return <p role="status" className="rounded-2xl border border-line bg-surface px-5 py-4 text-sm text-ink">Payment confirmed. Your {PLAN_NAME[offer.plan]} pass is active.</p>
  }
  return (
    <p role="status" className="rounded-2xl border border-line px-5 py-4 text-sm text-muted">
      {waiting
        ? 'Waiting for Dodo to confirm your payment. This usually takes a few seconds.'
        : 'We have not received a payment confirmation for this offer. If you paid, it turns on as soon as Dodo confirms it; refresh in a minute.'}
    </p>
  )
}

function OfferRow({ offer, enabled }: { offer: BillingOffer; enabled: boolean }) {
  const [state, setState] = useState<{ kind: 'idle' } | { kind: 'opening' } | { kind: 'error'; message: string }>({ kind: 'idle' })
  const price = money(offer.price_cents, offer.currency)

  async function pay() {
    setState({ kind: 'opening' })
    try {
      window.location.assign(await startCheckout(offer.id))
    } catch (e) {
      setState({ kind: 'error', message: e instanceof Error ? e.message : 'Could not open the payment page' })
    }
  }

  return (
    <div className="grid gap-5 bg-bg p-6 sm:grid-cols-[1fr_auto] sm:items-center">
      <div>
        <p className="text-sm text-ink">{PLAN_NAME[offer.plan]}{offer.founding ? ', founding price' : ''}</p>
        <p className="mt-2 text-4xl font-extralight tracking-tight">{price}</p>
        <p className="mt-2 max-w-[56ch] text-sm leading-relaxed text-muted">
          One payment for {offer.runs} test runs within {offer.days} days. No auto-renewal. Unused runs expire at the end of the pass. Pay before {time(offer.checkout_expires_at)}.
        </p>
      </div>
      <div className="grid gap-2 sm:justify-items-end">
        <button type="button" onClick={pay} disabled={!enabled || state.kind === 'opening'} className={`${btnPrimary} disabled:cursor-not-allowed disabled:opacity-50`}>
          {state.kind === 'opening' ? 'Opening checkout' : `Pay ${price}`}
        </button>
        {!enabled && <p className="text-xs text-muted">Payments are not switched on yet.</p>}
        {state.kind === 'error' && <p role="alert" className="text-xs text-danger">{state.message}</p>}
      </div>
    </div>
  )
}

function RequestForm({ prices, renewing, onDone }: { prices: BillingStatus['prices']; renewing: boolean; onDone: () => void }) {
  const listed = prices.filter((p) => !p.founding)
  const [plan, setPlan] = useState<BillingOffer['plan']>('pro')
  const [note, setNote] = useState('')
  const [state, setState] = useState<{ kind: 'idle' } | { kind: 'sending' } | { kind: 'error'; message: string }>({ kind: 'idle' })

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setState({ kind: 'sending' })
    try {
      await requestAccess(plan, note.trim())
      onDone()
    } catch (e) {
      setState({ kind: 'error', message: e instanceof Error ? e.message : 'Could not send your request' })
    }
  }

  return (
    <section aria-labelledby="request-heading">
      <h2 id="request-heading" className="text-xl font-light">{renewing ? 'Request your next pass' : 'Request paid access'}</h2>
      <form onSubmit={submit} className="mt-6 grid gap-6">
        <fieldset className="grid gap-px overflow-hidden rounded-2xl border border-line bg-line sm:grid-cols-3">
          <legend className="sr-only">Plan</legend>
          {listed.map((p) => {
            const founding = prices.find((f) => f.plan === p.plan && f.founding)
            return (
              <label key={p.plan} className={`flex cursor-pointer flex-col gap-2 p-5 transition-colors ${plan === p.plan ? 'bg-surface' : 'bg-bg hover:bg-surface/60'}`}>
                <span className="flex items-center gap-3 text-sm text-ink">
                  <input type="radio" name="plan" value={p.plan} checked={plan === p.plan} onChange={() => setPlan(p.plan)} className="accent-ink" />
                  {PLAN_NAME[p.plan]}
                </span>
                <span className="text-2xl font-extralight tracking-tight">{money(p.price_cents, 'USD')}</span>
                <span className="text-xs leading-relaxed text-muted">
                  {p.runs} test runs, {p.days} days{founding ? `. Founding price ${money(founding.price_cents, 'USD')} for early users` : ''}
                </span>
                <span className="text-xs leading-relaxed text-ink">{includes(p.plan)}</span>
              </label>
            )
          })}
        </fieldset>
        <label htmlFor="request-note" className="grid gap-2 text-sm text-muted">
          What will you test? (optional)
          <textarea id="request-note" maxLength={500} rows={3} value={note} onChange={(e) => setNote(e.target.value)} placeholder="The signup and onboarding of my SaaS" className="w-full rounded-xl border border-line bg-bg px-4 py-3 text-sm text-ink placeholder:text-muted focus:border-ink focus:outline-none" />
        </label>
        <div className="flex flex-wrap items-center gap-4">
          <button type="submit" disabled={state.kind === 'sending'} className={`${btnPrimary} disabled:opacity-50`}>{state.kind === 'sending' ? 'Sending' : 'Request access'}</button>
          {state.kind === 'error' && <p role="alert" className="text-sm text-danger">{state.message}</p>}
        </div>
      </form>
    </section>
  )
}
