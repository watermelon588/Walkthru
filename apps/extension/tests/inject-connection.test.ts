import { afterEach, beforeEach, expect, test, vi } from "vitest";

vi.mock("../lib/snapshot", () => ({ settle: vi.fn(), snapshot: () => ({ url: "https://yap-chat-five.vercel.app/", text: "Yap Chat", elements: [], errors: [] }) }));
vi.mock("../lib/diagnostics", () => ({ observeWebVitals: () => () => ({}), collectBrowserDiagnostics: vi.fn().mockResolvedValue({}) }));
vi.mock("gsap", () => ({ default: { matchMedia: () => ({ add: vi.fn() }), set: vi.fn(), to: vi.fn() } }));

type Listener = Parameters<typeof chrome.runtime.onMessage.addListener>[0];
let listeners: Set<Listener>;
let main: () => void;

beforeEach(async () => {
  vi.resetModules();
  document.body.innerHTML = "";
  delete window.__walkthru;
  listeners = new Set();
  vi.stubGlobal("defineUnlistedScript", (setup: () => void) => ({ main: setup }));
  vi.stubGlobal("chrome", { runtime: { onMessage: {
    addListener: (listener: Listener) => listeners.add(listener),
    hasListener: (listener: Listener) => listeners.has(listener),
  } } });
  main = (await import("../entrypoints/inject")).default.main!;
});

afterEach(() => { delete window.__walkthru; });

async function message(value: unknown) {
  const reply = vi.fn();
  for (const listener of listeners) listener(value, {}, reply);
  await vi.waitFor(() => expect(reply).toHaveBeenCalled());
  return reply;
}

test("a legacy injection flag without a receiver cannot prevent reconnection", async () => {
  window.__walkthru = true;
  document.body.innerHTML = '<walkthru-agent role="status"></walkthru-agent>';
  main();
  expect((await message({ type: "ping" })).mock.calls[0]![0]).toEqual({ ok: true });
  expect((await message({ type: "snapshot" })).mock.calls[0]![0].text).toBe("Yap Chat");
  expect(document.querySelectorAll("walkthru-agent")).toHaveLength(1);
});

test("reinjecting a live receiver does not duplicate listeners or the overlay", async () => {
  main();
  await message({ type: "snapshot" });
  main();
  expect(listeners.size).toBe(1);
  expect(document.querySelectorAll("walkthru-agent")).toHaveLength(1);
});

test("an invalidated extension receiver is replaced on the same document", async () => {
  main();
  await message({ type: "snapshot" });
  listeners.clear(); // Chrome drops the receiver when the unpacked extension reloads.
  main();
  expect(listeners.size).toBe(1);
  expect((await message({ type: "snapshot" })).mock.calls[0]![0].text).toBe("Yap Chat");
  expect(document.querySelectorAll("walkthru-agent")).toHaveLength(1);
});
