"""Lost-response retries must replay results instead of creating runs or advancing the graph again."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

from app import db, main, migrate
from app.agent import runtime
from app.agent.schema import PersonaStep
from tests import test_migrate
from tests.conftest import USER
from tests.test_persona import page, use

HOME = page("https://fixture.test/", [{"id": 1, "tag": "a", "text": "Guide"}])
START = {"site": "https://fixture.test", "goal": "read the guide", "observation": HOME}
CLICK = PersonaStep(thought="Read the guide", action="click", target_id=1, confusion=0)
cluster = test_migrate.cluster
conn = test_migrate.conn


@pytest.fixture(autouse=True)
def claims(conn, monkeypatch):
    migrate.up(conn)
    conn.execute("insert into auth.users(id) values (%s)", (USER,))
    # HTTP routes, claim functions and constraints are real. Application rows/models remain the normal test fakes.
    def rpc(name, args):
        assert name in {"claim_run_request", "finish_run_request", "expire_run_requests"}
        values = [Jsonb(value) if isinstance(value, dict) else value for value in args.values()]
        with psycopg.connect(conn.info.dsn, autocommit=True) as c:
            return c.execute(f"select public.{name}({','.join(['%s'] * len(values))})", values).fetchone()[0]
    monkeypatch.setattr(db, "rpc", rpc)
    return conn


def key():
    return {"Idempotency-Key": str(uuid.uuid4())}


@pytest.mark.parametrize("revision", [None, "snapshot-1"])
def test_duplicate_start_returns_the_original_run_without_spending_twice(monkeypatch, fake_db, revision):
    model = use([CLICK, CLICK], monkeypatch)
    client, headers = TestClient(main.app), key()
    body = START | {"observation": HOME | {"revision": revision}}
    first = client.post("/runs", json=body, headers=headers)
    retry = client.post("/runs", json=body, headers=headers)
    assert first.status_code == retry.status_code == 200
    assert first.json() == retry.json()
    assert len(fake_db) == 1 and model.calls == 1
    assert first.json()["action"]["observation_revision"] == revision


@pytest.mark.parametrize("revision", [None, "snapshot-2"])
def test_duplicate_observation_does_not_consume_the_next_action(monkeypatch, revision):
    model = use([CLICK, CLICK, CLICK], monkeypatch)
    client = TestClient(main.app)
    started = client.post("/runs", json=START).json()
    run_id = started["run_id"]
    headers = key()
    body = {"observation": HOME | {"revision": revision}, "action_id": started["action_id"]}
    first = client.post(f"/runs/{run_id}/observe", json=body, headers=headers)
    retry = client.post(f"/runs/{run_id}/observe", json=body, headers=headers)
    assert first.status_code == retry.status_code == 200
    assert first.json() == retry.json() and model.calls == 2
    assert first.json()["action"]["observation_revision"] == revision


def test_wait_start_and_observe_replies_replay_without_another_action(monkeypatch):
    wait = PersonaStep(thought="Observe the pending page", action="wait", wait_condition="text_changed", confusion=0)
    model = use([wait, wait, wait], monkeypatch)
    client, headers = TestClient(main.app), key()
    observation = HOME | {"revision": "navigation-3", "navigation_version": 3}
    body = START | {"observation": observation}
    first = client.post("/runs", json=body, headers=headers)
    retry = client.post("/runs", json=body, headers=headers)
    assert first.status_code == 200 and first.json() == retry.json() and model.calls == 1
    assert first.json()["action"]["observation_revision"] == "navigation-3"
    begun = first.json()
    observed = {"observation": observation | {"executor_result": {"action": "wait", "status": "timeout", "elapsed_ms": 1000}},
                "action_id": begun["action_id"]}
    headers = key()
    first = client.post(f"/runs/{begun['run_id']}/observe", json=observed, headers=headers)
    retry = client.post(f"/runs/{begun['run_id']}/observe", json=observed, headers=headers)
    assert first.status_code == 200 and first.json() == retry.json() and model.calls == 2
    assert first.json()["action"]["action"] == "wait"


def test_changed_payload_operation_or_user_never_replays_someone_elses_intent(monkeypatch, claims):
    model = use([CLICK, CLICK], monkeypatch)
    client, headers = TestClient(main.app), key()
    first = client.post("/runs", json=START, headers=headers)
    assert first.status_code == 200
    assert client.post("/runs", json=START | {"goal": "read pricing"}, headers=headers).status_code == 409
    assert client.post(f"/runs/{first.json()['run_id']}/stop", json={}, headers=headers).status_code == 409
    other = str(uuid.uuid4())
    claims.execute("insert into auth.users(id) values (%s)", (other,))
    main.app.dependency_overrides[main.require_user] = lambda: {"id": other}
    assert client.post(f"/runs/{first.json()['run_id']}/stop", json={}, headers=headers).status_code == 404
    second = client.post("/runs", json=START, headers=headers)
    assert second.status_code == 200 and second.json()["run_id"] != first.json()["run_id"] and model.calls == 2


def test_stale_action_with_a_new_key_cannot_advance_the_next_action(monkeypatch):
    model = use([CLICK, CLICK], monkeypatch)
    client = TestClient(main.app)
    first = client.post("/runs", json=START).json()
    url = f"/runs/{first['run_id']}/observe"
    body = {"observation": HOME, "action_id": first["action_id"]}
    assert client.post(url, json=body, headers=key()).status_code == 200
    assert client.post(url, json=body, headers=key()).status_code == 409
    assert model.calls == 2


def test_simultaneous_start_and_inflight_run_mutations_are_not_executed(monkeypatch, fake_db):
    entered, release = Event(), Event()
    calls = []
    def slow(body, user, run_id):
        calls.append(run_id)
        entered.set()
        assert release.wait(10)
        return {"run_id": run_id, "status": "done", "steps": []}
    monkeypatch.setattr(main, "_start_run", slow)
    headers = key()
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(lambda: TestClient(main.app).post("/runs", json=START, headers=headers))
        try:
            assert entered.wait(5)
            duplicate = TestClient(main.app).post("/runs", json=START, headers=headers)
            assert duplicate.status_code == 409 and duplicate.headers["retry-after"] == "2"
            fake_db[calls[0]] = {"id": calls[0], "user_id": USER, "status": "running"}
            assert TestClient(main.app).post(f"/runs/{calls[0]}/stop", json={}, headers=key()).status_code == 409
        finally:
            release.set()
        assert first.result().status_code == 200 and len(calls) == 1


def test_unknown_outcome_is_never_reexecuted_or_automatically_taken_over(monkeypatch, claims):
    calls = []
    def interrupted(body, user, run_id):
        calls.append(run_id)
        raise psycopg.OperationalError("lost acknowledgement")
    monkeypatch.setattr(main, "_start_run", interrupted)
    client, headers = TestClient(main.app), key()
    assert client.post("/runs", json=START, headers=headers).status_code == 503
    claims.execute("update public.run_requests set created_at = now() - interval '7 days'")
    db.expire_run_requests()
    replay = client.post("/runs", json=START, headers=headers)
    assert replay.status_code == 409 and replay.headers["x-walkthru-code"] == "request_outcome_unknown"
    assert len(calls) == 1


def test_completed_stop_is_replayed_even_when_the_report_changes(monkeypatch, fake_db, inline_jobs):
    use([CLICK], monkeypatch)
    client = TestClient(main.app)
    started = client.post("/runs", json=START).json()
    run_id = started["run_id"]
    headers = key()
    first = client.post(f"/runs/{run_id}/stop", json={"reason": "Stopped by owner"}, headers=headers)
    fake_db[run_id]["report"] = {"title": "Finished writing"}
    retry = client.post(f"/runs/{run_id}/stop", json={"reason": "Stopped by owner"}, headers=headers)
    assert first.status_code == retry.status_code == 200 and first.json() == retry.json()
    assert inline_jobs.count("finish_run") == 1 and retry.headers["idempotency-replayed"] == "true"
    assert first.headers["x-request-id"] != retry.headers["x-request-id"]


def test_expired_response_becomes_tombstone_and_run_deletion_erases_cache(monkeypatch, claims):
    use([CLICK, CLICK], monkeypatch)
    client, headers = TestClient(main.app), key()
    assert client.post("/runs", json=START, headers=headers).status_code == 200
    claims.execute("update public.run_requests set finished_at = now() - interval '25 hours'")
    db.expire_run_requests()
    assert client.post("/runs", json=START, headers=headers).status_code == 410
    headers = key()
    second = client.post("/runs", json=START, headers=headers).json()
    claims.execute("insert into public.runs(id,user_id,site,goal,persona,tier) values (%s,%s,'https://fixture.test','guide','first_timer','free')", (second["run_id"], USER))
    claims.execute("delete from public.runs where id = %s", (second["run_id"],))
    assert client.post("/runs", json=START, headers=headers).status_code == 410
    assert claims.execute("select count(*) from public.run_requests where response is not null").fetchone()[0] == 0
    assert claims.execute("select count(*) from public.run_requests").fetchone()[0] == 2
    claims.execute("delete from auth.users where id = %s", (USER,))
    assert claims.execute("select count(*) from public.run_requests").fetchone()[0] == 0


def test_claim_rpc_retries_have_one_owner_and_browser_roles_cannot_call_them(claims):
    request_key, owner, run_id = (str(uuid.uuid4()) for _ in range(3))
    args = (USER, request_key, "start", "a" * 64, owner, run_id)
    assert db.claim_run_request(*args)["state"] == db.claim_run_request(*args)["state"] == "claimed"
    assert db.claim_run_request(*args[:4], str(uuid.uuid4()), run_id)["state"] == "pending"
    assert db.finish_run_request(USER, request_key, str(uuid.uuid4()), "complete", 200, {}, {}) is False
    assert db.finish_run_request(USER, request_key, owner, "complete", 200, {}, {}) is True
    assert db.finish_run_request(USER, request_key, owner, "complete", 200, {}, {}) is True
    assert db.finish_run_request(USER, request_key, owner, "complete", 200, {"changed": True}, {}) is False
    for role in ("anon", "authenticated"):
        claims.execute(f"set role {role}")
        try:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                claims.execute("select public.expire_run_requests()")
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                claims.execute("select * from public.run_requests")
        finally:
            claims.execute("reset role")


def test_mutating_graph_call_is_not_repeated_after_database_acknowledgement_loss(monkeypatch):
    calls = []
    class InterruptedGraph:
        def invoke(self, value, config):
            calls.append(value)
            raise psycopg.OperationalError("acknowledgement lost after applying state")
    monkeypatch.setattr(runtime, "graph", lambda tier: InterruptedGraph())
    with pytest.raises(psycopg.OperationalError):
        runtime.invoke("free", {}, {})
    assert len(calls) == 1


def test_lost_completion_acknowledgement_replays_the_committed_response(monkeypatch, fake_db):
    model = use([CLICK], monkeypatch)
    finish = db.finish_run_request
    def lost_ack(*args):
        result = finish(*args)
        if args[3] == "complete":
            raise psycopg.OperationalError("completion committed but reply lost")
        return result
    monkeypatch.setattr(db, "finish_run_request", lost_ack)
    client, headers = TestClient(main.app), key()
    first = client.post("/runs", json=START, headers=headers)
    assert first.status_code == 503
    retry = client.post("/runs", json=START, headers=headers)
    assert retry.status_code == 200 and retry.headers["idempotency-replayed"] == "true"
    assert retry.json()["run_id"] in fake_db and len(fake_db) == model.calls == 1


def test_pending_claim_survives_age_and_deletion_fences_late_completion(claims):
    request_key, owner, run_id = (str(uuid.uuid4()) for _ in range(3))
    args = (USER, request_key, "start", "b" * 64, owner, run_id)
    assert db.claim_run_request(*args)["state"] == "claimed"
    claims.execute("update public.run_requests set created_at = now() - interval '7 days'")
    db.expire_run_requests()
    assert db.claim_run_request(*args[:4], str(uuid.uuid4()), run_id)["state"] == "pending"
    claims.execute("insert into public.runs(id,user_id,site,goal,persona,tier) values (%s,%s,'https://fixture.test','guide','first_timer','free')", (run_id, USER))
    claims.execute("delete from public.runs where id = %s", (run_id,))
    assert db.finish_run_request(USER, request_key, owner, "complete", 200, {"secret": "deleted"}, {}) is False
    assert db.claim_run_request(*args)["state"] == "gone"
    assert claims.execute("select response from public.run_requests").fetchone()[0] is None


def test_invalid_keys_missing_actions_and_stale_requests_do_no_work(monkeypatch):
    model = use([CLICK, CLICK], monkeypatch)
    client = TestClient(main.app)
    assert client.post("/runs", json=START, headers={"Idempotency-Key": "bad"}).status_code == 422
    assert model.calls == 0
    started = client.post("/runs", json=START).json()
    url = f"/runs/{started['run_id']}/observe"
    assert client.post(url, json={"observation": HOME}, headers=key()).status_code == 422
    headers = key()
    body = {"observation": HOME, "action_id": str(uuid.uuid4())}
    first = client.post(url, json=body, headers=headers)
    replay = client.post(url, json=body, headers=headers)
    assert first.status_code == replay.status_code == 409 and first.json() == replay.json()
    assert replay.headers["idempotency-replayed"] == "true" and model.calls == 1


def test_browser_preflight_accepts_request_keys():
    response = TestClient(main.app).options("/runs", headers={
        "Origin": main.WEB_URL, "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type,idempotency-key",
    })
    assert response.status_code == 200
    assert "idempotency-key" in response.headers["access-control-allow-headers"].lower()
