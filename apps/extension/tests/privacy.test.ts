/** What the privacy policy promises about the extension, checked on every test run (docs/agent-safety-plan.md
 *  section 12): it never reads the tested site's cookies or storage, and asks for no broad permissions. */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const ROOT = join(__dirname, "..");

function sources(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return sources(path);
    return /\.(ts|tsx)$/.test(name) ? [path] : [];
  });
}

const FORBIDDEN = [/chrome\.cookies/, /document\.cookie/, /\blocalStorage\b/, /\bsessionStorage\b/, /\bindexedDB\b/, /chrome\.history/, /chrome\.webRequest/];

test("the extension never touches cookies, page storage, history or network requests of the sites it tests", () => {
  const files = [...sources(join(ROOT, "lib")), ...sources(join(ROOT, "entrypoints"))];
  expect(files.length).toBeGreaterThan(10);
  for (const file of files) {
    const code = readFileSync(file, "utf-8").replace(/\/\*[\s\S]*?\*\/|\/\/.*$/gm, ""); // comments may name the APIs
    for (const api of FORBIDDEN) expect(code, `${file} uses ${api}`).not.toMatch(api);
  }
});

test("the manifest asks for no cookies, history or request access, and site access only per test", () => {
  const config = readFileSync(join(ROOT, "wxt.config.ts"), "utf-8");
  const permissions: string[] = JSON.parse(config.match(/permissions: (\[[^\]]*\])/)?.[1] ?? "[]");
  expect(permissions.sort()).toEqual(["activeTab", "scripting", "sidePanel", "storage", "tabs"]);
  expect(config).not.toMatch(/\bhost_permissions:/); // only optional_host_permissions, requested when a test starts
  expect(config).toMatch(/optional_host_permissions: \["<all_urls>"\]/);
});
