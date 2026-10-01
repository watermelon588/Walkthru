/** Credentials live in extension storage; only the background worker may change them. */
export type Session = { access_token: string; refresh_token: string; expires_at?: number; user_id?: string; connection_id?: string; auth_session_id?: string };
export const SESSION_CHANGED = "Your extension connection changed. Reconnect to start a new test. End any unfinished run from its original account's dashboard.";

export async function getSession(): Promise<Session | null> {
  const { session } = await chrome.storage.local.get("session");
  return (session as Session | undefined) ?? null;
}

export function connectionId(session: Session | null): string | undefined {
  return session?.connection_id ?? session?.access_token; // legacy sessions are fenced too
}

export function authSessionId(token: string): string | undefined {
  try {
    const payload = token.split(".")[1]!;
    const id: unknown = JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/"))).session_id;
    return typeof id === "string" && /^[a-f0-9]{8}(-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i.test(id) ? id : undefined;
  } catch { return undefined; }
}

export async function assertConnection(expected: string): Promise<Session> {
  const session = await getSession();
  if (!session || connectionId(session) !== expected) throw new Error(SESSION_CHANGED);
  return session;
}

export async function updateSession(previous: Session, fresh?: Session): Promise<void> {
  let timeout: ReturnType<typeof setTimeout> | undefined;
  const result = await Promise.race([
    chrome.runtime.sendMessage({ type: "update_session", expected: connectionId(previous),
      access_token: previous.access_token, ...(fresh ? { session: fresh } : {}) }),
    new Promise<never>((_resolve, reject) => { timeout = setTimeout(() => reject(new Error("Could not confirm the extension connection. Reconnect and try again.")), 3000); }),
  ]).finally(() => clearTimeout(timeout));
  if (!result?.ok) throw new Error(SESSION_CHANGED);
}
