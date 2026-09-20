type SidePanelOpener = {
  open(options: { tabId: number }): Promise<void>;
};

/** Opening from chrome.action.onClicked gives activeTab to the tested tab. */
export async function openSidePanelForTab(
  tab: Pick<chrome.tabs.Tab, "id">,
  sidePanel: SidePanelOpener = chrome.sidePanel,
): Promise<void> {
  if (tab.id == null) return;
  await sidePanel.open({ tabId: tab.id });
}
