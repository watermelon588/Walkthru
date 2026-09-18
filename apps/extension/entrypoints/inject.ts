/** Injected into the tab under test by the side panel (chrome.scripting.executeScript).
 *  An unlisted script rather than a content script so the manifest carries no host_permissions;
 *  access is requested per site when a test starts. */

import { snapshot } from "../lib/snapshot";
import { execute, type ExecOptions, type Step } from "../lib/execute";

export type ContentRequest = { type: "snapshot" } | { type: "act"; step: Step; opts: ExecOptions } | { type: "ping" };

declare global {
  interface Window { __walkthru?: true }
}

export default defineUnlistedScript(() => {
  if (window.__walkthru) return; // already injected on this page
  window.__walkthru = true;
  chrome.runtime.onMessage.addListener((msg: ContentRequest, _sender, reply) => {
    if (msg.type === "ping") reply({ ok: true });
    else if (msg.type === "snapshot") reply(snapshot());
    else if (msg.type === "act") reply(execute(msg.step, document, msg.opts));
    return true;
  });
});
