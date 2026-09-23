import { BookOpenTextIcon, GearSixIcon, ListIcon, PathIcon, PuzzlePieceIcon, SignOutIcon, XIcon, type Icon } from '@phosphor-icons/react'
import { useEffect, useRef, type ReactNode } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router'
import { brand } from '../brand'
import { accountAvatar, accountProfile, signOut, useSession } from '../lib/auth'
import { AccountAvatar } from './AccountAvatar'
import { Logo, SkipLink } from './Shared'

const workspace: { to: string; label: string; icon: Icon; end?: boolean }[] = [
  { to: '/app', label: 'Runs', icon: PathIcon, end: true },
  { to: '/app/settings', label: 'Settings', icon: GearSixIcon },
]
const help: { href: string; label: string; icon: Icon }[] = [
  { href: '/docs', label: 'Documentation', icon: BookOpenTextIcon },
  { href: '/docs#install', label: 'Install the extension', icon: PuzzlePieceIcon },
]

const item = 'flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm transition-colors lg:min-h-9'

/** Signed-in frame. Desktop: a quiet sidebar. Phones: a top bar with a drawer holding the same navigation. */
export function AppShell({ children, title }: { children: ReactNode; title?: string }) {
  const drawer = useRef<HTMLDialogElement>(null)
  const { pathname } = useLocation()
  useEffect(() => { drawer.current?.close() }, [pathname])

  return (
    <div className="min-h-[100dvh] bg-bg text-ink lg:grid lg:grid-cols-[15rem_minmax(0,1fr)] print:block">
      {title && <title>{`${title} · ${brand.name}`}</title>}
      <SkipLink />

      <aside className="no-print sticky top-0 hidden h-[100dvh] flex-col border-r border-line px-4 py-6 lg:flex">
        <Logo className="px-3" />
        <SidebarNav />
      </aside>

      <header className="no-print sticky top-0 z-20 flex h-14 items-center justify-between border-b border-line/70 bg-bg/80 px-5 backdrop-blur-md lg:hidden">
        <Logo withName={false} />
        <button
          type="button"
          onClick={() => drawer.current?.showModal()}
          aria-label="Open navigation"
          className="grid size-10 place-items-center rounded-full border border-line transition hover:bg-surface"
        >
          <ListIcon weight="light" className="size-4" />
        </button>
      </header>

      <dialog
        ref={drawer}
        aria-label="Navigation"
        onClick={(e) => e.target === e.currentTarget && drawer.current?.close()}
        className="no-print m-0 h-[100dvh] max-h-none w-[min(20rem,86vw)] -translate-x-full bg-bg p-0 text-ink shadow-[24px_0_60px_-30px_rgba(27,27,31,0.35)] transition-[translate,overlay,display] transition-discrete duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] backdrop:bg-ink/0 backdrop:transition-[background-color,overlay,display] backdrop:transition-discrete backdrop:duration-300 open:translate-x-0 open:backdrop:bg-ink/25 motion-reduce:transition-none motion-reduce:backdrop:transition-none starting:open:-translate-x-full starting:open:backdrop:bg-ink/0 lg:hidden"
      >
        <div className="flex h-full flex-col px-4 pt-4 pb-[max(1.5rem,env(safe-area-inset-bottom))]">
          <div className="flex h-10 items-center justify-between pl-3">
            <Logo />
            <button type="button" onClick={() => drawer.current?.close()} aria-label="Close navigation" className="grid size-10 place-items-center rounded-full transition hover:bg-surface">
              <XIcon weight="light" className="size-4" />
            </button>
          </div>
          <SidebarNav />
        </div>
      </dialog>

      <main id="main" className="mx-auto w-full max-w-7xl px-5 pt-8 pb-24 md:px-10 lg:pt-12">{children}</main>
    </div>
  )
}

function SidebarNav() {
  const { session } = useSession()
  const navigate = useNavigate()
  const profile = accountProfile(session)
  const displayName = profile.full_name || session?.user.email || 'Your account'

  return (
    <>
      <nav aria-label="Workspace" className="mt-8 grid gap-1">
        {workspace.map(({ to, label, icon: I, end }) => (
          <NavLink key={to} to={to} end={end} className={({ isActive }) => `${item} ${isActive ? 'bg-surface text-ink' : 'text-muted hover:bg-surface/60 hover:text-ink'}`}>
            <I weight="light" className="size-[18px]" aria-hidden /> {label}
          </NavLink>
        ))}
      </nav>

      <nav aria-label="Help" className="mt-8 grid gap-1 border-t border-line pt-6">
        {help.map(({ href, label, icon: I }) => (
          <Link key={href} to={href} className={`${item} text-muted hover:bg-surface/60 hover:text-ink`}>
            <I weight="light" className="size-[18px]" aria-hidden /> {label}
          </Link>
        ))}
      </nav>

      <div className="mt-auto flex items-center gap-2 border-t border-line pt-4">
        <Link to="/app/settings" aria-label={`Open settings for ${displayName}`} className="flex min-w-0 flex-1 items-center gap-3 rounded-xl p-2 transition hover:bg-surface">
          <AccountAvatar name={displayName} src={accountAvatar(session)} />
          <span className="min-w-0 leading-tight">
            <span className="block truncate text-sm text-ink">{displayName}</span>
            {profile.full_name && session?.user.email && <span className="block truncate text-xs text-muted">{session.user.email}</span>}
          </span>
        </Link>
        <button
          type="button"
          aria-label="Sign out"
          title="Sign out"
          onClick={() => signOut().then(() => navigate('/login', { replace: true }))}
          className="grid size-10 shrink-0 place-items-center rounded-full text-muted transition hover:bg-surface hover:text-ink"
        >
          <SignOutIcon weight="light" className="size-4" />
        </button>
      </div>
    </>
  )
}
