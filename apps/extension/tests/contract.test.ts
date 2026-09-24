/** Snapshot -> API contract. Runs only when the API (:8010) and fixtures (:8101) are up and
 *  WALKTHRU_TOKEN holds a Supabase access token (see apps/api/scripts/test_user.py).
 *  Start the "api" and "fixtures" launch configs, then: WALKTHRU_TOKEN=... npx vitest run tests/contract.test.ts */

import { JSDOM } from "jsdom";
import { snapshot } from "../lib/snapshot";

const API = "http://127.0.0.1:8010";
const EASY = "http://127.0.0.1:8101";

async function up(url: string) {
  try {
    return (await fetch(url)).ok;
  } catch {
    return false;
  }
}

const TOKEN = process.env.WALKTHRU_TOKEN;
const live = !!TOKEN && (await up(API + "/health")) && (await up(EASY + "/"));

describe.skipIf(!live)("snapshot of the easy fixture drives the live persona API", () => {
  test("first action targets an element the snapshot numbered", async () => {
    const html = await (await fetch(EASY + "/")).text();
    const dom = new JSDOM(html, { url: EASY + "/" });
    const obs = snapshot(dom.window.document, { geometry: false });
    expect(obs.elements.some((e) => /sign up|create/i.test(e.text))).toBe(true);

    const res = await fetch(API + "/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${TOKEN}` },
      body: JSON.stringify({ site: EASY, goal: "create an account", persona: "first_timer", logged_in: false, max_steps: 3, observation: obs }),
    });
    expect(res.status).toBe(200);
    const reply = await res.json();
    expect(reply.status).toBe("running");
    expect(["click", "type", "scroll", "back"]).toContain(reply.action.action);
    if (reply.action.target_id != null) {
      expect(obs.elements.map((e) => e.id)).toContain(reply.action.target_id);
    }
  }, 60_000);
});
