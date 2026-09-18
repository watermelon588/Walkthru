/** Thin client for the Walkthru step API (apps/api/app/main.py). */

import type { Observation } from "./snapshot";
import type { Step } from "./execute";

export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

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

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(API_URL + path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!res.ok) throw new Error(`API ${res.status}: ${(await res.text()).slice(0, 200)}`);
  return res.json();
}

export const startRun = (body: StartBody) => post<RunReply>("/runs", body);
export const observe = (runId: string, observation: Observation) => post<RunReply>(`/runs/${runId}/observe`, { observation });
