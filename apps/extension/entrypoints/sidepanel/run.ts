/** The step loop. Lives here (side panel page) because Chrome suspends the MV3 worker. */

import { observe, startRun, type RunReply } from "../../lib/api";
import type { ExecResult, Step } from "../../lib/execute";
import { MAX_MINUTES, sameOrigin } from "../../lib/safety";
import type { Observation } from "../../lib/snapshot";

export type RunOptions = { site: string; goal: string; persona: string; logged_in: boolean; max_steps: number; signal: AbortSignal };
export type Progress = {
  phase: "idle" | "starting" | "running" | "finished" | "error";
  steps: Step[];
  status?: string;
  message?: string;
};

const SETTLE_MS = 1200;

async function activeTab(): Promise<chrome.tabs.Tab> {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) throw new Error("No active tab");
  return tab;
}

async function ensureContentScript(tabId: number) {
  try {
    await chrome.tabs.sendMessage(tabId, { type: "ping" });
  } catch {
    await chrome.scripting.executeScript({ target: { tabId }, files: ["inject.js"] });
  }
}

async function send<T>(tabId: number, msg: unknown): Promise<T> {
  await ensureContentScript(tabId);
  return chrome.tabs.sendMessage(tabId, msg);
}

async function settled(tabId: number, signal: AbortSignal) {
  await new Promise((r) => setTimeout(r, SETTLE_MS));
  for (let i = 0; i < 20 && !signal.aborted; i++) {
    const tab = await chrome.tabs.get(tabId);
    if (tab.status === "complete") return;
    await new Promise((r) => setTimeout(r, 250));
  }
}

export async function runTest(opts: RunOptions, onProgress: (p: Progress) => void) {
  const steps: Step[] = [];
  const emit = (p: Partial<Progress>) => onProgress({ phase: "running", steps: [...steps], ...p });
  try {
    emit({ phase: "starting" });
    const origin = new URL(opts.site).origin;
    const granted = await chrome.permissions.request({ origins: [origin + "/*"] });
    if (!granted) throw new Error("Walkthru needs access to this site to read pages. Allow it and start again.");
    const tab = await activeTab();
    const tabId = tab.id!;
    const deadline = Date.now() + MAX_MINUTES * 60_000;

    let obs = await send<Observation>(tabId, { type: "snapshot" });
    let reply = await startRun({ ...opts, observation: obs });

    while (reply.status === "running") {
      if (opts.signal.aborted) return onProgress({ phase: "finished", steps, status: "aborted" });
      if (Date.now() > deadline) return onProgress({ phase: "finished", steps, status: "budget" });
      const step = reply.action;
      steps.push(step);
      emit({ message: step.thought });

      const note = await act(tabId, step, opts, origin);
      await settled(tabId, opts.signal);
      const current = await chrome.tabs.get(tabId);
      if (current.url && !sameOrigin(current.url, origin)) {
        return onProgress({ phase: "finished", steps, status: "gave_up", message: "Left the site" });
      }
      obs = await send<Observation>(tabId, { type: "snapshot" });
      if (note) obs.note = obs.note ? `${obs.note}; ${note}` : note;
      reply = await observe(reply.run_id, obs);
    }
    finish(reply, steps, onProgress);
  } catch (e) {
    onProgress({ phase: "error", steps, message: e instanceof Error ? e.message : String(e) });
  }
}

/** Executes one step in the tab and returns a note for the agent, if any. */
async function act(tabId: number, step: Step, opts: RunOptions, origin: string): Promise<string | undefined> {
  if (step.action === "done" || step.action === "give_up") return;
  const base = { logged_in: opts.logged_in };
  if (opts.logged_in && step.action === "click") {
    // SPEC safety rule: confirm before anything that submits a form on a logged-in page. Dry-run first.
    const probe = await send<ExecResult>(tabId, { type: "act", step, opts: { ...base, dryRun: true } });
    if (probe.note) return probe.note;
    if (probe.submits && !window.confirm(`The test user wants to submit a form on ${origin}. Allow it?`)) {
      return "form submit declined by the site owner";
    }
  }
  const result = await send<ExecResult>(tabId, { type: "act", step, opts: base });
  return result.note;
}

function finish(reply: RunReply, steps: Step[], onProgress: (p: Progress) => void) {
  if (reply.status === "running") return;
  const last = reply.steps.at(-1);
  if (last && (last.action === "done" || last.action === "give_up") && steps.at(-1) !== last) steps.push(last);
  onProgress({ phase: "finished", steps, status: reply.status });
}
