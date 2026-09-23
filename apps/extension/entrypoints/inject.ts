/** Injected into the tab under test by the side panel (chrome.scripting.executeScript).
 *  An unlisted script rather than a content script so the manifest carries no host_permissions;
 *  access is requested per site when a test starts. */

import { snapshot } from "../lib/snapshot";
import { execute, type ExecOptions, type Step } from "../lib/execute";
import { AGENT_BIRD, AGENT_TONE, type AgentState } from "../lib/agent-bird";
import gsap from "gsap";
import { collectBrowserDiagnostics, observeWebVitals } from "../lib/diagnostics";

export type ContentRequest =
  | { type: "snapshot" }
  | { type: "act"; step: Step; opts: ExecOptions }
  | { type: "agent_status"; state: AgentState; activity: string }
  | { type: "agent_visibility"; visible: boolean }
  | { type: "evidence_capture"; active: boolean }
  | { type: "ping" };

declare global {
  interface Window { __walkthru?: true }
}

export default defineUnlistedScript(() => {
  if (window.__walkthru) return; // already injected on this page
  window.__walkthru = true;
  const readWebVitals = observeWebVitals();
  // Injection can land mid-navigation, before the new page has a <body>. The listener registers now
  // (so pings succeed), but everything that touches the page waits for the body to exist.
  const ready = whenBody().then(() => mountAgent());
  chrome.runtime.onMessage.addListener((msg: ContentRequest, _sender, reply) => {
    if (msg.type === "ping") {
      reply({ ok: true });
      return true;
    }
    ready.then(async (agent) => {
      if (msg.type === "snapshot") {
        const observation = snapshot();
        reply({ ...observation, diagnostics: await collectBrowserDiagnostics(document, readWebVitals()) });
      } else if (msg.type === "act") reply(execute(msg.step, document, msg.opts));
      else if (msg.type === "agent_status") {
        agent.update(msg.state, msg.activity);
        reply({ ok: true });
      } else if (msg.type === "agent_visibility") {
        agent.setVisible(msg.visible);
        reply({ ok: true });
      } else if (msg.type === "evidence_capture") {
        await agent.setCaptureMode(msg.active);
        reply({ ok: true });
      }
    });
    return true;
  });
});

function whenBody(): Promise<void> {
  return new Promise((resolve) => {
    const check = () => (document.body ? resolve() : requestAnimationFrame(check));
    check();
  });
}

/** Injection can land while a navigation is swapping documents (no root element yet). Wait for it. */
function appendWhenReady(node: Node) {
  const root = document.documentElement;
  if (root) root.append(node);
  else requestAnimationFrame(() => appendWhenReady(node));
}

/** A closed shadow root keeps Scout visible to the site owner but absent from agent snapshots. */
function mountAgent() {
  const host = document.createElement("walkthru-agent");
  host.setAttribute("role", "status");
  host.setAttribute("aria-live", "polite");
  const shadow = host.attachShadow({ mode: "closed" });
  shadow.innerHTML = `
    <style>
      :host {
        --ink: #1b1b1f;
        --muted: #63636b;
        --accent: #4d7274;
        --danger: #a33b3b;
        position: fixed;
        right: 24px;
        bottom: 24px;
        z-index: 2147483647;
        display: block;
        opacity: 0;
        visibility: hidden;
        pointer-events: none;
        color: var(--accent);
        font-family: ui-sans-serif, system-ui, sans-serif;
      }
      .agent { display: flex; align-items: center; gap: 10px; filter: drop-shadow(0 2px 7px rgb(255 255 255 / 0.8)); }
      svg { width: 64px; height: 64px; flex: 0 0 auto; overflow: visible; }
      .copy { min-width: 0; line-height: 1.15; text-shadow: 0 1px 4px white, 0 0 10px white; }
      strong { display: block; color: var(--ink); font: 700 10px/1 ui-monospace, monospace; letter-spacing: 0.18em; text-transform: uppercase; }
      .activity { display: block; max-width: 150px; margin-top: 6px; color: var(--muted); font-size: 12px; }
      @media (max-width: 520px) {
        :host { right: 16px; bottom: 16px; }
        svg { width: 52px; height: 52px; }
        .activity { max-width: 112px; font-size: 11px; }
      }
    </style>
    <div class="agent">
      <svg viewBox="0 0 200 200" aria-hidden="true">
        <g class="agent-bird__rig">
          <path class="agent-bird__tail" d="${AGENT_BIRD.tail}" fill="currentColor" stroke="currentColor" stroke-linejoin="round" />
          <path d="${AGENT_BIRD.backLeg}" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="4" />
          <path d="${AGENT_BIRD.frontLeg}" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="4" />
          <path d="${AGENT_BIRD.body}" fill="currentColor" stroke="currentColor" stroke-linejoin="round" />
          <g class="agent-bird__eye">
            <circle cx="145" cy="22" r="7" fill="white" />
            <circle cx="145" cy="22" r="3" fill="currentColor" />
          </g>
        </g>
      </svg>
      <span class="copy"><strong>Scout</strong><span class="activity">Reading the page</span></span>
    </div>`;
  appendWhenReady(host);

  const rig = shadow.querySelector<SVGGElement>(".agent-bird__rig")!;
  const eye = shadow.querySelector<SVGGElement>(".agent-bird__eye")!;
  const tail = shadow.querySelector<SVGPathElement>(".agent-bird__tail")!;
  const activityNode = shadow.querySelector<HTMLElement>(".activity")!;
  let hideTween: gsap.core.Tween | null = null;
  let evidenceStyle: HTMLStyleElement | null = null;

  const media = gsap.matchMedia();
  media.add("(prefers-reduced-motion: no-preference)", () => {
    gsap.set(rig, { svgOrigin: "120 184" });
    gsap.set(eye, { svgOrigin: "145 22" });
    gsap.set(tail, { svgOrigin: "80 113" });
    gsap.timeline({ repeat: -1, repeatDelay: 4.4 })
      .to(eye, { scaleY: 0.12, duration: 0.1, ease: "power1.inOut" })
      .to(eye, { scaleY: 1, duration: 0.14, ease: "power1.inOut" });
    gsap.timeline({ repeat: -1, repeatDelay: 0.7, defaults: { ease: "power2.inOut" } })
      .to(rig, { rotation: 1.6, y: 1, duration: 1.8 })
      .to(tail, { rotation: -3, duration: 1.8 }, "<")
      .to(rig, { rotation: -0.7, y: 0, duration: 1.5 }, "+=0.35")
      .to(tail, { rotation: 2, duration: 1.5 }, "<")
      .to([rig, tail], { rotation: 0, duration: 1.2 }, "+=0.2");
  });

  let visible = true;
  return {
    setVisible(next: boolean) {
      visible = next;
      gsap.set(host, { autoAlpha: next ? 1 : 0 });
    },
    async setCaptureMode(active: boolean) {
      if (active) {
        gsap.set(host, { autoAlpha: 0 });
        if (!evidenceStyle) {
          evidenceStyle = document.createElement("style");
          evidenceStyle.dataset.walkthruEvidenceMask = "true";
          evidenceStyle.textContent = `
            input:not([type="button"]):not([type="submit"]):not([type="reset"]):not([type="checkbox"]):not([type="radio"]),
            textarea,
            select,
            [contenteditable="true"] {
              color: transparent !important;
              caret-color: transparent !important;
              text-shadow: 0 0 12px currentColor !important;
              filter: blur(5px) !important;
            }
          `;
          appendWhenReady(evidenceStyle);
        }
        await new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve())));
        return;
      }
      evidenceStyle?.remove();
      evidenceStyle = null;
      if (visible) gsap.set(host, { autoAlpha: 1 });
    },
    update(state: AgentState, activity: string) {
    hideTween?.kill();
    const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
    host.setAttribute("aria-label", `Scout. ${activity}`);
    if (visible) gsap.to(host, { autoAlpha: 1, duration: reduceMotion ? 0 : 0.4, overwrite: "auto" });
    gsap.to(shadow.querySelector(".agent"), { color: AGENT_TONE[state], duration: reduceMotion ? 0 : 0.8, ease: "power2.out", overwrite: "auto" });
    gsap.to(activityNode, {
      autoAlpha: reduceMotion ? 1 : 0,
      y: reduceMotion ? 0 : 3,
      duration: reduceMotion ? 0 : 0.16,
      onComplete: () => {
        activityNode.textContent = activity;
        gsap.to(activityNode, { autoAlpha: 1, y: 0, duration: reduceMotion ? 0 : 0.34, ease: "power2.out" });
      },
    });
    if (state === "complete" || state === "stopped") {
      hideTween = gsap.to(host, { autoAlpha: 0, duration: reduceMotion ? 0 : 0.5, delay: 4 });
    }
    },
  };
}
