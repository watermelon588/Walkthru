import { EnvelopeSimpleIcon, GithubLogoIcon, GoogleLogoIcon } from '@phosphor-icons/react'
import { useRef, useState, type FormEvent } from 'react'
import { Navigate } from 'react-router'
import { brand } from '../brand'
import { Asset, btnGhost, btnPrimary, Logo } from '../components/Shared'
import { useSession } from '../lib/auth'
import { useReveal } from '../lib/motion'
import { supabase } from '../lib/supabase'

type Status = { kind: 'idle' } | { kind: 'sending' } | { kind: 'sent'; email: string } | { kind: 'error'; message: string }

// Where Supabase sends people after they sign in.
const redirectTo = `${location.origin}/app`

export default function Login() {
  const root = useRef<HTMLDivElement>(null)
  const [status, setStatus] = useState<Status>({ kind: 'idle' })
  const { session } = useSession()
  useReveal(root)
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

  async function oauth(provider: 'google' | 'github') {
    if (!supabase) return setStatus({ kind: 'error', message: 'Sign-in is not configured yet. Add the Supabase keys to apps/web/.env.' })
    const { error } = await supabase.auth.signInWithOAuth({ provider, options: { redirectTo } })
    if (error) setStatus({ kind: 'error', message: error.message })
  }

  const busy = status.kind === 'sending'

  return (
    <div ref={root} className="grid min-h-[100dvh] bg-bg text-ink lg:grid-cols-[1fr_1.1fr]">
      <main className="flex flex-col px-5 py-8 md:px-10">
        <Logo className="self-start" />

        <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center py-16">
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
                <button type="button" onClick={() => oauth('google')} className={`${btnGhost} justify-center`}>
                  <GoogleLogoIcon weight="light" className="size-4" /> Continue with Google
                </button>
                <button type="button" onClick={() => oauth('github')} className={`${btnGhost} justify-center`}>
                  <GithubLogoIcon weight="light" className="size-4" /> Continue with GitHub
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
                  {busy ? 'Sending link...' : 'Email me a sign-in link'}
                </button>
              </form>

              <p className="hero-fade mt-10 text-xs leading-relaxed text-muted">
                By continuing you agree to our <a href="#" className="underline underline-offset-2 hover:text-ink">Terms</a> and{' '}
                <a href="#" className="underline underline-offset-2 hover:text-ink">Privacy Policy</a>.
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
