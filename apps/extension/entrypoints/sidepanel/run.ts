/** The step loop. Lives here (side panel page) because Chrome suspends the MV3 worker. */

import { observe, startRun, stopRun, type RunReply, type StepEvidence } from "../../lib/api";
import type { AgentState } from "../../lib/agent-bird";
import { captureStepEvidence, evidenceFailureMessage, shouldCaptureEvidence } from "../../lib/evidence";
import type { ExecResult, Step } from "../../lib/execute";
import { MAX_MINUTES, sameOrigin } from "../../lib/safety";
import type { Observation } from "../../lib/snapshot";

export type RunOptions = { site: string; goal: string; persona: string; logged_in: boolean; max_steps: number; signal: AbortSignal; verified?: boolean; sentOnce?: boolean };
export type Progress = {
  phase: "idle" | "starting" | "running" | "finished" | "error";
  steps: Step[];
  status?: string;
  message?: string;
  runId?: string;
  evidenceWarning?: string;
};

const SETTLE_MS = 1200;
const ACTION_ACTIVITY: Record<Step["action"], string> = {
  click: "Clicking the next step",
  type: "Filling in the form",
  scroll: "Looking further down",
  back: "Going back",
  done: "Checking the result",
  give_up: "Could not continue",
};

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

async function setAgentStatus(tabId: number, state: AgentState, activity: string) {
  try {
    await send(tabId, { type: "agent_status", state, activity });
  } catch {
    // A navigation can remove the overlay before the next page is available.
  }
}

async function setEvidenceCapture(tabId: number, active: boolean) {
  try {
    await send(tabId, { type: "evidence_capture", active });
  } catch {
    // Navigation can replace the page between capture steps.
  }
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
  let capturedCount = 0;
  let evidenceWarning: string | undefined;
  const emit = (p: Partial<Progress>) => onProgress({ phase: "running", steps: [...steps], evidenceWarning, ...p });
  let tabId: number | undefined;
  let runId: string | undefined;
  try {
    emit({ phase: "starting" });
    const origin = new URL(opts.site).origin;
    // Chrome's side panel does not grant activeTab to captureVisibleTab. The API only
    // accepts activeTab or <all_urls>, so request the optional capture permission from
    // this explicit Start Test gesture. Chrome prompts once and remembers the choice.
    const granted = await chrome.permissions.request({ origins: ["<all_urls>"] });
    if (!granted) throw new Error("Walkthru needs screenshot access to save visual evidence. Allow it and start again.");
    const tab = await activeTab();
    tabId = tab.id!;
    const deadline = Date.now() + MAX_MINUTES * 60_000;

    await setAgentStatus(tabId, "observing", "Reading the page");
    let obs = await send<Observation>(tabId, { type: "snapshot" });
    let reply = await startRun({ ...opts, observation: obs });
    runId = reply.run_id;
    // Owner-verified domains may send real messages, but only after the owner approves each one.
    opts = { ...opts, verified: reply.status === "running" && reply.verified === true };

    while (reply.status === "running") {
      if (opts.signal.aborted) {
        await setAgentStatus(tabId, "stopped", "Test stopped");
        if (!await closeRun(runId, steps, onProgress, evidenceWarning, "the site owner pressed Stop")) {
          onProgress({ phase: "error", steps, message: "The test stopped locally, but Walkthru could not close the server run. End it from the dashboard.", evidenceWarning });
        }
        return;
      }
      if (Date.now() > deadline) {
        await setAgentStatus(tabId, "stopped", "Ran out of test time");
        if (!await closeRun(runId, steps, onProgress, evidenceWarning, "the 4-minute time limit ended the test")) {
          onProgress({ phase: "error", steps, message: "The time limit ended, but Walkthru could not close the server run. End it from the dashboard.", evidenceWarning });
        }
        return;
      }
      const step = reply.action;
      steps.push(step);
      emit({ message: step.thought });

      await setAgentStatus(tabId, step.action === "give_up" ? "stopped" : step.action === "done" ? "observing" : "acting", ACTION_ACTIVITY[step.action]);
      const note = await act(tabId, step, opts, origin);
      await settled(tabId, opts.signal);
      if (opts.signal.aborted) {
        await setAgentStatus(tabId, "stopped", "Test stopped");
        if (!await closeRun(runId, steps, onProgress, evidenceWarning, "the site owner pressed Stop")) {
          onProgress({ phase: "error", steps, message: "The test stopped locally, but Walkthru could not close the server run. End it from the dashboard.", evidenceWarning });
        }
        return;
      }
      const current = await chrome.tabs.get(tabId);
      if (current.url && !sameOrigin(current.url, origin)) {
        await setAgentStatus(tabId, "stopped", "Left the site");
        if (!await closeRun(runId, steps, onProgress, evidenceWarning, `the last click led away from the site, to ${current.url}`)) {
          onProgress({ phase: "error", steps, message: "The test left the site, but Walkthru could not close the server run. End it from the dashboard.", evidenceWarning });
        }
        return;
      }
      await setAgentStatus(tabId, "observing", "Reading the updated page");
      obs = await send<Observation>(tabId, { type: "snapshot" });
      if (note) obs.note = obs.note ? `${obs.note}; ${note}` : note;
      const stepIndex = steps.length - 1;
      let evidence: StepEvidence | undefined;
      if (shouldCaptureEvidence(step, obs, stepIndex, capturedCount)) {
        const latestTab = await chrome.tabs.get(tabId);
        await setEvidenceCapture(tabId, true);
        try {
          evidence = await captureStepEvidence(runId, stepIndex, latestTab, obs.url, note);
          capturedCount += 1;
        } catch (error) {
          // Evidence should enrich a journey, never stop it.
          evidenceWarning = evidenceFailureMessage(error);
          emit({ evidenceWarning });
        } finally {
          await setEvidenceCapture(tabId, false);
        }
      }
      reply = await observe(reply.run_id, obs, evidence);
    }
    const finished = reply.status === "done" || reply.status === "safe_stop";
    await setAgentStatus(tabId, finished ? "complete" : "stopped", reply.status === "safe_stop" ? "Stopped before sending" : finished ? "Goal reached" : "Test finished");
    finish(reply, steps, onProgress, evidenceWarning);
  } catch (e) {
    if (tabId) await setAgentStatus(tabId, "stopped", "The run needs attention");
    if (runId && await closeRun(runId, steps, onProgress, evidenceWarning, `the browser run failed: ${e instanceof Error ? e.message : String(e)}`.slice(0, 280))) return;
    onProgress({ phase: "error", steps, message: e instanceof Error ? e.message : String(e), evidenceWarning });
  }
}

async function closeRun(
  runId: string,
  steps: Step[],
  onProgress: (p: Progress) => void,
  evidenceWarning?: string,
  reason?: string,
): Promise<boolean> {
  try {
    const stopped = await stopRun(runId, reason);
    onProgress({ phase: "finished", steps: stopped.steps, status: "stopped", runId, evidenceWarning });
    return true;
  } catch {
    return false;
  }
}

/** Executes one step in the tab and returns a note for the agent, if any. */
async function act(tabId: number, step: Step, opts: RunOptions, origin: string): Promise<string | undefined> {
  if (step.action === "done" || step.action === "give_up") return;
  const base = { logged_in: opts.logged_in, verified: opts.verified };
  let confirmed = false;
  if (opts.sentOnce && step.action === "click") {
    const probe = await send<ExecResult>(tabId, { type: "act", step, opts: { ...base, dryRun: true } });
    if (probe.confirm === "send") return "a message was already sent in this run; Walkthru never sends twice";
  }
  if (step.action === "click" && (opts.logged_in || opts.verified)) {
    // Dry-run first. Ask the owner before a real message leaves a verified site, and before any
    // form submit on a logged-in page (SPEC safety rule).
    const probe = await send<ExecResult>(tabId, { type: "act", step, opts: { ...base, dryRun: true } });
    if (probe.note) return probe.note;
    if (probe.confirm === "send" || (opts.logged_in && probe.submits)) {
      const what = probe.confirm === "send" ? "send a real message from" : "submit a form on";
      if (!window.confirm(`The test user wants to ${what} ${origin}. Allow it?`)) return "the site owner declined this submit";
      confirmed = true;
      if (probe.confirm === "send") opts.sentOnce = true;
    }
  }
  const result = await send<ExecResult>(tabId, { type: "act", step, opts: { ...base, confirmed } });
  return result.note;
}

function finish(reply: RunReply, steps: Step[], onProgress: (p: Progress) => void, evidenceWarning?: string) {
  if (reply.status === "running") return;
  const last = reply.steps.at(-1);
  if (last && (last.action === "done" || last.action === "give_up") && steps.at(-1) !== last) steps.push(last);
  onProgress({ phase: "finished", steps, status: reply.status, runId: reply.run_id, evidenceWarning });
}
