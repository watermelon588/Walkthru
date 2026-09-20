import { SignOutIcon } from '@phosphor-icons/react'
import type { ReactNode } from 'react'
import { Link, NavLink, useNavigate } from 'react-router'
import { accountAvatar, accountProfile, signOut, useSession } from '../lib/auth'
import { AccountAvatar } from './AccountAvatar'
import { Logo } from './Shared'

/** Signed-in frame: bird, account email, sign out. Pages render inside. */
export function AppShell({ children }: { children: ReactNode }) {
  const { session } = useSession()
  const navigate = useNavigate()
  const profile = accountProfile(session)
  const displayName = profile.full_name || session?.user.email || 'Your account'
  const navClass = ({ isActive }: { isActive: boolean }) =>
    `text-sm transition hover:text-ink ${isActive ? 'text-ink' : 'text-muted'}`
  return (
    <div className="min-h-[100dvh] bg-bg text-ink">
      <header className="no-print mx-auto grid max-w-7xl grid-cols-[auto_1fr_auto] items-center gap-4 px-5 py-5 md:px-10">
        <Logo withName={false} />
        <nav aria-label="Workspace" className="hidden items-center justify-center gap-6 sm:flex">
          <NavLink end to="/app" className={navClass}>Runs</NavLink>
          <NavLink to="/app/settings" className={navClass}>Settings</NavLink>
        </nav>
        <div className="flex items-center justify-end gap-2 sm:gap-3">
          <Link to="/app/settings" aria-label={`Open settings for ${displayName}`} className="flex min-w-0 items-center gap-2 rounded-full p-1 pr-2 transition hover:bg-surface">
            <AccountAvatar name={displayName} src={accountAvatar(session)} />
            <span className="hidden max-w-36 truncate text-xs text-muted lg:block">{displayName}</span>
          </Link>
          <button
            type="button"
            aria-label="Sign out"
            onClick={() => signOut().then(() => navigate('/login', { replace: true }))}
            className="grid size-9 place-items-center rounded-full border border-line transition hover:bg-surface"
          >
            <SignOutIcon weight="light" className="size-4" />
          </button>
        </div>
        <nav aria-label="Workspace mobile" className="col-span-3 flex items-center gap-6 border-t border-line pt-4 sm:hidden">
          <NavLink end to="/app" className={navClass}>Runs</NavLink>
          <NavLink to="/app/settings" className={navClass}>Settings</NavLink>
        </nav>
      </header>
      <main className="mx-auto max-w-7xl px-5 pb-24 pt-8 md:px-10">{children}</main>
    </div>
  )
}
