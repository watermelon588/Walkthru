import { beforeEach, expect, test, vi } from "vitest";

type Reply = (value: { ok: boolean; challenge?: string }) => void;
let receive: (message: unknown, sender: chrome.runtime.MessageSender, reply: Reply) => boolean | undefined;
let internal: typeof receive;
let store: ReturnType<typeof vi.fn>;
let saved: Record<string, any>;
const user = "00000000-0000-0000-0000-000000000001";
const other = "00000000-0000-0000-0000-000000000002";
const own = { id: "extension-id", url: "chrome-extension://extension-id/sidepanel.html" };
const trusted = { origin: "http://localhost:5173", url: "http://localhost:5173/app" };
const session = { access_token: "access", refresh_token: "refresh", expires_at: 2_000_000_000, user_id: user };

async function external(message: unknown) {
  const reply = vi.fn();
  receive(message, trusted, reply);
  await vi.waitFor(() => expect(reply).toHaveBeenCalled());
  return reply.mock.calls[0]![0];
}
async function connect(s = session, session_id?: string) {
  const { challenge } = await external({ type: "begin_connect", user_id: s.user_id, session_id });
  return external({ type: "session", session: s, challenge });
}
async function update(message: unknown, sender = own) {
  const reply = vi.fn();
  internal(message, sender, reply);
  await vi.waitFor(() => expect(reply).toHaveBeenCalled());
  return reply.mock.calls[0]![0];
}

beforeEach(async () => {
  vi.resetModules();
  vi.stubEnv("VITE_WEB_URL", "http://localhost:5173");
  saved = {};
  store = vi.fn().mockImplementation(async (values) => { Object.assign(saved, values); });
  vi.stubGlobal("defineBackground", (setup: () => void) => setup());
  vi.stubGlobal("chrome", {
    action: { onClicked: { addListener: vi.fn() } },
    runtime: { id: "extension-id", onMessageExternal: { addListener: (listener: typeof receive) => { receive = listener; } },
      onMessage: { addListener: (listener: typeof internal) => { internal = listener; } } },
    storage: { local: { set: store, get: vi.fn().mockImplementation(async (key) => ({ [key]: saved[key] })),
      remove: vi.fn().mockImplementation(async (key) => { delete saved[key]; }) } },
  });
  await import("../entrypoints/background");
});

test.each([
  {}, { origin: "null" },
  { origin: "http://localhost:5173.evil.test", url: "http://localhost:5173.evil.test/app" },
  { origin: "http://localhost:5174", url: "http://localhost:5174/app" },
  { ...trusted, url: "https://evil.test" },
  { ...trusted, id: "another-extension" },
])("rejects untrusted or ambiguous senders: %j", (sender) => {
  const reply = vi.fn();
  receive({ type: "session", session }, sender, reply);
  expect(store).not.toHaveBeenCalled();
  expect(reply).toHaveBeenCalledWith({ ok: false });
});

test.each([
  null, {}, { type: "other", session },
  { type: "session", session: { ...session, access_token: 12 } },
  { type: "session", session: { ...session, refresh_token: " " } },
  { type: "session", session: { ...session, access_token: "x".repeat(16385) } },
  { type: "session", session: { ...session, expires_at: "tomorrow" } },
  { type: "session", session: { ...session, expires_at: Infinity } },
])("rejects malformed session message %#", (message) => {
  const reply = vi.fn();
  receive(message, trusted, reply);
  expect(store).not.toHaveBeenCalled();
  expect(reply).toHaveBeenCalledWith({ ok: false });
});

test("stores only session credentials from the configured dashboard", async () => {
  expect(await connect({ ...session, user: { email: "private@example.test" } } as typeof session)).toEqual({ ok: true });
  expect(saved.session).toMatchObject(session);
  expect(saved.session.connection_id).toMatch(/^[a-f0-9-]{36}$/);
  expect(saved.session).not.toHaveProperty("user");
});

test("reports storage failure without acknowledging a successful connection", async () => {
  const { challenge } = await external({ type: "begin_connect", user_id: user });
  store.mockRejectedValue(new Error("storage unavailable"));
  expect(await external({ type: "session", session, challenge })).toEqual({ ok: false });
});

test("logout removes the matching connection and invalidates its pending handoff", async () => {
  await connect();
  const { challenge } = await external({ type: "begin_connect", user_id: user });
  expect(await external({ type: "disconnect", user_id: user })).toEqual({ ok: true });
  expect(saved.session).toBeUndefined();
  expect(await external({ type: "session", session, challenge })).toEqual({ ok: false });
});

test("old account logout cannot cancel a different account connection or handoff", async () => {
  await connect({ ...session, user_id: other });
  const { challenge } = await external({ type: "begin_connect", user_id: other });
  await external({ type: "disconnect", user_id: user });
  expect(saved.session.user_id).toBe(other);
  expect(await external({ type: "session", session: { ...session, user_id: other }, challenge })).toEqual({ ok: true });
});

test("late refresh and 401 cannot resurrect logout or clear a replacement account", async () => {
  await connect();
  const old = saved.session;
  await external({ type: "disconnect", user_id: user });
  expect(await update({ type: "update_session", expected: old.connection_id, access_token: old.access_token, session })).toEqual({ ok: false });
  expect(saved.session).toBeUndefined();
  await connect({ ...session, user_id: other });
  expect(await update({ type: "update_session", expected: old.connection_id, access_token: old.access_token })).toEqual({ ok: false });
  expect(saved.session.user_id).toBe(other);
});

test("refresh preserves the connection and stores only credentials", async () => {
  await connect();
  const old = saved.session;
  expect(await update({ type: "update_session", expected: old.connection_id, access_token: old.access_token,
    session: { ...session, access_token: "fresh", user: { email: "private" } } })).toEqual({ ok: true });
  expect(saved.session.connection_id).toBe(old.connection_id);
  expect(saved.session.access_token).toBe("fresh");
  expect(saved.session).not.toHaveProperty("user");
});

test.each([{ ...own, tab: { id: 1 } }, { id: "other", url: own.url }, { ...own, url: trusted.url }])(
  "content scripts and other senders cannot mutate stored credentials: %j", (sender) => {
    const reply = vi.fn();
    internal({ type: "update_session", expected: "x", access_token: "x" }, sender as chrome.runtime.MessageSender, reply);
    expect(reply).not.toHaveBeenCalled();
    expect(store).not.toHaveBeenCalled();
  });

test("expired and consumed handoff challenges cannot be used", async () => {
  const { challenge } = await external({ type: "begin_connect", user_id: user });
  saved.connect_intent.expires_at = Date.now() - 1;
  expect(await external({ type: "session", session, challenge })).toEqual({ ok: false });
  const next = await external({ type: "begin_connect", user_id: user });
  expect(await external({ type: "session", session, challenge: next.challenge })).toEqual({ ok: true });
  expect(await external({ type: "session", session, challenge: next.challenge })).toEqual({ ok: false });
});

test("a delayed logout of an earlier login cannot disconnect the same user's new login", async () => {
  const old = "00000000-0000-0000-0000-000000000010", fresh = "00000000-0000-0000-0000-000000000011";
  const jwt = (id: string) => `header.${btoa(JSON.stringify({ session_id: id }))}.signature`;
  await connect({ ...session, access_token: jwt(fresh) }, fresh);
  const { challenge } = await external({ type: "begin_connect", user_id: user, session_id: fresh });
  await external({ type: "disconnect", user_id: user, session_id: old });
  expect(saved.session.auth_session_id).toBe(fresh);
  expect(await external({ type: "session", session: { ...session, access_token: jwt(fresh) }, challenge })).toEqual({ ok: true });
});

test("logout drops legacy credentials whose identity cannot be established", async () => {
  saved.session = { access_token: "old-refreshed", refresh_token: "different" };
  await external({ type: "disconnect", user_id: user });
  expect(saved.session).toBeUndefined();
});
