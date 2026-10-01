/** Thin client for the Walkthru step API (apps/api/app/main.py). Sends the Supabase session as a bearer token. */

import type { Observation } from "./snapshot";
import type { Step } from "./execute";
import { assertConnection, connectionId, getSession, SESSION_CHANGED, updateSession, type Session } from "./session";
export { getSession } from "./session";
export type { Session } from "./session";

export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8010";
export const WEB_URL = import.meta.env.VITE_WEB_URL ?? "http://localhost:5173";
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const SUPABASE_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;


export type StepEvidence = {
  screenshot_path: string;
  captured_at: string;
  result_url: string;
  width: number;
  height: number;
  note?: string;
};

export type RunReply =
  | { run_id: string; status: "running"; action: Step & { url: string }; action_id?: string; verified?: boolean; plan?: GoalPlan }
  | {
      run_id: string;
      status: "done" | "gave_up" | "budget" | "stuck" | "captcha" | "bot_wall" | "stopped" | "safe_stop" | "looping" | "agent_lost";
      steps: (Step & { url: string })[];
      plan?: GoalPlan;
      code?: string; // the stop reason (apps/api/app/agent/policy.py STOP_REASONS) and its plain message
      message?: string;
    };

/** How the API understood the typed goal (apps/api/app/agent/goal.py). */
export type GoalPlan = { intent: string; checkpoints: string[] };

export type StopReply = {
  run_id: string;
  status: "stopped";
  steps: (Step & { url: string; interrupted?: boolean })[];
  report_status: "generating" | "ready";
};

export type StartBody = {
  site: string;
  goal: string;
  persona: string; // a built-in key, or "custom:<id>" for a Plus test user
  group_id?: string; // Plus: several test users on one goal share it and appear side by side in each report
  logged_in: boolean;
  max_steps: number;
  observation: Observation;
};

/** A Plus owner's own test user (`GET /me/test-users`). */
export type TestUser = { id: string; name: string; description: string };

/** What `GET /me/plan` returns: the server decides the plan and its limits (apps/api/app/plans.py). */
export type PlanSummary = {
  plan: "free" | "launch" | "pro" | "plus";
  runs_allowed: number;
  runs_left: number;
  expires_at: string | null;
  max_steps: number;
  logged_in: boolean;
  personas: string[];
  sites: number;
  sites_used: string[];
};

/** Access token, refreshed through Supabase when within 30 s of expiry. Null when signed out. */
const refreshing = new Map<string, Promise<Session | null>>();
async function token(expected?: string): Promise<Session | null> {
  const session = await getSession();
  if (!session) return null;
  const connection = connectionId(session)!;
  if (expected && connection !== expected) throw new Error(SESSION_CHANGED);
  if (!session.expires_at || session.expires_at * 1000 > Date.now() + 30_000) return session;
  if (!SUPABASE_URL || !SUPABASE_KEY) throw new Error("Session expired. Connect the extension again.");
  const pending = refreshing.get(connection);
  if (pending) return pending;
  const work = refresh(session, connection).finally(() => refreshing.delete(connection));
  refreshing.set(connection, work);
  return work;
}

async function refresh(session: Session, connection: string): Promise<Session | null> {
  const res = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=refresh_token`, {
    method: "POST",
    headers: { apikey: SUPABASE_KEY!, "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: session.refresh_token }),
    signal: AbortSignal.timeout(10_000),
  });
  if (!res.ok) {
    if ([400, 401, 403].includes(res.status)) {
      try { await updateSession(session); return null; }
      catch (error) {
        const current = await assertConnection(connection);
        if (current.access_token === session.access_token) throw error;
        return current;
      }
    }
    throw new Error("Sign-in refresh is temporarily unavailable. Try again.");
  }
  const fresh = (await res.json()) as Session;
  try { await updateSession(session, fresh); }
  catch (error) {
    const current = await assertConnection(connection);
    if (current.access_token === session.access_token) throw error;
    return current; // another panel refreshed this same connection first
  }
  return assertConnection(connection);
}

let runRetriesSupported = false;
const wait = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

/** POST when a body is given. A key is created by the intent caller, never by this retry loop. */
async function call<T>(path: string, body?: unknown, requestKey?: string, expected?: string): Promise<T> {
  const t = await token(expected);
  if (!t) throw new Error(`Not signed in. Open ${WEB_URL}/app and click "Connect extension".`);
  const attempts = requestKey && runRetriesSupported ? 3 : 1;
  const connection = connectionId(t)!;
  const headers: Record<string, string> = { Authorization: `Bearer ${t.access_token}` };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (requestKey) headers["Idempotency-Key"] = requestKey;
  // Capture the body once: a retry must not take another snapshot or repeat a browser action.
  const serialized = body === undefined ? undefined : JSON.stringify(body);
  for (let attempt = 0; attempt < attempts; attempt++) {
    await assertConnection(connection);
    let res: Response;
    try {
      res = await fetch(API_URL + path, { headers, ...(body === undefined ? {} : { method: "POST", body: serialized }),
        signal: AbortSignal.timeout(requestKey ? 90_000 : 15_000) });
    } catch (error) {
      if (attempt + 1 === attempts) throw error;
      await wait(250 * (attempt + 1));
      continue;
    }
    await assertConnection(connection);
    const code = res.ok ? null : res.headers.get("X-Walkthru-Code");
    const retryable = code !== "request_outcome_unknown" && ([408, 502, 503, 504].includes(res.status)
      || (res.status === 409 && code === "request_in_progress"));
    if (retryable && attempt + 1 < attempts) {
      const seconds = Number(res.headers.get("Retry-After"));
      await res.body?.cancel();
      await wait(Number.isFinite(seconds) && seconds > 0 ? Math.min(seconds * 1000, 5000) : 250 * (attempt + 1));
      continue;
    }
    if (!res.ok) return fail(res, t);
    try {
      const result = await res.json() as T;
      await assertConnection(connection);
      return result;
    } catch (error) {
      if (attempt + 1 === attempts) throw error; // Response body may have been cut off after headers arrived.
      await wait(250 * (attempt + 1));
    }
  }
  throw new Error("The server response could not be confirmed. Check your dashboard.");
}

async function fail(res: Response, t: Session): Promise<never> {
  if (res.status === 401) {
    await updateSession(t);
    throw new Error(withReference(`Session expired. Open ${WEB_URL}/app and click "Connect extension" again.`, res));
  }
  const text = await res.text();
  let detail: unknown;
  try { detail = JSON.parse(text).detail; } catch { /* not JSON */ }
  throw new Error(withReference(typeof detail === "string" ? detail : `API request failed (${res.status}).`, res));
}

function withReference(message: string, response: Response): string {
  const id = response.headers.get("X-Request-Id");
  return /^[a-f0-9]{32}$/.test(id ?? "") ? `${message} Reference: ${id}.` : message;
}

export async function uploadEvidenceImage(path: string, dataUrl: string, expected?: string): Promise<void> {
  const t = await token(expected);
  if (!t || !SUPABASE_URL || !SUPABASE_KEY) throw new Error("Screenshot storage is not configured");
  const image = await (await fetch(dataUrl)).blob();
  await assertConnection(connectionId(t)!);
  const res = await fetch(`${SUPABASE_URL}/storage/v1/object/run-evidence/${path}`, {
    method: "POST",
    headers: {
      apikey: SUPABASE_KEY,
      Authorization: `Bearer ${t.access_token}`,
      "Content-Type": "image/jpeg",
    },
    body: image,
    signal: AbortSignal.timeout(15_000),
  });
  if (!res.ok) throw new Error(`Screenshot upload failed (${res.status})`);
}

export const getPlan = () => call<PlanSummary>("/me/plan");
export const getTestUsers = () => call<TestUser[]>("/me/test-users");
/** Are test runs on for this account right now (kill switches, automatic suspension)? The API enforces it anyway. */
export async function getRunPolicy() {
  runRetriesSupported = false;
  const policy = await call<{ journeys: boolean; message: string; idempotency?: string }>("/runs/policy");
  runRetriesSupported = policy.idempotency === "v1";
  return policy;
}
export const startRun = (body: StartBody, requestKey = crypto.randomUUID(), connection?: string) => call<RunReply>("/runs", body, requestKey, connection);
export const observe = (runId: string, observation: Observation, evidence?: StepEvidence, actionId?: string, requestKey = crypto.randomUUID(), connection?: string) =>
  call<RunReply>(`/runs/${runId}/observe`, { observation, ...(evidence ? { evidence } : {}), ...(actionId ? { action_id: actionId } : {}) }, requestKey, connection);
export const stopRun = (runId: string, reason?: string, requestKey = crypto.randomUUID(), connection?: string) =>
  call<StopReply>(`/runs/${runId}/stop`, reason ? { reason } : {}, requestKey, connection);
