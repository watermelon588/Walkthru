/** Thin client for the Walkthru step API (apps/api/app/main.py). Sends the Supabase session as a bearer token. */

import type { Observation } from "./snapshot";
import type { Step } from "./execute";

export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8010";
export const WEB_URL = import.meta.env.VITE_WEB_URL ?? "http://localhost:5173";
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const SUPABASE_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

export type Session = { access_token: string; refresh_token: string; expires_at?: number };

export type StepEvidence = {
  screenshot_path: string;
  captured_at: string;
  result_url: string;
  width: number;
  height: number;
  note?: string;
};

export type RunReply =
  | { run_id: string; status: "running"; action: Step & { url: string }; verified?: boolean; plan?: GoalPlan }
  | { run_id: string; status: "done" | "gave_up" | "budget" | "stuck" | "captcha" | "stopped" | "safe_stop" | "looping"; steps: (Step & { url: string })[]; plan?: GoalPlan };

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
  persona: string;
  logged_in: boolean;
  max_steps: number;
  observation: Observation;
};

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

export async function getSession(): Promise<Session | null> {
  const { session } = await chrome.storage.local.get("session");
  return (session as Session | undefined) ?? null;
}

/** Access token, refreshed through Supabase when within 30 s of expiry. Null when signed out. */
async function token(): Promise<string | null> {
  const session = await getSession();
  if (!session) return null;
  if (!session.expires_at || session.expires_at * 1000 > Date.now() + 30_000) return session.access_token;
  if (!SUPABASE_URL || !SUPABASE_KEY) return session.access_token;
  const res = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=refresh_token`, {
    method: "POST",
    headers: { apikey: SUPABASE_KEY, "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: session.refresh_token }),
  });
  if (!res.ok) {
    await chrome.storage.local.remove("session");
    return null;
  }
  const fresh = (await res.json()) as Session;
  await chrome.storage.local.set({ session: fresh });
  return fresh.access_token;
}

/** POST when a body is given, GET otherwise. */
async function call<T>(path: string, body?: unknown): Promise<T> {
  const t = await token();
  if (!t) throw new Error(`Not signed in. Open ${WEB_URL}/app and click "Connect extension".`);
  const res = await fetch(API_URL + path, body === undefined
    ? { headers: { Authorization: `Bearer ${t}` } }
    : { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${t}` }, body: JSON.stringify(body) });
  if (res.status === 401) {
    await chrome.storage.local.remove("session");
    throw new Error(`Session expired. Open ${WEB_URL}/app and click "Connect extension" again.`);
  }
  if (!res.ok) {
    const text = await res.text();
    let detail: unknown;
    try { detail = JSON.parse(text).detail; } catch { /* not JSON */ }
    // Plan limits and other API refusals carry a plain-language `detail`; show it as is.
    throw new Error(typeof detail === "string" ? detail : `API ${res.status}: ${text.slice(0, 200)}`);
  }
  return res.json();
}

export async function uploadEvidenceImage(path: string, dataUrl: string): Promise<void> {
  const t = await token();
  if (!t || !SUPABASE_URL || !SUPABASE_KEY) throw new Error("Screenshot storage is not configured");
  const image = await (await fetch(dataUrl)).blob();
  const res = await fetch(`${SUPABASE_URL}/storage/v1/object/run-evidence/${path}`, {
    method: "POST",
    headers: {
      apikey: SUPABASE_KEY,
      Authorization: `Bearer ${t}`,
      "Content-Type": "image/jpeg",
    },
    body: image,
  });
  if (!res.ok) throw new Error(`Screenshot upload failed (${res.status})`);
}

export const getPlan = () => call<PlanSummary>("/me/plan");
export const startRun = (body: StartBody) => call<RunReply>("/runs", body);
export const observe = (runId: string, observation: Observation, evidence?: StepEvidence) =>
  call<RunReply>(`/runs/${runId}/observe`, { observation, ...(evidence ? { evidence } : {}) });
export const stopRun = (runId: string, reason?: string) => call<StopReply>(`/runs/${runId}/stop`, reason ? { reason } : {});
