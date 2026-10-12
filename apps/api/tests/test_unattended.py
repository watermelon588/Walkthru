"""R-S14: nothing unattended can invent a browser session. Journeys start only from the owner's own browser (an
executed observation per step); schedules, deploy hooks and MCP stay on server scanning."""

import inspect

from fastapi.testclient import TestClient

from app import db, mcp_server, watch
from app.agent import runtime
from app.main import app
from tests.conftest import USER
from tests.test_watch_compare import fake_sites


def test_a_journey_cannot_start_without_the_owners_browser_observation():
    r = TestClient(app).post("/runs", json={"site": "https://fixture.test/", "goal": "Sign up"})
    assert r.status_code == 422 and "observation" in r.text


def test_mcp_has_no_journey_entry_point():
    source = inspect.getsource(mcp_server)
    assert "_start_run" not in source and "runtime.invoke" not in source and "/observe" not in source


def test_watch_checks_are_server_scans_never_journeys(monkeypatch, fake_db):
    sites = fake_sites(monkeypatch)  # offline: every sites table call is faked
    site = db.add_site(USER, "https://fixture.test/")
    monkeypatch.setattr(runtime, "invoke", lambda *a, **k: (_ for _ in ()).throw(AssertionError("a watch check started a journey")))
    scans = []
    monkeypatch.setattr("app.main.run_scan", lambda site, **kw: scans.append(kw["kind"]) or ("run-1", {"report": {"findings": []}}))
    watch.check(site)
    assert scans == ["watch"] and sites[site["id"]]["last_run_id"] == "run-1"
