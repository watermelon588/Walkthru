import { beforeEach, expect, test, vi } from "vitest";
import { getRecheck } from "../lib/api";

// R-S13: the side panel asks for the last count check on a site by origin only; tab URLs can carry tokens.
let urls: string[];

beforeEach(() => {
  urls = [];
  vi.stubGlobal("chrome", { storage: { local: { get: vi.fn().mockResolvedValue({ session: { access_token: "fake", expires_at: Date.now() / 1000 + 3600 } }) } } });
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    urls.push(url);
    return new Response(JSON.stringify({ run_id: "r1", goal: "Filter Active records", persona: "first_timer", logged_in: true, status: "failed",
      assertion: { path: "/dashboard", filter_value: "Active", count_label: "Filtered records", expected_count: 2, dataset_id: "synthetic-sales-v1", dataset_at: null, max_age_seconds: 3600, tolerance: 0 } }));
  }));
});

test("the recheck lookup sends the site's origin only", async () => {
  const last = await getRecheck("https://app.example.test/dashboard?token=secret#x");
  expect(urls[0]).toMatch(/\/me\/recheck\?site=https%3A%2F%2Fapp\.example\.test$/);
  expect(urls[0]).not.toContain("secret");
  expect(last.assertion?.dataset_at).toBeNull();
});
