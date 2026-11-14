import type { HarnessEvent } from './runs'

const reasons: Record<string, string> = {
  observation_ready: 'Read the current page and pending checkpoint.',
  missing_navigation_marker: 'The plan has no destination to verify. Navigation remains unconfirmed.',
  unobserved_navigation_target: 'The planned destination is not supported by an observed link on this page.',
  section_evidence_required: 'This is a section destination. Section visibility has not been verified.',
  contract_grounded: 'The current task contract has an observable expectation.',
  contract_revised: 'Bound the navigation task to one uniquely observed control without changing the owner objective.',
  discovery_pending: 'The next checkpoint remains uncertain. Discovery is limited to two attempts.',
  contract_unresolved: 'Discovery could not establish a supported task contract. Completion remains unknown.',
  document_changed: 'The document or route changed, so earlier section evidence cannot be reused.',
  section_action_unconfirmed: 'The action was not a verified click on the control for this section.',
  section_not_newly_visible: 'The section was not newly observed as visible and uncovered.',
  section_identity_changed: 'The section identity changed between observations.',
  reveal_requested: 'Scrolled in the measured direction to reveal an observed control without activating it.',
  missing_outcome_expectation: 'The plan has no observable success condition. Completion remains unconfirmed.',
  action_accepted: 'The proposed action passed the execution checks.',
  target_unavailable: 'The proposed control is outside the viewport or covered. The action was refused.',
  recovery_exhausted: 'The control is still unavailable and no further refresh is allowed.',
  refresh_requested: 'Requested a fresh page snapshot without clicking or typing.',
  ineligible_action: 'This action cannot establish checkpoint completion.',
  observation_blocked: 'An execution note or visible error prevents confirmation.',
  different_origin: 'The observed result is outside the original site.',
  route_mismatch: 'The observed URL does not match the declared destination.',
  navigation_not_new: 'No new navigation to the declared destination was observed.',
  contradictory_notice: 'A visible notice contradicts the expected success condition.',
  preexisting_text: 'The expected text was already present before this action.',
  outcome_not_observed: 'The expected outcome was not observed after this action.',
  checkpoint_confirmed: 'New public evidence matches this checkpoint.',
  duplicate_signal: 'The same evidence cannot establish another checkpoint.',
  wait_without_causal_action: 'This refresh or wait does not establish a task outcome.',
  no_pending_checkpoint: 'There is no pending checkpoint to assess.',
  legacy_observation: 'Received an older observation format without action outcome evidence.',
  execution_refused: 'The browser refused a stale target. No action outcome was credited.',
  continue: 'Continue with the confirmed progress and latest observation.',
  done: 'All declared checkpoints have matching public evidence.',
  agent_lost: 'Walkthru could not establish the next action or outcome. This does not establish a website defect.',
  budget: 'The action budget ended before all checkpoints were confirmed.',
  stopped: 'The journey was stopped before the pending action was confirmed.',
  stuck: 'Repeated actions did not complete the remaining task.',
  looping: 'The journey revisited the same page too many times.',
  gave_up: 'An observed action error prevented further progress.',
  site_block: 'An observed action error supports stopping this attempt.',
  safe_stop: 'A safety boundary stopped the journey.',
  visitor_mode_limit: 'The action is outside the permitted scope for an unverified site.',
  bot_wall: 'Bot protection stopped the journey.',
  captcha: 'A CAPTCHA stopped the journey.',
}

const nodes = new Set(['validate', 'revise', 'prepare', 'guard', 'recover', 'assess', 'check'])
const actions = new Set(['click', 'type', 'scroll', 'wait', 'back', 'done', 'give_up'])

/** Older reports have no log. Malformed saved rows must never manufacture an execution explanation. */
export function worklogRows(value: unknown): (HarnessEvent & { explanation: string })[] {
  if (!Array.isArray(value)) return []
  return value.slice(0, 256).flatMap((item) => {
    if (!item || typeof item !== 'object') return []
    const e = item as HarnessEvent
    if (!Number.isInteger(e.sequence) || e.sequence < 1 || e.sequence > 256 ||
        !Number.isInteger(e.step) || e.step < 1 || e.step > 100 ||
        !Number.isInteger(e.progress) || e.progress < 0 || e.progress > 4 ||
        !nodes.has(e.node) || typeof e.reason !== 'string' || !/^[a-z_]{1,64}$/.test(e.reason)) return []
    return [{ sequence: e.sequence, step: e.step, node: e.node, reason: e.reason, progress: e.progress,
      checkpoint: Number.isInteger(e.checkpoint) && e.checkpoint! > 0 && e.checkpoint! <= 4 ? e.checkpoint : null,
      action: e.action && actions.has(e.action) ? e.action : null,
      before_kind: ['navigation', 'section', 'outcome'].includes(e.before_kind ?? '') ? e.before_kind : null,
      after_kind: ['navigation', 'section', 'outcome'].includes(e.after_kind ?? '') ? e.after_kind : null,
      before_target: typeof e.before_target === 'string' && /^\/(?!\/)[A-Za-z0-9/_~.#-]{0,239}$/.test(e.before_target) ? e.before_target : null,
      after_target: typeof e.after_target === 'string' && /^\/(?!\/)[A-Za-z0-9/_~.#-]{0,239}$/.test(e.after_target) ? e.after_target : null,
      explanation: Object.hasOwn(reasons, e.reason) ? reasons[e.reason] : 'A harness decision was recorded by a newer version.',
    }]
  })
}
