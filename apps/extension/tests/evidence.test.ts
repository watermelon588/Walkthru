import { describe, expect, test } from "vitest";
import { evidencePath, shouldCaptureEvidence } from "../lib/evidence";
import type { Step } from "../lib/execute";
import type { Observation } from "../lib/snapshot";

const observation: Observation = {
  url: "https://fixture.test/signup",
  title: "Sign up",
  elements: [],
  text: "Create your account",
  errors: [],
};

function step(overrides: Partial<Step> = {}): Step {
  return { thought: "Continue", action: "click", target_id: 2, text: null, confusion: 0, ...overrides };
}

describe("screenshot evidence policy", () => {
  test("uses a run-scoped deterministic storage path", () => {
    expect(evidencePath("abc123", 0)).toBe("abc123/step-01.jpg");
    expect(evidencePath("abc123", 11)).toBe("abc123/step-12.jpg");
  });

  test("captures the first result and meaningful interactions", () => {
    expect(shouldCaptureEvidence(step(), observation, 0, 0)).toBe(true);
    expect(shouldCaptureEvidence(step({ action: "type" }), observation, 3, 2)).toBe(true);
    expect(shouldCaptureEvidence(step({ action: "scroll" }), observation, 3, 2)).toBe(false);
  });

  test("captures confusion and visible errors but respects the cap", () => {
    expect(shouldCaptureEvidence(step({ action: "scroll", confusion: 2 }), observation, 4, 2)).toBe(true);
    expect(shouldCaptureEvidence(step({ action: "scroll" }), { ...observation, errors: ["Email is required"] }, 4, 2)).toBe(true);
    expect(shouldCaptureEvidence(step(), observation, 8, 8)).toBe(false);
  });
});
