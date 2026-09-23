import { findById, ID_ATTR, snapshot } from "../lib/snapshot";
import { execute } from "../lib/execute";

function page(html: string) {
  document.body.innerHTML = html;
  return snapshot(document, { geometry: false });
}

test("numbers visible interactive elements with labels", () => {
  const obs = page(`
    <nav><a href="/pricing">Pricing</a><a href="/login" hidden>Hidden</a></nav>
    <form>
      <label for="email">Email address</label><input id="email" type="email" value="me@secret.com">
      <input type="hidden" name="csrf" value="x">
      <button type="submit">Create account</button>
      <button disabled>Nope</button>
    </form>
    <div role="button" aria-label="Open menu"></div>`);
  expect(obs.elements).toEqual([
    { id: 1, tag: "a", text: "Pricing" },
    { id: 2, tag: "input", text: "Email address", type: "email" },
    { id: 3, tag: "button", text: "Create account" },
    { id: 4, tag: "div", text: "Open menu" },
  ]);
  expect(document.querySelector(`[${ID_ATTR}="3"]`)?.textContent).toBe("Create account");
  expect(obs.text).not.toContain("secret.com"); // input values are never in text
});

test("collects errors, redacts text, flags captcha", () => {
  const obs = page(`
    <p role="alert">Email jane@x.io already taken</p>
    <p class="field-error">Card 4111 1111 1111 1111 declined</p>
    <p>Reach us at help@x.io</p>
    <iframe src="https://www.google.com/recaptcha/api2/anchor"></iframe>`);
  expect(obs.errors).toEqual(["Email [email] already taken", "Card [number] declined"]);
  expect(obs.text).toContain("Reach us at [email]");
  expect(obs.note).toBe("captcha detected");
});

test("reaches into open shadow roots", () => {
  document.body.innerHTML = `<x-app></x-app>`;
  const host = document.querySelector("x-app")!;
  host.attachShadow({ mode: "open" }).innerHTML = `<button>Inside shadow</button>`;
  const obs = snapshot(document, { geometry: false });
  expect(obs.elements).toEqual([{ id: 1, tag: "button", text: "Inside shadow" }]);
  expect(findById(document, 1)?.textContent).toBe("Inside shadow");
});

test("does not inspect a closed agent-overlay shadow root", () => {
  document.body.innerHTML = `<button>Site action</button><walkthru-agent></walkthru-agent>`;
  const host = document.querySelector("walkthru-agent")!;
  host.attachShadow({ mode: "closed" }).innerHTML = `<button>Scout status</button>`;
  const obs = snapshot(document, { geometry: false });
  expect(obs.elements).toEqual([{ id: 1, tag: "button", text: "Site action" }]);
  expect(obs.text).not.toContain("Scout status");
});

test("execute: types into inputs, clicks, blocks dangerous clicks in safe mode", () => {
  page(`<form><input id="e" type="email"><button type="submit">Delete account</button></form><a href="#" id="a">Go</a>`);
  expect(execute({ thought: "", action: "type", target_id: 1, text: "a@b.co", confusion: 0 }, document)).toEqual({ ok: true });
  expect((document.getElementById("e") as HTMLInputElement).value).toBe("a@b.co");
  const click2 = { thought: "", action: "click" as const, target_id: 2, text: null, confusion: 0 };
  expect(execute(click2, document, { logged_in: true }).note).toMatch(/safe mode/);
  expect(execute(click2, document).note).toMatch(/safe mode/); // public page: a destructive button never fires either
  document.querySelector("button")!.textContent = "Create account";
  let clicked = 0;
  document.querySelector("button")!.addEventListener("click", (e) => { clicked++; e.preventDefault(); });
  expect(execute(click2, document, { dryRun: true })).toEqual({ ok: true, submits: true });
  expect(clicked).toBe(0); // dry run never touches the page
  expect(execute(click2, document)).toEqual({ ok: true, submits: true });
  expect(clicked).toBe(1);
  expect(execute({ ...click2, target_id: 9 }, document).note).toBe("element #9 not found");
});

test("execute: public pages block send buttons (including input values) but allow plain links", () => {
  page(`<form><input type="submit" value="Send message"></form><a href="#pricing">Buy now</a>`);
  const click = (id: number) => ({ thought: "", action: "click" as const, target_id: id, text: null, confusion: 0 });
  expect(execute(click(1), document).note).toMatch(/safe mode: "Send message"/);
  expect(execute(click(2), document)).toEqual({ ok: true, submits: false });
});

test("execute: mailto and tel links are reported as contact methods, never opened", () => {
  page(`<a href="mailto:owner@site.dev">Email me</a><a href="tel:+15550100">Call</a>`);
  let opened = 0;
  document.querySelectorAll("a").forEach((a) => a.addEventListener("click", (e) => { opened++; e.preventDefault(); }));
  const click = (id: number) => ({ thought: "", action: "click" as const, target_id: id, text: null, confusion: 0 });
  const email = execute(click(1), document);
  expect(email.note).toMatch(/opens an email app/);
  expect(email.note).not.toContain("owner@site.dev");
  expect(execute(click(2), document).note).toMatch(/phone call/);
  expect(opened).toBe(0);
});
