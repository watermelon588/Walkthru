/** Runs one PersonaStep inside the page. Returns a note for the agent when something went wrong. */

import { findById } from "./snapshot";
import { isDangerous } from "./safety";

export type Step = {
  thought: string;
  action: "click" | "type" | "scroll" | "back" | "done" | "give_up";
  target_id: number | null;
  text: string | null;
  confusion: number;
};

export type ExecResult = { ok: boolean; note?: string; submits?: boolean };

/** True when the element would submit a form (needs user confirmation on logged-in pages). */
export function submits(el: Element): boolean {
  const form = el.closest("form");
  if (!form) return false;
  if (el.tagName === "BUTTON") return (el as HTMLButtonElement).type !== "button";
  if (el.tagName === "INPUT") return ["submit", "image"].includes((el as HTMLInputElement).type);
  return false;
}

export type ExecOptions = { logged_in?: boolean; dryRun?: boolean };

/** dryRun reports what would happen (safe-mode block, form submit) without touching the page. */
export function execute(step: Step, doc: Document = document, opts: ExecOptions = {}): ExecResult {
  const win = doc.defaultView!;
  switch (step.action) {
    case "scroll":
      if (!opts.dryRun) win.scrollBy({ top: win.innerHeight * 0.8, behavior: "instant" as ScrollBehavior });
      return { ok: true };
    case "back":
      if (!opts.dryRun) win.history.back();
      return { ok: true };
    case "click":
    case "type": {
      const el = step.target_id == null ? null : findById(doc, step.target_id);
      if (!el) return { ok: false, note: `element #${step.target_id} not found` };
      const text = (el as HTMLElement).innerText ?? el.textContent ?? "";
      if (opts.logged_in && isDangerous(text)) return { ok: false, note: `blocked by safe mode: "${text.trim().slice(0, 40)}"` };
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
  return { ok: true };
}
