"""R-S13: a targeted recheck compares the declared count check like for like. A fix needs the same declared
conditions and a real passed result; missing coverage and changed conditions never read as fixed."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.agent import compare, report
from app.agent.schema import Comparison, Report
from app.main import app
from app.main import finish_run as real_finish_run  # imported before the test fixture swaps it out
from tests.conftest import USER
from tests.test_assertions import assessment

SITE = "https://fixture.test/"
GOAL = "Filter Active records"


def row(rep, **changes):
    return {"report": rep, "persona": "first_timer", "logged_in": True, **changes}


def declared(status, count=None, **expected):
    base = {"path": "/dashboard", "filter_value": "Active", "count_label": "Filtered records", "expected_count": 2,
            "dataset_id": "synthetic-sales-v1", "dataset_at": "2026-10-06T04:00:00+00:00", "max_age_seconds": 3600, "tolerance": 0}
    return {"assessment": {"assertions": [{"status": status, "observed_count": count, "reason": f"{status} reason", "expected": base | expected}]}}


@pytest.mark.parametrize(("before", "after", "verdict"), [("failed", "passed", "fixed"), ("failed", "failed", "still_failing"),
                                                          ("passed", "failed", "regressed"), ("passed", "passed", "still_passing"),
                                                          ("inconclusive", "passed", "first_result"), ("blocked", "failed", "first_result")])
def test_like_for_like_verdicts(before, after, verdict):
    got = compare.recheck_assertion(row(declared(before, 3)), row(declared(after, 2)))
    assert got["verdict"] == verdict and got["before"] == before and got["after"] == after
    assert got["fingerprint"] == "assertion:/dashboard|Active|Filtered records"
    Comparison.model_validate({"previous_run_id": "a", "previous_at": "t", "assertion": got})


@pytest.mark.parametrize("after", ["inconclusive", "blocked"])
def test_partial_coverage_is_not_rechecked_never_fixed(after):
    got = compare.recheck_assertion(row(declared("failed", 3)), row(declared(after)))
    assert got["verdict"] == "not_rechecked" and after in got["reason"]
    missing = compare.recheck_assertion(row(declared("failed", 3)), row({"findings": []}))
    assert missing["verdict"] == "not_rechecked" and missing["after"] is None and "did not declare" in missing["reason"]
    assert compare.recheck_assertion(row({"findings": []}), row(declared("passed", 2))) is None  # nothing declared before


@pytest.mark.parametrize(("expected", "rows", "named"), [({"expected_count": 3}, {}, "expected count"), ({"dataset_id": "synthetic-sales-v2"}, {}, "dataset"),
                                                         ({"tolerance": 1}, {}, "tolerance"), ({}, {"persona": "skeptic"}, "persona"),
                                                         ({}, {"logged_in": False}, "logged in"), ({"filter_value": "Archived"}, {}, "different path, filter")])
def test_changed_conditions_are_not_comparable(expected, rows, named):
    got = compare.recheck_assertion(row(declared("failed", 3)), row(declared("passed", 2, **expected), **rows))
    assert got["verdict"] == "not_comparable" and named in got["reason"]


def test_a_fresh_dataset_time_is_not_a_changed_condition():
    later = declared("passed", 2, dataset_at="2026-10-07T09:00:00+00:00")
    assert compare.recheck_assertion(row(declared("failed", 3)), row(later))["verdict"] == "fixed"


def test_a_paid_rerun_with_the_same_declaration_reports_the_fix(fake_db):
    fake_db["old"] = {"id": "old", "user_id": USER, "site": SITE, "goal": GOAL, "persona": "first_timer", "logged_in": False, "kind": "test",
                      "tier": "paid", "status": "done", "steps": [], "report": assessment(3), "created_at": (datetime.now(UTC) - timedelta(days=1)).isoformat()}
    current = {"id": "new", "user_id": USER, "site": SITE, "goal": GOAL, "persona": "first_timer", "logged_in": False, "tier": "paid"}
    result = Comparison.model_validate(compare.attach(current, assessment(2), status="done"))
    assert result.assertion.verdict == "fixed" and (result.assertion.before_count, result.assertion.after_count) == (3, 2)


def test_the_report_job_stores_the_recheck_and_old_comparisons_still_read(monkeypatch, fake_db):
    fake_db["old"] = {"id": "old", "user_id": USER, "site": SITE, "goal": GOAL, "persona": "first_timer", "logged_in": False, "kind": "test",
                      "tier": "paid", "status": "done", "steps": [], "report": assessment(3), "created_at": (datetime.now(UTC) - timedelta(days=1)).isoformat()}
    fake_db["r1"] = {"id": "r1", "user_id": USER, "site": SITE, "goal": GOAL, "persona": "first_timer", "logged_in": False, "kind": "test", "tier": "paid",
                     "status": "done", "steps": [], "report": None, "email": None, "created_at": datetime.now(UTC).isoformat()}
    monkeypatch.setattr(report, "run_report", lambda *a, **k: Report.model_validate(assessment(2)))
    real_finish_run("r1", {})
    assert fake_db["r1"]["report"]["comparison"]["assertion"]["verdict"] == "fixed"
    assert Comparison.model_validate({"previous_run_id": "a", "previous_at": "t", "fixed": []}).assertion is None


def f(kind, title):
    return {"kind": kind, "severity": "medium", "title": title, "detail": "d", "fix": "x", "evidence": None}


def test_duplicate_findings_count_once():
    a = f("seo", "Missing meta description")
    assert len(compare.compare([a], [a, a])["still_broken"]) == 1
    assert len(compare.compare([a, a], [])["fixed"]) == 1


def test_ux_findings_from_an_unfinished_journey_are_not_called_fixed():
    stuck, seo = f("ux", "Sign up button hidden behind the cookie banner"), f("seo", "Missing meta description")
    unfinished = compare.compare([stuck, seo], [], journey_finished=False)
    assert [x["title"] for x in unfinished["not_rechecked"]] == [stuck["title"]] and [x["title"] for x in unfinished["fixed"]] == [seo["title"]]
    assert [x["title"] for x in compare.compare([stuck], [], journey_finished=True)["fixed"]] == [stuck["title"]]
    assert [x["title"] for x in compare.compare([stuck], [])["fixed"]] == [stuck["title"]]  # callers without a status keep the old answer


def test_recheck_terms_repeat_the_latest_declaration_without_a_stale_dataset_time(fake_db):
    client = TestClient(app)
    assert client.get("/me/recheck", params={"site": SITE}).json() == {"run_id": None}
    fake_db["old"] = {"id": "old", "user_id": USER, "site": SITE + "dashboard", "goal": GOAL, "persona": "first_timer", "logged_in": True,
                      "kind": "test", "tier": "paid", "status": "done", "steps": [], "report": assessment(3), "created_at": datetime.now(UTC).isoformat()}
    got = client.get("/me/recheck", params={"site": SITE}).json()
    assert got["run_id"] == "old" and got["goal"] == GOAL and got["persona"] == "first_timer" and got["logged_in"] is True and got["status"] == "failed"
    assert got["assertion"]["filter_value"] == "Active" and got["assertion"]["expected_count"] == 2 and got["assertion"]["dataset_at"] is None
    assert client.get("/me/recheck", params={"site": "https://other.test/"}).json() == {"run_id": None}
    fake_db["theirs"] = fake_db["old"] | {"id": "theirs", "user_id": "someone-else", "created_at": (datetime.now(UTC) + timedelta(minutes=1)).isoformat()}
    assert client.get("/me/recheck", params={"site": SITE}).json()["run_id"] == "old"  # never another account's declaration
