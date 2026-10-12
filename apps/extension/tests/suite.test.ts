import { beforeEach, expect, test, vi } from "vitest";
import { coverage, loadRun, loadSuites, newRun, nextIndex, runSuite, saveRun, saveSuite, validSuite, type Scenario, type Suite, type SuiteDeps, type SuiteRun } from "../lib/suite";

// R-S14: bounded suites run scenario by scenario with their own quotes, survive stop/resume and a closed panel,
// never record work across accounts, and report tested, blocked and not-tested scenarios apart from discovered routes.
const site = "https://app.example.test";
const scenario = (id: string, extra: Partial<Scenario> = {}): Scenario => ({ id, name: `Scenario ${id}`, start_url: `${site}/`, goal: `Goal ${id}`, persona: "first_timer", logged_in: false, max_steps: 12, ...extra });
const suite: Suite = { id: "s1", name: "Launch checks", origin: site, scenarios: [scenario("a"), scenario("b"), scenario("c")] };

function deps(outcomes: Record<string, { status?: string; error?: string; urls?: string[] }>, extra: Partial<SuiteDeps> = {}) {
  const saved: SuiteRun[] = [];
  const ran: string[] = [];
  const quoted: string[] = [];
  const d: SuiteDeps = {
    signal: new AbortController().signal,
    connectionOk: () => true,
    handoff: async () => true,
    quote: async (s) => { quoted.push(s.id); return { token: `quote-${s.id}` }; },
    run: async (s, token) => { ran.push(`${s.id}:${token}`); const o = outcomes[s.id] ?? { status: "done" }; return { runId: `run-${s.id}`, urls: o.urls ?? [], ...o }; },
    save: async (run) => { saved.push(structuredClone(run)); },
    ...extra,
  };
  return { d, saved, ran, quoted };
}

test("each scenario runs with its own quote and its own outcome", async () => {
  const { d, ran } = deps({ b: { status: "budget" }, c: { status: "captcha" } });
  const run = await runSuite(suite, newRun(suite, "acct-1"), d);
  expect(ran).toEqual(["a:quote-a", "b:quote-b", "c:quote-c"]);
  expect(run.results.map((r) => r.state)).toEqual(["tested", "not_tested", "blocked"]);
  expect(run.results[1]).toMatchObject({ resumable: false, run_id: "run-b" });
  expect(nextIndex(run)).toBe(-1); // a step-cap stop is not silently rerun on resume
});

test("stop then resume continues where the suite stopped, without rerunning finished scenarios", async () => {
  const abort = new AbortController();
  const first = deps({}, { signal: abort.signal, run: async (s) => { abort.abort(); return { status: "stopped", runId: `run-${s.id}`, urls: [] }; } });
  const stopped = await runSuite(suite, newRun(suite, "acct-1"), first.d);
  expect(stopped.results.map((r) => r.state)).toEqual(["not_tested", "pending", "pending"]);
  const resume = deps({});
  const done = await runSuite(suite, stopped, resume.d);
  expect(resume.ran).toEqual(["a:quote-a", "b:quote-b", "c:quote-c"]); // the owner-stopped one runs again as a new run
  expect(done.results.every((r) => r.state === "tested")).toBe(true);
});

test("a panel closed mid-scenario recovers as not tested and resumable", async () => {
  const crashed: SuiteRun = { ...newRun(suite, "acct-1"), results: [{ scenario_id: "a", state: "tested", run_id: "run-a" }, { scenario_id: "b", state: "running" }, { scenario_id: "c", state: "pending" }] };
  const { d, ran, saved } = deps({});
  await runSuite(suite, crashed, d);
  expect(ran).toEqual(["b:quote-b", "c:quote-c"]);
  expect(saved[0]?.results[1]).toMatchObject({ state: "running" }); // saved before the run, so the next crash is recorded too
});

test("a refused quote stops the suite and keeps the rest pending", async () => {
  const { d, ran } = deps({}, { quote: async (s) => { if (s.id === "b") throw new Error("No test runs left in this pass."); return { token: "q" }; } });
  const run = await runSuite(suite, newRun(suite, "acct-1"), d);
  expect(ran).toEqual(["a:q"]);
  expect(run.results.map((r) => r.state)).toEqual(["tested", "not_tested", "pending"]);
  expect(run.results[1]).toMatchObject({ reason: "No test runs left in this pass.", resumable: true });
});

test("an account change stops the suite and records nothing under the new account", async () => {
  let connected = true;
  const { d } = deps({}, { connectionOk: () => connected, run: async () => { connected = false; return { status: "done", runId: "x", urls: [] }; } });
  const run = await runSuite(suite, newRun(suite, "acct-1"), d);
  expect(run.results.map((r) => r.state)).toEqual(["running", "pending", "pending"]); // recovered as interrupted on the next load
});

test("signed-in scenarios wait for the owner's own sign-in", async () => {
  const signedIn: Suite = { ...suite, scenarios: [scenario("a"), scenario("b", { logged_in: true }), scenario("c")] };
  const declined = deps({}, { handoff: async () => false });
  const run = await runSuite(signedIn, newRun(signedIn, "acct-1"), declined.d);
  expect(declined.ran).toEqual(["a:quote-a"]);
  expect(declined.quoted).toEqual(["a"]); // no quote, no credit, until the owner is ready
  expect(run.results[1]).toMatchObject({ state: "not_tested", resumable: true, reason: "Waiting for you to sign in to the site in this tab." });
  const ready = deps({});
  expect((await runSuite(signedIn, run, ready.d)).results.every((r) => r.state === "tested")).toBe(true);
});

test("coverage separates tested, blocked and not-tested scenarios from discovered routes", () => {
  const withCheck: Suite = { ...suite, scenarios: [scenario("a", { assertion: { path: "/dashboard", filter_value: "Active", count_label: "Filtered records", expected_count: 2, dataset_id: "d", dataset_at: null, max_age_seconds: 3600, tolerance: 0 } }), scenario("b"), scenario("c")] };
  const run: SuiteRun = { ...newRun(withCheck, "acct-1"), results: [
    { scenario_id: "a", state: "tested", run_id: "run-a", urls: [`${site}/`, `${site}/dashboard`, "https://elsewhere.test/x"] },
    { scenario_id: "b", state: "blocked", reason: "A human check stopped the test.", urls: [`${site}/signup`] },
    { scenario_id: "c", state: "pending" },
  ] };
  const got = coverage(withCheck, run);
  expect(got.tested.map((x) => x.name)).toEqual(["Scenario a"]);
  expect(got.blocked.map((x) => x.name)).toEqual(["Scenario b"]);
  expect(got.not_tested).toEqual([{ name: "Scenario c", reason: "Not started.", run_id: undefined }]);
  expect(got.routes).toEqual(["/", "/dashboard", "/signup"]); // other origins never count as coverage
  expect(got.promised).toEqual([{ name: "Scenario a", check: "/dashboard, Filter: Active, Filtered records", run_id: "run-a" }]);
});

test("progress from an edited suite is not resumed", async () => {
  const old = newRun(suite, "acct-1");
  const edited: Suite = { ...suite, scenarios: [scenario("a"), scenario("c")] };
  await expect(runSuite(edited, old, deps({}).d)).rejects.toThrow(/different version/);
});

test("suites stay on one site and within bounds", () => {
  expect(validSuite(suite)).toBeNull();
  expect(validSuite({ ...suite, scenarios: [] })).toMatch(/at least one/);
  expect(validSuite({ ...suite, scenarios: Array.from({ length: 7 }, (_, i) => scenario(String(i))) })).toMatch(/at most 6/);
  expect(validSuite({ ...suite, scenarios: [scenario("a", { start_url: "https://other.test/" })] })).toMatch(/same site/);
  expect(validSuite({ ...suite, scenarios: [scenario("a", { max_steps: 99 })] })).toMatch(/step cap/);
});

let store: Record<string, unknown>;
beforeEach(() => {
  store = {};
  vi.stubGlobal("chrome", { storage: { local: {
    get: vi.fn(async (key: string) => (key in store ? { [key]: store[key] } : {})),
    set: vi.fn(async (value: Record<string, unknown>) => { Object.assign(store, value); }),
    remove: vi.fn(async (key: string) => { delete store[key]; }),
  } } });
});

test("suites and progress persist in this browser, and another account's progress is dropped", async () => {
  await saveSuite(suite);
  expect(await loadSuites()).toEqual([suite]);
  await expect(saveSuite({ ...suite, id: "bad", scenarios: [] })).rejects.toThrow(/at least one/);
  await saveRun(newRun(suite, "acct-1"));
  expect((await loadRun("acct-1"))?.suite_id).toBe("s1");
  expect(await loadRun("acct-2")).toBeNull();
  expect(await loadRun("acct-1")).toBeNull(); // dropped, not hidden
});
