import { beforeEach, expect, test, vi } from "vitest";
import { getRunPolicy, observe, startRun, stopRun } from "../lib/api";

type FetchRequest = (url: string, options: { headers: Record<string, string>; body: string }) => Promise<Response>;

beforeEach(async () => {
  vi.stubGlobal("chrome", {
    storage: {
      local: {
        get: vi.fn().mockResolvedValue({
          session: { access_token: "test-token", refresh_token: "refresh", expires_at: Math.floor(Date.now() / 1000) + 3600 },
        }),
        remove: vi.fn().mockResolvedValue(undefined),
      },
    },
  });
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ journeys: true }))));
  await getRunPolicy(); // Reset capability negotiation, so older API deployments never get automatic retries.
});

test("stops an interrupted run through the authenticated API", async () => {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: vi.fn().mockResolvedValue({ run_id: "run-1", status: "stopped", steps: [], report_status: "generating" }),
  });
  vi.stubGlobal("fetch", fetchMock);

  const result = await stopRun("run-1");

  expect(result.status).toBe("stopped");
  expect(fetchMock).toHaveBeenCalledWith(
    "http://localhost:8010/runs/run-1/stop",
    expect.objectContaining({ method: "POST", body: "{}" }),
  );
});

test("one run intent reuses its key and frozen payload after a lost response", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ journeys: true, idempotency: "v1" }))));
  await getRunPolicy();
  const fetchMock = vi.fn().mockRejectedValueOnce(new TypeError("response lost"))
    .mockResolvedValueOnce(new Response(JSON.stringify({ run_id: "r", status: "stopped", steps: [] })));
  vi.stubGlobal("fetch", fetchMock);
  await stopRun("r", "Owner stopped");
  expect(fetchMock).toHaveBeenCalledTimes(2);
  const options = fetchMock.mock.calls.map((call) => call[1]);
  expect(options[0].headers["Idempotency-Key"]).toMatch(/^[a-f0-9-]{36}$/);
  expect(options[1].headers["Idempotency-Key"]).toBe(options[0].headers["Idempotency-Key"]);
  expect(options[1].body).toBe(options[0].body);
});

test("new starts receive distinct keys even when their bodies match", async () => {
  const fetchMock = vi.fn<FetchRequest>().mockImplementation(() => Promise.resolve(new Response('{}')));
  vi.stubGlobal("fetch", fetchMock);
  const body = { site: "https://fixture.test", goal: "read", persona: "first_timer", logged_in: false, max_steps: 5,
    observation: { url: "https://fixture.test", title: "Guide", text: "", elements: [], errors: [] } };
  await startRun(body);
  await startRun(body);
  expect(fetchMock.mock.calls[0]![1].headers["Idempotency-Key"]).not.toBe(fetchMock.mock.calls[1]![1].headers["Idempotency-Key"]);
});

test("observations carry the pending action ID and honor a caller-owned request key", async () => {
  const fetchMock = vi.fn<FetchRequest>().mockResolvedValue(new Response('{}'));
  vi.stubGlobal("fetch", fetchMock);
  const requestKey = crypto.randomUUID(), actionId = crypto.randomUUID();
  await observe("r", { url: "https://fixture.test", title: "Guide", text: "", elements: [], errors: [] }, undefined, actionId, requestKey);
  expect(JSON.parse(fetchMock.mock.calls[0]![1].body).action_id).toBe(actionId);
  expect(fetchMock.mock.calls[0]![1].headers["Idempotency-Key"]).toBe(requestKey);
});

test("old APIs and uncertain outcomes are never retried automatically", async () => {
  const oldFetch = vi.fn().mockRejectedValue(new TypeError("lost response"));
  vi.stubGlobal("fetch", oldFetch);
  await expect(stopRun("r")).rejects.toThrow();
  expect(oldFetch).toHaveBeenCalledTimes(1);
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ journeys: true, idempotency: "v1" }))));
  await getRunPolicy();
  const unknownFetch = vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify({ detail: "Check the dashboard." }), {
    status: 503, headers: { "X-Walkthru-Code": "request_outcome_unknown" },
  })));
  vi.stubGlobal("fetch", unknownFetch);
  await expect(stopRun("r")).rejects.toThrow("Check the dashboard.");
  expect(unknownFetch).toHaveBeenCalledTimes(1);
});

test("API failures carry a safe support reference without exposing raw error bodies", async () => {
  const id = "a".repeat(32);
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Please try again." }), {
    status: 503, headers: { "X-Request-Id": id },
  })));
  await expect(stopRun("run-1")).rejects.toThrow(`Please try again. Reference: ${id}.`);
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("<html>private upstream error</html>", {
    status: 500, headers: { "X-Request-Id": "unsafe-id" },
  })));
  await expect(stopRun("run-1")).rejects.toThrow("API request failed (500).");
});

test("pending requests retry with the same key and stop at the attempt budget", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ idempotency: "v1" }))));
  await getRunPolicy();
  const fetchMock = vi.fn<FetchRequest>().mockImplementation(() => Promise.resolve(new Response(JSON.stringify({ detail: "Still processing" }), {
    status: 409, headers: { "X-Walkthru-Code": "request_in_progress" },
  })));
  vi.stubGlobal("fetch", fetchMock);
  await expect(stopRun("r")).rejects.toThrow("Still processing");
  expect(fetchMock).toHaveBeenCalledTimes(3);
  expect(new Set(fetchMock.mock.calls.map((call) => call[1].headers["Idempotency-Key"])).size).toBe(1);
});

test.each([401, 409, 422, 429])("does not retry a terminal HTTP %s", async (status) => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ idempotency: "v1" }))));
  await getRunPolicy();
  const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(new Response('{}', { status })));
  vi.stubGlobal("fetch", fetchMock);
  await expect(stopRun("r")).rejects.toThrow();
  expect(fetchMock).toHaveBeenCalledTimes(1);
});
