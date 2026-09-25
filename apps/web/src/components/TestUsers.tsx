import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import { createTestUser, deleteTestUser, getPlan, listTestUsers, type TestUser } from '../lib/runs'
import { btnPrimary } from './Shared'

type State = { kind: 'loading' } | { kind: 'locked' } | { kind: 'ready'; users: TestUser[] } | { kind: 'error'; message: string }

const MAX = 10
const input = 'w-full rounded-xl border border-line bg-bg px-4 py-3 text-sm text-ink placeholder:text-muted focus:border-ink focus:outline-none'

/** Plus: test users described in the owner's own words. Same layout as the other settings sections. */
export function TestUsers() {
  const [state, setState] = useState<State>({ kind: 'loading' })
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = () =>
    getPlan()
      .then((plan) => (plan.plan === 'plus' ? listTestUsers().then((users) => setState({ kind: 'ready', users })) : setState({ kind: 'locked' })))
      .catch((e: Error) => setState({ kind: 'error', message: e.message }))
  useEffect(() => { load() }, [])

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!name.trim()) return setError('Give the test user a name.')
    if (description.trim().length < 10) return setError('Describe who they are and what they care about, in a sentence or two.')
    setBusy(true)
    setError(null)
    try {
      await createTestUser(name.trim(), description.trim())
      setName('')
      setDescription('')
      await load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not save the test user.')
    } finally {
      setBusy(false)
    }
  }

  async function remove(user: TestUser) {
    if (!window.confirm(`Delete "${user.name}"? Past reports keep their name.`)) return
    setError(null)
    try {
      await deleteTestUser(user.id)
      await load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not delete the test user.')
    }
  }

  return (
    <section id="test-users" aria-labelledby="test-users-heading" className="mt-14 scroll-mt-24 border-t border-line pt-10">
      <div className="grid gap-10 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
        <div>
          <h2 id="test-users-heading" className="text-xl font-light">Your test users</h2>
          <p className="mt-2 max-w-[48ch] text-sm leading-relaxed text-muted">
            Describe the people who really use your product. They appear in the extension next to the four built-in test users, and you can run several on one goal to compare them in one report.
          </p>
          <Link to="/docs#test-users" className="mt-4 inline-block text-sm text-ink underline decoration-line underline-offset-4 transition hover:decoration-ink">How test users work</Link>
        </div>

        <div aria-live="polite" className="min-w-0">
          {state.kind === 'loading' && <div aria-busy="true" aria-label="Loading your test users" className="h-40 animate-pulse rounded-2xl bg-surface motion-reduce:animate-none" />}
          {state.kind === 'error' && (
            <div role="alert" className="rounded-2xl border border-line px-5 py-5">
              <p className="text-sm text-danger">Could not load your test users: {state.message}</p>
              <button type="button" onClick={() => { setState({ kind: 'loading' }); load() }} className="mt-3 text-sm text-ink underline decoration-line underline-offset-4 hover:decoration-ink">Try again</button>
            </div>
          )}
          {state.kind === 'locked' && (
            <div className="rounded-2xl border border-line px-5 py-5">
              <p className="text-sm text-ink">Custom test users are part of the Plus plan.</p>
              <p className="mt-1 text-sm text-muted">Every paid plan has the four built-in test users. <Link to="/#pricing" className="text-ink underline decoration-line underline-offset-4 hover:decoration-ink">See the plans</Link></p>
            </div>
          )}
          {state.kind === 'ready' && (
            <div className="grid gap-5">
              {state.users.length > 0 ? (
                <ul className="divide-y divide-line rounded-2xl border border-line">
                  {state.users.map((user) => (
                    <li key={user.id} className="flex items-start justify-between gap-4 px-5 py-4">
                      <div className="min-w-0">
                        <p className="text-sm text-ink">{user.name}</p>
                        <p className="mt-1 text-sm leading-relaxed text-muted">{user.description}</p>
                      </div>
                      <button type="button" onClick={() => remove(user)} className="shrink-0 text-xs text-muted underline decoration-line underline-offset-4 transition hover:text-danger hover:decoration-danger">Delete</button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="rounded-2xl border border-line px-5 py-4 text-sm text-muted">No test users of your own yet. Add the first one below.</p>
              )}
              {state.users.length < MAX ? (
                <form onSubmit={create} className="grid gap-4" noValidate>
                  <label htmlFor="test-user-name" className="grid gap-2 text-sm text-muted">
                    Name
                    <input id="test-user-name" value={name} onChange={(e) => setName(e.target.value)} maxLength={40} className={input} placeholder="Agency owner on a train" />
                  </label>
                  <label htmlFor="test-user-description" className="grid gap-2 text-sm text-muted">
                    Who they are and what they care about
                    <textarea id="test-user-description" value={description} onChange={(e) => setDescription(e.target.value)} maxLength={300} rows={3} className={input}
                      placeholder="Runs a small design agency, reads on a phone between meetings, wants pricing and a case study fast." />
                    <span className="text-xs">{description.trim().length} of 300 characters</span>
                  </label>
                  <div className="flex flex-wrap items-center gap-4">
                    <button type="submit" disabled={busy} className={`${btnPrimary} disabled:opacity-50`}>{busy ? 'Saving' : 'Add test user'}</button>
                    {error && <p role="alert" className="text-sm text-danger">{error}</p>}
                  </div>
                </form>
              ) : (
                <p className="text-sm text-muted">You have {MAX} test users, the most one account can keep. Delete one to add another.</p>
              )}
              <p className="text-xs leading-relaxed text-muted">Safety rules still apply to every test user: nothing that pays, deletes or cancels, and sends only on verified domains after you approve.</p>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
