import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { useRef } from "react";
import { AGENT_BIRD, AGENT_TONE, type AgentState } from "../../lib/agent-bird";

gsap.registerPlugin(useGSAP);

type AgentStatusProps = {
  activity: string;
  state: AgentState;
};

export function AgentStatus({ activity, state }: AgentStatusProps) {
  const root = useRef<HTMLDivElement>(null);
  const activityRef = useRef<HTMLSpanElement>(null);

  useGSAP(() => {
    const media = gsap.matchMedia();
    media.add("(prefers-reduced-motion: no-preference)", () => {
      const rig = root.current?.querySelector(".agent-bird__rig");
      const eye = root.current?.querySelector(".agent-bird__eye");
      const tail = root.current?.querySelector(".agent-bird__tail");
      if (!rig || !eye || !tail) return;
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
    return () => media.revert();
  }, { scope: root });

  useGSAP(() => {
    const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
    gsap.to(root.current, { color: AGENT_TONE[state], duration: reduceMotion ? 0 : 0.8, ease: "power2.out", overwrite: "auto" });
    gsap.fromTo(activityRef.current, { autoAlpha: reduceMotion ? 1 : 0.35, y: reduceMotion ? 0 : 3 }, { autoAlpha: 1, y: 0, duration: reduceMotion ? 0 : 0.45, ease: "power2.out" });
  }, { dependencies: [activity, state], scope: root });

  return (
    <div ref={root} className="agent-status" aria-label={`Scout. ${activity}`}>
      <svg viewBox="0 0 200 200" aria-hidden="true">
        <g className="agent-bird__rig">
          <path className="agent-bird__tail" d={AGENT_BIRD.tail} fill="currentColor" stroke="currentColor" strokeLinejoin="round" />
          <path d={AGENT_BIRD.backLeg} fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="4" />
          <path d={AGENT_BIRD.frontLeg} fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="4" />
          <path d={AGENT_BIRD.body} fill="currentColor" stroke="currentColor" strokeLinejoin="round" />
          <g className="agent-bird__eye">
            <circle cx="145" cy="22" r="7" fill="var(--bg)" />
            <circle cx="145" cy="22" r="3" fill="currentColor" />
          </g>
        </g>
      </svg>
      <span className="agent-copy">
        <strong>Scout</strong>
        <span ref={activityRef} aria-live="polite">{activity}</span>
      </span>
    </div>
  );
}
