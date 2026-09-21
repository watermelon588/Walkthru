import axe from "axe-core";

const MAX_ISSUES = 12;

export type VitalState = {
  lcp_ms?: number;
  cls?: number;
  inp_ms?: number;
};

export type AccessibilityIssue = {
  rule: string;
  severity: "high" | "medium" | "low";
  message: string;
  target?: string;
};

export type BrowserDiagnostics = {
  captured_at: string;
  accessibility: {
    status: "complete" | "unavailable";
    total: number;
    issues: AccessibilityIssue[];
  };
  web_vitals: VitalState;
};

type AxeViolation = {
  id: string;
  impact?: string | null;
  help: string;
  nodes: Array<{ target: unknown[] }>;
};

function severity(impact?: string | null): AccessibilityIssue["severity"] {
  if (impact === "critical" || impact === "serious") return "high";
  if (impact === "moderate") return "medium";
  return "low";
}

function targetText(target: unknown[] | undefined): string | undefined {
  if (!target?.length) return undefined;
  const text = target
    .map((part) => Array.isArray(part) ? part.join(" ") : String(part))
    .join(" ")
    .slice(0, 300);
  return text || undefined;
}

export function summarizeAxeResults(violations: AxeViolation[]) {
  return {
    total: violations.length,
    issues: violations.slice(0, MAX_ISSUES).map((violation) => {
      const target = targetText(violation.nodes[0]?.target);
      return {
        rule: violation.id.slice(0, 100),
        severity: severity(violation.impact),
        message: violation.help.slice(0, 300),
        ...(target ? { target } : {}),
      };
    }),
  };
}

/** Runs WCAG A/AA checks in the actual rendered page, including open shadow roots. */
export async function collectBrowserDiagnostics(doc: Document, webVitals: VitalState): Promise<BrowserDiagnostics> {
  const capturedAt = new Date().toISOString();
  try {
    const result = await axe.run(doc.documentElement, {
      runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"] },
      resultTypes: ["violations"],
    });
    return {
      captured_at: capturedAt,
      accessibility: { status: "complete", ...summarizeAxeResults(result.violations) },
      web_vitals: webVitals,
    };
  } catch {
    return {
      captured_at: capturedAt,
      accessibility: { status: "unavailable", total: 0, issues: [] },
      web_vitals: webVitals,
    };
  }
}

type LayoutShiftEntry = PerformanceEntry & { value: number; hadRecentInput: boolean };
type EventTimingEntry = PerformanceEntry & { duration: number; interactionId: number };

/** Observes Core Web Vitals for the lifetime of the injected page script. */
export function observeWebVitals(): () => VitalState {
  const state: VitalState = {};
  const interactions = new Map<number, number>();
  let clsSessionValue = 0;
  let clsSessionStart = 0;
  let clsSessionLast = 0;

  const watch = (type: string, onEntries: (entries: PerformanceEntry[]) => void, extra: Record<string, unknown> = {}) => {
    try {
      const observer = new PerformanceObserver((list) => onEntries(list.getEntries()));
      observer.observe({ type, buffered: true, ...extra } as PerformanceObserverInit);
    } catch {
      // Unsupported entry types remain absent rather than reporting a false zero.
    }
  };

  watch("largest-contentful-paint", (entries) => {
    const latest = entries.at(-1);
    if (latest) state.lcp_ms = Math.round(latest.startTime);
  });
  watch("layout-shift", (entries) => {
    for (const entry of entries as LayoutShiftEntry[]) {
      if (entry.hadRecentInput) continue;
      const newSession = entry.startTime - clsSessionLast > 1000 || entry.startTime - clsSessionStart > 5000;
      if (newSession) {
        clsSessionValue = entry.value;
        clsSessionStart = entry.startTime;
      } else {
        clsSessionValue += entry.value;
      }
      clsSessionLast = entry.startTime;
      state.cls = Math.round(Math.max(state.cls ?? 0, clsSessionValue) * 1000) / 1000;
    }
  });
  watch("event", (entries) => {
    for (const entry of entries as EventTimingEntry[]) {
      if (!entry.interactionId) continue;
      interactions.set(entry.interactionId, Math.max(interactions.get(entry.interactionId) ?? 0, entry.duration));
    }
  }, { durationThreshold: 40 });

  return () => {
    const durations = [...interactions.values()].sort((a, b) => b - a);
    if (durations.length) {
      const percentileIndex = Math.min(durations.length - 1, Math.floor(durations.length / 50));
      state.inp_ms = Math.round(durations[percentileIndex]!);
    }
    return { ...state };
  };
}
