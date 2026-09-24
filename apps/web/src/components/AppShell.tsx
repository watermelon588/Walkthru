import { BookOpenTextIcon, GearSixIcon, ListIcon, PathIcon, PuzzlePieceIcon, SignOutIcon, XIcon, type Icon } from '@phosphor-icons/react'
import { useEffect, useRef, type ReactNode } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router'
import { brand } from '../brand'
import { accountAvatar, accountProfile, signOut, useSession } from '../lib/auth'
import { AccountAvatar } from './AccountAvatar'
import { PlanPill } from './PlanMeter'
import { Logo, SkipLink } from './Shared'

const links: { to: string; label: string; icon: Icon; end?: boolean }[] = [
  { to: '/app', label: 'Runs', icon: PathIcon, end: true },
  { to: '/app/settings', label: 'Settings', icon: GearSixIcon },
  { to: '/docs', label: 'Docs', icon: BookOpenTextIcon },
]

/** Signed-in frame. The same top bar and centred column as the marketing and docs pages, so the product reads as one site. */
export function AppShell({ children, title }: { children: ReactNode; title?: string }) {
  const { session } = useSession()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const account = useRef<HTMLDetailsElement>(null)
  const menu = useRef<HTMLDetailsElement>(null)
  useEffect(() => {
    account.current?.removeAttribute('open')
    menu.current?.removeAttribute('open')
  }, [pathname])

  const profile = accountProfile(session)
  const displayName = profile.full_name || session?.user.email || 'Your account'
  const leave = () => signOut().then(() => navigate('/login', { replace: true }))

  return (
    <div className="min-h-[100dvh] bg-bg text-ink">
      {title && <title>{`${title} · ${brand.name}`}</title>}
      <header className="no-print sticky top-0 z-20 border-b border-line/70 bg-bg/80 backdrop-blur-md">
        <SkipLink />
        <nav aria-label="Workspace" className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-5 md:px-10">
          <div className="flex items-center gap-8">
            <Logo withName={false} />
            <div className="hidden items-center gap-7 text-sm md:flex">
              {links.map(({ to, label, end }) => (
                <NavLink key={to} to={to} end={end} className={({ isActive }) => (isActive ? 'text-ink' : 'text-muted transition hover:text-ink')}>
                  {label}
                </NavLink>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-3">
            <PlanPill />
            <details ref={account} className="relative hidden md:block">
              <summary aria-label={`Account menu for ${displayName}`} className="flex cursor-pointer list-none items-center rounded-full transition hover:opacity-80 [&::-webkit-details-marker]:hidden">
                <AccountAvatar name={displayName} src={accountAvatar(session)} />
              </summary>
              <div className="absolute right-0 top-12 w-64 rounded-2xl border border-line bg-card p-2 shadow-[0_18px_40px_-24px_rgba(27,27,31,0.35)]">
                <p className="truncate px-3 pt-2 text-sm text-ink">{displayName}</p>
                {profile.full_name && session?.user.email && <p className="truncate px-3 text-xs text-muted">{session.user.email}</p>}
                <div className="mt-2 grid border-t border-line pt-2">
                  <MenuLink to="/docs#install" icon={PuzzlePieceIcon}>Install the extension</MenuLink>
                  <MenuLink to="/app/settings" icon={GearSixIcon}>Settings</MenuLink>
                  <button type="button" onClick={leave} className="flex min-h-10 items-center gap-3 rounded-xl px-3 text-left text-sm text-muted transition hover:bg-surface hover:text-ink">
                    <SignOutIcon weight="light" className="size-4" aria-hidden /> Sign out
                  </button>
                </div>
              </div>
            </details>

            <details ref={menu} className="group md:hidden">
              <summary aria-label="Menu" className="grid size-10 cursor-pointer list-none place-items-center rounded-full border border-line transition hover:bg-surface [&::-webkit-details-marker]:hidden">
                <ListIcon weight="light" className="size-4 group-open:hidden" />
                <XIcon weight="light" className="hidden size-4 group-open:block" />
              </summary>
              <div className="absolute inset-x-0 top-16 border-y border-line bg-bg px-5 pb-6 shadow-[0_24px_40px_-32px_rgba(27,27,31,0.4)]">
                <ul className="grid text-lg font-light">
                  {links.map(({ to, label }) => (
                    <li key={to} className="border-b border-line">
                      <Link to={to} className="flex min-h-12 items-center py-2 text-ink">{label}</Link>
                    </li>
                  ))}
                  <li className="border-b border-line"><Link to="/docs#install" className="flex min-h-12 items-center py-2 text-ink">Install the extension</Link></li>
                  <li><button type="button" onClick={leave} className="flex min-h-12 w-full items-center py-2 text-left text-muted">Sign out</button></li>
                </ul>
              </div>
            </details>
          </div>
        </nav>
      </header>

      <main id="main" className="mx-auto w-full max-w-6xl px-5 pt-10 pb-24 md:px-10 md:pt-14">{children}</main>
    </div>
  )
}

function MenuLink({ to, icon: I, children }: { to: string; icon: Icon; children: ReactNode }) {
  return (
    <Link to={to} className="flex min-h-10 items-center gap-3 rounded-xl px-3 text-sm text-muted transition hover:bg-surface hover:text-ink">
      <I weight="light" className="size-4" aria-hidden /> {children}
    </Link>
  )
}
