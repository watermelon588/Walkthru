import { describe, expect, test, vi } from "vitest";
import { openSidePanelForTab } from "../lib/side-panel";

describe("toolbar side panel launch", () => {
  test("opens a tab-scoped panel from the toolbar invocation", async () => {
    const open = vi.fn().mockResolvedValue(undefined);

    await openSidePanelForTab({ id: 42 }, { open });

    expect(open).toHaveBeenCalledWith({ tabId: 42 });
  });

  test("does nothing when Chrome does not provide a tab id", async () => {
    const open = vi.fn().mockResolvedValue(undefined);

    await openSidePanelForTab({}, { open });

    expect(open).not.toHaveBeenCalled();
  });
});
