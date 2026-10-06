"""One owner-defined synthetic filtered-count assertion; no provider or external data."""
from datetime import UTC, datetime, timedelta

import pytest
from langgraph.types import Command

from app.agent.assertions import evaluate, finish, mission_plan
from app.agent.schema import FilterCountAssertion
from tests.test_completion import session

NOW = datetime(2026, 10, 6, 4, 0, tzinfo=UTC)


def definition(**changes):
    return FilterCountAssertion.model_validate({'path': '/dashboard', 'filter_value': 'Active', 'count_label': 'Filtered records',
        'expected_count': 2, 'dataset_id': 'synthetic-sales-v1', 'dataset_at': NOW.isoformat(), 'max_age_seconds': 3600, 'tolerance': 0, **changes})


def observation(count=2, **changes):
    return {'url': 'https://fixture.test/dashboard', 'text': f'Filter: Active Filtered records: {count} Dataset: synthetic-sales-v1 Dataset time: {NOW.isoformat()}', 'elements': [], **changes}


@pytest.mark.parametrize('count,tolerance,status', [(2,0,'passed'),(3,0,'failed'),(3,1,'passed')])
def test_declared_count_is_separate_from_reaching_the_ui_state(count, tolerance, status):
    value = evaluate(definition(tolerance=tolerance), observation(count), 'https://fixture.test/', 1, NOW)
    assert value['result']['status'] == status and value['result']['state_reached'] is True
    assert value['result']['observed_count'] == count
    assert value['evidence']['source'] == 'assertion'


@pytest.mark.parametrize('changes', [{'expected_count': None}, {'dataset_id': None}, {'dataset_at': None}, {'dataset_at': (NOW-timedelta(hours=2)).isoformat()}, {'dataset_at': (NOW+timedelta(minutes=1)).isoformat()}])
def test_missing_stale_and_future_expectations_are_inconclusive(changes):
    value = evaluate(definition(**changes), observation(), 'https://fixture.test/', 1, NOW)
    assert value['result']['status'] == 'inconclusive'


@pytest.mark.parametrize('changes', [{'text': 'Filter: Active Filtered records: 2'}, {'text': 'Filter: Active Filtered records: 2 Filtered records: 3'}, {'url': 'https://other.test/dashboard'}, {'note': 'stale target: replaced'}, {'context_truncated': True}])
def test_missing_ambiguous_inaccessible_or_unexecuted_evidence_does_not_pass(changes):
    value = evaluate(definition(), observation(**changes), 'https://fixture.test/', 1, NOW)
    assert value is None or value['result']['status'] == 'inconclusive'


def test_genuine_boundary_is_blocked_and_controller_loss_is_inconclusive():
    assert finish(definition(), None, 'captcha', NOW)['status'] == 'blocked'
    assert finish(definition(), None, 'agent_lost', NOW)['status'] == 'inconclusive'


def test_graph_finishes_state_but_retains_failed_assertion(monkeypatch):
    from app.agent import assertions
    monkeypatch.setattr(assertions, 'now', lambda: NOW)
    declared = definition().model_dump(mode='json')
    graph, cfg, model, _ = session(goal='Open dashboard and filter Active', checkpoints=mission_plan(definition(), 'Open dashboard and filter Active')['checkpoints'], assertion=declared)
    value = graph.invoke(Command(resume={'observation': observation(3)}), cfg)
    assert value['status'] == 'done' and model.calls == 1
    assert value['assertion_outcome']['result']['status'] == 'failed'
    assert value['assertion_outcome']['result']['state_reached'] is True


def test_multiple_filter_regions_cannot_confirm_the_declared_state():
    assert evaluate(definition(), observation(text=observation()['text'] + ' Filter: Archived'), 'https://fixture.test/', 1, NOW) is None


def test_longer_filter_name_is_not_a_matching_filter():
    assert evaluate(definition(), observation(text=observation()['text'].replace('Filter: Active', 'Filter: Active users')), 'https://fixture.test/', 1, NOW) is None


def test_a_second_unparseable_count_label_is_still_ambiguous():
    value = evaluate(definition(), observation(text=observation()['text'] + ' Filtered records: loading'), 'https://fixture.test/', 1, NOW)
    assert value['result']['status'] == 'inconclusive' and value['result']['observed_count'] is None


def test_definition_rejects_connectors_naive_dates_and_coerced_counts():
    for changes in ({'connector': 'database'}, {'dataset_at': '2026-10-06T04:00:00'}, {'expected_count': '2'}):
        with pytest.raises(ValueError):
            definition(**changes)


def assessment(count=3):
    from app.agent.report_contract import build_assessment
    from app.agent.schema import Report
    state = {'site': 'https://fixture.test/', 'goal': 'Filter Active records', 'status': 'done',
             'checkpoints': mission_plan(definition(), 'Filter Active records')['checkpoints'],
             'steps': [{'action': 'click', 'result_url': 'https://fixture.test/dashboard',
                        'checkpoint_evidence': {'checkpoint': 1, 'step': 1, 'url': 'https://fixture.test/dashboard', 'signal': 'public_text', 'matched': 'Filter: Active'}}],
             'assertion': definition().model_dump(mode='json'), 'assertion_outcome': evaluate(definition(), observation(count), 'https://fixture.test/', 1, NOW)}
    value = build_assessment(state, [], [], {})
    return Report(version=2, summary='Scoped synthetic filter check', findings=[], top_fixes=[], assessment=value).model_dump(mode='json')


def test_report_retains_failed_count_and_completed_state_without_invented_findings():
    from app.agent.report_chapters import chapters
    from app.agent.report_contract import ensure_supported, scope_lines
    value = assessment()
    ensure_supported(value)
    assert value['assessment']['outcome'] == 'completed'
    assert value['assessment']['assertions'][0]['status'] == 'failed'
    assert value['findings'] == []
    journey = chapters(value, 'test', 'done')[0]
    assert journey['status'] == 'unconfirmed' and 'filtered count: failed' in journey['summary']
    assert 'failed' in ' '.join(scope_lines(value)) and 'synthetic-sales-v1' in ' '.join(scope_lines(value))


@pytest.mark.parametrize('field,value', [('step', 99), ('observed', 'Filter: Active; Filtered records: 3; Dataset: other;')])
def test_saved_assertion_rejects_unrelated_step_or_dataset(field, value):
    from app.agent.report_contract import ensure_supported
    saved = assessment()
    saved['assessment']['evidence_index'][-1][field] = value
    with pytest.raises(ValueError, match='invalid evidence'):
        ensure_supported(saved)


def test_assertion_requires_owner_verification_before_using_a_run(fake_db):
    from fastapi.testclient import TestClient

    from app.main import app
    response = TestClient(app).post('/runs', json={'site': 'https://fixture.test/', 'goal': 'Filter Active records',
        'observation': {'url': 'https://fixture.test/', 'title': 'Fixture', 'text': 'Fixture', 'elements': []}, 'assertion': definition().model_dump(mode='json')})
    assert response.status_code == 403 and 'Verify ownership' in response.json()['detail']
    assert not fake_db


def test_verified_assertion_uses_deterministic_plan_and_retains_definition(monkeypatch):
    from fastapi.testclient import TestClient
    from langgraph.checkpoint.memory import MemorySaver

    from app import main
    from app.agent import goal, runtime
    from app.agent.persona import build_graph
    from tests.test_completion import Script
    monkeypatch.setattr(main, '_verified', lambda site, uid: True)
    monkeypatch.setattr(goal, 'plan', lambda *a, **kw: pytest.fail('A declared assertion needs no planner model'))
    graph = build_graph(Script(['click']), MemorySaver())
    monkeypatch.setattr(runtime, 'graph', lambda tier: graph)
    response = TestClient(main.app).post('/runs', json={'site': 'https://fixture.test/', 'goal': 'Filter Active records',
        'observation': {'url': 'https://fixture.test/', 'title': 'Fixture', 'text': 'Fixture', 'elements': [{'id': 1, 'tag': 'button', 'text': 'Active'}]}, 'assertion': definition().model_dump(mode='json')})
    assert response.status_code == 200
    run_id = response.json()['run_id']
    retained = graph.get_state(main._cfg(run_id)).values
    assert retained['assertion']['expected_count'] == 2 and retained['verified'] is True


def test_shared_assertion_fixture_roundtrips():
    import json
    from pathlib import Path

    from app.agent.schema import Report
    saved = json.loads((Path(__file__).resolve().parents[2] / 'web/tests/fixtures/report-assertion.json').read_text())
    assert Report.model_validate(saved).model_dump(mode='json') == saved


def test_fractional_dataset_timestamp_survives_report_privacy_masking():
    from app.agent.report_contract import build_assessment
    stamp = NOW.replace(microsecond=123000)
    declared = definition(dataset_at=stamp)
    obs = observation(text=observation()['text'].replace(NOW.isoformat(), stamp.isoformat()))
    outcome = evaluate(declared, obs, 'https://fixture.test/', 1, stamp)
    report = build_assessment({'status': 'done', 'steps': [{'action': 'click', 'result_url': obs['url']}],
        'assertion': declared.model_dump(mode='json'), 'assertion_outcome': outcome}, [], [], {})
    assert report.assertions[0].status == 'passed'
    assert stamp.isoformat() in report.evidence_index[-1].observed


def test_private_looking_dataset_labels_are_not_retained():
    with pytest.raises(ValueError):
        definition(dataset_id='sk_private_token1234')
    value = evaluate(definition(), observation(text=observation()['text'].replace('synthetic-sales-v1', 'sk_private_token1234')), 'https://fixture.test/', 1, NOW)
    assert value['result']['status'] == 'inconclusive'
    assert value['result']['observed_dataset_id'] is None


def test_inconclusive_observations_still_need_recorded_evidence():
    from app.agent.schema import ReportAssertion
    value = assessment()['assessment']['assertions'][0]
    value.update(status='inconclusive', evidence_refs=[])
    with pytest.raises(ValueError, match='recorded evidence'):
        ReportAssertion.model_validate(value)


def test_full_chat_and_mcp_keep_assertion_context_without_findings():
    from app import mcp_server
    from app.agent import fix_prompt
    rep = assessment()
    row = {'id': 'a'*32, 'site': 'https://fixture.test/', 'goal': 'Filter Active records', 'kind': 'test', 'status': 'done', 'created_at': NOW.isoformat(), 'report': rep}
    texts = [fix_prompt.build(row, rep, {}, style=style) for style in ('full', 'chat')]
    texts.append(mcp_server._summary(row, full=True))
    for text in texts:
        assert 'filtered_count:1: failed' in text
        assert 'synthetic-sales-v1' in text and 'tolerance: 0' in text and 'filter: Active' in text
