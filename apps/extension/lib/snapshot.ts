/** Page snapshot: what the persona agent sees. Mirrors app/agent/schema.py Observation. */

import { redact } from "./redact";
import type { BrowserDiagnostics } from "./diagnostics";

export type FieldState = "filled" | "empty" | "checked" | "unchecked";
export type Element = { id: number; tag: string; text: string; type?: string; state?: FieldState; region?: string; row?: string; in_view?: boolean; occluded?: boolean; scroll_container_id?: number };
export type ScrollPosition = { top: number; left: number };
export type ScrollContainer = ScrollPosition & { id: number; label: string; scroll_height: number; client_height: number; scroll_width: number; client_width: number; in_view?: boolean; occluded?: boolean; at_start: boolean; at_end: boolean; can_up: boolean; can_down: boolean; can_left: boolean; can_right: boolean };
export type ExecutorResult = { action: 'scroll' | 'wait'; status: 'moved' | 'no_progress' | 'settled' | 'changed' | 'timeout' | 'aborted'; container_id?: number; before?: ScrollPosition; after?: ScrollPosition; elapsed_ms?: number };
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
  revision?: string;
  elements_truncated?: boolean;
  candidate_limit_reached?: boolean;
  omitted_elements?: number; // lower bound when the candidate limit is reached
  context_truncated?: boolean;
  navigation_version?: number;
  scroll_containers?: ScrollContainer[];
  scroll_containers_truncated?: boolean;
  executor_result?: ExecutorResult;
};

export const ID_ATTR = "data-walkthru-id";
const INTERACTIVE = 'a[href], button, input, select, textarea, summary, [role="button"], [role="link"], [role="tab"], [role="menuitem"], [role="checkbox"], [role="switch"], [role="option"], [contenteditable="true"]';
const MAX_ELEMENTS = 120;
const MAX_LABEL = 80;
const MAX_TEXT = 6000;

type Opts = { geometry?: boolean }; // geometry=false for jsdom, which has no layout

type Captured = { el: globalThis.Element; ancestors: globalThis.Element[]; semantic: string; form: HTMLFormElement | null };
type CapturedScroll = { el: globalThis.Element; ancestors: globalThis.Element[]; name: string; overflow: string };
type Registry = { revision: string; url: string; geometry: boolean; targets: Map<number, Captured>; scrolls: Map<number, CapturedScroll>; state?: PublicState };
// References and full raw semantics stay in this document's memory, never in an Observation.
const registries = new WeakMap<Document, Registry>();
const CONTEXT_LIMIT = 6000;
const REGION = 'dialog, [role="dialog"], main, nav, aside, form, section, [role="region"], [role="main"], [role="navigation"]';
const ROW = 'tr, [role="row"], li, [role="listitem"], article';
const PRIVATE_TEXT = 'input, textarea, select, [contenteditable]:not([contenteditable="false"]), script, style, [hidden], [aria-hidden="true"], [inert]';

function parent(el: globalThis.Element): globalThis.Element | null {
  const root = el.getRootNode();
  return el.parentElement ?? (root.nodeType === 11 ? (root as ShadowRoot).host : null);
}

function ancestors(el: globalThis.Element): globalThis.Element[] {
  const out: globalThis.Element[] = [];
  for (let node = parent(el); node; node = parent(node)) out.push(node);
  return out;
}

/** Excludes editable values even when textContent (rather than innerText) is needed. */
function safeText(el: globalThis.Element, memo?: WeakMap<globalThis.Element, boolean>, budget?: { chars: number; nodes: number }): string {
  if (!visible(el, false, memo)) return '';
  const parts: string[] = [];
  function read(node: globalThis.Element) {
    if (budget && (budget.chars <= 0 || budget.nodes-- <= 0)) return;
    if (node.matches(PRIVATE_TEXT)) return;
    if (!shown(node, memo)) return;
    for (const child of node.childNodes) {
      if (budget && (budget.chars <= 0 || budget.nodes <= 0)) break;
      if (child.nodeType === 3) {
        const text = (child.textContent ?? '').slice(0, budget?.chars);
        parts.push(text);
        if (budget) budget.chars -= text.length;
      }
      else if (child.nodeType === 1) read(child as globalThis.Element);
    }
    if (node.matches('td,th,button,p,div,li,br')) parts.push(' ');
  }
  read(el);
  return parts.join('').replace(/\s+/g, ' ').trim();
}

function closest(el: globalThis.Element, selector: string): globalThis.Element | undefined {
  return [el, ...ancestors(el)].find(node => node.matches(selector));
}

function context(el: globalThis.Element, memo?: WeakMap<globalThis.Element, boolean>): { region: string; row: string } {
  const area = closest(el, REGION);
  const heading = area?.querySelector('h1,h2,h3,h4,h5,h6');
  const name = area ? area.getAttribute('aria-label') || labelledBy(area, memo) || (heading ? safeText(heading, memo) : '') : '';
  // Unnamed broad containers don't contribute all their page text as a region label.
  const named = area && name;
  return { region: named ? `${area!.getAttribute('role') || area!.tagName.toLowerCase()}: ${name}` : '', row: safeText(closest(el, ROW) ?? el, memo) };
}

function formOwner(el: globalThis.Element): HTMLFormElement | null {
  return (el as HTMLInputElement).form ?? null;
}

function semantic(el: globalThis.Element, memo?: WeakMap<globalThis.Element, boolean>): string {
  const attrs = ['href','type','role','aria-label','aria-labelledby','aria-disabled','name','placeholder','form','formaction','formmethod','formtarget','target','download','contenteditable'];
  const form = formOwner(el);
  return JSON.stringify([el.tagName, label(el, memo), context(el, memo), fieldState(el), attrs.map(attr => el.getAttribute(attr)), el.tagName === 'A' ? (el as HTMLAnchorElement).href : null, form ? [form.action, form.method, form.target] : null]);
}

function unavailable(el: globalThis.Element, geometry: boolean): boolean {
  return !el.isConnected || !visible(el, geometry) || disabled(el);
}

function disabled(el: globalThis.Element): boolean {
  return el.matches(':disabled') || [el, ...ancestors(el)].some(node => node.getAttribute('aria-disabled') === 'true');
}

function within(el: globalThis.Element, container: globalThis.Element): boolean {
  return el === container || ancestors(el).includes(container);
}

function modal(doc: Document): globalThis.Element | null {
  return [...walk(doc)].filter(el => (el.matches('[aria-modal="true"]') || el.matches(':modal')) && visible(el, false)).at(-1) ?? null;
}

function geometryState(el: globalThis.Element, active: globalThis.Element | null): { in_view: boolean; occluded?: boolean } {
  const doc = el.ownerDocument;
  const win = doc.defaultView!;
  const r = el.getBoundingClientRect();
  const left = Math.max(0, r.left), right = Math.min(win.innerWidth, r.right);
  const top = Math.max(0, r.top), bottom = Math.min(win.innerHeight, r.bottom);
  const in_view = right > left && bottom > top;
  if (active && !within(el, active)) return { in_view, occluded: true };
  if (!in_view || typeof doc.elementFromPoint !== 'function') return { in_view };
  // MDN elementFromPoint returns the topmost hit, including hosts of shadow roots.
  const x = (left + right) / 2, y = (top + bottom) / 2;
  let hit = doc.elementFromPoint(x, y);
  while (hit?.shadowRoot) {
    const root = hit.shadowRoot as ShadowRoot & { elementFromPoint?: (x: number, y: number) => globalThis.Element | null };
    if (!root.elementFromPoint) break; // nonstandard API: never assume a host proves its inner control is hittable
    const inner = root.elementFromPoint(x, y);
    if (!inner || inner === hit) break;
    hit = inner;
  }
  return { in_view, occluded: !hit || !within(hit, el) };
}

/** Rechecks captured identity and observable semantics immediately before dispatch. */
export function resolveTarget(doc: Document, id: number | null, revision?: string | null, requireInView = false): { el?: globalThis.Element; note?: string } {
  const registry = registries.get(doc);
  const reject = (why: string) => ({ note: `stale target: ${why}. Read the page again or update Walkthru and restart the test` });
  if (!revision || !registry || registry.revision !== revision) return reject('the observation revision is missing or changed');
  const captured = id == null ? undefined : registry.targets.get(id);
  if (!captured) return reject(`element #${id} was not captured`);
  const el = captured.el;
  const chain = ancestors(el);
  if (registry.url !== doc.location.href || unavailable(el, registry.geometry) || captured.form !== formOwner(el)
    || chain.length !== captured.ancestors.length || chain.some((node, i) => node !== captured.ancestors[i]) || semantic(el) !== captured.semantic) return reject('the control or its context changed');
  const active = modal(doc);
  if (active && !within(el, active)) return reject('a dialog now covers the control');
  if (registry.geometry) {
    const state = geometryState(el, active);
    if (state.occluded === true || (requireInView && (!state.in_view || state.occluded !== false))) return reject('the control is covered or cannot be hit');
  }
  return { el };
}

/** Walks the document, including open shadow roots. */
function* walk(root: ParentNode): Generator<globalThis.Element> {
  const doc = root.nodeType === 9 ? root as Document : root.ownerDocument!;
  const walker = doc.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const el = node as globalThis.Element;
    yield el;
    if (el.shadowRoot) yield* walk(el.shadowRoot);
  }
}

function shown(el: globalThis.Element, memo?: WeakMap<globalThis.Element, boolean>): boolean {
  let result = memo?.get(el);
  if (result === undefined) {
    const cs = getComputedStyle(el);
    result = !el.matches('[hidden], [aria-hidden="true"], [inert]') && cs.display !== 'none' && cs.visibility !== 'hidden' && cs.visibility !== 'collapse' && cs.opacity !== '0';
    memo?.set(el, result);
  }
  return result;
}

function visible(el: globalThis.Element, geometry: boolean, memo?: WeakMap<globalThis.Element, boolean>): boolean {
  if ([el, ...ancestors(el)].some(node => !shown(node, memo))) return false;
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

function label(el: globalThis.Element, memo?: WeakMap<globalThis.Element, boolean>): string {
  const h = el as HTMLElement;
  const input = el as HTMLInputElement;
  // Icon-only buttons (a heart, a share arrow) carry their name on an inner svg or img, or in aria-labelledby.
  const icon = el.querySelector("svg[aria-label], [role='img'][aria-label], img[alt]:not([alt=''])");
  const candidates = [
    h.getAttribute("aria-label"),
    labelledBy(el, memo),
    el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT" ? labelFor(input, memo) : null,
    input.placeholder,
    el.tagName === "INPUT" && ["submit", "button"].includes(input.type) ? input.value : null,
    safeText(el, memo),
    icon?.getAttribute("aria-label") ?? icon?.getAttribute("alt"),
    el.querySelector("svg title")?.textContent,
    h.title || el.querySelector("[title]")?.getAttribute("title"),
    testId(el),
  ];
  const text = (candidates.find((c) => c && c.trim()) ?? "").replace(/\s+/g, " ").trim();
  return text;
}

function labelledBy(el: globalThis.Element, memo?: WeakMap<globalThis.Element, boolean>): string | null {
  const ids = el.getAttribute("aria-labelledby")?.split(/\s+/).filter(Boolean) ?? [];
  const scope = el.getRootNode() as Document | ShadowRoot;
  const text = ids.map((id) => { const node = scope.getElementById(id); return node ? safeText(node, memo) : ''; }).join(" ").trim();
  return text || null;
}

/** A last resort: "like-button" or "shareButton" in data-testid reads as "like button" or "share Button". */
function testId(el: globalThis.Element): string | null {
  const id = el.getAttribute("data-testid") ?? el.querySelector("[data-testid]")?.getAttribute("data-testid");
  return id ? id.replace(/([a-z])([A-Z])/g, "$1 $2").replace(/[-_]+/g, " ") : null;
}

function labelFor(input: HTMLInputElement, memo?: WeakMap<globalThis.Element, boolean>): string | null {
  const byFor = input.id ? (input.getRootNode() as Document | ShadowRoot).querySelector(`label[for="${CSS.escape(input.id)}"]`) : null;
  const el = byFor ?? input.closest("label");
  return el ? safeText(el, memo) : null;
}

function errors(doc: Document, geometry: boolean): string[] {
  const sel = '[role="alert"], [aria-invalid="true"], [aria-live="assertive"], .error, [class*="error"], [class*="invalid"]';
  const out = new Set<string>();
  for (const el of doc.querySelectorAll(sel)) {
    if (!visible(el, geometry)) continue;
    const t = safeText(el);
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
    const t = safeText(el);
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
  for (const el of walk(doc)) if (el.hasAttribute(ID_ATTR)) el.removeAttribute(ID_ATTR);
  const revision = crypto.randomUUID();
  const registry: Registry = { revision, url: doc.location.href, geometry, targets: new Map(), scrolls: new Map() };
  registries.set(doc, registry);
  const active = geometry ? modal(doc) : null;
  const memo = new WeakMap<globalThis.Element, boolean>();
  const candidates = ordered(doc, geometry, active, memo);
  let budget = CONTEXT_LIMIT;
  let contextTruncated = false;
  const panes = scrollCandidates(doc, geometry, active, memo);
  const paneIds = new Map(panes.kept.map((el, index) => [el, index]).filter(([, index]) => index !== 0) as [globalThis.Element, number][]);
  const elements: Element[] = [];
  for (const el of candidates.slice(0, MAX_ELEMENTS)) {
    const id = elements.length + 1;
    el.setAttribute(ID_ATTR, String(id));
    const tag = el.tagName === "INPUT" ? "input" : el.tagName.toLowerCase();
    const type = el.tagName === "INPUT" ? (el as HTMLInputElement).type : undefined;
    const state = fieldState(el);
    const raw = context(el, memo);
    const extra: { region?: string; row?: string } = {};
    for (const key of ['region', 'row'] as const) {
      const masked = redact(raw[key]);
      const kept = masked.slice(0, Math.min(160, budget));
      budget -= kept.length;
      if (kept.length < masked.length) contextTruncated = true;
      if (kept) extra[key] = kept;
    }
    registry.targets.set(id, { el, ancestors: ancestors(el), semantic: semantic(el, memo), form: formOwner(el) });
    const pane = [el, ...ancestors(el)].find(node => paneIds.has(node));
    elements.push({ id, tag, text: redact(label(el, memo)).slice(0, MAX_LABEL), ...(type ? { type } : {}), ...(state ? { state } : {}), ...extra, ...(pane ? { scroll_container_id: paneIds.get(pane) } : {}), ...(geometry ? geometryState(el, active) : {}) });
  }
  const scrollContainers = panes.kept.map((el, id) => {
    const name = id === 0 ? 'Page' : scrollName(el, memo);
    const masked = redact(name);
    const kept = masked.slice(0, Math.min(160, budget));
    budget -= kept.length;
    if (kept.length < masked.length) contextTruncated = true;
    const cs = getComputedStyle(el);
    registry.scrolls.set(id, { el, ancestors: ancestors(el), name, overflow: `${cs.overflowX}/${cs.overflowY}` });
    return { id, label: kept, ...scrollState(el, id === 0, doc), ...(geometry ? (id === 0 ? { in_view: true, occluded: !!active } : geometryState(el, active)) : {}) };
  });
  const body = doc.body as HTMLElement | null;
  const text = redact(body ? safeText(body, memo) : '').slice(0, MAX_TEXT);
  const obs: Observation = {
    url: doc.location?.href ?? "",
    title: doc.title,
    elements,
    text,
    errors: errors(doc, geometry).map(redact),
    revision,
    elements_truncated: candidates.length > MAX_ELEMENTS,
    candidate_limit_reached: candidates.length >= SCAN_LIMIT,
    omitted_elements: Math.max(0, candidates.length - elements.length),
    context_truncated: contextTruncated,
    navigation_version: 3,
    scroll_containers: scrollContainers,
    scroll_containers_truncated: panes.truncated,
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
  registry.state = publicState(doc);
  return obs;
}

function scrollName(el: globalThis.Element, memo?: WeakMap<globalThis.Element, boolean>): string {
  const heading = el.querySelector('h1,h2,h3,h4,h5,h6');
  return el.getAttribute('aria-label') || labelledBy(el, memo) || (heading ? safeText(heading, memo) : '') || `${el.getAttribute('role') || el.tagName.toLowerCase()} pane`;
}

function scrollCandidates(doc: Document, geometry: boolean, active: globalThis.Element | null, memo: WeakMap<globalThis.Element, boolean>) {
  const root = doc.scrollingElement ?? doc.documentElement;
  const panes: globalThis.Element[] = [];
  let scanned = 0;
  let capped = false;
  for (const el of walk(doc)) {
    if (++scanned > 2000) { capped = true; break; }
    if (el === root || !visible(el, geometry, memo)) continue;
    const cs = getComputedStyle(el);
    if ((/(auto|scroll)/.test(cs.overflowY) && el.scrollHeight > el.clientHeight + 4) || (/(auto|scroll)/.test(cs.overflowX) && el.scrollWidth > el.clientWidth + 4)) panes.push(el);
    if (panes.length >= 24) { capped = true; break; }
  }
  if (geometry) panes.sort((a, b) => Number(!!geometryState(a, active).occluded) - Number(!!geometryState(b, active).occluded) || Number(!geometryState(a, active).in_view) - Number(!geometryState(b, active).in_view));
  return { kept: [root, ...panes.slice(0, 11)], truncated: capped || panes.length > 11 };
}

export function scrollState(el: globalThis.Element, windowTarget: boolean, doc: Document): Omit<ScrollContainer, 'id' | 'label' | 'in_view' | 'occluded'> {
  const win = doc.defaultView!;
  const top = windowTarget ? win.scrollY : el.scrollTop;
  const left = windowTarget ? win.scrollX : el.scrollLeft;
  const height = windowTarget ? win.innerHeight : el.clientHeight;
  const width = windowTarget ? win.innerWidth : el.clientWidth;
  const maxTop = Math.max(0, el.scrollHeight - height), maxLeft = Math.max(0, el.scrollWidth - width);
  const cs = getComputedStyle(el);
  // Negative RTL/reversed ranges vary by layout. Keep signed offsets but decline those axes.
  const vertical = cs.flexDirection !== 'column-reverse' && top >= 0 && (windowTarget || /^(auto|scroll)$/.test(cs.overflowY));
  const horizontal = cs.direction !== 'rtl' && cs.flexDirection !== 'row-reverse' && left >= 0 && (windowTarget || /^(auto|scroll)$/.test(cs.overflowX));
  return { top, left, scroll_height: el.scrollHeight, client_height: height, scroll_width: el.scrollWidth, client_width: width, at_start: vertical && top <= 4, at_end: vertical && top >= maxTop - 4, can_up: vertical && top > 4, can_down: vertical && top < maxTop - 4, can_left: horizontal && left > 4, can_right: horizontal && left < maxLeft - 4 };
}

/** Container IDs are a separate registry; page attributes cannot impersonate a pane. */
export function resolveScrollContainer(doc: Document, id: number | null | undefined, revision?: string | null): { el?: globalThis.Element; note?: string; windowTarget?: boolean } {
  const registry = registries.get(doc);
  const reject = (why: string) => ({ note: `stale target: ${why}. Read the page again or update Walkthru and restart the test` });
  const legacy = id == null;
  if (!legacy && (!registry || !revision || revision !== registry.revision)) return reject('the scroll observation revision is missing or changed');
  const captured = registry?.scrolls.get(id ?? 0);
  const el = legacy ? (doc.scrollingElement ?? doc.documentElement) : captured?.el;
  if (!el || (!legacy && !captured)) return reject('the scroll container was not captured');
  const windowTarget = (id ?? 0) === 0;
  if (registry && registry.url !== doc.location.href) return reject('the page changed');
  if (!windowTarget) {
    const chain = ancestors(el);
    const cs = getComputedStyle(el);
    if (!el.isConnected || !visible(el, registry!.geometry) || chain.length !== captured!.ancestors.length || chain.some((node, i) => node !== captured!.ancestors[i]) || scrollName(el) !== captured!.name || `${cs.overflowX}/${cs.overflowY}` !== captured!.overflow) return reject('the scroll pane changed or is hidden');
  }
  const active = modal(doc);
  if (active && (windowTarget || !within(el, active))) return reject('a dialog covers the scroll container');
  if (!windowTarget && registry?.geometry) {
    const geometry = geometryState(el, active);
    if (!geometry.in_view || geometry.occluded !== false) return reject('the scroll pane is outside the viewport or covered');
  }
  return { el, windowTarget };
}

export type PublicState = { url: string; text: string; signature: string; busy: boolean };
/** Bounded public state only: no field values, diagnostics, overlay animation or arbitrary mutation count. */
export function publicState(doc: Document): PublicState {
  const memo = new WeakMap<globalThis.Element, boolean>();
  const controls: unknown[] = [];
  let busy = doc.readyState !== 'complete';
  let scanned = 0;
  for (const el of walk(doc)) {
    if (++scanned > 2000) break;
    if (!visible(el, false, memo)) continue;
    if (el.getAttribute('aria-busy') === 'true') busy = true;
    if (controls.length < 120 && el.matches(INTERACTIVE)) controls.push([el.tagName, redact(el.getAttribute('aria-label') || safeText(el, memo, { chars: 160, nodes: 40 })).slice(0, 80), fieldState(el), el.getAttribute('aria-expanded'), el.getAttribute('aria-selected'), disabled(el)]);
  }
  const text = redact(doc.body ? safeText(doc.body, memo, { chars: MAX_TEXT, nodes: 2000 }) : '').slice(0, MAX_TEXT);
  const publicText = JSON.stringify([doc.title, text, controls]);
  const offsets = [...(registries.get(doc)?.scrolls ?? [])].slice(0, 12).map(([id, captured]) => [id, id === 0 ? doc.defaultView!.scrollY : captured.el.scrollTop, id === 0 ? doc.defaultView!.scrollX : captured.el.scrollLeft]);
  return { url: doc.location.href, text: publicText, signature: JSON.stringify([doc.location.href, publicText, offsets, busy]), busy };
}

export function waitBaseline(doc: Document, revision?: string | null): { state?: PublicState; note?: string } {
  const registry = registries.get(doc);
  if (!revision || !registry || revision !== registry.revision) return { note: 'stale target: the wait observation revision is missing or changed. Read the page again and restart the test' };
  return { state: registry.state };
}

const SCAN_LIMIT = 800; // candidates read before ordering; long feeds hold thousands of controls

/** Interactive elements as a person meets them: what is on screen top to bottom, then the next screen down, then
 *  what is above, then the rest. Without layout (jsdom) the document order stays. */
function ordered(doc: Document, geometry: boolean, active: globalThis.Element | null, memo: WeakMap<globalThis.Element, boolean>): globalThis.Element[] {
  const found: globalThis.Element[] = [];
  for (const el of walk(doc)) {
    if (!el.matches(INTERACTIVE) || !visible(el, geometry, memo)) continue;
    if ((el as HTMLInputElement).type === "hidden" || disabled(el)) continue;
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
      const state = geometryState(el, active);
      return { el, index, band: state.occluded ? 4 : band(r.top, r.bottom), top: r.top };
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
  return registries.get(doc)?.targets.get(id)?.el ?? null;
}
