import type { ReportAssessment as Assessment, ReportIssue } from '../lib/reportContract'
import { OUTCOME_LABEL } from '../lib/reportContract'

export function ReportScope({ assessment: a }: { assessment: Assessment }) {
  return (
    <section aria-label="Tested scope and limitations" className="report-print-section mt-8 border-y border-line py-5">
      <h2 className="text-xl font-light tracking-tight">{OUTCOME_LABEL[a.outcome]}</h2>
      <p className="mt-2 text-sm text-muted">{a.coverage.actions_with_outcomes} actions with recorded outcomes. {a.coverage.confirmed_checkpoints} of {a.coverage.declared_checkpoints} declared checkpoints confirmed.</p>
      <p className="mt-1 text-sm text-muted">Technical checks: {Object.entries(a.coverage.checks).map(([name, status]) => `${name}: ${status === 'complete' ? 'measured' : 'unavailable'}`).join('; ') || 'not recorded'}.</p>
      {a.checkpoints.length > 0 && <dl className="mt-4 space-y-3">
        {a.checkpoints.map((c, i) => <div key={i}>
          <dt className="text-sm font-medium">{i + 1}. {c.description}: {c.status === 'passed' ? 'confirmed' : 'unconfirmed'}</dt>
          <dd className="mt-1 text-sm text-muted">Expected: {c.expected_result ?? 'Unknown, not declared'}. Recorded result: {c.actual_result ?? 'Not confirmed'}.</dd>
        </div>)}
      </dl>}
      {(a.assertions ?? []).map((check) => <section key={check.id} aria-label="Declared count assertion" className="mt-5 rounded-2xl border border-line p-4 text-sm">
        <h3 className="font-medium">Synthetic filtered count: {check.status}</h3>
        <p className="mt-1 text-muted">State: {check.expected.path}, Filter: {check.expected.filter_value}. Count label: {check.expected.count_label}.</p>
        <p className="mt-2 text-muted">Filter state reached: {check.state_reached ? 'yes' : 'unconfirmed'}. Expected {check.expected.expected_count ?? 'unknown'} records; observed {check.observed_count ?? 'unknown'}; tolerance {check.expected.tolerance} records.</p>
        <p className="mt-1 text-muted">{check.reason}</p>
        <p className="mt-2 text-muted">Dataset: {check.expected.dataset_id ?? 'unknown'}. Observed dataset: {check.observed_dataset_id ?? 'unknown'}. Expected time: {check.expected.dataset_at ?? 'unknown'}. Observed time: {check.observed_dataset_at ?? 'unknown'}. Checked at: {check.evaluated_at}. Maximum age: {check.expected.max_age_seconds} seconds.</p>
        <p className="mt-1 text-muted">Visible UI only; backend persistence and authorization are unverified.</p>
        {check.evidence_refs.map((ref) => <p key={ref} className="mt-2 font-mono text-xs text-muted">{ref}: {a.evidence_index.find((record) => record.id === ref)?.observed}</p>)}
      </section>)}
      <ul className="mt-4 max-w-[80ch] list-disc space-y-1 pl-5 text-sm leading-relaxed text-muted">
        {a.limitations.map((text, i) => <li key={i}>{text}</li>)}
      </ul>
    </section>
  )
}

export function FindingAssessment({ issue, assessment }: { issue: ReportIssue; assessment: Assessment }) {
  return (
    <details className="report-print-section mt-4 text-sm">
      <summary className="w-fit cursor-pointer py-1 text-ink">Inspect facts, reproduction and acceptance</summary>
      <dl className="mt-3 space-y-3 border-l border-line pl-4">
        <div><dt className="font-medium">Observed facts</dt><dd className="mt-1 text-muted">{issue.observed_facts.join(' ')}</dd></div>
        <div><dt className="font-medium">Expected result</dt><dd className="mt-1 text-muted">{issue.expected_result ?? 'Unknown, not declared'}</dd></div>
        <div><dt className="font-medium">Actual result</dt><dd className="mt-1 text-muted">{issue.actual_result}</dd></div>
        <div><dt className="font-medium">Interpretation</dt><dd className="mt-1 text-muted">{issue.interpretation}</dd></div>
        <div><dt className="font-medium">Cause hypothesis</dt><dd className="mt-1 text-muted">{issue.cause_hypothesis ?? 'Not established'}</dd></div>
        <div><dt className="font-medium">Proposed change</dt><dd className="mt-1 text-muted">{issue.proposed_change}</dd></div>
        <div><dt className="font-medium">Reproduction</dt><dd className="mt-1 text-muted">
          {issue.reproduction_steps.length ? <ol className="list-decimal pl-5">{issue.reproduction_steps.map((text, i) => <li key={i}>{text}</li>)}</ol> : 'Repeat the recorded check in the same scope. Missing steps were not inferred.'}
        </dd></div>
        <div><dt className="font-medium">Acceptance test</dt><dd className="mt-1 text-muted">{issue.acceptance_test}</dd></div>
        <div><dt className="font-medium">Evidence references</dt><dd className="mt-1 space-y-2 text-muted">
          {issue.evidence_refs.map((ref) => {
            const evidence = assessment.evidence_index.find((e) => e.id === ref)!
            return <p key={ref}><span className="font-mono text-xs">{ref}</span>: {evidence.observed}{evidence.url && <span className="block text-xs">{evidence.url}</span>}</p>
          })}
        </dd></div>
      </dl>
    </details>
  )
}
