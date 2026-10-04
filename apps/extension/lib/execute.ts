/** Runs one PersonaStep inside the page. Returns a note for the agent when something went wrong. */

import { publicState, resolveScrollContainer, resolveTarget, scrollState, waitBaseline, type ExecutorResult } from "./snapshot";
import { isBasket, isCommerce, isDestructive, isSearchField, isSearchForm, isSending, isSocial } from "./safety";

export type Step = {
  thought: string;
  action: "click" | "type" | "scroll" | "wait" | "back" | "done" | "give_up";
  target_id: number | null;
  text: string | null;
  confusion: number;
  observation_revision?: string | null;
  scroll_container_id?: number | null;
  scroll_direction?: 'up' | 'down' | 'left' | 'right';
  scroll_distance?: number | null;
  wait_condition?: 'settled' | 'url_changed' | 'text_changed';
  wait_timeout_ms?: number;
};

/** confirm: "send" means the owner must approve in the side panel before this click runs for real. */
export type ExecResult = { ok: boolean; note?: string; submits?: boolean; confirm?: "send"; executor_result?: ExecutorResult };

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
export type ExecOptions = { logged_in?: boolean; dryRun?: boolean; verified?: boolean; confirmed?: boolean; deadline_ms?: number };

/** dryRun reports what would happen (safe-mode block, form submit) without touching the page. */
export function execute(step: Step, doc: Document = document, opts: ExecOptions = {}): ExecResult {
  const win = doc.defaultView!;
  switch (step.action) {
    case "scroll":
      return scroll(step, doc, opts);
    case "wait":
      return { ok: false, note: 'bounded wait requires the current asynchronous executor' };
    case "back":
      if (!opts.dryRun) win.history.back();
      return { ok: true };
    case "click":
    case "type": {
      const target = resolveTarget(doc, step.target_id, step.observation_revision);
      if (!target.el) return { ok: false, note: target.note };
      const el = target.el;
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
      const ready = resolveTarget(doc, step.target_id, step.observation_revision, true);
      if (!ready.el) return { ok: false, note: ready.note };
      if (step.action === "type") return type(el as HTMLElement, step.text ?? "", () => resolveTarget(doc, step.target_id, step.observation_revision, true).note);
      (el as HTMLElement).click();
      return { ok: true, submits: willSubmit };
    }
    default:
      return { ok: true };
  }
}

function scroll(step: Step, doc: Document, opts: ExecOptions): ExecResult {
  const started = Date.now();
  const elapsed = () => Math.min(600000, Math.max(0, Date.now() - started));
  if (opts.deadline_ms !== undefined && Date.now() >= opts.deadline_ms) return { ok: false, executor_result: { action: 'scroll', status: 'aborted', container_id: step.scroll_container_id ?? 0, elapsed_ms: 0 } };
  const id = step.scroll_container_id ?? ((step.scroll_direction != null && step.scroll_direction !== 'down') || step.scroll_distance != null ? 0 : undefined);
  const resolved = resolveScrollContainer(doc, id, step.observation_revision);
  if (!resolved.el) return { ok: false, note: resolved.note };
  const el = resolved.el;
  const win = doc.defaultView!;
  const windowTarget = !!resolved.windowTarget;
  const beforeState = scrollState(el, windowTarget, doc);
  const before = { top: beforeState.top, left: beforeState.left };
  const direction = step.scroll_direction ?? 'down';
  const horizontal = direction === 'left' || direction === 'right';
  const cs = getComputedStyle(el);
  if (!windowTarget && !/^(auto|scroll)$/.test(horizontal ? cs.overflowX : cs.overflowY)) {
    return { ok: true, executor_result: { action: 'scroll', status: 'no_progress', container_id: step.scroll_container_id ?? 0, before, after: before, elapsed_ms: elapsed() }, note: 'this pane does not expose scrolling on the requested axis' };
  }
  if ((horizontal && (cs.direction === 'rtl' || cs.flexDirection === 'row-reverse' || before.left < 0)) || (!horizontal && (cs.flexDirection === 'column-reverse' || before.top < 0))) {
    return { ok: true, executor_result: { action: 'scroll', status: 'no_progress', container_id: step.scroll_container_id ?? 0, before, after: before, elapsed_ms: elapsed() }, note: 'this reversed scroll axis is not supported by the bounded executor' };
  }
  const viewport = horizontal ? beforeState.client_width : beforeState.client_height;
  const distance = Math.min(1000, viewport * .85, Math.max(1, step.scroll_distance ?? viewport * .85));
  if (opts.deadline_ms !== undefined && Date.now() >= opts.deadline_ms) return { ok: false, executor_result: { action: 'scroll', status: 'aborted', container_id: step.scroll_container_id ?? 0, elapsed_ms: elapsed() } };
  if (!opts.dryRun) {
    const amount = direction === 'up' || direction === 'left' ? -distance : distance;
    const move = { top: horizontal ? 0 : amount, left: horizontal ? amount : 0, behavior: 'instant' as ScrollBehavior };
    // MDN Element/scrollBy: instant movement lets feedback measure the actual offset, not intended distance.
    // https://developer.mozilla.org/en-US/docs/Web/API/Element/scrollBy
    if (windowTarget) win.scrollBy(move);
    else el.scrollBy(move);
  }
  const afterState = scrollState(el, windowTarget, doc);
  const after = { top: afterState.top, left: afterState.left };
  return { ok: true, executor_result: { action: 'scroll', status: Math.abs(after.top - before.top) > .5 || Math.abs(after.left - before.left) > .5 ? 'moved' : 'no_progress', container_id: step.scroll_container_id ?? 0, before, after, elapsed_ms: elapsed() } };
}

/** Only observation is retried while waiting. A dispatched click/type/back is never repeated. */
export async function executeAsync(step: Step, doc: Document = document, opts: ExecOptions = {}, signal?: AbortSignal): Promise<ExecResult> {
  const started = Date.now();
  const aborted = () => signal?.aborted || (opts.deadline_ms !== undefined && Date.now() >= opts.deadline_ms);
  const outcome = (status: ExecutorResult['status']): ExecResult => ({ ok: status !== 'aborted', executor_result: { action: step.action === 'scroll' ? 'scroll' : 'wait', status, ...(step.action === 'scroll' ? { container_id: step.scroll_container_id ?? 0 } : {}), elapsed_ms: Math.min(600000, Math.max(0, Date.now() - started)) } });
  if (aborted()) return outcome('aborted');
  if (step.action !== 'wait') return execute(step, doc, opts);
  const baseline = waitBaseline(doc, step.observation_revision);
  if (!baseline.state) return { ok: false, note: baseline.note };
  if (opts.dryRun) return { ok: true };
  const timeout = Math.min(5000, Math.max(100, step.wait_timeout_ms ?? 1000));
  const end = Math.min(started + timeout, opts.deadline_ms ?? Infinity);
  const condition = step.wait_condition ?? 'settled';
  let previous = publicState(doc).signature;
  let quietSince = Date.now();
  while (true) {
    if (aborted()) return outcome('aborted');
    const current = publicState(doc);
    // A throttled tab or slow read can overrun the requested bound. Never label a late change as timely.
    if (aborted()) return outcome('aborted');
    if (Date.now() >= end) return outcome('timeout');
    if (condition === 'url_changed' && current.url !== baseline.state.url) return outcome('changed');
    if (condition === 'text_changed' && current.text !== baseline.state.text) return outcome('changed');
    if (current.signature !== previous) { previous = current.signature; quietSince = Date.now(); }
    if (condition === 'settled' && !current.busy && Date.now() - quietSince >= 300) return outcome('settled');
    await new Promise<void>(resolve => {
      const timer = doc.defaultView!.setTimeout(done, Math.min(100, Math.max(1, end - Date.now())));
      signal?.addEventListener('abort', done, { once: true });
      function done() { doc.defaultView!.clearTimeout(timer); signal?.removeEventListener('abort', done); resolve(); }
    });
  }
}

function type(el: HTMLElement, value: string, recheck: () => string | undefined): ExecResult {
  const input = el as HTMLInputElement;
  if (el.isContentEditable) {
    el.focus();
    const stale = recheck();
    if (stale) return { ok: false, note: stale };
    el.textContent = value;
    el.dispatchEvent(new Event("input", { bubbles: true }));
    return { ok: true };
  }
  if (!("value" in input)) return { ok: false, note: "element is not an input" };
  input.focus();
  const stale = recheck();
  if (stale) return { ok: false, note: stale };
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
