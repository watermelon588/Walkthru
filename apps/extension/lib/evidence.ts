import { uploadEvidenceImage, type StepEvidence } from "./api";
import type { Step } from "./execute";
import type { Observation } from "./snapshot";

export const MAX_SCREENSHOTS = 8;

export function evidencePath(runId: string, stepIndex: number): string {
  return `${runId}/step-${String(stepIndex + 1).padStart(2, "0")}.jpg`;
}

export function shouldCaptureEvidence(
  step: Step,
  observation: Observation,
  stepIndex: number,
  capturedCount: number,
): boolean {
  if (capturedCount >= MAX_SCREENSHOTS) return false;
  if (stepIndex === 0 || step.confusion >= 2 || observation.errors.length > 0) return true;
  return step.action === "click" || step.action === "type" || step.action === "back";
}

export async function captureStepEvidence(
  runId: string,
  stepIndex: number,
  tab: chrome.tabs.Tab,
  resultUrl: string,
  note?: string,
): Promise<StepEvidence> {
  const screenshotPath = evidencePath(runId, stepIndex);
  const image = await chrome.tabs.captureVisibleTab(tab.windowId, { format: "jpeg", quality: 72 });
  await uploadEvidenceImage(screenshotPath, image);
  return {
    screenshot_path: screenshotPath,
    captured_at: new Date().toISOString(),
    result_url: resultUrl,
    width: tab.width ?? 1,
    height: tab.height ?? 1,
    ...(note ? { note: note.slice(0, 300) } : {}),
  };
}
