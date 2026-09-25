import { loadEnv } from "vite";
import { defineConfig } from "wxt";

// Public half of the key that fixes the unpacked extension's id (cilngbcfpoojecjoiklimnjnomjglcdo) on every machine,
// so the dashboard's "Connect extension" reaches it (VITE_EXTENSION_ID in apps/web). Remove it for a Chrome Web Store
// upload: the store assigns its own id.
const KEY = "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEApJcLbI1lNMeyWFmvRDtK0GN9t3bfdsPRAQyDtllBsfOt98hpzCHr0P6i4AygZg7eyJCLB8oYHdkqVY4zzcfP/eiZYZCqRJ4UZmSeN/sYpN4KwGsGA5VZeEtgrGeF1y8gUsZCpMCjvrgxafh9ZqhcSB9iw9o9/SM6dlGNaI6IyDRze6kMOfXIVHEbJr/AnWBMfWnz9Q+Hxhau6zECQ7zuz5cHUEdySEC/voAhpHltkEIkBYiZ7hAxQd3x9vBn0Tl0kDo7vjV8Y4r34BFZYXHGEBANYeB85YeQFUFc3HVfk2WEcidQXQQTr/wR7xK9VrM7lZv00QWhvI5+LflMEqMo/wIDAQAB";

export default defineConfig({
  modules: ["@wxt-dev/module-react"],
  manifest: ({ mode }) => {
    const web = (loadEnv(mode, process.cwd()).VITE_WEB_URL ?? "http://localhost:5173").replace(/\/$/, "");
    return {
      name: "Walkthru",
      description: "AI test users try your site's flows in your own browser and report where they get stuck.",
      key: KEY,
      permissions: ["activeTab", "sidePanel", "scripting", "tabs", "storage"],
      // Host access is requested per site when a test starts, never granted up front.
      optional_host_permissions: ["<all_urls>"],
      action: { default_title: "Open Walkthru" },
      // Only the dashboard may hand us a session (see background.ts).
      externally_connectable: { matches: [`${web}/*`] },
    };
  },
});
