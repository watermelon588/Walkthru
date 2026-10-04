import { beforeEach, expect, test, vi } from "vitest";
import { runTest, type Progress } from "../entrypoints/sidepanel/run";

vi.mock("../lib/evidence", () => ({ shouldCaptureEvidence: () => false, captureStepEvidence: vi.fn(), evidenceFailureMessage: String }));

const site = "https://fixture.test";
const actionId = "00000000-0000-0000-0000-000000000005";
const revision = "00000000-0000-4000-8000-000000000006";
const action = { observation_revision: revision, action: "click", target_id: 1, thought: "Read the guide", confusion: 0, url: site };
const running = { run_id: "00000000000000000000000000000001", status: "running", action, action_id: actionId };
const observation = { revision, url: site, title: "Guide", text: "Guide", errors: [], elements: [{ id: 1, tag: "a", text: "Guide" }] };
let actions: number;
let snapshots: number;

beforeEach(() => {
  actions = 0;
  snapshots = 0;
  vi.stubGlobal("chrome", {
    permissions: { contains: vi.fn().mockResolvedValue(true) },
    scripting: { executeScript: vi.fn().mockResolvedValue([]) },
    storage: { local: { get: vi.fn().mockResolvedValue({ session: { access_token: "fake", expires_at: Date.now() / 1000 + 3600 } }) } },
    tabs: {
      query: vi.fn().mockResolvedValue([{ id: 1, url: site }]),
      get: vi.fn().mockResolvedValue({ id: 1, url: site, status: "complete" }),
      sendMessage: vi.fn().mockImplementation(async (_tab, message) => {
        if (message.type === "ping") return { ok: true };
        if (message.type === "snapshot") { snapshots++; return observation; }
        if (message.type === "act") { actions++; return {}; }
        return {};
      }),
    },
  });
});

test("a missing content receiver is injected and acknowledged before reading the page", async () => {
  const original = vi.mocked(chrome.tabs.sendMessage).getMockImplementation()!;
  let injected = false;
  vi.mocked(chrome.scripting.executeScript).mockImplementation(async () => { injected = true; return []; });
  vi.mocked(chrome.tabs.sendMessage).mockImplementation(async (...args: any[]) => {
    if (!injected) throw new Error("Could not establish connection. Receiving end does not exist.");
    return Reflect.apply(original, chrome.tabs, args);
  });
  vi.stubGlobal("fetch", vi.fn(async (url: string) => url.endsWith("/policy") ? response({ journeys: true }) : response({ ...running, status: "done", steps: [] })));
  const progress: Progress[] = [];
  await runTest(options(), (p) => progress.push(p));
  expect(progress.at(-1)?.status).toBe("done");
  expect(chrome.scripting.executeScript).toHaveBeenCalledOnce();
  expect(snapshots).toBe(1);
});

test("a receiver that stays unavailable stops before creating a run with useful recovery guidance", async () => {
  vi.mocked(chrome.tabs.sendMessage).mockRejectedValue(new Error("Could not establish connection. Receiving end does not exist."));
  const fetcher = vi.fn(async () => response({ journeys: true }));
  vi.stubGlobal("fetch", fetcher);
  const progress: Progress[] = [];
  await runTest(options(), (p) => progress.push(p));
  expect(progress.at(-1)).toMatchObject({ phase: "error", code: "browser_connection" });
  expect(progress.at(-1)?.message).toContain("Reload the website tab");
  expect(fetcher).toHaveBeenCalledOnce(); // policy only, no saved run or consumed run quota
  expect(actions).toBe(0);
});

test("losing the receiver after a click is dispatched never automatically repeats that click", async () => {
  const original = vi.mocked(chrome.tabs.sendMessage).getMockImplementation()!;
  vi.mocked(chrome.tabs.sendMessage).mockImplementation(async (...args: any[]) => {
    if (args[1].type === "act") { actions++; throw new Error("Could not establish connection. Receiving end does not exist."); }
    return Reflect.apply(original, chrome.tabs, args);
  });
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    if (url.endsWith("/policy")) return response({ journeys: true });
    if (url.endsWith("/stop")) return response({ ...running, status: "stopped", steps: [action] });
    return response(running);
  }));
  await runTest(options(), () => {});
  expect(actions).toBe(1);
});

const response = (body: unknown) => new Response(JSON.stringify(body));
const options = () => ({ site, goal: "read the guide", persona: "first_timer", logged_in: false, max_steps: 5, signal: new AbortController().signal });

test("a lost observation response retries HTTP without clicking or capturing the page again", async () => {
  const observed: RequestInit[] = [];
  vi.stubGlobal("fetch", vi.fn().mockImplementation(async (url: string, init: RequestInit) => {
    if (url.endsWith("/policy")) return response({ journeys: true, idempotency: "v1" });
    if (url.endsWith("/runs")) return response(running);
    if (url.endsWith("/observe")) {
      observed.push(init);
      if (observed.length === 1) throw new TypeError("server response lost after advancing");
      return response({ ...running, status: "done", steps: [action] });
    }
    throw new Error("Unexpected endpoint");
  }));
  const progress: Progress[] = [];
  await runTest(options(), (value) => progress.push(value));
  expect(progress.at(-1)?.status).toBe("done");
  expect(actions).toBe(1);
  expect(snapshots).toBe(2);
  expect(observed).toHaveLength(2);
  expect(observed[0]!.body).toBe(observed[1]!.body);
  expect((observed[0]!.headers as Record<string, string>)["Idempotency-Key"]).toBe((observed[1]!.headers as Record<string, string>)["Idempotency-Key"]);
  expect(JSON.parse(observed[0]!.body as string).action_id).toBe(actionId);
});

test("an accidentally replayed action is stopped before another browser click", async () => {
  let stopped = 0;
  vi.stubGlobal("fetch", vi.fn().mockImplementation(async (url: string) => {
    if (url.endsWith("/policy")) return response({ journeys: true, idempotency: "v1" });
    if (url.endsWith("/runs") || url.endsWith("/observe")) return response(running);
    if (url.endsWith("/stop")) { stopped++; return response({ ...running, status: "stopped", steps: [action] }); }
    throw new Error("Unexpected endpoint");
  }));
  await runTest(options(), () => {});
  expect(actions).toBe(1);
  expect(stopped).toBe(1);
});

test("account change while a start reply arrives prevents any browser click or wrong-account stop", async () => {
  const fetcher = vi.fn(async (url: string) => {
    if (url.endsWith("/policy")) return response({ journeys: true, idempotency: "v1" });
    if (url.endsWith("/runs")) {
      vi.mocked(chrome.storage.local.get).mockReturnValue(Promise.resolve({ session: { access_token: "account-b", refresh_token: "b" } }) as never);
      return response(running);
    }
    throw new Error("Must not mutate the old run with the new account");
  });
  vi.stubGlobal("fetch", fetcher);
  const progress: Progress[] = [];
  await runTest(options(), (p) => progress.push(p));
  expect(actions).toBe(0);
  expect(fetcher).toHaveBeenCalledTimes(2);
  expect(progress.at(-1)?.phase).toBe("error");
  expect(progress.at(-1)?.message).toContain("connection changed");
});

test("disconnect during the final content-script ping prevents the next click", async () => {
  const original = vi.mocked(chrome.tabs.sendMessage).getMockImplementation()!;
  vi.mocked(chrome.tabs.sendMessage).mockImplementation(async (...args: any[]) => {
    if (args[1].type === "ping" && snapshots === 1) {
      vi.mocked(chrome.storage.local.get).mockReturnValue(Promise.resolve({}) as never);
    }
    return Reflect.apply(original, chrome.tabs, args);
  });
  vi.stubGlobal("fetch", vi.fn(async (url: string) => url.endsWith("/policy") ? response({ journeys: true }) : response(running)));
  await runTest(options(), () => {});
  expect(actions).toBe(0);
});

test("a page that never answers ends the step instead of hanging the run", async () => {
  vi.useFakeTimers();
  const { withTimeout, PageTimeoutError } = await import("../entrypoints/sidepanel/run");
  const hung = withTimeout(new Promise(() => {}), 30_000, "The page stopped responding");
  const check = expect(hung).rejects.toBeInstanceOf(PageTimeoutError);
  await vi.advanceTimersByTimeAsync(30_000);
  await check;
  vi.useRealTimers();
});

test.each(['scroll', 'back'] as const)('the run loop accepts %s with a captured revision and no target revision echo', async (kind) => {
  const step = { ...action, action: kind, target_id: null, observation_revision: null };
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    if (url.endsWith('/policy')) return response({ journeys: true });
    if (url.endsWith('/observe')) return response({ ...running, status: 'done', steps: [step] });
    return response({ ...running, action: step });
  }));
  const progress: Progress[] = [];
  await runTest(options(), p => progress.push(p));
  expect(progress.at(-1)?.status).toBe('done');
  expect(actions).toBe(1);
  expect(snapshots).toBe(2);
});

test.each(['old page', 'old API', 'wrong revision'])('mixed versions (%s) stop before any browser action or dry run', async (version) => {
  if (version === 'old page') {
    const original = vi.mocked(chrome.tabs.sendMessage).getMockImplementation()!;
    vi.mocked(chrome.tabs.sendMessage).mockImplementation(async (...args: any[]) => args[1].type === 'snapshot' ? { ...observation, revision: undefined } : Reflect.apply(original, chrome.tabs, args));
  }
  const step = { ...action, observation_revision: version === 'old API' ? undefined : version === 'wrong revision' ? 'different' : revision };
  const stops: string[] = [];
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    if (url.endsWith('/policy')) return response({ journeys: true });
    if (url.endsWith('/stop')) { stops.push(String(init?.body)); return response({ ...running, status: 'stopped', steps: [] }); }
    return response({ ...running, verified: true, action: step });
  }));
  const progress: Progress[] = [];
  await runTest(options(), p => progress.push(p));
  expect(actions).toBe(0);
  expect(stops).toHaveLength(1);
  expect(stops[0]).toContain('stale target:');
  expect(progress.at(-1)).toMatchObject({ phase: 'finished', status: 'stopped', code: 'browser_version' });
  expect(progress.at(-1)?.message).toContain('reload the website tab');
});

test.each(['wait', 'scroll'] as const)('new %s directives refuse an R-S2 receiver before dispatch', async kind => {
  const step = { ...action, action: kind, target_id: null, scroll_container_id: kind === 'scroll' ? 1 : undefined };
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    if (url.endsWith('/policy')) return response({ journeys: true });
    if (url.endsWith('/stop')) return response({ ...running, status: 'stopped', steps: [] });
    return response({ ...running, action: step });
  }));
  const progress: Progress[] = [];
  await runTest(options(), p => progress.push(p));
  expect(actions).toBe(0);
  expect(progress.at(-1)?.code).toBe('browser_version');
});

test('wait outcome reaches the next observation once with operation identity and bounded deadline', async () => {
  const step = { ...action, action: 'wait', target_id: null, wait_condition: 'text_changed', wait_timeout_ms: 1000 };
  const outcome = { action: 'wait', status: 'changed', elapsed_ms: 200 };
  const original = vi.mocked(chrome.tabs.sendMessage).getMockImplementation()!;
  vi.mocked(chrome.tabs.sendMessage).mockImplementation(async (...args: any[]) => {
    if (args[1].type === 'snapshot') { snapshots++; return { ...observation, navigation_version: 3 }; }
    if (args[1].type === 'act') {
      actions++;
      expect(args[1].operation_id).toMatch(/^[0-9a-f-]{36}$/);
      expect(args[1].opts.deadline_ms).toBeGreaterThan(Date.now());
      return { ok: true, executor_result: outcome };
    }
    return Reflect.apply(original, chrome.tabs, args);
  });
  let observed: any;
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    if (url.endsWith('/policy')) return response({ journeys: true });
    if (url.endsWith('/observe')) { observed = JSON.parse(String(init?.body)); return response({ ...running, status: 'done', steps: [step] }); }
    return response({ ...running, action: step });
  }));
  await runTest(options(), () => {});
  expect(actions).toBe(1);
  expect(observed.observation.executor_result).toEqual(outcome);
});

test('expired run budget after browser observation stops before another API decision', async () => {
  const step = { ...action, action: 'wait', target_id: null };
  let now = 1_000_000;
  vi.spyOn(Date, 'now').mockImplementation(() => now);
  const original = vi.mocked(chrome.tabs.sendMessage).getMockImplementation()!;
  vi.mocked(chrome.tabs.sendMessage).mockImplementation(async (...args: any[]) => {
    if (args[1].type === 'snapshot') {
      snapshots++;
      if (snapshots > 1) now += 240_001;
      return { ...observation, navigation_version: 3 };
    }
    if (args[1].type === 'act') { actions++; return { ok: true, executor_result: { action: 'wait', status: 'timeout' } }; }
    return Reflect.apply(original, chrome.tabs, args);
  });
  const endpoints: string[] = [];
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    endpoints.push(url);
    if (url.endsWith('/policy')) return response({ journeys: true });
    if (url.endsWith('/stop')) return response({ ...running, status: 'stopped', steps: [step] });
    return response({ ...running, action: step });
  }));
  try { await runTest(options(), () => {}); }
  finally { vi.restoreAllMocks(); }
  expect(actions).toBe(1);
  expect(endpoints.some(url => url.endsWith('/observe'))).toBe(false);
  expect(endpoints.some(url => url.endsWith('/stop'))).toBe(true);
});

test('owner Stop cancels the matching pending wait without a second action or observation', async () => {
  const step = { ...action, action: 'wait', target_id: null };
  const owner = new AbortController();
  const original = vi.mocked(chrome.tabs.sendMessage).getMockImplementation()!;
  let operationId: string | undefined;
  let complete: ((value: unknown) => void) | undefined;
  let cancelled: string | undefined;
  vi.mocked(chrome.tabs.sendMessage).mockImplementation(async (...args: any[]) => {
    if (args[1].type === 'snapshot') { snapshots++; return { ...observation, navigation_version: 3 }; }
    if (args[1].type === 'act') {
      actions++; operationId = args[1].operation_id;
      return new Promise<unknown>(resolve => { complete = resolve; setTimeout(() => owner.abort(), 10); });
    }
    if (args[1].type === 'act_cancel') { cancelled = args[1].operation_id; complete!({ ok: false, executor_result: { action: 'wait', status: 'aborted' } }); return { ok: true }; }
    return Reflect.apply(original, chrome.tabs, args);
  });
  const endpoints: string[] = [];
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    endpoints.push(url);
    if (url.endsWith('/policy')) return response({ journeys: true });
    if (url.endsWith('/stop')) return response({ ...running, status: 'stopped', steps: [step] });
    return response({ ...running, action: step });
  }));
  await runTest({ ...options(), signal: owner.signal }, () => {});
  expect(cancelled).toBe(operationId);
  expect(actions).toBe(1);
  expect(snapshots).toBe(1);
  expect(endpoints.some(url => url.endsWith('/observe'))).toBe(false);
});
