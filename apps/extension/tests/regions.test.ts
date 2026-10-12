import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { captureStepEvidence } from "../lib/evidence";
import { issueRegions } from "../lib/snapshot";

vi.mock("../lib/api", async (orig) => ({ ...(await orig<typeof import("../lib/api")>()), uploadEvidenceImage: vi.fn().mockResolvedValue(undefined) }));

// R-S19: error boxes are measured in the captured viewport as fractions, clipped to it, boxes only (no page text).
const rects = new Map<string, DOMRect>();
const rect = (x: number, y: number, w: number, h: number) => ({ x, y, left: x, top: y, width: w, height: h, right: x + w, bottom: y + h, toJSON() {} }) as DOMRect;

beforeEach(() => {
  Object.defineProperty(window, "innerWidth", { value: 1000, configurable: true });
  Object.defineProperty(window, "innerHeight", { value: 500, configurable: true });
  vi.spyOn(Element.prototype, "getBoundingClientRect").mockImplementation(function (this: Element) {
    return rects.get(this.id) ?? rect(0, 0, 0, 0);
  });
});
afterEach(() => { vi.restoreAllMocks(); rects.clear(); document.body.innerHTML = ""; });

test("visible errors become boxes in viewport fractions, clipped to the frame", () => {
  document.body.innerHTML = `
    <p id="a" role="alert">Email is required</p>
    <p id="b" class="field-error">Password too short</p>
    <p id="c" role="alert">Below the fold</p>
    <p id="d" role="alert" style="display:none">Hidden</p>
    <p id="e" role="alert"></p>`;
  rects.set("a", rect(100, 50, 200, 25));
  rects.set("b", rect(900, 480, 300, 40)); // runs past the right and bottom edges
  rects.set("c", rect(100, 900, 200, 25)); // outside this frame
  rects.set("d", rect(0, 0, 100, 20));
  rects.set("e", rect(0, 0, 100, 20)); // no text: nothing to point at
  expect(issueRegions(document)).toEqual([
    { kind: "error", x: 0.1, y: 0.1, w: 0.2, h: 0.05 },
    { kind: "error", x: 0.9, y: 0.96, w: 0.1, h: 0.04 },
  ]);
  expect(JSON.stringify(issueRegions(document))).not.toMatch(/Email|Password/);
});

test("at most ten boxes, duplicates once", () => {
  document.body.innerHTML = Array.from({ length: 14 }, (_, i) => `<p id="r${i}" role="alert">Error ${i}</p>`).join("") + `<p id="dup" role="alert">Again</p>`;
  for (let i = 0; i < 14; i++) rects.set(`r${i}`, rect(0, i * 10, 50, 10));
  rects.set("dup", rect(0, 0, 50, 10));
  const got = issueRegions(document);
  expect(got).toHaveLength(10);
  expect(new Set(got.map((r) => `${r.x},${r.y}`)).size).toBe(10);
});

test("the saved evidence carries the boxes measured for that capture", async () => {
  vi.stubGlobal("chrome", { tabs: { captureVisibleTab: vi.fn().mockResolvedValue("data:image/jpeg;base64,AA") } });
  const regions = [{ kind: "error" as const, x: 0.1, y: 0.1, w: 0.2, h: 0.05 }];
  const evidence = await captureStepEvidence("a".repeat(32), 0, { windowId: 1, width: 1000, height: 500 } as chrome.tabs.Tab, "https://fixture.test/", undefined, undefined, regions);
  expect(evidence.regions).toEqual(regions);
  expect(await captureStepEvidence("a".repeat(32), 1, { windowId: 1, width: 1000, height: 500 } as chrome.tabs.Tab, "https://fixture.test/")).not.toHaveProperty("regions");
});
