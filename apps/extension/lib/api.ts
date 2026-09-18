/** Thin client for the Walkthru step API (apps/api/app/main.py). Sends the Supabase session as a bearer token. */

import type { Observation } from "./snapshot";
import type { Step } from "./execute";

export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
export const WEB_URL = import.meta.env.VITE_WEB_URL ?? "http://localhost:5173";
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const SUPABASE_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

export type Session = { access_token: string; refresh_token: string; expires_at?: number };

export type RunReply =
  | { run_id: string; status: "running"; action: Step & { url: string } }
  | { run_id: string; status: "done" | "gave_up" | "budget" | "stuck" | "captcha"; steps: (Step & { url: string })[] };

export type StartBody = {
  site: string;
  goal: string;
  persona: string;
  logged_in: boolean;
  max_steps: number;
  observation: Observation;
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

async function post<T>(path: string, body: unknown): Promise<T> {
  const t = await token();
  if (!t) throw new Error(`Not signed in. Open ${WEB_URL}/app and click "Connect extension".`);
  const res = await fetch(API_URL + path, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${t}` },
    body: JSON.stringify(body),
  });
  if (res.status === 401) {
    await chrome.storage.local.remove("session");
    throw new Error(`Session expired. Open ${WEB_URL}/app and click "Connect extension" again.`);
  }
  if (!res.ok) throw new Error(`API ${res.status}: ${(await res.text()).slice(0, 200)}`);
  return res.json();
}

export const startRun = (body: StartBody) => post<RunReply>("/runs", body);
export const observe = (runId: string, observation: Observation) => post<RunReply>(`/runs/${runId}/observe`, { observation });
