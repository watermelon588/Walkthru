import { beforeEach, expect, test, vi } from "vitest";
import { getQuote } from "../lib/api";
import { runTest } from "../entrypoints/sidepanel/run";

// R-S10: the side panel asks for the run's quote and sends the accepted token with the run.
vi.mock("../lib/evidence", () => ({ shouldCaptureEvidence: () => false, captureStepEvidence: vi.fn(), evidenceFailureMessage: String }));

const site = "https://fixture.test";
const observation = { revision: "00000000-0000-4000-8000-000000000006", url: site, title: "Guide", text: "Guide", errors: [], elements: [] };
const response = (body: unknown) => new Response(JSON.stringify(body));
let posts: { url: string; body: any }[];

beforeEach(() => {
  posts = [];
  vi.stubGlobal("chrome", {
    permissions: { contains: vi.fn().mockResolvedValue(true) },
    scripting: { executeScript: vi.fn().mockResolvedValue([]) },
    storage: { local: { get: vi.fn().mockResolvedValue({ session: { access_token: "fake", expires_at: Date.now() / 1000 + 3600 } }) } },
    tabs: {
      query: vi.fn().mockResolvedValue([{ id: 1, url: site }]),
      get: vi.fn().mockResolvedValue({ id: 1, url: site, status: "complete" }),
      sendMessage: vi.fn().mockImplementation(async (_tab, message) => (message.type === "ping" ? { ok: true } : message.type === "snapshot" ? observation : {})),
    },
  });
  vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
    if (init?.body) posts.push({ url, body: JSON.parse(String(init.body)) });
    if (url.endsWith("/policy")) return response({ journeys: true });
    if (url.endsWith("/runs/quote")) return response({ token: "signed-quote", summary: "terms", rules: [], terms: { exp: Date.now() / 1000 + 600 } });
    return response({ run_id: "00000000000000000000000000000001", status: "done", steps: [] });
  }));
});

test("the quote is requested for exactly the run's scope", async () => {
  const quote = await getQuote({ site, personas: ["first_timer", "buyer"], logged_in: false, max_steps: 12, assertion: false });
  expect(quote.token).toBe("signed-quote");
  expect(posts[0]?.url.endsWith("/runs/quote")).toBe(true);
  expect(posts[0]?.body).toEqual({ site, personas: ["first_timer", "buyer"], logged_in: false, max_steps: 12, assertion: false });
});

test("starting a run sends the accepted quote token", async () => {
  await runTest({ site, goal: "read the guide", persona: "first_timer", logged_in: false, max_steps: 5, signal: new AbortController().signal, quote: "signed-quote" }, () => {});
  const start = posts.find((p) => p.url.endsWith("/runs"));
  expect(start?.body.quote).toBe("signed-quote");
});

test("a run without a quote sends none, for older servers", async () => {
  await runTest({ site, goal: "read the guide", persona: "first_timer", logged_in: false, max_steps: 5, signal: new AbortController().signal }, () => {});
  expect(posts.find((p) => p.url.endsWith("/runs"))?.body).not.toHaveProperty("quote");
});
