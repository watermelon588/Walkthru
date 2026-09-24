import { CrownSimpleIcon, GlobeSimpleIcon, LockKeyIcon, FootprintsIcon, UserIcon } from '@phosphor-icons/react'
import { Link } from 'react-router'
import { usePlan, type PlanState } from '../lib/plan'
import type { PlanSummary } from '../lib/runs'

const PLAN_NAME: Record<PlanSummary['plan'], string> = { free: 'Free', launch: 'Launch Pack', pro: 'Pro', plus: 'Plus' }

function renewal(plan: PlanSummary): string | null {
  if (!plan.expires_at) return null
  const day = new Date(plan.expires_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  return plan.plan === 'free' ? `Renews ${day}` : `Pass ends ${day}`
}

function Bar({ plan, thin = false }: { plan: PlanSummary; thin?: boolean }) {
  const share = plan.runs_allowed ? plan.runs_left / plan.runs_allowed : 0
  const low = share <= 0.2
  return (
    <span
      role="meter"
      aria-label="Test runs left"
      aria-valuemin={0}
      aria-valuemax={plan.runs_allowed}
      aria-valuenow={plan.runs_left}
      className={`block ${thin ? 'h-1' : 'h-2'} overflow-hidden rounded-full bg-surface`}
    >
      <span
        className={`block h-full rounded-full transition-[clip-path] duration-700 ease-[cubic-bezier(0.16,1,0.3,1)] motion-reduce:transition-none ${low ? 'bg-danger' : 'bg-ink'}`}
        style={{ clipPath: `inset(0 ${100 - Math.round(share * 100)}% 0 0 round 999px)` }}
      />
    </span>
  )
}

/** The dashboard's lead cell: runs left as the biggest number on the page, the plan behind it, and what it unlocks. */
export function PlanMeter({ state }: { state: PlanState }) {
  if (state.kind === 'loading') return <div aria-busy="true" aria-label="Loading your plan" className="h-full min-h-44 animate-pulse bg-bg motion-reduce:animate-none" />
  if (state.kind === 'error') {
    return (
      <div className="flex h-full flex-col justify-center bg-bg p-6">
        <p className="text-sm text-ink">Your plan could not be read just now.</p>
        <p className="mt-1 text-sm text-muted">Runs still work; reload the page in a moment to see what is left.</p>
      </div>
    )
  }
  const { plan } = state
  const paid = plan.plan !== 'free'
  const low = plan.runs_allowed > 0 && plan.runs_left / plan.runs_allowed <= 0.2
  const facts = [
    { icon: FootprintsIcon, text: `Up to ${plan.max_steps} steps a run` },
    { icon: plan.logged_in ? LockKeyIcon : GlobeSimpleIcon, text: plan.logged_in ? 'Logged-in pages included' : 'Public pages only' },
    { icon: GlobeSimpleIcon, text: `${plan.sites_used.length} of ${plan.sites} site${plan.sites > 1 ? 's' : ''} used` },
  ]
  return (
    <section aria-labelledby="plan-title" className="flex h-full flex-col bg-bg p-6">
      <div className="flex items-center justify-between gap-3">
        <h2 id="plan-title" className="flex items-center gap-2 text-sm font-medium">
          {paid ? <CrownSimpleIcon weight="fill" className="size-4 text-accent" aria-hidden /> : <UserIcon weight="light" className="size-4 text-muted" aria-hidden />}
          {PLAN_NAME[plan.plan]} plan
        </h2>
        {renewal(plan) && <span className="text-xs text-muted">{renewal(plan)}</span>}
      </div>
      <p className="mt-6 flex items-baseline gap-3">
        <span data-count={plan.runs_left} className={`text-6xl leading-none font-extralight tracking-[-0.03em] tabular-nums ${low ? 'text-danger' : 'text-ink'}`}>{plan.runs_left}</span>
        <span className="text-sm text-muted">of {plan.runs_allowed} test runs left</span>
      </p>
      <div className="mt-5"><Bar plan={plan} /></div>
      <ul className="mt-5 flex flex-wrap gap-x-5 gap-y-2 text-xs text-muted">
        {facts.map(({ icon: I, text }) => (
          <li key={text} className="flex items-center gap-1.5"><I weight="light" className="size-3.5" aria-hidden />{text}</li>
        ))}
      </ul>
      {(low || !paid) && (
        <p className="mt-auto pt-5 text-sm">
          {low && <span className="text-danger">Running low. </span>}
          <Link to="/#pricing" className="text-ink underline decoration-line underline-offset-4 transition hover:decoration-ink">
            {paid ? 'Extend your pass' : 'See paid plans'}
          </Link>
          <span className="text-muted">{paid ? '' : ' for logged-in pages and more runs.'}</span>
        </p>
      )}
    </section>
  )
}

/** Always-visible runs left, for the sidebar. */
export function PlanMeterCompact() {
  const state = usePlan()
  if (state.kind !== 'ready') return null
  const { plan } = state
  return (
    <Link to="/app" className="mt-6 block rounded-xl border border-line p-3 transition hover:bg-surface/60" aria-label={`${plan.runs_left} of ${plan.runs_allowed} test runs left on the ${PLAN_NAME[plan.plan]} plan`}>
      <span className="flex items-baseline justify-between gap-2">
        <span className="text-lg font-light tabular-nums">{plan.runs_left}<span className="text-xs text-muted"> / {plan.runs_allowed} runs</span></span>
        <span className="text-xs text-muted">{PLAN_NAME[plan.plan]}</span>
      </span>
      <span className="mt-2 block"><Bar plan={plan} thin /></span>
    </Link>
  )
}
