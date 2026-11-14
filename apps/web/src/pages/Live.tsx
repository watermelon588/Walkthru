import { ArrowRightIcon, CameraIcon, CursorClickIcon, GlobeSimpleIcon, TimerIcon } from '@phosphor-icons/react'
import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { Link, useNavigate } from 'react-router'
import { AppShell } from '../components/AppShell'
import { Orb, Skeleton } from '../components/Loading'
import { GOAL_IDEAS, MAX_LIVE_PERSONAS, PERSONA_HINT, personaOrb, siteUrl } from '../lib/live'
import { listTestUsers, liveGoalIdeas, loadPlan, PERSONA_LABEL, startLive, type PlanSummary, type TestUser } from '../lib/runs'

const BUILT_IN = ['first_timer', 'phone_user', 'buyer', 'skeptic']
const FACTS = [
  { icon: GlobeSimpleIcon, text: 'Opens the page in Walkthru\'s browser, signed out.' },
  { icon: CursorClickIcon, text: 'Reads, scrolls and clicks. Never submits, buys or sends.' },
  { icon: CameraIcon, text: 'Saves a frame per step with form fields blurred.' },
  { icon: TimerIcon, text: 'One browser at a time, up to four minutes each.' },
]

/** Start a live run: a test user walks a public site in Walkthru's own browser, no extension needed. One column:
 *  where, what, who, then go. */
export default function Live() {
  const navigate = useNavigate()
  const [plan, setPlan] = useState<PlanSummary | null>(null)
  const [custom, setCustom] = useState<TestUser[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)
  const [site, setSite] = useState('')
  const [goal, setGoal] = useState('')
  const [chosen, setChosen] = useState<string[]>(['first_timer'])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [ideas, setIdeas] = useState<{ site: string; state: 'reading' | 'ready'; list: string[] } | null>(null)

  // Suggestions from the site's own links and buttons, once the address looks complete. One request per address.
  const address = siteUrl(site)
  useEffect(() => {
    if (!address) return
    const timer = window.setTimeout(() => {
      setIdeas({ site: address, state: 'reading', list: [] })
      liveGoalIdeas(address)
        .then(({ ideas: list }) => setIdeas((now) => now?.site === address ? { site: address, state: 'ready', list } : now))
        .catch(() => setIdeas((now) => now?.site === address ? { site: address, state: 'ready', list: [] } : now))
    }, 900)
    return () => window.clearTimeout(timer)
  }, [address])
  const reading = !!address && ideas?.site === address && ideas.state === 'reading'
  const fromSite = address && ideas?.site === address && ideas.state === 'ready' ? ideas.list : []

  useEffect(() => {
    loadPlan()
      .then((loaded) => {
        setPlan(loaded)
        if (loaded.plan === 'plus') listTestUsers().then(setCustom).catch(() => setCustom([])) // saved test users are extra; the built-in ones still work
      })
      .catch((e: Error) => setLoadError(e.message))
  }, [])

  const many = plan?.plan === 'plus'
  const allowed = (key: string) => !!plan && (key.startsWith('custom:') ? many : plan.personas.includes(key))

  function toggle(key: string) {
    setError(null)
    if (!many) return setChosen([key])
    setChosen((now) => now.includes(key) ? (now.length > 1 ? now.filter((k) => k !== key) : now) : now.length < MAX_LIVE_PERSONAS ? [...now, key] : now)
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const url = siteUrl(site)
    if (!url) return setError('Enter the address of a public website, like yoursite.com.')
    if (!goal.trim()) return setError('Say what the test user should try to do.')
    if (plan && plan.runs_left < chosen.length) return setError(`This test needs ${chosen.length} ${chosen.length === 1 ? 'run' : 'runs'} and you have ${plan.runs_left} left.`)
    setBusy(true)
    setError(null)
    try {
      const test = await startLive(url, goal.trim(), chosen)
      navigate(`/app/live/${test.group_id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'The test could not start. Try again.')
      setBusy(false)
    }
  }

  const options = [
    ...BUILT_IN.map((key) => ({ key, name: PERSONA_LABEL[key] ?? key, about: PERSONA_HINT[key] ?? '' })),
    ...custom.map((user) => ({ key: `custom:${user.id}`, name: user.name, about: user.description })),
  ]

  return (
    <AppShell title="Live run">
      <div className="relative isolate mx-auto max-w-3xl">
        <div aria-hidden className="pointer-events-none absolute inset-x-0 -top-32 -z-10 flex justify-center overflow-hidden opacity-25">
          <Orb size={560} state={busy ? 'working' : 'breathing'} speed={0.5} className="shrink-0 max-md:scale-[0.65]" />
        </div>

        <header className="pt-4 text-center md:pt-10">
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-accent">Live run <span className="text-muted">· no install</span></p>
          <h1 className="mt-4 text-4xl font-extralight tracking-[-0.035em] md:text-6xl">Watch a stranger<br />try your site</h1>
          <p className="mx-auto mt-5 max-w-[50ch] leading-relaxed text-muted">
            A test user opens a public page, chases one goal and thinks aloud. You watch every step, then get the usual report.
          </p>
        </header>

        {loadError && <p role="alert" className="mt-14 text-center text-sm text-danger">Could not load your plan: {loadError}</p>}
        {!plan && !loadError && (
          <div role="status" aria-busy="true" aria-label="Loading your plan" className="mt-14 grid gap-5 rounded-2xl border border-line bg-bg/80 p-6 sm:p-8">
            <Skeleton className="h-3 w-24" /><Skeleton className="h-12 rounded-xl" />
            <Skeleton className="h-3 w-40" /><Skeleton className="h-24 rounded-xl" />
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-32 rounded-xl" />)}</div>
          </div>
        )}

        {plan && (
          <form onSubmit={submit} noValidate className="mt-16 divide-y divide-line">
            <Section n="01" label="Where" htmlFor="live-site" title="Page to start on">
              <div className="flex items-center gap-3 rounded-xl border border-line bg-bg px-4 transition-[border-color,box-shadow] duration-150 focus-within:border-ink focus-within:shadow-[0_0_0_3px_var(--color-surface)]">
                <GlobeSimpleIcon aria-hidden className="size-4 shrink-0 text-muted" />
                <input id="live-site" inputMode="url" autoComplete="url" spellCheck={false} value={site} onChange={(e) => { setSite(e.target.value); setError(null) }} placeholder="yoursite.com" disabled={busy}
                  className="field-bare min-w-0 flex-1 bg-transparent py-3.5 font-mono text-sm text-ink placeholder:text-muted" />
              </div>
            </Section>

            <Section n="02" label="Goal" htmlFor="live-goal" title="What should the test user try to do?">
              <textarea id="live-goal" rows={2} maxLength={500} value={goal} onChange={(e) => { setGoal(e.target.value); setError(null) }} placeholder="Find the pricing and work out which plan fits a team of three" disabled={busy}
                className="field-bare w-full resize-none rounded-xl border border-line bg-bg px-4 py-3.5 text-lg leading-snug font-light text-ink transition-[border-color,box-shadow] duration-150 placeholder:text-muted/70 focus:border-ink focus:shadow-[0_0_0_3px_var(--color-surface)]" />
              <p className="mt-4 text-xs text-muted" aria-live="polite">
                {reading ? 'Reading your site for goals it supports...' : fromSite.length ? 'Goals your site supports, from its own links and buttons' : address && ideas?.site === address ? 'Could not read goals from this site. Some general ones' : 'Some goals to start from'}
              </p>
              <ul className="mt-2.5 flex flex-wrap gap-2">
                {reading && [0, 1, 2].map((i) => <li key={i} className="skeleton h-8 w-44 rounded-full" aria-hidden />)}
                {!reading && (fromSite.length ? fromSite : GOAL_IDEAS).map((idea) => (
                  <li key={idea}>
                    <button type="button" disabled={busy} onClick={() => { setGoal(idea); setError(null) }} aria-pressed={goal === idea}
                      className={`rounded-full border px-3.5 py-1.5 text-left text-xs transition-[background-color,border-color,transform] duration-150 active:scale-[0.97] disabled:opacity-60 ${goal === idea ? 'border-ink bg-surface text-ink' : 'border-line text-muted hover:border-ink/30 hover:text-ink'}`}>{idea}</button>
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-xs leading-relaxed text-muted/90">Say what a visitor would want, not where to click.</p>
            </Section>

            <fieldset disabled={busy} className="py-8">
              <legend className="sr-only">{many ? `Test users, up to ${MAX_LIVE_PERSONAS}` : 'Test user'}</legend>
              <StepLabel n="03" label="Who" title={many ? `Test users · up to ${MAX_LIVE_PERSONAS}, one after another` : 'Test user'} />
              <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
                {options.map(({ key, name, about }) => {
                  const on = chosen.includes(key)
                  const open = allowed(key)
                  return (
                    <label key={key} className={`group relative grid cursor-pointer justify-items-center gap-2 rounded-xl border px-3 pt-4 pb-4 text-center transition-[background-color,border-color,transform] duration-150 active:scale-[0.98] has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-accent ${on ? 'border-ink bg-surface' : 'border-line hover:border-ink/30'} ${open ? '' : 'cursor-not-allowed opacity-50'}`}>
                      <input type={many ? 'checkbox' : 'radio'} name="live-persona" checked={on} disabled={!open} onChange={() => toggle(key)} className="sr-only" />
                      <Orb size={56} state={personaOrb(key)} speed={on ? 1 : 0.25} className={`transition-opacity duration-300 ${on ? 'opacity-100' : 'opacity-55 group-hover:opacity-80'}`} />
                      <span className="text-sm text-ink">{name}</span>
                      <span className="text-[11px] leading-snug text-muted">{open ? about || 'Your test user' : 'On a paid plan'}</span>
                      <span aria-hidden className={`absolute top-2.5 right-2.5 size-2 rounded-full transition-colors ${on ? 'bg-ink' : 'bg-line'}`} />
                    </label>
                  )
                })}
              </div>
            </fieldset>

            <div className="flex flex-wrap items-center justify-between gap-4 py-7">
              <p className="text-xs text-muted">Uses {chosen.length} of your {plan.runs_left} {plan.runs_left === 1 ? 'run' : 'runs'} left</p>
              <button type="submit" disabled={busy} className="group inline-flex items-center gap-2 rounded-full bg-ink px-6 py-3 text-sm text-bg transition-[opacity,transform] duration-150 hover:opacity-90 active:scale-[0.97] disabled:opacity-60">
                {busy ? 'Starting...' : 'Start live run'}
                <ArrowRightIcon aria-hidden className="size-4 transition-transform duration-200 group-hover:translate-x-0.5 motion-reduce:transition-none" />
              </button>
              {error && <p role="alert" className="w-full text-sm text-danger">{error}</p>}
            </div>
          </form>
        )}

        <ul aria-label="What a live run does" className="mt-4 grid gap-x-10 gap-y-4 border-t border-line pt-8 sm:grid-cols-2">
          {FACTS.map(({ icon: Icon, text }) => (
            <li key={text} className="flex items-start gap-3 text-sm leading-relaxed text-muted">
              <Icon aria-hidden className="mt-0.5 size-4 shrink-0 text-accent" />{text}
            </li>
          ))}
        </ul>
        <p className="mt-6 text-center text-sm text-muted">
          Testing a signed-in area or a site on your computer? <Link to="/docs#install" className="text-ink underline decoration-line underline-offset-4 hover:decoration-ink">Use the extension</Link>
        </p>
      </div>
    </AppShell>
  )
}

function StepLabel({ n, label, title, htmlFor }: { n: string; label: string; title: string; htmlFor?: string }) {
  const Tag = htmlFor ? 'label' : 'p'
  return (
    <div className="flex items-baseline gap-3">
      <span aria-hidden className="font-mono text-[11px] text-muted">{n}</span>
      <span aria-hidden className="font-mono text-[11px] uppercase tracking-[0.16em] text-accent">{label}</span>
      <Tag htmlFor={htmlFor} className="text-sm text-ink">{title}</Tag>
    </div>
  )
}

function Section({ n, label, title, htmlFor, children }: { n: string; label: string; title: string; htmlFor: string; children: ReactNode }) {
  return (
    <div className="py-8 first:pt-0">
      <StepLabel n={n} label={label} title={title} htmlFor={htmlFor} />
      <div className="mt-4">{children}</div>
    </div>
  )
}
