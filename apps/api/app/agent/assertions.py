"""A single supplied filtered-count check over already collected public UI, never a connector."""
import re
from datetime import UTC, datetime
from urllib.parse import urlsplit

from app.agent.schema import FilterCountAssertion, ReportAssertion, _context_text


def now():
    return datetime.now(UTC)


def mission_plan(assertion: FilterCountAssertion, goal: str) -> dict:
    return {'intent': goal[:300], 'feasible': True, 'refusal': None, 'checkpoints': [
        {'description': f'Reach {assertion.path} with Filter: {assertion.filter_value}'[:200], 'kind': 'outcome',
         'url_contains': assertion.path, 'text_contains': f'Filter: {assertion.filter_value}'}]}


def _one(label: str, pattern: str, text: str):
    if len(re.findall(r'(?<!\w)' + re.escape(label) + r'\s*:', text)) != 1:
        return None
    values = re.findall(r'(?<!\w)' + re.escape(label) + r'\s*:\s*(' + pattern + r')(?![\w.,])', text)
    return values[0] if len(values) == 1 else None


def evaluate(assertion: FilterCountAssertion, observation: dict, start_url: str, step: int, at: datetime | None = None) -> dict | None:
    at = at or now()
    try:
        current, start = urlsplit(observation.get('url', '')), urlsplit(start_url)
        def origin(u):
            return u.scheme, u.hostname, u.port or (443 if u.scheme == 'https' else 80)
        if origin(current) != origin(start) or current.path != assertion.path or current.scheme not in {'http', 'https'}:
            return None
    except ValueError:
        return None
    if observation.get('note'):
        return None  # refusals and handoffs are not executed outcome evidence
    text = observation.get('text', '')
    filter_marker = r'(?<!\w)Filter\s*:\s*' + re.escape(assertion.filter_value) + r'(?=\s*(?:;|\r?\n|' + re.escape(assertion.count_label) + r'\s*:|$))'
    if len(re.findall(r'(?<!\w)Filter\s*:', text)) != 1 or len(re.findall(filter_marker, text)) != 1:
        return None
    raw_count = _one(assertion.count_label, r'\d{1,6}', text)
    count = int(raw_count) if raw_count is not None and int(raw_count) <= 100_000 else None
    dataset = _one('Dataset', r'[A-Za-z0-9_.-]+', text)
    if dataset and (len(dataset) > 80 or _context_text(dataset) != dataset):
        dataset = None
    raw_date = _one('Dataset time', r'\d{4}-\d{2}-\d{2}T[0-9:.]+(?:Z|[+-]\d{2}:\d{2})', text)
    try:
        dataset_at = datetime.fromisoformat(raw_date) if raw_date else None
    except ValueError:
        dataset_at = None
    reason = 'The declared filter state was reached; the visible count matches the supplied synthetic expectation.'
    status = 'passed'
    if assertion.expected_count is None or not assertion.dataset_id or not assertion.dataset_at:
        status, reason = 'inconclusive', 'Expected count, synthetic dataset identity or timestamp is missing.'
    elif not 0 <= (at - assertion.dataset_at).total_seconds() <= assertion.max_age_seconds:
        status, reason = 'inconclusive', 'Expected dataset is stale or dated in the future.'
    elif dataset != assertion.dataset_id or dataset_at != assertion.dataset_at:
        status, reason = 'inconclusive', 'Visible dataset identity/time does not match the supplied expectation.'
    elif count is None or observation.get('context_truncated') or len(text) >= 6000 or observation.get('errors'):
        status, reason = 'inconclusive', 'Count evidence is missing, ambiguous, truncated or accompanied by a page error.'
    elif abs(count - assertion.expected_count) > assertion.tolerance:
        status, reason = 'failed', 'The declared filter state was reached; the visible count differs from the supplied expectation.'
    facts = [f'Filter: {assertion.filter_value};']
    if count is not None:
        facts.append(f'{assertion.count_label}: {count};')
    if dataset:
        facts.append(f'Dataset: {dataset};')
    if dataset_at:
        facts.append(f'Dataset time: {dataset_at.isoformat()};')
    result = ReportAssertion(status=status, expected=assertion, observed_count=count, observed_dataset_id=dataset,
                             observed_dataset_at=dataset_at, evaluated_at=at, state_reached=True, reason=reason, evidence_refs=['assertion:1'])
    return {'result': result.model_dump(mode='json'), 'evidence': {'id': 'assertion:1', 'source': 'assertion', 'step': step,
                                                               'url': observation['url'], 'observed': ' '.join(facts)}}


def finish(assertion: FilterCountAssertion, outcome: dict | None, status: str, at: datetime | None = None) -> dict:
    if outcome:
        return ReportAssertion.model_validate(outcome['result']).model_dump(mode='json')
    blocked = status in {'captcha', 'bot_wall', 'safe_stop', 'site_block'}
    return ReportAssertion(status='blocked' if blocked else 'inconclusive', expected=assertion, evaluated_at=at or now(),
                           reason='A site or safety boundary prevented the declared state from being checked.' if blocked else
                           'No executed observation confirmed the declared filter state. Controller completion and count correctness remain separate.').model_dump(mode='json')
