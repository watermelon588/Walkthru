import { openSidePanelForTab } from "../lib/side-panel";

export default defineBackground(() => {
  // Opening explicitly inside action.onClicked grants activeTab to this tab. Chrome's
  // openPanelOnActionClick shortcut opens the panel but does not reliably grant activeTab,
  // which makes tabs.captureVisibleTab fail even though the user invoked the extension.
  chrome.action.onClicked.addListener((tab) => {
    void openSidePanelForTab(tab).catch((error) => console.error("Could not open Walkthru", error));
  });

  // The dashboard (externally_connectable origins only) hands us the signed-in session.
  chrome.runtime.onMessageExternal.addListener((msg, _sender, reply) => {
    if (msg?.type === "session" && msg.session?.access_token && msg.session?.refresh_token) {
      chrome.storage.local.set({ session: msg.session }).then(() => reply({ ok: true }));
      return true;
    }
    reply({ ok: false });
  });
});
