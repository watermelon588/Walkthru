// R-S14: a saved suite is a short, bounded list of scenarios run one after another in the owner's own browser.
// Each scenario is an ordinary run with its own quote, so its step cap and credit are its phase budget. Suites and
// suite progress live in this browser only (chrome.storage.local): no server schema, no schedule, no unattended runner.
// Coverage lists tested, blocked and not-tested scenarios; routes the test users happened to visit are listed apart
// from the checks the owner declared. Contract: docs/saved-suites.md.
import type { FilterCountAssertion } from "./api";

export const MAX_SCENARIOS = 6;
export const MAX_SUITES = 20;
const SUITES = "walkthru_suites";
const RUN = "walkthru_suite_run";

export type Scenario = { id: string; name: string; start_url: string; goal: string; persona: string; logged_in: boolean; max_steps: number; assertion?: FilterCountAssertion };
export type Suite = { id: string; name: string; origin: string; scenarios: Scenario[] };
export type ScenarioState = "pending" | "running" | "tested" | "blocked" | "not_tested";
export type ScenarioResult = { scenario_id: string; state: ScenarioState; run_id?: string; status?: string; reason?: string; resumable?: boolean; urls?: string[] };
export type SuiteRun = { suite_id: string; connection: string; started_at: string; results: ScenarioResult[] };

export const origin = (url: string) => new URL(url).origin;

/** A suite keeps every scenario on one site and within the plan's caps; anything else is refused before it is saved. */
export function validSuite(suite: Suite): string | null {
  if (!suite.name.trim() || suite.name.length > 80) return "Give the suite a name of up to 80 characters.";
  if (suite.scenarios.length === 0) return "Add at least one scenario.";
  if (suite.scenarios.length > MAX_SCENARIOS) return `A suite holds at most ${MAX_SCENARIOS} scenarios.`;
  for (const s of suite.scenarios) {
    if (origin(s.start_url) !== suite.origin) return "Every scenario in a suite starts on the same site.";
    if (!s.goal.trim() || s.goal.length > 500) return "Every scenario needs a goal.";
    if (!Number.isInteger(s.max_steps) || s.max_steps < 1 || s.max_steps > 40) return "A scenario's step cap must be between 1 and 40.";
  }
  return null;
}

export function newRun(suite: Suite, connection: string): SuiteRun {
  return { suite_id: suite.id, connection, started_at: new Date().toISOString(), results: suite.scenarios.map((s) => ({ scenario_id: s.id, state: "pending" })) };
}

/** Where a run left its scenario. Only a finished journey or a genuine stuck point counts as tested. */
export function outcome(status: string | undefined, error?: string): Pick<ScenarioResult, "state" | "reason" | "resumable"> {
  if (error) return { state: "not_tested", reason: error, resumable: true };
  switch (status) {
    case "done": return { state: "tested", reason: "The test user reached the goal." };
    case "gave_up": case "stuck": return { state: "tested", reason: "The test user got stuck; the report says where." };
    case "captcha": case "bot_wall": return { state: "blocked", reason: "A human check stopped the test. Walkthru never solves it." };
    case "safe_stop": return { state: "blocked", reason: "Walkthru stopped before an unsafe action (payment, delete or similar)." };
    case "budget": return { state: "not_tested", reason: "Stopped at its step cap; the partial evidence is in the report.", resumable: false };
    case "looping": case "agent_lost": return { state: "not_tested", reason: "Walkthru lost its way; that is Walkthru's limit, not a site result.", resumable: false };
    case "stopped": return { state: "not_tested", reason: "Stopped by you.", resumable: true };
    default: return { state: "not_tested", reason: `Ended as ${status ?? "unknown"}.`, resumable: true };
  }
}

/** After the side panel closed mid-scenario, that scenario was not tested; it can run again (as a new run). */
export function recover(run: SuiteRun): SuiteRun {
  return { ...run, results: run.results.map((r) => (r.state === "running" ? { ...r, state: "not_tested", reason: "Interrupted: the side panel closed during this test.", resumable: true } : r)) };
}

/** Saved progress belongs to this exact suite: after the suite is edited it starts afresh instead of resuming. */
export const matches = (suite: Suite, run: SuiteRun | null): run is SuiteRun =>
  !!run && run.suite_id === suite.id && run.results.length === suite.scenarios.length && run.results.every((r, i) => r.scenario_id === suite.scenarios[i]?.id);

export const nextIndex = (run: SuiteRun) => run.results.findIndex((r) => r.state === "pending" || (r.state === "not_tested" && r.resumable));

export type Coverage = {
  tested: { name: string; reason?: string; run_id?: string }[];
  blocked: { name: string; reason?: string; run_id?: string }[];
  not_tested: { name: string; reason?: string; run_id?: string }[];
  promised: { name: string; check: string; run_id?: string }[]; // declared checks; their verdict is in each report
  routes: string[]; // pages the test users visited: discovered, not promised or checked
};

export function coverage(suite: Suite, run: SuiteRun): Coverage {
  const out: Coverage = { tested: [], blocked: [], not_tested: [], promised: [], routes: [] };
  const routes = new Set<string>();
  suite.scenarios.forEach((s, i) => {
    const r = run.results[i] ?? { scenario_id: s.id, state: "pending" };
    const item = { name: s.name, reason: r.state === "pending" ? "Not started." : r.reason, run_id: r.run_id };
    if (r.state === "tested") out.tested.push(item);
    else if (r.state === "blocked") out.blocked.push(item);
    else out.not_tested.push(item);
    if (s.assertion) out.promised.push({ name: s.name, check: `${s.assertion.path}, Filter: ${s.assertion.filter_value}, ${s.assertion.count_label}`, run_id: r.run_id });
    for (const url of r.urls ?? []) {
      try { const u = new URL(url); if (u.origin === suite.origin) routes.add(u.pathname); } catch { /* not a URL */ }
    }
  });
  out.routes = [...routes].sort();
  return out;
}

export type SuiteDeps = {
  signal: AbortSignal;
  connectionOk: () => boolean;
  handoff: (s: Scenario) => Promise<boolean>; // signed-in scenarios wait for the owner to prepare the login
  quote: (s: Scenario) => Promise<{ token: string }>;
  run: (s: Scenario, quote: string) => Promise<{ status?: string; runId?: string; error?: string; urls: string[] }>;
  save: (run: SuiteRun) => Promise<void>;
};

/** Run (or resume) a suite. Progress is saved before and after every scenario, so a closed panel, a stop or a refused
 *  quote leaves an exact record to resume from. A changed account, an abort or a declined sign-in stops the suite. */
export async function runSuite(suite: Suite, start: SuiteRun, deps: SuiteDeps): Promise<SuiteRun> {
  if (!matches(suite, start)) throw new Error("This progress belongs to a different version of the suite.");
  let run = recover(start);
  const set = async (i: number, result: Partial<ScenarioResult>) => {
    run = { ...run, results: run.results.map((r, j) => (j === i ? { ...r, ...result } : r)) };
    await deps.save(run);
  };
  for (let i = nextIndex(run); i !== -1; i = nextIndex(run)) {
    if (deps.signal.aborted || !deps.connectionOk()) break;
    const s = suite.scenarios[i];
    if (!s) break;
    if (s.logged_in && !(await deps.handoff(s))) {
      await set(i, { state: "not_tested", reason: "Waiting for you to sign in to the site in this tab.", resumable: true });
      break;
    }
    let token: string;
    try {
      token = (await deps.quote(s)).token;
    } catch (error) {
      await set(i, outcome(undefined, error instanceof Error ? error.message : "This scenario's terms could not be confirmed."));
      break; // a plan limit or an expired session would refuse the next scenario too
    }
    await set(i, { state: "running", reason: undefined, run_id: undefined, status: undefined });
    const got = await deps.run(s, token);
    if (!deps.connectionOk()) break; // another account connected: do not record this account's work under it
    await set(i, { ...outcome(got.status, got.error), run_id: got.runId, status: got.status, urls: got.urls.slice(0, 40) });
    if (got.error) break;
  }
  return run;
}

// ---------- storage (this browser only) ----------

export async function loadSuites(): Promise<Suite[]> {
  const got = await chrome.storage.local.get(SUITES);
  return Array.isArray(got[SUITES]) ? (got[SUITES] as Suite[]) : [];
}

export async function saveSuite(suite: Suite): Promise<Suite[]> {
  const problem = validSuite(suite);
  if (problem) throw new Error(problem);
  const all = (await loadSuites()).filter((s) => s.id !== suite.id);
  if (all.length >= MAX_SUITES) throw new Error(`Keep at most ${MAX_SUITES} suites; delete one first.`);
  const next = [...all, suite];
  await chrome.storage.local.set({ [SUITES]: next });
  return next;
}

export async function deleteSuite(id: string): Promise<Suite[]> {
  const next = (await loadSuites()).filter((s) => s.id !== id);
  await chrome.storage.local.set({ [SUITES]: next });
  const run = await loadRun();
  if (run?.suite_id === id) await chrome.storage.local.remove(RUN);
  return next;
}

/** The saved progress, only for the account that made it: another account's suite progress is dropped. */
export async function loadRun(connection?: string): Promise<SuiteRun | null> {
  const got = (await chrome.storage.local.get(RUN))[RUN] as SuiteRun | undefined;
  if (!got) return null;
  if (connection !== undefined && got.connection !== connection) {
    await chrome.storage.local.remove(RUN);
    return null;
  }
  return got;
}

export const saveRun = (run: SuiteRun) => chrome.storage.local.set({ [RUN]: run });
export const clearRun = () => chrome.storage.local.remove(RUN);
