import axe from "axe-core";
import { collectBrowserDiagnostics, summarizeAxeResults, type VitalState } from "../lib/diagnostics";

test("summarizes and caps axe violations for the wire payload", () => {
  const violations = Array.from({ length: 14 }, (_, index) => ({
    id: `rule-${index}`,
    impact: index === 0 ? "critical" : index === 1 ? "serious" : "minor",
    help: `Fix rule ${index}`,
    nodes: [{ target: [`#field-${index}`] }],
  }));

  const summary = summarizeAxeResults(violations);

  expect(summary.total).toBe(14);
  expect(summary.issues).toHaveLength(12);
  expect(summary.issues[0]).toEqual({
    rule: "rule-0",
    severity: "high",
    message: "Fix rule 0",
    target: "#field-0",
  });
  expect(summary.issues[2]!.severity).toBe("low");
});

test("vital state starts empty and stays serializable", () => {
  const state: VitalState = {};
  expect(JSON.stringify(state)).toBe("{}");
});

test("runs axe against the rendered page and preserves observed vitals", async () => {
  const canvasContext = vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
  document.documentElement.lang = "en";
  document.title = "Signup";
  document.body.innerHTML = '<main><h1>Create account</h1><input id="email"></main>';

  const diagnostics = await collectBrowserDiagnostics(document, { lcp_ms: 1200, cls: 0.02 });

  expect(diagnostics.accessibility.status).toBe("complete");
  expect(diagnostics.accessibility.issues.some((issue) => issue.rule === "label")).toBe(true);
  expect(diagnostics.web_vitals).toEqual({ lcp_ms: 1200, cls: 0.02 });
  canvasContext.mockRestore();
});

test("audits each address once and never waits past the time budget", async () => {
  const canvasContext = vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
  const run = vi.spyOn(axe, "run");
  history.pushState({}, "", "/slow-page");
  run.mockReturnValueOnce(new Promise(() => {}) as never); // an audit that never finishes
  const started = Date.now();
  const slow = await collectBrowserDiagnostics(document, {}, 50);
  expect(slow.accessibility.status).toBe("unavailable");
  expect(Date.now() - started).toBeLessThan(1000);

  history.pushState({}, "", "/form-page");
  const first = await collectBrowserDiagnostics(document, {});
  const second = await collectBrowserDiagnostics(document, {});
  expect(second.accessibility).toEqual(first.accessibility);
  expect(run).toHaveBeenCalledTimes(2); // slow page once, form page once (second call was cached)
  run.mockRestore();
  canvasContext.mockRestore();
});
