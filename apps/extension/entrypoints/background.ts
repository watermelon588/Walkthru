export default defineBackground(() => {
  // Clicking the toolbar icon opens the side panel. The step loop lives in the panel, not here
  // (Chrome suspends this worker after ~30 s idle).
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(() => {});

  // The dashboard (externally_connectable origins only) hands us the signed-in session.
  chrome.runtime.onMessageExternal.addListener((msg, _sender, reply) => {
    if (msg?.type === "session" && msg.session?.access_token && msg.session?.refresh_token) {
      chrome.storage.local.set({ session: msg.session }).then(() => reply({ ok: true }));
      return true;
    }
    reply({ ok: false });
  });
});
