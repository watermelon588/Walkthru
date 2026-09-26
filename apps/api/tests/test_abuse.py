"""Item 6 and part of item 8 of docs/agent-safety-plan.md: kill switches, per-target rate limits, the run audit log and
automatic suspension (app/abuse.py)."""

from fastapi.testclient import TestClient

from app import abuse, main
from app.agent.schema import PersonaStep
from app.main import app
from tests.conftest import USER
from tests.test_persona import observe, page, use

OTHER = "00000000-0000-0000-0000-000000000009"
HOME = page("https://fixture.test/", [{"id": 1, "tag": "a", "text": "Pricing"}, {"id": 2, "tag": "input", "type": "search", "text": "Search"}])


def begin(c, goal="find pricing", site="https://fixture.test"):
    return c.post("/runs", json={"site": site, "goal": goal, "observation": HOME})


def step(action="click", target=1, text=None):
    return PersonaStep(thought="next", action=action, target_id=target, text=text, confusion=0)


def test_a_global_kill_switch_stops_new_journeys_and_the_policy_endpoint_says_so(fake_db, monkeypatch):
    use([step()], monkeypatch)
    c = TestClient(app)
    assert c.get("/runs/policy").json() == {"journeys": True, "message": ""}
    fake_db.blocks.append({"id": 1, "scope": "global", "value": "", "reason": "incident"})
    abuse.forget_blocks()
    r = begin(c)
    assert r.status_code == 403 and r.headers["X-Walkthru-Code"] == "journeys_paused"
    assert c.get("/runs/policy").json()["journeys"] is False


def test_a_host_block_covers_its_subdomains_and_stops_a_running_journey(fake_db, monkeypatch):
    use([step(), step()], monkeypatch)
    c = TestClient(app)
    run = begin(c).json()
    fake_db.blocks.append({"id": 1, "scope": "host", "value": "test", "reason": "owner opted out"})
    abuse.forget_blocks()
    stopped = observe(c, run["run_id"], HOME).json()
    assert stopped["status"] == "stopped" and stopped["code"] == "journeys_paused"
    assert begin(c).headers["X-Walkthru-Code"] == "journeys_paused"  # fixture.test is under "test"


def test_too_many_journeys_against_one_unverified_host_are_refused(fake_db, monkeypatch):
    use([step()], monkeypatch)
    fake_db.audit.extend({"user_id": OTHER, "host": "fixture.test", "mode": "visitor", "goal": "g"} for _ in range(abuse.HOST_PER_HOUR))
    r = begin(TestClient(app))
    assert r.status_code == 429 and r.headers["X-Walkthru-Code"] == "rate_limited"
    monkeypatch.setattr(main, "_verified", lambda site, user_id: True)  # the owner's own site is limited by their plan
    assert begin(TestClient(app)).status_code == 200


def test_one_user_hammering_one_host_is_refused(fake_db, monkeypatch):
    use([step()], monkeypatch)
    fake_db.audit.extend({"user_id": USER, "host": "fixture.test", "mode": "visitor", "goal": "g"} for _ in range(abuse.USER_HOST_PER_HOUR))
    assert begin(TestClient(app)).headers["X-Walkthru-Code"] == "rate_limited"


def test_the_audit_log_keeps_actions_and_labels_but_never_typed_values(fake_db, monkeypatch):
    use([step("type", 2, "private search words"), step("click", 1), PersonaStep(thought="ok", action="done", confusion=0)], monkeypatch)
    c = TestClient(app)
    run = begin(c).json()
    observe(c, run["run_id"], HOME)
    observe(c, run["run_id"], page("https://fixture.test/pricing", [{"id": 1, "tag": "a", "text": "Plans"}]))  # the click worked
    [row] = [a for a in fake_db.audit if a.get("run_id") == run["run_id"]]
    assert row["mode"] == "visitor" and row["host"] == "fixture.test" and row["status"] == "done"
    assert [a["action"] for a in row["actions"]] == ["type", "click", "done"]
    assert row["actions"][0]["target"] == "Search" and row["actions"][1]["target"] == "Pricing"
    assert "private search words" not in str(row["actions"])


def test_repeated_refused_goals_pause_the_account_and_tell_the_founder(fake_db, monkeypatch):
    use([step()], monkeypatch)
    c = TestClient(app)
    for _ in range(abuse.SUSPEND_AFTER):
        assert begin(c, goal="like 50 posts").status_code == 422  # a bulk goal, refused before any model call
    assert any(b["scope"] == "user" and b["value"] == USER for b in fake_db.blocks)
    assert fake_db.events and fake_db.events[-1][0] == "abuse" and fake_db.events[-1][1] == USER
    assert begin(c).headers["X-Walkthru-Code"] == "journeys_paused"  # even an ordinary goal waits for review


def test_an_opted_out_or_paused_site_is_never_scanned(fake_db, monkeypatch):
    import pytest

    from app.agent import policy

    monkeypatch.setitem(policy.BLOCKLIST, "site owner opt-out", ["optedout.example"])
    with pytest.raises(ValueError, match="asked Walkthru not to scan"):
        main.run_scan("https://www.optedout.example/")
    fake_db.blocks.append({"id": 1, "scope": "host", "value": "paused.example", "reason": "abuse report"})
    abuse.forget_blocks()
    with pytest.raises(ValueError, match="asked Walkthru not to scan"):
        main.run_scan("paused.example")
