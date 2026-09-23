import { beforeEach, expect, test, vi } from "vitest";
import { stopRun } from "../lib/api";

beforeEach(() => {
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
    "http://localhost:8000/runs/run-1/stop",
    expect.objectContaining({ method: "POST", body: "{}" }),
  );
});
