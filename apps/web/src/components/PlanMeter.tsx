import { useGSAP } from '@gsap/react'
import { ArrowRightIcon, LightningIcon } from '@phosphor-icons/react'
import gsap from 'gsap'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { NOTIFICATION_EVENT, type Notification } from '../lib/notifications'
import { loadPlan, type PlanSummary } from '../lib/runs'
import { Orb, Skeleton } from './Loading'

gsap.registerPlugin(useGSAP)

const PLAN_NAME: Record<PlanSummary['plan'], string> = { free: 'Free', launch: 'Launch Pack', pro: 'Pro', plus: 'Plus' }
const short = (iso: string) => new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
const daysLeft = (iso: string) => Math.max(0, Math.ceil((new Date(iso).getTime() - Date.now()) / 86_400_000))

type State = { kind: 'loading' } | { kind: 'ready'; plan: PlanSummary } | { kind: 'error' }

function usePlan() {
  const [state, setState] = useState<State>({ kind: 'loading' })
  useEffect(() => {
    let active = true
    const read = (fresh: boolean) => loadPlan(fresh).then((plan) => active && setState({ kind: 'ready', plan })).catch(() => active && setState({ kind: 'error' }))
    read(false)
    // A finished run or a new pass changes the count: re-read it (lib/notifications).
    const onNote = (e: Event) => { const s = (e as CustomEvent<Notification>).detail?.section; if (s === 'runs' || s === 'billing') read(true) }
    window.addEventListener(NOTIFICATION_EVENT, onNote)
    return () => { active = false; window.removeEventListener(NOTIFICATION_EVENT, onNote) }
  }, [])
  return state
}

function tone(p: PlanSummary) {
  const share = p.runs_allowed ? p.runs_left / p.runs_allowed : 0
  return p.runs_left === 0 ? 'danger' : share <= 0.2 ? 'low' : 'ok'
}

/** Dashboard: which plan you are on and how many test runs are left, the first thing under the page title. */
export function PlanMeter() {
  const state = usePlan()
  const root = useRef<HTMLElement>(null)
  const plan = state.kind === 'ready' ? state.plan : null

  useGSAP(() => {
    if (!plan) return
    gsap.matchMedia().add('(prefers-reduced-motion: no-preference)', () => {
      const count = { n: 0 }
      const out = root.current?.querySelector('.plan-count')
      gsap.to(count, { n: plan.runs_left, duration: 1.4, ease: 'expo.out', onUpdate: () => { if (out) out.textContent = String(Math.round(count.n)) } })
      gsap.from('.plan-cell', { scaleY: 0, transformOrigin: 'bottom', duration: 0.7, ease: 'expo.out', stagger: { amount: 0.6 } })
      gsap.from('.plan-fade', { y: 10, autoAlpha: 0, duration: 0.9, ease: 'expo.out', stagger: 0.08 })
    })
  }, { scope: root, dependencies: [plan?.runs_left, plan?.plan] })

  if (state.kind === 'error') return null
  if (!plan) {
    return (
      <section role="status" aria-busy="true" aria-label="Loading your plan" className="mt-8 grid gap-5 rounded-2xl border border-line p-6 md:grid-cols-[auto_1fr] md:items-end md:gap-10">
        <div className="grid gap-3"><Skeleton className="h-6 w-24 rounded-full" /><Skeleton className="h-14 w-40" /></div>
        <div className="grid gap-3"><Skeleton className="h-3 w-1/2" /><Skeleton className="h-10" /></div>
      </section>
    )
  }

  const t = tone(plan)
  const used = Math.max(0, plan.runs_allowed - plan.runs_left)
  const cells = Math.min(plan.runs_allowed, 50)  // one cell per run up to 50; bigger plans share cells
  const filled = plan.runs_allowed ? Math.round((plan.runs_left / plan.runs_allowed) * cells) : 0
  const until = plan.expires_at ? `${plan.plan === 'free' ? 'Resets' : 'Pass ends'} ${short(plan.expires_at)}, ${daysLeft(plan.expires_at)} days` : plan.plan === 'free' ? 'Resets monthly' : 'No end date'
  const perks = [
    plan.logged_in ? 'Logged-in pages' : 'Public pages only',
    `Up to ${plan.max_steps} steps a run`,
    `${plan.sites_used.length} of ${plan.sites} site${plan.sites === 1 ? '' : 's'}`,
  ]

  return (
    <section ref={root} aria-labelledby="plan-meter-title" className="relative isolate mt-8 overflow-hidden rounded-2xl border border-line bg-bg">
      <Orb size={320} state="breathing" speed={0.6} className="pointer-events-none absolute -top-24 -right-20 -z-10 opacity-30" />
      <div className="grid gap-8 p-6 md:grid-cols-[auto_minmax(0,1fr)_auto] md:items-end md:gap-12 md:p-8">
        <div>
          <h2 id="plan-meter-title" className="plan-fade flex items-center gap-2">
            <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${plan.plan === 'free' ? 'border border-line text-ink' : 'bg-ink text-bg'}`}>
              {plan.plan !== 'free' && <LightningIcon weight="fill" className="size-3" aria-hidden />}
              {PLAN_NAME[plan.plan]} plan
            </span>
          </h2>
          <p className="mt-4 flex items-baseline gap-3" aria-label={`${plan.runs_left} of ${plan.runs_allowed} test runs left`}>
            <span aria-hidden className={`plan-count text-6xl font-extralight tracking-[-0.03em] tabular-nums md:text-7xl ${t === 'danger' ? 'text-danger' : 'text-ink'}`}>{plan.runs_left}</span>
            <span aria-hidden className="text-sm text-muted">of {plan.runs_allowed}<br />test runs left</span>
          </p>
        </div>

        <div className="min-w-0">
          <div className="plan-fade flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 text-xs text-muted">
            <span>{used} used</span>
            <span>{until}</span>
          </div>
          <div aria-hidden className="mt-3 flex h-10 items-end gap-[3px]">
            {Array.from({ length: cells }, (_, i) => (
              <span
                key={i}
                className={`plan-cell h-full flex-1 rounded-[3px] ${i < filled ? (t === 'danger' ? 'bg-danger' : t === 'low' ? 'bg-accent' : 'bg-ink') : 'bg-surface'}`}
              />
            ))}
          </div>
          <ul className="plan-fade mt-4 flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted">
            {perks.map((p) => <li key={p}>{p}</li>)}
          </ul>
        </div>

        <div className="plan-fade flex flex-col items-start gap-2 md:items-end">
          {t !== 'ok' && <p role="status" className={`text-xs ${t === 'danger' ? 'text-danger' : 'text-accent'}`}>{t === 'danger' ? 'No test runs left' : 'Running low'}</p>}
          <Link
            to="/app/billing"
            className={`inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm whitespace-nowrap transition active:scale-[0.98] ${plan.plan === 'free' || t !== 'ok' ? 'bg-ink text-bg hover:opacity-85' : 'border border-line text-ink hover:bg-surface'}`}
          >
            {plan.plan === 'free' ? 'Upgrade' : t !== 'ok' ? 'Get more runs' : 'Plan & billing'} <ArrowRightIcon weight="light" className="size-4" />
          </Link>
        </div>
      </div>
    </section>
  )
}

/** Sidebar: the same numbers in one line and a thin bar, on every signed-in page. */
export function PlanMini() {
  const state = usePlan()
  if (state.kind !== 'ready') return null
  const p = state.plan
  const t = tone(p)
  const share = p.runs_allowed ? (100 * p.runs_left) / p.runs_allowed : 0
  return (
    <Link to="/app/billing" aria-label={`${PLAN_NAME[p.plan]} plan, ${p.runs_left} of ${p.runs_allowed} test runs left. Open plan and billing.`} className="mt-6 block rounded-xl border border-line px-3 py-3 transition hover:bg-surface/60">
      <span className="flex items-baseline justify-between gap-2 text-xs">
        <span className="font-medium text-ink">{PLAN_NAME[p.plan]}</span>
        <span className={`tabular-nums ${t === 'danger' ? 'text-danger' : 'text-muted'}`}>{p.runs_left} / {p.runs_allowed} runs</span>
      </span>
      <span aria-hidden className="mt-2 block h-1 overflow-hidden rounded-full bg-surface">
        <span className={`block h-full rounded-full transition-[width] duration-700 ${t === 'danger' ? 'bg-danger' : t === 'low' ? 'bg-accent' : 'bg-ink'}`} style={{ width: `${share}%` }} />
      </span>
    </Link>
  )
}
