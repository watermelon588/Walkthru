export default defineBackground(() => {
  // Clicking the toolbar icon opens the side panel. The step loop lives in the panel, not here
  // (Chrome suspends this worker after ~30 s idle).
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(() => {});
});
