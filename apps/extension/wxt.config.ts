import { defineConfig } from "wxt";

export default defineConfig({
  modules: ["@wxt-dev/module-react"],
  manifest: {
    name: "Walkthru",
    description: "AI test users try your site's flows in your own browser and report where they get stuck.",
    permissions: ["activeTab", "sidePanel", "scripting", "tabs", "storage"],
    // Host access is requested per site when a test starts, never granted up front.
    optional_host_permissions: ["<all_urls>"],
    action: { default_title: "Open Walkthru" },
    // Only the dashboard may hand us a session (see background.ts).
    externally_connectable: { matches: ["http://localhost:5173/*"] },
  },
});
