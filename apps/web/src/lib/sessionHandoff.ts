/** Exact named extension only. A bounded acknowledgment prevents a missing worker blocking website logout. */
export type ExtensionRuntime = { sendMessage: (id: string, message: unknown, callback: (response: unknown) => void) => void; lastError?: { message?: string } }
export type HandoffSession = { access_token: string; refresh_token: string; expires_at?: number; user: { id: string } }

export function authSessionId(token: string): string | undefined {
  try {
    const payload = token.split('.')[1]!
    const id: unknown = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/'))).session_id
    return typeof id === 'string' && /^[a-f0-9]{8}(-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i.test(id) ? id : undefined
  } catch { return undefined }
}

export function sameLogin(first: HandoffSession | null, second: HandoffSession | null): boolean {
  if (!first || !second || first.user.id !== second.user.id) return false
  const id = authSessionId(first.access_token)
  return id ? id === authSessionId(second.access_token) : first.access_token === second.access_token
}

export function extensionMessage(runtime: ExtensionRuntime | undefined, id: string | undefined, message: unknown): Promise<Record<string, unknown> | null> {
  if (!runtime?.sendMessage || !id) return Promise.resolve(null)
  return new Promise((resolve) => {
    const timeout = setTimeout(() => resolve(null), 3000)
    try {
      runtime.sendMessage(id, message, (response) => {
        clearTimeout(timeout)
        resolve(runtime.lastError || !response || typeof response !== 'object' ? null : response as Record<string, unknown>)
      })
    } catch { clearTimeout(timeout); resolve(null) }
  })
}

export async function connectSession(runtime: ExtensionRuntime | undefined, id: string | undefined,
  current: () => Promise<HandoffSession | null>, allowed: () => boolean): Promise<boolean> {
  const first = await current()
  if (!first || !allowed()) return false
  const challenge = await extensionMessage(runtime, id, { type: 'begin_connect', user_id: first.user.id, session_id: authSessionId(first.access_token) })
  if (!challenge?.ok || typeof challenge.challenge !== 'string') return false
  const session = await current() // do not hand off a stale render's session
  if (!session || !sameLogin(first, session) || !allowed()) return false
  const { access_token, refresh_token, expires_at } = session
  const response = await extensionMessage(runtime, id, { type: 'session', challenge: challenge.challenge,
    session: { access_token, refresh_token, expires_at, user_id: session.user.id } })
  if (response?.ok !== true || !allowed()) return false
  return sameLogin(session, await current()) && allowed()
}
