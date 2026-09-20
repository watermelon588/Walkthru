export const AGENT_BIRD = {
  body: "M76 117c11 7 23 11 36 11 22 1 39-8 47-24 9-19 5-43 1-62l30-4q7-1 2-6L165 10c-12-10-28-9-37 1-8 9-9 21-13 32-10 26-23 49-38 65l-1 9Z",
  tail: "M96 126 40 42q-2-4-7-2L13 50q-6 3-2 9c18 22 41 44 65 58l18 9Z",
  frontLeg: "M108 115 97 158 72 169 56 189M72 169l-5 20m5-20 5 18m-5-18-13 11",
  backLeg: "M124 115 146 155l6 29m0 0-1 12m1-12 11 10m-11-10 17 5",
} as const;

export type AgentState = "ready" | "observing" | "acting" | "complete" | "stopped";

export const AGENT_TONE: Record<AgentState, string> = {
  ready: "var(--ink)",
  observing: "var(--accent)",
  acting: "var(--ink)",
  complete: "var(--accent)",
  stopped: "var(--danger)",
};
