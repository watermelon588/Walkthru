"""Rerun and compare (Pro): each finding marked fixed, still broken or new against the previous run of the same
goal on the same site. Ignoring a finding keeps it out of those lists. Code only, never the model."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.agent import compare
from app.main import app
from app.main import finish_run as real_finish_run  # imported before the test fixture swaps it out
from tests.conftest import USER


def f(kind, title, severity="medium"):
    return {"kind": kind, "severity": severity, "title": title, "detail": "d", "fix": "x", "evidence": None}


def test_fingerprint_ignores_case_numbers_and_spacing():
    assert compare.fingerprint(f("geo", "3 more pages only render with JavaScript")) == compare.fingerprint(f("geo", "5  More pages only render with javascript"))
    assert compare.fingerprint(f("seo", "Missing meta description")) != compare.fingerprint(f("geo", "Missing meta description"))


def test_rule_id_is_preferred_and_old_report_still_compares_with_its_page_map():
    old = f("security", "No HSTS header")
    current = old | {"rule": "sec.hsts.missing"}
    assert compare.fingerprint(current) == "security:sec.hsts.missing"
    old_key, new_key = compare.fingerprint(old), compare.fingerprint(current)
    result = compare.compare([old], [current], prev_pages={old_key: ["https://site.test/a"]},
                             cur_pages={new_key: ["https://site.test/b"]},
                             audited=["https://site.test/a", "https://site.test/b"])
    assert result["fixed"] == result["new"] == []
    assert result["still_broken"][0]["pages_fixed"] == ["https://site.test/a"]
    assert result["still_broken"][0]["pages_new"] == ["https://site.test/b"]
    assert compare.compare([old], [current], {old_key}) == {"fixed": [], "still_broken": [], "new": [], "not_rechecked": []}
    assert compare.compare([old], [current], {new_key}) == {"fixed": [], "still_broken": [], "new": [], "not_rechecked": []}


def test_two_new_checks_with_the_same_title_keep_distinct_rule_ids():
    first = f("security", "Configuration issue") | {"rule": "sec.headers.configuration"}
    second = f("security", "Configuration issue") | {"rule": "sec.cookies.configuration"}
    result = compare.compare([first], [second])
    assert len(result["fixed"]) == len(result["new"]) == 1
    assert result["still_broken"] == []


def test_fixed_still_broken_and_new():
    before = [f("seo", "Missing meta description"), f("security", "No HSTS header"), f("ux", "Sign-up button hidden in the footer")]
    after = [f("security", "No HSTS header"), f("ux", "Sign-up is hidden in the footer"), f("geo", "No structured data")]
    result = compare.compare(before, after)
    assert [x["title"] for x in result["fixed"]] == ["Missing meta description"]
    assert [x["title"] for x in result["still_broken"]] == ["No HSTS header", "Sign-up is hidden in the footer"]  # UX titles are model-written: close wording still matches
    assert [x["title"] for x in result["new"]] == ["No structured data"]


def test_ignored_findings_leave_every_list():
    before = [f("security", "No HSTS header")]
    after = [f("security", "No HSTS header"), f("geo", "No llms.txt", "low")]
    ignored = {compare.fingerprint(f("security", "No HSTS header")), compare.fingerprint(f("geo", "No llms.txt"))}
    assert compare.compare(before, after, ignored) == {"fixed": [], "still_broken": [], "new": [], "not_rechecked": []}


def _previous(fake_db, *, goal="Sign up for an account", site="https://site.test/", days_ago=1):
    fake_db["old"] = {"id": "old", "user_id": USER, "site": site, "goal": goal, "kind": "test", "tier": "paid", "status": "done", "steps": [],
                      "report": {"findings": [f("seo", "Missing meta description")]}, "created_at": (datetime.now(UTC) - timedelta(days=days_ago)).isoformat()}


def test_a_paid_rerun_is_compared_with_the_previous_run_of_the_same_goal(fake_db):
    _previous(fake_db)
    row = {"id": "new", "user_id": USER, "site": "https://site.test/pricing", "goal": "sign up for an account ", "tier": "paid"}
    result = compare.attach(row, {"findings": [f("geo", "No structured data")]})
    assert result["previous_run_id"] == "old"
    assert [x["title"] for x in result["fixed"]] == ["Missing meta description"] and [x["title"] for x in result["new"]] == ["No structured data"]


def test_free_runs_and_other_goals_are_not_compared(fake_db):
    _previous(fake_db)
    assert compare.attach({"id": "new", "user_id": USER, "site": "https://site.test/", "goal": "Sign up for an account", "tier": "free"}, {"findings": []}) is None
    assert compare.attach({"id": "new", "user_id": USER, "site": "https://site.test/", "goal": "Find pricing", "tier": "paid"}, {"findings": []}) is None
    assert compare.attach({"id": "new", "user_id": USER, "site": "https://other.test/", "goal": "Sign up for an account", "tier": "paid"}, {"findings": []}) is None


def test_ignoring_a_finding_needs_a_paid_plan_and_ownership(fake_db, passes):
    _previous(fake_db)
    c = TestClient(app)
    fp = compare.fingerprint(f("seo", "Missing meta description"))
    assert c.post("/runs/old/findings/ignore", json={"fingerprint": fp, "reason": "handled by the CMS"}).status_code == 402
    passes.append({"user_id": USER, "plan": "pro", "starts_at": "2000-01-01T00:00:00+00:00", "expires_at": "2999-01-01T00:00:00+00:00", "runs_granted": 40})
    assert c.post("/runs/old/findings/ignore", json={"fingerprint": fp, "reason": "handled by the CMS"}).status_code == 200
    from app import db
    assert db.ignored_fingerprints(USER, "https://site.test") == {fp: "handled by the CMS"}
    assert c.request("DELETE", "/runs/old/findings/ignore", params={"fingerprint": fp}).status_code == 200
    assert db.ignored_fingerprints(USER, "https://site.test") == {}
    fake_db["theirs"] = fake_db["old"] | {"id": "theirs", "user_id": "someone-else"}
    assert c.post("/runs/theirs/findings/ignore", json={"fingerprint": fp, "reason": "x"}).status_code == 404


def test_a_failed_comparison_never_loses_the_report(monkeypatch, fake_db):
    from app.agent import report
    from app.agent.schema import Report

    fake_db["r1"] = {"id": "r1", "user_id": USER, "site": "https://site.test/", "goal": "g", "persona": "first_timer", "tier": "paid",
                     "status": "done", "steps": [], "report": None, "email": None}
    monkeypatch.setattr(report, "run_report", lambda *a, **k: Report(summary="s", findings=[], top_fixes=[]))

    def broken(row, rep):
        raise RuntimeError("finding_states table missing")

    monkeypatch.setattr(compare, "attach", broken)
    real_finish_run("r1", {})
    assert fake_db["r1"]["report"]["summary"] == "s"


def test_page_level_changes_are_reported():
    before = [f("geo", "Few section headings")]
    after = [f("geo", "Few section headings")]
    fp = compare.fingerprint(before[0])
    prev_pages = {fp: ["https://s.test/contact", "https://s.test/login", "https://s.test/signup"]}
    cur_pages = {fp: ["https://s.test/welcome"]}
    audited = ["https://s.test/", "https://s.test/contact", "https://s.test/login", "https://s.test/signup", "https://s.test/welcome"]
    [item] = compare.compare(before, after, prev_pages=prev_pages, cur_pages=cur_pages, audited=audited)["still_broken"]
    assert item["pages_fixed"] == prev_pages[fp] and item["pages_new"] == ["https://s.test/welcome"] and item["pages_unchecked"] == []


def test_a_finding_whose_pages_were_not_audited_again_is_not_called_fixed():
    before = [f("geo", "Few section headings"), f("seo", "Missing meta description")]
    fp = compare.fingerprint(before[0])
    result = compare.compare(before, [], prev_pages={fp: ["https://s.test/changelog"]}, cur_pages={}, audited=["https://s.test/"])
    assert [x["title"] for x in result["not_rechecked"]] == ["Few section headings"]
    assert [x["title"] for x in result["fixed"]] == ["Missing meta description"]  # site-wide findings without pages stay fixed
