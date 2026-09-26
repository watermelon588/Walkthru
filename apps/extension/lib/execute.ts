/** Runs one PersonaStep inside the page. Returns a note for the agent when something went wrong. */

import { findById } from "./snapshot";
import { isBasket, isCommerce, isDestructive, isSearchField, isSearchForm, isSending, isSocial } from "./safety";

export type Step = {
  thought: string;
  action: "click" | "type" | "scroll" | "back" | "done" | "give_up";
  target_id: number | null;
  text: string | null;
  confusion: number;
};

/** confirm: "send" means the owner must approve in the side panel before this click runs for real. */
export type ExecResult = { ok: boolean; note?: string; submits?: boolean; confirm?: "send" };

/** True when the element would submit a form (needs user confirmation on logged-in pages). */
export function submits(el: Element): boolean {
  // `.form` is the form owner, which also covers buttons outside the form linked with form="id".
  if (el.tagName === "BUTTON") {
    const button = el as HTMLButtonElement;
    return !!button.form && button.type !== "button" && button.type !== "reset";
  }
  if (el.tagName === "INPUT") {
    const input = el as HTMLInputElement;
    return !!input.form && ["submit", "image"].includes(input.type);
  }
  return false;
}

const APP_LINKS: Record<string, string> = { mailto: "an email app", tel: "a phone call", sms: "a text message" };

/** verified: the owner proved control of this domain. confirmed: the owner approved this exact send. */
export type ExecOptions = { logged_in?: boolean; dryRun?: boolean; verified?: boolean; confirmed?: boolean };

/** dryRun reports what would happen (safe-mode block, form submit) without touching the page. */
export function execute(step: Step, doc: Document = document, opts: ExecOptions = {}): ExecResult {
  const win = doc.defaultView!;
  switch (step.action) {
    case "scroll":
      if (!opts.dryRun) {
        // One screen down, the way a person scrolls; the next snapshot waits for lazy content to settle (snapshot.settle).
        const reduce = win.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
        win.scrollBy({ top: win.innerHeight * 0.85, behavior: (reduce ? "instant" : "smooth") as ScrollBehavior });
      }
      return { ok: true };
    case "back":
      if (!opts.dryRun) win.history.back();
      return { ok: true };
    case "click":
    case "type": {
      const el = step.target_id == null ? null : findById(doc, step.target_id);
      if (!el) return { ok: false, note: `element #${step.target_id} not found` };
      const input = el as HTMLInputElement;
      const text = [(el as HTMLElement).innerText ?? el.textContent, el.tagName === "INPUT" ? input.value : "", el.getAttribute("aria-label")].filter(Boolean).join(" ");
      // Mirrors _enforce in app/agent/persona.py. Plain links only navigate, so they stay allowed.
      const button = step.action === "click" && el.tagName !== "A";
      const shown = text.trim().slice(0, 40);
      if (isDestructive(text) && (opts.logged_in || button)) return { ok: false, note: `blocked by safe mode: "${shown}"` };
      if (button && isSending(text)) {
        if (!opts.verified) return { ok: false, note: `not sent: "${shown}" only fires on a domain the owner has verified` };
        if (opts.dryRun) return { ok: true, submits: submits(el), confirm: "send" };
        if (!opts.confirmed) return { ok: false, note: `not sent: the owner has not approved "${shown}"` };
      }
      if (!opts.verified) {
        // Visitor mode, mirroring persona._enforce: the server never asks for these; this is a second wall in the page.
        if (step.action === "type" && !isSearchField(el)) return { ok: false, note: `not typed: visitor mode only uses the site's search box ("${shown}")` };
        const acts = el.tagName !== "A" || isBasket(text);
        if (step.action === "click" && acts && (isSocial(text) || isCommerce(text))) {
          return { ok: false, note: `not pressed: visitor mode never likes, follows, posts, buys or adds to a cart ("${shown}")` };
        }
        if (step.action === "click" && submits(el) && !isSearchForm((el as HTMLButtonElement).form)) {
          return { ok: false, note: `not submitted: visitor mode only submits the site's search ("${shown}")` };
        }
      }
      const scheme = el.tagName === "A" ? ((el.getAttribute("href") ?? "").split(":")[0] ?? "").toLowerCase() : "";
      if (step.action === "click" && APP_LINKS[scheme]) {
        // Opening a mail or phone app is a real side effect and gives the agent nothing to observe.
        return { ok: true, note: `this link opens ${APP_LINKS[scheme]}; it is a working contact method, so Walkthru did not open it` };
      }
      const willSubmit = step.action === "click" && submits(el);
      if (opts.dryRun) return { ok: true, submits: willSubmit };
      (el as HTMLElement).scrollIntoView?.({ block: "center", behavior: "instant" as ScrollBehavior });
      if (step.action === "type") return type(el as HTMLElement, step.text ?? "");
      (el as HTMLElement).click();
      return { ok: true, submits: willSubmit };
    }
    default:
      return { ok: true };
  }
}

function type(el: HTMLElement, value: string): ExecResult {
  const input = el as HTMLInputElement;
  if (el.isContentEditable) {
    el.focus();
    el.textContent = value;
    el.dispatchEvent(new Event("input", { bubbles: true }));
    return { ok: true };
  }
  if (!("value" in input)) return { ok: false, note: "element is not an input" };
  input.focus();
  // React and Vue listen for native setters, so set through the prototype descriptor.
  const proto = el.tagName === "TEXTAREA" ? HTMLTextAreaElement.prototype : el.tagName === "SELECT" ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
  const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
  if (setter) setter.call(input, value);
  else input.value = value;
  input.dispatchEvent(new Event("input", { bubbles: true }));
  input.dispatchEvent(new Event("change", { bubbles: true }));
  // Controlled inputs can reject a value (masks, maxlength, select without that option). Say so.
  if (input.value !== value) return { ok: false, note: "the field did not keep the typed text" };
  return { ok: true };
}
