import { beforeEach, expect, test, vi } from "vitest";

let saved: Record<string, any>;
let external: (message: any, sender: chrome.runtime.MessageSender, reply: (value: any) => void) => unknown;
let internal: typeof external;
const user = "00000000-0000-0000-0000-000000000001";
const old = { access_token: "old", refresh_token: "refresh", user_id: user, connection_id: "connection-a", expires_at: 1 };
const own = { id: "extension-id", url: "chrome-extension://extension-id/sidepanel.html" };
const trusted = { origin: "http://localhost:5173", url: "http://localhost:5173/app" };
const response = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status });

beforeEach(async () => {
  vi.resetModules();
  vi.stubEnv("VITE_WEB_URL", "http://localhost:5173");
  vi.stubEnv("VITE_SUPABASE_URL", "https://sb.test");
  vi.stubEnv("VITE_SUPABASE_ANON_KEY", "public-key");
  saved = { session: { ...old } };
  vi.stubGlobal("defineBackground", (fn: () => void) => fn());
  vi.stubGlobal("chrome", {
    action: { onClicked: { addListener: vi.fn() } },
    runtime: { id: own.id, onMessage: { addListener: (fn: typeof internal) => { internal = fn; } },
      onMessageExternal: { addListener: (fn: typeof external) => { external = fn; } },
      sendMessage: (msg: any) => new Promise((resolve) => internal(msg, own, resolve)) },
    storage: { local: {
      get: async (key: string) => ({ [key]: saved[key] }),
      set: async (values: unknown) => { Object.assign(saved, values); },
      remove: async (key: string) => { delete saved[key]; },
    } },
  });
  await import("../entrypoints/background");
});

const disconnect = () => new Promise((resolve) => external({ type: "disconnect", user_id: user }, trusted, resolve));
const fresh = () => ({ access_token: "fresh", refresh_token: "fresh-refresh", expires_at: Date.now() / 1000 + 3600, user: { id: user } });

test("a late refresh response cannot restore credentials after website logout", async () => {
  let finish!: (r: Response) => void;
  const fetcher = vi.fn(() => new Promise<Response>((resolve) => { finish = resolve; }));
  vi.stubGlobal("fetch", fetcher);
  const api = await import("../lib/api");
  const plan = api.getPlan();
  const rejected = expect(plan).rejects.toThrow("connection changed");
  await vi.waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1));
  await disconnect();
  finish(response(fresh()));
  await rejected;
  expect(saved.session).toBeUndefined();
  expect(fetcher).toHaveBeenCalledTimes(1);
});

test("concurrent requests refresh once and use the same fresh connection", async () => {
  let refreshes = 0;
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    if (url.includes("grant_type")) { refreshes++; return response(fresh()); }
    return response({ journeys: true, plan: "free" });
  }));
  const api = await import("../lib/api");
  await Promise.all([api.getPlan(), api.getRunPolicy()]);
  expect(refreshes).toBe(1);
  expect(saved.session.access_token).toBe("fresh");
  expect(saved.session.connection_id).toBe(old.connection_id);
  expect(saved.session).not.toHaveProperty("user");
});

test("a stale refresh rejection reuses another panel's fresh credentials on the same connection", async () => {
  let finish!: (r: Response) => void;
  const fetcher = vi.fn((url: string) => url.includes("grant_type")
    ? new Promise<Response>((resolve) => { finish = resolve; }) : Promise.resolve(response({ plan: "free" })));
  vi.stubGlobal("fetch", fetcher);
  const api = await import("../lib/api");
  const pending = api.getPlan();
  await vi.waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1));
  saved.session = { ...old, ...fresh() };
  finish(response({}, 400));
  await expect(pending).resolves.toEqual({ plan: "free" });
  expect(saved.session.access_token).toBe("fresh");
  expect(fetcher.mock.calls[1]?.[0]).toContain("/me/plan");
});

test("failed refresh disconnects only its own connection, temporary provider failures preserve it", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => response({}, 503)));
  const api = await import("../lib/api");
  await expect(api.getPlan()).rejects.toThrow("temporarily unavailable");
  expect(saved.session.access_token).toBe("old");
  vi.stubGlobal("fetch", vi.fn(async () => response({}, 400)));
  await expect(api.getPlan()).rejects.toThrow("Not signed in");
  expect(saved.session).toBeUndefined();
});

test("a late 401 for account A cannot remove newly connected account B", async () => {
  saved.session.expires_at = Date.now() / 1000 + 3600;
  let finish!: (r: Response) => void;
  const fetcher = vi.fn(() => new Promise<Response>((resolve) => { finish = resolve; }));
  vi.stubGlobal("fetch", fetcher);
  const api = await import("../lib/api");
  const plan = api.getPlan();
  const rejected = expect(plan).rejects.toThrow("connection changed");
  await vi.waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1));
  saved.session = { ...old, connection_id: "connection-b", user_id: "00000000-0000-0000-0000-000000000002" };
  finish(response({}, 401));
  await rejected;
  expect(saved.session.connection_id).toBe("connection-b");
});

test("lost request is not retried after disconnect", async () => {
  saved.session.expires_at = Date.now() / 1000 + 3600;
  vi.stubGlobal("fetch", vi.fn(async () => response({ journeys: true, idempotency: "v1" })));
  const api = await import("../lib/api");
  await api.getRunPolicy();
  const fetcher = vi.fn(async () => { await disconnect(); throw new TypeError("lost response"); });
  vi.stubGlobal("fetch", fetcher);
  await expect(api.stopRun("run-a")).rejects.toThrow("connection changed");
  expect(fetcher).toHaveBeenCalledTimes(1);
});

test("pinned screenshot upload and observation cannot use a replacement connection", async () => {
  saved.session = { ...old, connection_id: "connection-b", expires_at: Date.now() / 1000 + 3600 };
  const fetcher = vi.fn();
  vi.stubGlobal("fetch", fetcher);
  const api = await import("../lib/api");
  await expect(api.uploadEvidenceImage("run-a/step-01.jpg", "data:image/jpeg;base64,AA==", "connection-a")).rejects.toThrow("connection changed");
  await expect(api.observe("run-a", { url: "https://fixture.test", title: "", text: "", elements: [], errors: [] }, undefined, "action-a", undefined, "connection-a")).rejects.toThrow("connection changed");
  expect(fetcher).not.toHaveBeenCalled();
});
