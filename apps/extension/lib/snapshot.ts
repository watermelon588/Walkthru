/** Page snapshot: what the persona agent sees. Mirrors app/agent/schema.py Observation. */

import { redact } from "./redact";

export type Element = { id: number; tag: string; text: string; type?: string };
export type Observation = {
  url: string;
  title: string;
  elements: Element[];
  text: string;
  errors: string[];
  note?: string;
};

export const ID_ATTR = "data-walkthru-id";
const INTERACTIVE = 'a[href], button, input, select, textarea, [role="button"], [role="link"], [role="tab"], [contenteditable="true"]';
const MAX_ELEMENTS = 120;
const MAX_LABEL = 80;
const MAX_TEXT = 6000;

type Opts = { geometry?: boolean }; // geometry=false for jsdom, which has no layout

/** Walks the document, including open shadow roots. */
function* walk(root: ParentNode): Generator<globalThis.Element> {
  for (const el of root.querySelectorAll("*")) {
    yield el;
    if (el.shadowRoot) yield* walk(el.shadowRoot);
  }
}

function visible(el: globalThis.Element, geometry: boolean): boolean {
  if (el.closest("[hidden]") || el.closest("[aria-hidden='true']")) return false;
  const cs = getComputedStyle(el);
  if (cs.display === "none" || cs.visibility === "hidden") return false;
  if (!geometry) return true;
  const r = el.getBoundingClientRect();
  return r.width > 0 && r.height > 0;
}

function label(el: globalThis.Element): string {
  const h = el as HTMLElement;
  const input = el as HTMLInputElement;
  const candidates = [
    h.getAttribute("aria-label"),
    el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT" ? labelFor(input) : null,
    input.placeholder,
    el.tagName === "INPUT" && ["submit", "button"].includes(input.type) ? input.value : null,
    h.innerText ?? h.textContent,
    el.querySelector("img[alt]")?.getAttribute("alt"),
    h.title,
  ];
  const text = (candidates.find((c) => c && c.trim()) ?? "").replace(/\s+/g, " ").trim();
  return text.slice(0, MAX_LABEL);
}

function labelFor(input: HTMLInputElement): string | null {
  const byFor = input.id ? input.ownerDocument.querySelector(`label[for="${CSS.escape(input.id)}"]`) : null;
  const el = byFor ?? input.closest("label");
  return el?.textContent ?? null;
}

function errors(doc: Document, geometry: boolean): string[] {
  const sel = '[role="alert"], [aria-invalid="true"], [aria-live="assertive"], .error, [class*="error"], [class*="invalid"]';
  const out = new Set<string>();
  for (const el of doc.querySelectorAll(sel)) {
    if (!visible(el, geometry)) continue;
    const t = ((el as HTMLElement).innerText ?? el.textContent ?? "").replace(/\s+/g, " ").trim();
    if (t && t.length <= 200) out.add(t);
  }
  return [...out].slice(0, 10);
}

function captcha(doc: Document): boolean {
  if (doc.querySelector('iframe[src*="recaptcha"], iframe[src*="hcaptcha"], iframe[src*="turnstile"], .g-recaptcha, .h-captcha')) return true;
  return /\bcaptcha\b/i.test(doc.body?.textContent ?? "");
}

export function snapshot(doc: Document = document, opts: Opts = {}): Observation {
  const geometry = opts.geometry ?? true;
  for (const el of doc.querySelectorAll(`[${ID_ATTR}]`)) el.removeAttribute(ID_ATTR);
  const elements: Element[] = [];
  for (const el of walk(doc)) {
    if (!el.matches(INTERACTIVE) || !visible(el, geometry)) continue;
    if ((el as HTMLInputElement).type === "hidden" || (el as HTMLButtonElement).disabled) continue;
    const id = elements.length + 1;
    el.setAttribute(ID_ATTR, String(id));
    const tag = el.tagName === "INPUT" ? "input" : el.tagName.toLowerCase();
    const type = el.tagName === "INPUT" ? (el as HTMLInputElement).type : undefined;
    elements.push({ id, tag, text: redact(label(el)), ...(type ? { type } : {}) });
    if (elements.length >= MAX_ELEMENTS) break;
  }
  const body = doc.body as HTMLElement | null;
  const text = redact((body?.innerText ?? body?.textContent ?? "").replace(/\s+/g, " ").trim().slice(0, MAX_TEXT));
  const obs: Observation = {
    url: doc.location?.href ?? "",
    title: doc.title,
    elements,
    text,
    errors: errors(doc, geometry).map(redact),
  };
  if (captcha(doc)) obs.note = "captcha detected";
  return obs;
}

export function findById(doc: Document, id: number): globalThis.Element | null {
  for (const el of walk(doc)) if (el.getAttribute(ID_ATTR) === String(id)) return el;
  return null;
}
