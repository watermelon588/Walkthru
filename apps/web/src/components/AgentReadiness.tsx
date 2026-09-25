import type { Report } from '../lib/runs'

type AgentReady = NonNullable<Report['agent_ready']>

/** Agent readiness (P1.7): can AI agents (browsing assistants, WebMCP clients) use the site? Same layout as the GEO block. */
export function AgentReadiness({ agent }: { agent: AgentReady }) {
  if (agent.score === null || agent.parts.length === 0) return null
  const tone = agent.score >= 80 ? 'text-accent' : agent.score >= 50 ? 'text-ink' : 'text-danger'
  const label = agent.score >= 80 ? 'Ready for agents' : agent.score >= 50 ? 'Partly usable' : 'Hard for agents'
  return (
    <section aria-labelledby="agent-title" className="report-print-section mt-12">
      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Agent readiness</p>
      <div className="mt-2 grid gap-6 border-y border-line py-5 md:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
        <div>
          <h2 id="agent-title" className="text-xl font-light tracking-tight">Can AI agents use your site?</h2>
          <p className="mt-3 flex items-baseline gap-3">
            <span className="text-5xl font-extralight tracking-[-0.03em]">{agent.score}</span>
            <span className="text-sm text-muted">of 100</span>
            <span className={`text-sm font-medium ${tone}`}>{label}</span>
          </p>
          <p className="mt-3 max-w-[48ch] text-sm leading-relaxed text-muted">
            Assistants that act for people read control names, fill labelled forms and give up at CAPTCHAs. Scored from this report's evidence only; parts it could not measure are left out.
          </p>
        </div>
        <dl className="grid content-start gap-3">
          {agent.parts.map((p) => (
            <div key={p.id} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-1 text-sm">
              <dt>{p.label}</dt>
              <dd className="font-mono text-xs text-muted">{p.earned}/{p.max}</dd>
              <dd className="col-span-2 h-1 overflow-hidden rounded-full bg-line" aria-hidden="true">
                <div className="h-full rounded-full bg-ink" style={{ width: `${Math.round((100 * p.earned) / p.max)}%` }} />
              </dd>
              <dd className="col-span-2 text-xs leading-relaxed text-muted">{p.note}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  )
}
