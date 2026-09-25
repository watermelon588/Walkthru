"""Launch Ready score (ARCHITECTURE.md `share-loop`) and the public badge."""

from fastapi.testclient import TestClient

from app import db
from app.agent import score
from app.main import app

ALL = {"accessibility": "complete", "performance": "complete", "seo": "complete", "security": "complete", "geo": "complete"}


def finding(kind, severity="medium"):
    return {"kind": kind, "severity": severity, "title": f"{kind} {severity}", "detail": "d", "fix": "f"}


def test_clean_run_scores_100_and_findings_cost_points_by_severity():
    clean = score.launch_ready({"findings": [], "checks": ALL, "geo": {"score": 100}}, "done")
    assert clean["score"] == 100 and clean["areas"]["ux"] == 100
    hurt = score.launch_ready({"findings": [finding("security", "high"), finding("seo", "low")], "checks": ALL, "geo": {"score": 100}}, "done")
    assert hurt["areas"]["security"] == 75 and hurt["areas"]["seo"] == 97
    assert hurt["score"] == round((30 * 100 + 20 * 75 + 20 * 100 + 15 * 97 + 15 * 100) / 100)


def test_unmeasured_areas_leave_the_score_and_share_their_weight():
    report = {"findings": [finding("seo", "high")], "checks": {**ALL, "security": "unavailable", "performance": "unavailable", "accessibility": "unavailable"}, "geo": {"score": 50}}
    result = score.launch_ready(report, "scan")  # an Instant Scan has no journey, so no UX area
    assert result["areas"] == {"ux": None, "security": None, "geo": 50, "seo": 75, "speed": None}
    assert result["score"] == round((20 * 50 + 15 * 75) / 35)


def test_walkthrus_own_stops_never_count_against_the_site():
    for status in ("stopped", "looping", "captcha"):
        assert score.launch_ready({"findings": [], "checks": ALL, "geo": {"score": 80}}, status)["areas"]["ux"] is None
    assert score.launch_ready({"findings": [], "checks": ALL, "geo": {"score": 80}}, "gave_up")["areas"]["ux"] == 50
    assert score.launch_ready({"findings": [], "checks": {}}, "scan")["score"] is None  # nothing measured, no number


def _public_run(fake_db, run_id, *, user="u1", site="https://site.test/", public=True, created="2026-09-24T10:00:00+00:00", seo=0):
    report = {"findings": [finding("seo", "high")] * seo, "checks": ALL, "geo": {"score": 100}, "top_fixes": [], "summary": "s"}
    fake_db[run_id] = {"id": run_id, "user_id": user, "site": site, "status": "done", "kind": "test", "public": public, "report": report, "created_at": created}


def test_badge_serves_the_latest_public_report_of_that_site(fake_db, monkeypatch):
    monkeypatch.setattr(db, "public_reports", lambda user_id: [r for r in fake_db.values() if r["user_id"] == user_id and r["public"] and r["report"]])
    old, new, private = "a" * 32, "b" * 32, "c" * 32
    _public_run(fake_db, old, seo=2)
    _public_run(fake_db, new, created="2026-09-25T10:00:00+00:00")
    _public_run(fake_db, private, public=False)
    c = TestClient(app)

    r = c.get(f"/badge/{old}.svg")
    assert r.status_code == 200 and r.headers["content-type"].startswith("image/svg+xml")
    assert "max-age=3600" in r.headers["cache-control"]
    assert "Launch Ready 100<" in r.text  # the rerun's score, not the embedded run's (which had 2 high SEO findings)
    link = c.get(f"/badge/{old}", follow_redirects=False)
    assert link.status_code == 302 and link.headers["location"].endswith(f"/r/{new}")

    assert c.get(f"/badge/{private}.svg").status_code == 404  # private reports never leak a score
    assert c.get("/badge/not-a-run.svg").status_code == 404
