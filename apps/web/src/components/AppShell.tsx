import type { ReactNode } from 'react'
import { useNavigate } from 'react-router'
import { signOut, useSession } from '../lib/auth'
import { Logo } from './Shared'

/** Signed-in frame: bird, account email, sign out. Pages render inside. */
export function AppShell({ children }: { children: ReactNode }) {
  const { session } = useSession()
  const navigate = useNavigate()
  return (
    <div className="min-h-[100dvh] bg-bg text-ink">
      <header className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 md:px-10">
        <Logo withName={false} />
        <div className="flex items-center gap-4 text-sm">
          <span className="hidden text-muted sm:block">{session?.user.email}</span>
          <button type="button" onClick={() => signOut().then(() => navigate('/login', { replace: true }))} className="rounded-full border border-line px-4 py-1.5 hover:bg-surface">
            Sign out
          </button>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-5 pb-24 pt-8 md:px-10">{children}</main>
    </div>
  )
}
