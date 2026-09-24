import { Link } from 'react-router'
import { usePlan, type PlanState } from '../lib/plan'
import type { PlanSummary } from '../lib/runs'

const PLAN_NAME: Record<PlanSummary['plan'], string> = { free: 'Free', launch: 'Launch Pack', pro: 'Pro', plus: 'Plus' }

const isLow = (plan: PlanSummary) => plan.runs_allowed > 0 && plan.runs_left / plan.runs_allowed <= 0.2

function renewal(plan: PlanSummary): string {
  if (!plan.expires_at) return plan.plan === 'free' ? 'Renews monthly' : 'Active pass'
  const day = new Date(plan.expires_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  return plan.plan === 'free' ? `Renews ${day}` : `Pass ends ${day}`
}

function Bar({ plan }: { plan: PlanSummary }) {
  const share = plan.runs_allowed ? plan.runs_left / plan.runs_allowed : 0
  return (
    <span role="meter" aria-label="Test runs left" aria-valuemin={0} aria-valuemax={plan.runs_allowed} aria-valuenow={plan.runs_left} className="block h-1.5 overflow-hidden rounded-full bg-surface">
      <span
        className={`block h-full rounded-full transition-[clip-path] duration-700 ease-[cubic-bezier(0.16,1,0.3,1)] motion-reduce:transition-none ${isLow(plan) ? 'bg-danger' : 'bg-ink'}`}
        style={{ clipPath: `inset(0 ${100 - Math.round(share * 100)}% 0 0 round 999px)` }}
      />
    </span>
  )
}

/** Runs left and the plan, as figures in the dashboard's status card. Runs left leads: it decides whether a test can start. */
export function PlanFigures({ state }: { state: PlanState }) {
  if (state.kind === 'loading') return <div aria-busy="true" aria-label="Loading your plan" className="h-16 w-56 animate-pulse rounded-xl bg-surface motion-reduce:animate-none" />
  if (state.kind === 'error') return <p className="max-w-[28ch] text-sm text-muted">Your plan could not be read just now. Reload in a moment.</p>
  const { plan } = state
  return (
    <>
      <div className="min-w-[12rem] flex-1">
        <p className="flex items-baseline gap-2">
          <span data-count={plan.runs_left} className={`text-4xl leading-none font-extralight tracking-[-0.02em] tabular-nums ${isLow(plan) ? 'text-danger' : 'text-ink'}`}>{plan.runs_left}</span>
          <span className="text-sm text-muted">of {plan.runs_allowed} test runs left</span>
        </p>
        <div className="mt-3 max-w-xs"><Bar plan={plan} /></div>
        {(isLow(plan) || plan.plan === 'free') && (
          <Link to="/#pricing" className="mt-3 inline-block text-xs text-ink underline decoration-line underline-offset-4 transition hover:decoration-ink">
            {plan.plan === 'free' ? 'Paid plans add logged-in pages and more runs' : 'Running low: extend your pass'}
          </Link>
        )}
      </div>
      <div>
        <p className="text-4xl leading-none font-extralight tracking-[-0.02em]">{PLAN_NAME[plan.plan]}</p>
        <p className="mt-2 text-xs text-muted">{renewal(plan)}, {plan.max_steps} steps a run</p>
      </div>
    </>
  )
}

/** Runs left in the navigation bar, on every app page. */
export function PlanPill() {
  const state = usePlan()
  if (state.kind !== 'ready') return null
  const { plan } = state
  return (
    <Link
      to="/app"
      title={`${PLAN_NAME[plan.plan]} plan`}
      className={`hidden items-center gap-1.5 rounded-full border border-line px-3 py-1.5 text-xs tabular-nums transition hover:bg-surface sm:inline-flex ${isLow(plan) ? 'text-danger' : 'text-ink'}`}
    >
      {plan.runs_left} of {plan.runs_allowed} runs left
    </Link>
  )
}
