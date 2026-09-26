import { EnvelopeSimpleIcon, GithubLogoIcon, GoogleLogoIcon } from '@phosphor-icons/react'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Navigate } from 'react-router'
import { brand } from '../brand'
import { AgentPresence, type AgentPresenceState } from '../components/AgentPresence'
import { Asset, btnGhost, btnPrimary, Logo } from '../components/Shared'
import { useSession } from '../lib/auth'
import { useReveal } from '../lib/motion'
import { supabase } from '../lib/supabase'

type Provider = 'google' | 'github'
type Status =
  | { kind: 'idle' }
  | { kind: 'sending' }
  | { kind: 'oauth'; provider: Provider }
  | { kind: 'sent'; email: string }
  | { kind: 'error'; message: string }

// Where Supabase sends people after they sign in.
const redirectTo = `${location.origin}/app`
// If the provider's page has not opened by then (a blocked redirect, a dropped connection), free the buttons again.
const OAUTH_WAIT_MS = 10_000

export default function Login() {
  const root = useRef<HTMLDivElement>(null)
  const [status, setStatus] = useState<Status>({ kind: 'idle' })
  const waiting = useRef<number | undefined>(undefined)
  const { session } = useSession()
  useReveal(root)
  // Back from Google or GitHub without signing in: Chrome restores this page from its back-forward cache, frozen on
  // "Opening Google...". Start fresh instead, so every button works again.
  useEffect(() => {
    const restored = (e: PageTransitionEvent) => {
      if (!e.persisted) return
      window.clearTimeout(waiting.current)
      setStatus({ kind: 'idle' })
    }
    window.addEventListener('pageshow', restored)
    return () => {
      window.removeEventListener('pageshow', restored)
      window.clearTimeout(waiting.current)
    }
  }, [])
  if (session) return <Navigate to="/app" replace />

  async function sendLink(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const email = String(new FormData(e.currentTarget).get('email')).trim()
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return setStatus({ kind: 'error', message: 'Enter a valid email address.' })
    if (!supabase) return setStatus({ kind: 'error', message: 'Sign-in is not configured yet. Add the Supabase keys to apps/web/.env.' })
    setStatus({ kind: 'sending' })
    const { error } = await supabase.auth.signInWithOtp({ email, options: { emailRedirectTo: redirectTo } })
    setStatus(error ? { kind: 'error', message: error.message } : { kind: 'sent', email })
  }

  async function oauth(provider: Provider) {
    if (!supabase) return setStatus({ kind: 'error', message: 'Sign-in is not configured yet. Add the Supabase keys to apps/web/.env.' })
    setStatus({ kind: 'oauth', provider })
    window.clearTimeout(waiting.current)
    waiting.current = window.setTimeout(() => {
      if (document.visibilityState === 'visible') {
        setStatus({ kind: 'error', message: `${provider === 'google' ? 'Google' : 'GitHub'} did not open. Check your connection and try again.` })
      }
    }, OAUTH_WAIT_MS)
    const { error } = await supabase.auth.signInWithOAuth({ provider, options: { redirectTo } })
    if (error) {
      window.clearTimeout(waiting.current)
      setStatus({ kind: 'error', message: error.message })
    }
  }

  const busy = status.kind === 'sending' || status.kind === 'oauth'
  const agentState: AgentPresenceState = status.kind === 'error'
    ? 'stopped'
    : status.kind === 'sent'
      ? 'complete'
      : status.kind === 'sending' || status.kind === 'oauth'
        ? 'observing'
        : 'ready'
  const agentActivity = status.kind === 'error'
    ? 'Waiting for a valid sign-in'
    : status.kind === 'sent'
      ? 'Sign-in link sent'
      : status.kind === 'sending'
        ? 'Preparing your sign-in link'
        : status.kind === 'oauth'
          ? `Opening ${status.provider === 'google' ? 'Google' : 'GitHub'}`
        : 'Ready when you are'

  return (
    <div ref={root} className="grid min-h-[100dvh] bg-bg text-ink lg:grid-cols-[1fr_1.1fr]">
      <title>{`Sign in · ${brand.name}`}</title>
      <main id="main" className="flex flex-col px-5 py-8 md:px-10">
        <Logo className="self-start" />

        <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center py-16">
          <AgentPresence activity={agentActivity} state={agentState} className="mb-10" phase={0.16} />
          {status.kind === 'sent' ? (
            <div role="status" className="hero-fade">
              <EnvelopeSimpleIcon weight="light" className="size-8 text-accent" />
              <h1 className="mt-6 text-4xl font-extralight tracking-tight">Check your inbox.</h1>
              <p className="mt-4 leading-relaxed text-muted">
                We sent a sign-in link to <span className="text-ink">{status.email}</span>. It works once and expires in an hour.
              </p>
              <button type="button" onClick={() => setStatus({ kind: 'idle' })} className={`${btnGhost} mt-10`}>
                Use a different email
              </button>
            </div>
          ) : (
            <>
              <h1 className="text-4xl font-extralight tracking-tight md:text-5xl">
                <span className="inline-block overflow-hidden pb-[0.12em] align-bottom"><span className="word inline-block">Sign in</span></span>
              </h1>
              <p className="hero-fade mt-4 leading-relaxed text-muted">New to {brand.name}? The same steps create your account.</p>

              <div className="hero-fade mt-10 grid gap-3">
                <button type="button" disabled={busy} onClick={() => oauth('google')} className={`${btnGhost} justify-center disabled:opacity-60`}>
                  <GoogleLogoIcon weight="light" className="size-4" /> {status.kind === 'oauth' && status.provider === 'google' ? 'Opening Google...' : 'Continue with Google'}
                </button>
                <button type="button" disabled={busy} onClick={() => oauth('github')} className={`${btnGhost} justify-center disabled:opacity-60`}>
                  <GithubLogoIcon weight="light" className="size-4" /> {status.kind === 'oauth' && status.provider === 'github' ? 'Opening GitHub...' : 'Continue with GitHub'}
                </button>
              </div>

              <div className="hero-fade my-8 flex items-center gap-4 text-xs text-muted" aria-hidden>
                <span className="h-px flex-1 bg-line" /> or <span className="h-px flex-1 bg-line" />
              </div>

              <form onSubmit={sendLink} noValidate className="hero-fade grid gap-2">
                <label htmlFor="email" className="text-sm text-muted">Work email</label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  placeholder="you@yoursite.com"
                  aria-invalid={status.kind === 'error'}
                  aria-describedby="email-error"
                  className="w-full rounded-xl border border-line bg-bg px-4 py-3 text-sm placeholder:text-muted focus:border-ink focus:outline-none"
                />
                <p id="email-error" role="alert" className="min-h-5 text-sm text-danger">{status.kind === 'error' ? status.message : ''}</p>
                <button type="submit" disabled={busy} className={`${btnPrimary} mt-1 justify-center disabled:opacity-60`}>
                  {status.kind === 'sending' ? 'Sending link...' : 'Email me a sign-in link'}
                </button>
              </form>

              <p className="hero-fade mt-10 text-xs leading-relaxed text-muted">
                By continuing you agree to our <a href="/terms" className="underline underline-offset-2 hover:text-ink">Terms</a> and{' '}
                <a href="/privacy" className="underline underline-offset-2 hover:text-ink">Privacy Policy</a>.
              </p>
            </>
          )}
        </div>
      </main>

      {/* Full-height photo. Swap public/assets/login.jpg to change it (portrait, 1600x2000 or larger). */}
      <aside className="relative hidden lg:block">
        <Asset name="login.jpg" eager label="A person settling into a lounge chair, blurred in motion" className="absolute inset-0 h-full !rounded-none object-[50%_65%] saturate-[.55]" />
      </aside>
    </div>
  )
}
