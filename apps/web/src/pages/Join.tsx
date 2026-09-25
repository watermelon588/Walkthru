import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { brand } from '../brand'
import { btnGhost, btnPrimary, Footer, Nav } from '../components/Shared'
import { useSession } from '../lib/auth'
import { acceptInvite, clearPendingJoin, pendingJoin, previewInvite, ROLE_A, ROLE_HELP, savePendingJoin, type Preview } from '../lib/teams'

type State = { kind: 'loading' } | { kind: 'ready'; preview: Preview } | { kind: 'error'; message: string } | { kind: 'none' }

/** /join#CODE: see a workspace invitation, then join. The code rides in the #fragment (never sent to a server) and
 *  is kept in this browser for an hour if the invitee has to sign in first. */
export default function Join() {
  const { loading, session } = useSession()
  const navigate = useNavigate()
  const [code] = useState(() => decodeURIComponent(window.location.hash.slice(1)).trim() || pendingJoin() || '')
  const [state, setState] = useState<State>(code ? { kind: 'loading' } : { kind: 'none' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!code) return
    savePendingJoin(code)
    window.history.replaceState(null, '', '/join')  // keep the code out of the address bar, screenshots and history
  }, [code])

  useEffect(() => {
    if (!code || loading || !session) return
    previewInvite(code)
      .then((preview) => setState({ kind: 'ready', preview }))
      .catch((e: Error) => setState({ kind: 'error', message: e.message }))
  }, [code, loading, session])

  async function join() {
    setBusy(true)
    setError(null)
    try {
      const { team_id } = await acceptInvite(code)
      clearPendingJoin()
      navigate(`/app/team/${team_id}`, { replace: true })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not join. Try again.')
      setBusy(false)
    }
  }

  function dismiss() {
    clearPendingJoin()
    navigate('/app/team', { replace: true })
  }

  return (
    <div className="flex min-h-[100dvh] flex-col bg-bg text-ink">
      <title>{`Join a workspace · ${brand.name}`}</title>
      <Nav />
      <main id="main" className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center px-5 py-24 md:px-10">
        <p className="font-mono text-xs uppercase tracking-[0.16em] text-accent">Team workspace</p>
        {state.kind === 'none' && (
          <>
            <h1 className="mt-3 text-4xl font-extralight tracking-tight md:text-5xl">No invitation here.</h1>
            <p className="mt-4 max-w-[52ch] leading-relaxed text-muted">Open the link from your invitation email again, or paste the code on the Team page.</p>
            <div className="mt-8"><Link to="/app/team" className={btnPrimary}>Go to Team</Link></div>
          </>
        )}
        {state.kind !== 'none' && !loading && !session && (
          <>
            <h1 className="mt-3 text-4xl font-extralight tracking-tight md:text-5xl">Sign in to see your invitation.</h1>
            <p className="mt-4 max-w-[52ch] leading-relaxed text-muted">
              Use the email address the invitation was sent to. This browser keeps the invitation for an hour and brings you back here after you sign in.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/login" className={btnPrimary}>Sign in or sign up</Link>
              <button type="button" onClick={dismiss} className={btnGhost}>Forget this invitation</button>
            </div>
          </>
        )}
        {session && state.kind === 'loading' && <div aria-busy="true" aria-label="Reading the invitation" className="mt-6 h-40 animate-pulse rounded-2xl bg-surface motion-reduce:animate-none" />}
        {session && state.kind === 'error' && (
          <>
            <h1 className="mt-3 text-4xl font-extralight tracking-tight md:text-5xl">This invitation does not work.</h1>
            <p role="alert" className="mt-4 max-w-[52ch] leading-relaxed text-danger">{state.message}</p>
            <div className="mt-8"><button type="button" onClick={dismiss} className={btnGhost}>Go to Team</button></div>
          </>
        )}
        {session && state.kind === 'ready' && (
          <>
            <h1 className="mt-3 text-4xl font-extralight tracking-tight md:text-5xl">{state.preview.member ? `You are in ${state.preview.team.name}.` : `Join ${state.preview.team.name}`}</h1>
            <p className="mt-4 max-w-[56ch] leading-relaxed text-muted">
              {state.preview.invited_by_name} invited you as {ROLE_A[state.preview.role]}. {ROLE_HELP[state.preview.role]}
            </p>
            {state.preview.problem && <p role="alert" className="mt-6 max-w-[56ch] rounded-2xl border border-line px-5 py-4 text-sm text-danger">{state.preview.problem}</p>}
            <div className="mt-8 flex flex-wrap items-center gap-3">
              {state.preview.member ? (
                <Link to={`/app/team/${state.preview.team.id}`} onClick={clearPendingJoin} className={btnPrimary}>Open the workspace</Link>
              ) : (
                <button type="button" onClick={join} disabled={busy || !!state.preview.problem} className={`${btnPrimary} disabled:opacity-50`}>{busy ? 'Joining' : 'Join workspace'}</button>
              )}
              <button type="button" onClick={dismiss} className={btnGhost}>Not now</button>
            </div>
            {error && <p role="alert" className="mt-4 text-sm text-danger">{error}</p>}
            <p className="mt-10 max-w-[56ch] text-xs leading-relaxed text-muted">
              Members of a workspace see the reports shared into it, the findings board and the chat. Your own runs stay private unless you share them.
              Signed in as {session.user.email}.
            </p>
          </>
        )}
      </main>
      <Footer />
    </div>
  )
}
