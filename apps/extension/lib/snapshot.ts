/** Page snapshot: what the persona agent sees. Mirrors app/agent/schema.py Observation. */

import { redact } from "./redact";
import type { BrowserDiagnostics } from "./diagnostics";

export type FieldState = "filled" | "empty" | "checked" | "unchecked";
export type Element = { id: number; tag: string; text: string; type?: string; state?: FieldState };
export type Observation = {
  url: string;
  title: string;
  elements: Element[];
  text: string;
  errors: string[];
  notices?: string[];
  note?: string;
  diagnostics?: BrowserDiagnostics;
  scroll_pct?: number; // how far down the page the viewport is, so scrolling reads as progress
  at_end?: boolean;
};

export const ID_ATTR = "data-walkthru-id";
const INTERACTIVE = 'a[href], button, input, select, textarea, summary, [role="button"], [role="link"], [role="tab"], [role="menuitem"], [role="checkbox"], [role="switch"], [role="option"], [contenteditable="true"]';
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

/** Whether a form field holds something, never what it holds (values are private). */
function fieldState(el: globalThis.Element): FieldState | undefined {
  if (el.tagName === "INPUT") {
    const input = el as HTMLInputElement;
    if (input.type === "checkbox" || input.type === "radio") return input.checked ? "checked" : "unchecked";
    if (["submit", "button", "image", "reset", "hidden", "file"].includes(input.type)) return undefined;
    return input.value.trim() ? "filled" : "empty";
  }
  if (el.tagName === "TEXTAREA") return (el as HTMLTextAreaElement).value.trim() ? "filled" : "empty";
  if (el.tagName === "SELECT") return (el as HTMLSelectElement).value ? "filled" : "empty";
  return undefined;
}

function label(el: globalThis.Element): string {
  const h = el as HTMLElement;
  const input = el as HTMLInputElement;
  // Icon-only buttons (a heart, a share arrow) carry their name on an inner svg or img, or in aria-labelledby.
  const icon = el.querySelector("svg[aria-label], [role='img'][aria-label], img[alt]:not([alt=''])");
  const candidates = [
    h.getAttribute("aria-label"),
    labelledBy(el),
    el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT" ? labelFor(input) : null,
    input.placeholder,
    el.tagName === "INPUT" && ["submit", "button"].includes(input.type) ? input.value : null,
    h.innerText ?? h.textContent,
    icon?.getAttribute("aria-label") ?? icon?.getAttribute("alt"),
    el.querySelector("svg title")?.textContent,
    h.title || el.querySelector("[title]")?.getAttribute("title"),
    testId(el),
  ];
  const text = (candidates.find((c) => c && c.trim()) ?? "").replace(/\s+/g, " ").trim();
  return text.slice(0, MAX_LABEL);
}

function labelledBy(el: globalThis.Element): string | null {
  const ids = el.getAttribute("aria-labelledby")?.split(/\s+/).filter(Boolean) ?? [];
  const text = ids.map((id) => el.ownerDocument.getElementById(id)?.textContent ?? "").join(" ").trim();
  return text || null;
}

/** A last resort: "like-button" or "shareButton" in data-testid reads as "like button" or "share Button". */
function testId(el: globalThis.Element): string | null {
  const id = el.getAttribute("data-testid") ?? el.querySelector("[data-testid]")?.getAttribute("data-testid");
  return id ? id.replace(/([a-z])([A-Z])/g, "$1 $2").replace(/[-_]+/g, " ") : null;
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

/** Visible confirmations ("Thanks! Your message was sent"), so the agent knows an action succeeded. */
function notices(doc: Document, geometry: boolean, errorsSeen: string[]): string[] {
  const sel = '[role="status"], [aria-live="polite"], .success, [class*="success"], [class*="toast"]';
  const out = new Set<string>();
  for (const el of doc.querySelectorAll(sel)) {
    if (!visible(el, geometry)) continue;
    const t = ((el as HTMLElement).innerText ?? el.textContent ?? "").replace(/\s+/g, " ").trim();
    if (t && t.length <= 200 && !errorsSeen.includes(t)) out.add(t);
  }
  return [...out].slice(0, 5);
}

/** A bot wall: the site's protection stepped in before any page (Cloudflare "Just a moment", Akamai "Access Denied",
 *  DataDome, PerimeterX, a bare 403 or 429 page). Walkthru stops and hands over to the person; it never solves one. */
export function botWall(doc: Document): boolean {
  const title = (doc.title ?? "").trim().toLowerCase();
  if (/^(just a moment|attention required|access denied|please wait|403 forbidden|429 too many requests|pardon our interruption)\b/.test(title)) return true;
  if (doc.querySelector('#challenge-running, #challenge-form, #cf-challenge-running, iframe[src*="challenges.cloudflare.com"], iframe[src*="captcha-delivery.com"], #px-captcha, script[src*="perimeterx"]')) return true;
  const text = (doc.body?.textContent ?? "").slice(0, 3000);
  return /\b(verify you are (a )?human|checking (if the site connection is secure|your browser)|enable javascript and cookies to continue)\b/i.test(text)
    || (/\baccess denied/i.test(text) && /reference\s*#/i.test(text)); // textContent runs words together across tags
}

function captcha(doc: Document): boolean {
  if (doc.querySelector('iframe[src*="recaptcha"], iframe[src*="hcaptcha"], iframe[src*="turnstile"], .g-recaptcha, .h-captcha')) return true;
  return /\bcaptcha\b/i.test(doc.body?.textContent ?? "");
}

export function snapshot(doc: Document = document, opts: Opts = {}): Observation {
  const geometry = opts.geometry ?? true;
  for (const el of doc.querySelectorAll(`[${ID_ATTR}]`)) el.removeAttribute(ID_ATTR);
  const elements: Element[] = [];
  for (const el of ordered(doc, geometry)) {
    const id = elements.length + 1;
    el.setAttribute(ID_ATTR, String(id));
    const tag = el.tagName === "INPUT" ? "input" : el.tagName.toLowerCase();
    const type = el.tagName === "INPUT" ? (el as HTMLInputElement).type : undefined;
    const state = fieldState(el);
    elements.push({ id, tag, text: redact(label(el)), ...(type ? { type } : {}), ...(state ? { state } : {}) });
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
  const win = doc.defaultView;
  if (geometry && win) {
    const room = (doc.scrollingElement ?? doc.documentElement).scrollHeight - win.innerHeight;
    obs.scroll_pct = room <= 0 ? 100 : Math.min(100, Math.max(0, Math.round((100 * win.scrollY) / room)));
    obs.at_end = room <= 0 || win.scrollY >= room - 4;
  }
  const confirmations = notices(doc, geometry, obs.errors).map(redact);
  if (confirmations.length) obs.notices = confirmations;
  if (botWall(doc)) obs.note = "bot wall detected";
  else if (captcha(doc)) obs.note = "captcha detected";
  return obs;
}

const SCAN_LIMIT = 800; // candidates read before ordering; long feeds hold thousands of controls

/** Interactive elements as a person meets them: what is on screen top to bottom, then the next screen down, then
 *  what is above, then the rest. Without layout (jsdom) the document order stays. */
function ordered(doc: Document, geometry: boolean): globalThis.Element[] {
  const found: globalThis.Element[] = [];
  for (const el of walk(doc)) {
    if (!el.matches(INTERACTIVE) || !visible(el, geometry)) continue;
    if ((el as HTMLInputElement).type === "hidden" || (el as HTMLButtonElement).disabled) continue;
    found.push(el);
    if (found.length >= SCAN_LIMIT) break;
  }
  const win = doc.defaultView;
  if (!geometry || !win) return found;
  const height = win.innerHeight;
  const band = (top: number, bottom: number) => (bottom > 0 && top < height ? 0 : top >= height && top < 2 * height ? 1 : bottom <= 0 ? 2 : 3);
  return found
    .map((el, index) => {
      const r = el.getBoundingClientRect();
      return { el, index, band: band(r.top, r.bottom), top: r.top };
    })
    .sort((a, b) => a.band - b.band || (a.band === 2 ? b.top - a.top : a.top - b.top) || a.index - b.index)
    .map((c) => c.el);
}

/** Resolves once the page has stopped changing for `quietMs`, or after `maxMs`, so lazy feeds and menus have
 *  rendered before the next snapshot. */
export function settle(doc: Document = document, quietMs = 300, maxMs = 2000): Promise<void> {
  return new Promise((resolve) => {
    let timer = window.setTimeout(done, quietMs);
    const cap = window.setTimeout(done, maxMs);
    const observer = new MutationObserver(() => {
      window.clearTimeout(timer);
      timer = window.setTimeout(done, quietMs);
    });
    observer.observe(doc.documentElement, { childList: true, subtree: true, attributes: true, characterData: true });
    function done() {
      observer.disconnect();
      window.clearTimeout(timer);
      window.clearTimeout(cap);
      resolve();
    }
  });
}

export function findById(doc: Document, id: number): globalThis.Element | null {
  for (const el of walk(doc)) if (el.getAttribute(ID_ATTR) === String(id)) return el;
  return null;
}
