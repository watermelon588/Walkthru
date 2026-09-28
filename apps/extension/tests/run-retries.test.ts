import { beforeEach, expect, test, vi } from "vitest";
import { runTest, type Progress } from "../entrypoints/sidepanel/run";

vi.mock("../lib/evidence", () => ({ shouldCaptureEvidence: () => false, captureStepEvidence: vi.fn(), evidenceFailureMessage: String }));

const site = "https://fixture.test";
const actionId = "00000000-0000-0000-0000-000000000005";
const action = { action: "click", target_id: 1, thought: "Read the guide", confusion: 0, url: site };
const running = { run_id: "00000000000000000000000000000001", status: "running", action, action_id: actionId };
const observation = { url: site, title: "Guide", text: "Guide", errors: [], elements: [{ id: 1, tag: "a", text: "Guide" }] };
let actions: number;
let snapshots: number;

beforeEach(() => {
  actions = 0;
  snapshots = 0;
  vi.stubGlobal("chrome", {
    permissions: { contains: vi.fn().mockResolvedValue(true) },
    storage: { local: { get: vi.fn().mockResolvedValue({ session: { access_token: "fake", expires_at: Date.now() / 1000 + 3600 } }) } },
    tabs: {
      query: vi.fn().mockResolvedValue([{ id: 1, url: site }]),
      get: vi.fn().mockResolvedValue({ id: 1, url: site, status: "complete" }),
      sendMessage: vi.fn().mockImplementation(async (_tab, message) => {
        if (message.type === "snapshot") { snapshots++; return observation; }
        if (message.type === "act") { actions++; return {}; }
        return {};
      }),
    },
  });
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
