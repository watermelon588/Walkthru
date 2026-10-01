import { openSidePanelForTab } from "../lib/side-panel";
import { authSessionId, connectionId, getSession, type Session } from "../lib/session";

const token = (value: unknown, max: number): value is string =>
  typeof value === "string" && value.length > 0 && value.length <= max && !/\s/.test(value);
const uuid = (value: unknown): value is string => typeof value === "string" && /^[a-f0-9]{8}(-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i.test(value);
type Intent = { challenge: string; user_id: string; session_id?: string; expires_at: number };
async function intent(): Promise<Intent | null> {
  const { connect_intent } = await chrome.storage.local.get("connect_intent");
  if (!connect_intent || typeof connect_intent !== "object") return null;
  const value = connect_intent as Intent;
  return uuid(value.challenge) && uuid(value.user_id) && Number.isFinite(value.expires_at)
    && (value.session_id === undefined || uuid(value.session_id)) ? value : null;
}

function credentials(session: unknown): Session | null {
  if (!session || typeof session !== "object" || Array.isArray(session)) return null;
  const s = session as Session;
  if (!token(s.access_token, 16384) || !token(s.refresh_token, 4096)
    || (s.user_id !== undefined && !uuid(s.user_id))
    || (s.expires_at !== undefined && (typeof s.expires_at !== "number" || !Number.isFinite(s.expires_at) || s.expires_at <= 0))) return null;
  return { access_token: s.access_token, refresh_token: s.refresh_token,
    ...(s.user_id === undefined ? {} : { user_id: s.user_id }),
    ...(s.expires_at === undefined ? {} : { expires_at: s.expires_at }) };
}

export default defineBackground(() => {
  // Serialize external handoff/disconnect and internal refresh/401 writes. A late response cannot restore credentials.
  let queue = Promise.resolve();
  const change = (work: () => Promise<unknown>, reply: (value: unknown) => void) => {
    queue = queue.then(work).then(reply, () => reply({ ok: false }));
    return true;
  };
  chrome.runtime.onMessage.addListener((msg, sender, reply) => {
    try {
      const url = new URL(sender.url ?? "");
      if (sender.id !== chrome.runtime.id || sender.tab || url.protocol !== "chrome-extension:" || url.host !== chrome.runtime.id) return;
    } catch { return; }
    if (msg?.type !== "update_session" || !token(msg.expected, 16384) || !token(msg.access_token, 16384)) return;
    const fresh = msg.session === undefined ? null : credentials(msg.session);
    if (msg.session !== undefined && !fresh) { reply({ ok: false }); return; }
    return change(async () => {
      const previous = await getSession();
      if (!previous || connectionId(previous) !== msg.expected || previous.access_token !== msg.access_token) return { ok: false };
      if (fresh && previous.auth_session_id && authSessionId(fresh.access_token) !== previous.auth_session_id) return { ok: false };
      if (fresh) await chrome.storage.local.set({ session: { ...fresh, user_id: previous.user_id,
        connection_id: connectionId(previous), auth_session_id: previous.auth_session_id } });
      else await chrome.storage.local.remove("session");
      return { ok: true };
    }, reply);
  });
  // Opening explicitly inside action.onClicked grants activeTab to this tab. Chrome's
  // openPanelOnActionClick shortcut opens the panel but does not reliably grant activeTab,
  // which makes tabs.captureVisibleTab fail even though the user invoked the extension.
  chrome.action.onClicked.addListener((tab) => {
    void openSidePanelForTab(tab).catch((error) => console.error("Could not open Walkthru", error));
  });

  // The dashboard (externally_connectable origins only) hands us the signed-in session.
  chrome.runtime.onMessageExternal.addListener((msg, sender, reply) => {
    try {
      const webOrigin = new URL(import.meta.env.VITE_WEB_URL ?? "http://localhost:5173").origin;
      if (sender.id || sender.origin !== webOrigin || !sender.url || new URL(sender.url).origin !== webOrigin) {
        reply({ ok: false });
        return;
      }
    } catch {
      reply({ ok: false });
      return;
    }
    if (msg?.type === "begin_connect" && uuid(msg.user_id) && (msg.session_id === undefined || uuid(msg.session_id))) {
      return change(async () => {
        const challenge = crypto.randomUUID();
        await chrome.storage.local.set({ connect_intent: { challenge, user_id: msg.user_id, session_id: msg.session_id, expires_at: Date.now() + 30_000 } });
        return { ok: true, challenge };
      }, reply);
    }
    if (msg?.type === "disconnect" && uuid(msg.user_id) && (msg.session_id === undefined || uuid(msg.session_id))) {
      return change(async () => {
        const connect_intent = await intent();
        if (connect_intent && connect_intent.user_id === msg.user_id && connect_intent.session_id === msg.session_id) await chrome.storage.local.remove("connect_intent");
        const previous = await getSession();
        if (previous && (!previous.user_id || (previous.user_id === msg.user_id
          && (!previous.auth_session_id || previous.auth_session_id === msg.session_id)))) {
          await chrome.storage.local.remove("session");
        }
        return { ok: true };
      }, reply);
    }
    const session = credentials(msg?.session);
    if (msg?.type !== "session" || !session || !uuid(session.user_id) || !uuid(msg.challenge)) { reply({ ok: false }); return; }
    return change(async () => {
      const connect_intent = await intent();
      if (!connect_intent || connect_intent.challenge !== msg.challenge || connect_intent.user_id !== session.user_id
        || connect_intent.session_id !== authSessionId(session.access_token)
        || connect_intent.expires_at <= Date.now()) return { ok: false };
      await chrome.storage.local.remove("connect_intent");
      await chrome.storage.local.set({ session: { ...session, connection_id: crypto.randomUUID(), auth_session_id: authSessionId(session.access_token) } });
      return { ok: true };
    }, reply);
  });
});
