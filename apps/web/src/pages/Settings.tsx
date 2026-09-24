import { CheckCircleIcon, EnvelopeSimpleIcon, GithubLogoIcon, GoogleLogoIcon } from '@phosphor-icons/react'
import type { Session } from '@supabase/supabase-js'
import { useState, type FormEvent } from 'react'
import { AccountAvatar } from '../components/AccountAvatar'
import { AppShell } from '../components/AppShell'
import { DomainVerification } from '../components/DomainVerification'
import { YourData } from '../components/YourData'
import { AgentPresence } from '../components/AgentPresence'
import { btnPrimary } from '../components/Shared'
import { accountAvatar, accountProfile, updateAccountProfile, useSession, type AccountProfile } from '../lib/auth'

type SaveState = { kind: 'idle' } | { kind: 'saving' } | { kind: 'saved' } | { kind: 'error'; message: string }

const inputClass = 'w-full rounded-xl border border-line bg-bg px-4 py-3 text-sm text-ink placeholder:text-muted focus:border-ink focus:outline-none'
const labelClass = 'grid gap-2 text-sm text-muted'

export default function Settings() {
  const { loading, session } = useSession()

  if (loading || !session) {
    return <div role="status" aria-label="Loading account settings" className="min-h-[100dvh] bg-bg" />
  }

  return (
    <AppShell title="Settings">
      <SettingsContent key={session.user.id} session={session} />
    </AppShell>
  )
}

function SettingsContent({ session }: { session: Session }) {
  const [profile, setProfile] = useState<AccountProfile>(() => accountProfile(session))
  const [saveState, setSaveState] = useState<SaveState>({ kind: 'idle' })
  const displayName = profile.full_name || session.user.email || 'Your account'
  const providers = new Set(session.user.identities?.map((identity) => identity.provider) ?? [])

  function update<K extends keyof AccountProfile>(key: K, value: AccountProfile[K]) {
    setProfile((current) => ({ ...current, [key]: value }))
    setSaveState({ kind: 'idle' })
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const normalized = {
      ...profile,
      full_name: profile.full_name.trim(),
      company_name: profile.company_name.trim(),
      company_role: profile.company_role.trim(),
      website: profile.website.trim(),
    }
    if (normalized.account_type === 'business' && !normalized.company_name) {
      setSaveState({ kind: 'error', message: 'Add your business name before saving.' })
      return
    }
    if (normalized.website) {
      try {
        const protocol = new URL(normalized.website).protocol
        if (protocol !== 'http:' && protocol !== 'https:') throw new Error('Unsupported protocol')
      } catch {
        setSaveState({ kind: 'error', message: 'Use a full website address beginning with http:// or https://.' })
        return
      }
    }
    setSaveState({ kind: 'saving' })
    const next = normalized.account_type === 'business'
      ? normalized
      : { ...normalized, company_name: '', company_role: '', company_size: '' }
    try {
      await updateAccountProfile(session, next)
      setProfile(next)
      setSaveState({ kind: 'saved' })
    } catch (error) {
      setSaveState({ kind: 'error', message: error instanceof Error ? error.message : 'Could not save your profile' })
    }
  }

  return (
    <>
      <header className="grid gap-6 border-b border-line pb-10 sm:grid-cols-[1fr_auto] sm:items-end">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.16em] text-accent">Account</p>
          <h1 className="mt-3 text-4xl font-extralight tracking-tight md:text-5xl">Profile & settings</h1>
          <p className="mt-4 max-w-[58ch] leading-relaxed text-muted">Keep your identity and business context current. Walkthru uses this to make the workspace and reports feel like yours.</p>
        </div>
        <AgentPresence activity={saveState.kind === 'saving' ? 'Saving your profile' : saveState.kind === 'saved' ? 'Profile updated' : 'Keeping your workspace ready'} state={saveState.kind === 'error' ? 'stopped' : saveState.kind === 'saving' ? 'observing' : saveState.kind === 'saved' ? 'complete' : 'ready'} phase={0.22} />
      </header>

      <div className="mt-12 grid gap-16 lg:grid-cols-[minmax(0,1.35fr)_minmax(280px,0.65fr)]">
        <form onSubmit={save} className="min-w-0">
          <section aria-labelledby="profile-heading">
            <div className="flex items-center gap-4">
              <AccountAvatar name={displayName} src={accountAvatar(session)} large />
              <div>
                <h2 id="profile-heading" className="text-xl font-light">Your profile</h2>
                <p className="mt-1 text-sm text-muted">Shown only inside your Walkthru workspace.</p>
              </div>
            </div>

            <div className="mt-8 grid gap-5 sm:grid-cols-2">
              <label className={`${labelClass} sm:col-span-2`} htmlFor="full-name">
                Full name
                <input id="full-name" name="full_name" autoComplete="name" maxLength={120} value={profile.full_name} onChange={(event) => update('full_name', event.target.value)} className={inputClass} placeholder="Rohit Maity" />
              </label>
              <label className={`${labelClass} sm:col-span-2`} htmlFor="account-type">
                Account type
                <select id="account-type" name="account_type" value={profile.account_type} onChange={(event) => update('account_type', event.target.value === 'business' ? 'business' : 'individual')} className={inputClass}>
                  <option value="individual">Individual</option>
                  <option value="business">Business or agency</option>
                </select>
              </label>

              {profile.account_type === 'business' && (
                <>
                  <label className={labelClass} htmlFor="company-name">
                    Business name
                    <input id="company-name" name="company_name" autoComplete="organization" required maxLength={160} value={profile.company_name} onChange={(event) => update('company_name', event.target.value)} className={inputClass} placeholder="Your company" />
                  </label>
                  <label className={labelClass} htmlFor="company-role">
                    Your role
                    <input id="company-role" name="company_role" autoComplete="organization-title" maxLength={120} value={profile.company_role} onChange={(event) => update('company_role', event.target.value)} className={inputClass} placeholder="Founder, developer, QA lead" />
                  </label>
                  <label className={labelClass} htmlFor="company-size">
                    Team size
                    <select id="company-size" name="company_size" value={profile.company_size} onChange={(event) => update('company_size', event.target.value)} className={inputClass}>
                      <option value="">Choose a range</option>
                      <option value="1">Just me</option>
                      <option value="2-10">2 to 10</option>
                      <option value="11-50">11 to 50</option>
                      <option value="51-200">51 to 200</option>
                      <option value="201+">201+</option>
                    </select>
                  </label>
                </>
              )}

              <label className={`${labelClass} sm:col-span-2`} htmlFor="website">
                {profile.account_type === 'business' ? 'Business website' : 'Website'}
                <input id="website" name="website" type="url" autoComplete="url" maxLength={2048} value={profile.website} onChange={(event) => update('website', event.target.value)} className={inputClass} placeholder="https://yoursite.com" />
              </label>
            </div>

            <div className="mt-8 flex flex-wrap items-center gap-4">
              <button type="submit" disabled={saveState.kind === 'saving'} className={`${btnPrimary} disabled:opacity-60`}>
                {saveState.kind === 'saving' ? 'Saving...' : 'Save profile'}
              </button>
              <p aria-live="polite" className={`text-sm ${saveState.kind === 'error' ? 'text-danger' : 'text-muted'}`}>
                {saveState.kind === 'saved' && 'Your profile is up to date.'}
                {saveState.kind === 'error' && saveState.message}
              </p>
            </div>
          </section>
        </form>

        <aside className="min-w-0 border-t border-line pt-6 lg:border-l lg:border-t-0 lg:pl-10 lg:pt-0" aria-labelledby="access-heading">
          <h2 id="access-heading" className="text-xl font-light">Account access</h2>
          <p className="mt-2 text-sm leading-relaxed text-muted">Your session is secured by Supabase Auth. Connected identities are listed below.</p>

          <dl className="mt-7 grid gap-5">
            <ProviderRow icon={<EnvelopeSimpleIcon weight="light" />} name="Email" detail={session.user.email ?? 'No email'} connected />
            <ProviderRow icon={<GoogleLogoIcon weight="light" />} name="Google" detail={providers.has('google') ? 'Connected' : 'Use from the sign-in page'} connected={providers.has('google')} />
            <ProviderRow icon={<GithubLogoIcon weight="light" />} name="GitHub" detail={providers.has('github') ? 'Connected' : 'Use from the sign-in page'} connected={providers.has('github')} />
          </dl>

          <div className="mt-8 border-t border-line pt-6">
            <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-muted">Account ID</p>
            <p className="mt-2 break-all font-mono text-xs text-muted">{session.user.id}</p>
          </div>
        </aside>
      </div>
      <DomainVerification />
      <YourData email={session.user.email ?? ''} />
    </>
  )
}

function ProviderRow({ icon, name, detail, connected }: { icon: React.ReactNode; name: string; detail: string; connected: boolean }) {
  return (
    <div className="grid grid-cols-[auto_1fr_auto] items-center gap-3">
      <span className="grid size-9 place-items-center rounded-full border border-line text-muted [&>svg]:size-4" aria-hidden="true">{icon}</span>
      <div>
        <dt className="text-sm text-ink">{name}</dt>
        <dd className="mt-0.5 text-xs text-muted">{detail}</dd>
      </div>
      {connected && <CheckCircleIcon weight="fill" className="size-4 text-accent" aria-label="Connected" />}
    </div>
  )
}
