import { authSessionId, connectSession, extensionMessage, type ExtensionRuntime, type HandoffSession } from './sessionHandoff'
import { supabase } from './supabase'

const extensionId = import.meta.env.VITE_EXTENSION_ID as string | undefined
const runtime = () => (window as unknown as { chrome?: { runtime?: ExtensionRuntime } }).chrome?.runtime
let generation = 0
let signingOut = false
export function signingOutExtension(active: boolean) {
  signingOut = active
  generation++
}

export async function connectExtension(): Promise<boolean> {
  const attempt = generation
  return connectSession(runtime(), extensionId, async () => (await supabase?.auth.getSession())?.data.session ?? null,
    () => !signingOut && generation === attempt)
}

export async function disconnectExtension(session: HandoffSession): Promise<boolean> {
  generation++
  const response = await extensionMessage(runtime(), extensionId, { type: 'disconnect', user_id: session.user.id, session_id: authSessionId(session.access_token) })
  return response?.ok === true
}
