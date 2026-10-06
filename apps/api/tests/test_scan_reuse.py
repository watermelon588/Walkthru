"""R-S7a: a saved Instant Scan is reused only when current and labelled; fresh checks bypass it; simultaneous misses
start one scan; reuse keys never hold the URL."""

import threading
import time
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app import main, scan_reuse
from app.agent import runtime

SITE = "https://example.test/"


def saved(fake_db, run_id="saved", age=30, version=None, **changes):
    fake_db[run_id] = {"id": run_id, "site": SITE, "kind": "scan", "tier": "free", "user_id": None, "public": True, "status": "done",
                       "report": {"summary": run_id, "scan_version": scan_reuse.version() if version is None else version},
                       "created_at": (datetime.now(UTC) - timedelta(seconds=age)).isoformat(), **changes}
    return fake_db[run_id]


@pytest.fixture
def scans(monkeypatch, fake_db):
    """A stand-in for run_scan that records each real scan and saves a current report, like the real one."""
    monkeypatch.setattr(main.fetch, "assert_public", lambda site: None)
    started = []

    def scan(site, delay=0.0, **_):
        started.append(site)
        time.sleep(delay)
        run_id = f"new{len(started)}"
        saved(fake_db, run_id, age=0)
        return run_id, {"site": site, "report": fake_db[run_id]["report"]}

    monkeypatch.setattr(main, "run_scan", scan)
    return started


def post(**body):
    return TestClient(main.app).post("/scans", json={"site": SITE, **body})


def test_current_saved_scan_is_reused_and_labelled(fake_db, scans):
    row = saved(fake_db, age=125)
    reuse = post().json()["reuse"]
    assert scans == [] and reuse["status"] == "reused" and reuse["source_run_id"] == "saved"
    assert reuse["observed_at"] == row["created_at"] and 125 <= reuse["age_seconds"] < 135
    assert datetime.fromisoformat(reuse["reused_until"]) == datetime.fromisoformat(row["created_at"]) + timedelta(seconds=600)
    assert reuse["scan_version"] == scan_reuse.version()


@pytest.mark.parametrize("version", ["older-code", ""])
def test_scans_from_other_code_or_before_versioning_are_never_reused(fake_db, scans, version):
    saved(fake_db, version=version)
    if version == "":
        del fake_db["saved"]["report"]["scan_version"]  # reports saved before R-S7a
    body = post().json()
    assert scans == [SITE] and body["run_id"] == "new1" and body["reuse"]["status"] == "fresh"


def test_version_follows_scanner_report_and_model_configuration(monkeypatch):
    first = scan_reuse.version()
    monkeypatch.setattr(runtime, "GROQ_MODELS", ["another/model"])
    scan_reuse.version.cache_clear()
    try:
        assert scan_reuse.version() != first
    finally:
        monkeypatch.undo()
        scan_reuse.version.cache_clear()
    assert scan_reuse.version() == first
    assert any(p.name == "report.py" for p in scan_reuse.Path(scan_reuse.__file__).parent.glob("agent/report.py"))


def test_real_run_scan_stamps_the_current_version(monkeypatch, fake_db):
    class Page:
        status_code, url, text = 200, SITE, "<h1>Hello</h1>"

    monkeypatch.setattr(main.fetch, "assert_public", lambda site: None)
    monkeypatch.setattr(main.fetch, "get", lambda client, site: Page())
    monkeypatch.setattr(main.report, "run_report", lambda *a, **k: main.report.Report(summary="ok", findings=[], top_fixes=[]))
    run_id, result = main.run_scan(SITE)
    assert fake_db[run_id]["report"]["scan_version"] == scan_reuse.version() == result["report"]["scan_version"]


def test_fresh_check_bypasses_a_current_scan_but_pays_every_limit(fake_db, scans, monkeypatch):
    saved(fake_db)
    body = post(fresh=True).json()
    assert scans == [SITE] and body["run_id"] == "new1" and body["reuse"]["status"] == "fresh"
    monkeypatch.setattr(main.db, "free_runs_today", lambda kind: main.plans.FREE_SCANS_PER_DAY)
    assert post(fresh=True).status_code == 429  # daily free capacity, even though a saved scan exists
    assert post().json()["reuse"]["status"] == "reused"  # the ordinary request still reuses at capacity
    monkeypatch.setattr(main, "SCAN_LIMIT", 0)
    assert post(fresh=True).status_code == 429  # per-address limit


def test_simultaneous_misses_in_one_process_start_one_scan(fake_db, scans, monkeypatch):
    original = main.run_scan
    monkeypatch.setattr(main, "run_scan", lambda site, **_: original(site, delay=0.3))
    out = []
    threads = [threading.Thread(target=lambda: out.append(post().json())) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert scans == [SITE]
    assert sorted(r["reuse"]["status"] for r in out) == ["coalesced", "coalesced", "coalesced", "fresh"]
    assert {r["run_id"] for r in out} == {"new1"}


def test_a_scan_running_in_another_process_is_awaited_not_repeated(fake_db, scans, rate_limits, monkeypatch):
    monkeypatch.setattr(scan_reuse, "POLL_SECONDS", 0.02)
    rate_limits[f"scanflight:{scan_reuse.flight_key(SITE, None)}"] = 1  # another API process holds the claim
    threading.Timer(0.1, lambda: saved(fake_db, "other", age=0)).start()
    body = post().json()
    assert scans == [] and body["run_id"] == "other" and body["reuse"]["status"] == "coalesced"


def test_when_the_other_scan_never_lands_the_caller_retries_instead_of_scanning_twice(fake_db, scans, rate_limits, monkeypatch):
    monkeypatch.setattr(scan_reuse, "WAIT_SECONDS", 0.1)
    monkeypatch.setattr(scan_reuse, "POLL_SECONDS", 0.02)
    rate_limits[f"scanflight:{scan_reuse.flight_key(SITE, None)}"] = 1
    response = post()
    assert response.status_code == 503 and response.headers["retry-after"] == "30" and scans == []


def test_a_waiting_fresh_check_rejects_evidence_from_before_it_asked(fake_db, scans, rate_limits, monkeypatch):
    monkeypatch.setattr(scan_reuse, "WAIT_SECONDS", 0.1)
    monkeypatch.setattr(scan_reuse, "POLL_SECONDS", 0.02)
    saved(fake_db, age=5)  # current, but observed before the fix the owner wants to check
    rate_limits[f"scanflight:{scan_reuse.flight_key(SITE, 'saved')}"] = 1
    assert post(fresh=True).status_code == 503 and scans == []


def test_reuse_keys_hold_no_url_or_query(fake_db, scans, rate_limits):
    TestClient(main.app).post("/scans", json={"site": "https://example.test/?token=secret-value"})
    flight = [k for k in rate_limits if k.startswith("scanflight:")]
    assert len(flight) == 1 and "secret" not in flight[0] and "example" not in flight[0]


def test_unshared_or_deleted_saved_scans_stop_being_reused_at_once(fake_db, scans):
    saved(fake_db)
    assert post().json()["reuse"]["status"] == "reused"
    fake_db["saved"]["public"] = False
    assert post().json()["run_id"] == "new1"
    fake_db["new1"]["public"] = False  # unshared within the claim window: the finished scan freed the next claim
    assert post().json()["run_id"] == "new2"


def test_a_second_fresh_check_right_after_the_first_starts_its_own_scan(fake_db, scans):
    assert [post(fresh=True).json()["run_id"] for _ in range(2)] == ["new1", "new2"] and len(scans) == 2


latest = main.db.latest_public_scan_id  # the real query, captured before the autouse fake replaces it


def test_claim_generation_query_is_anonymous_free_exact_and_any_status(monkeypatch):
    seen = []
    monkeypatch.setattr(main.db, "_rows", lambda params: seen.append(params) or [{"id": "row"}])
    assert latest("https://example.test/a?x=1") == "row"
    assert seen == [{"site": "eq.https://example.test/a?x=1", "kind": "eq.scan", "tier": "eq.free", "user_id": "is.null",
                     "order": "created_at.desc,id.desc", "limit": "1", "select": "id"}]
