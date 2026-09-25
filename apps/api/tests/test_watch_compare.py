"""Weekly watch with deploy hooks (Plus) and competitor side by side (paid). ARCHITECTURE.md `watch`, `competitor-compare`."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app import db, deliver, main, watch
from app.main import app
from tests.conftest import USER


def grant(passes, plan="plus", user=USER):
    now = datetime.now(UTC)
    passes.append({"user_id": user, "plan": plan, "starts_at": (now - timedelta(days=1)).isoformat(),
                   "expires_at": (now + timedelta(days=29)).isoformat(), "runs_granted": 150})


def report(*titles, score=80):
    return {"findings": [{"kind": "seo", "severity": "high", "title": t, "detail": "d", "fix": "f"} for t in titles],
            "launch_ready": {"score": score, "areas": {"seo": score}}, "geo": {"score": 60}, "site_audit": {"pages_scanned": 4},
            "first_impression": {"what": "A notes app."}}


def fake_sites(monkeypatch):
    sites: dict[str, dict] = {}

    def add(user_id, site):
        sid = f"00000000-0000-0000-0000-{len(sites):012d}"
        sites[sid] = {"id": sid, "user_id": user_id, "site": site, "watch": True, "last_run_id": None, "last_changes": None,
                      "hook_hash": None, "last_hook_at": None, "next_check_at": datetime.now(UTC).isoformat()}
        return sites[sid]

    def claim(site_id, not_before):
        s = sites[site_id]
        if s["last_hook_at"] and s["last_hook_at"] >= not_before:
            return False
        s["last_hook_at"] = datetime.now(UTC).isoformat()
        return True

    monkeypatch.setattr(db, "add_site", add)
    monkeypatch.setattr(db, "sites_for_user", lambda user_id: [s for s in sites.values() if s["user_id"] == user_id])
    monkeypatch.setattr(db, "remove_site", lambda user_id, sid: sites.pop(sid, None) is not None)
    monkeypatch.setattr(db, "update_site", lambda sid, values: sites[sid].update(values))
    monkeypatch.setattr(db, "site_by_hook", lambda h: next((s for s in sites.values() if s["hook_hash"] == h), None))
    monkeypatch.setattr(db, "claim_hook", claim)
    monkeypatch.setattr(db, "due_sites", lambda now, limit=20: [s for s in sites.values() if s["watch"] and s["next_check_at"] <= now])
    return sites


def test_changes_are_compared_by_fingerprint():
    diff = watch.changes(report("Missing meta description", "No sitemap.xml"), report("Missing meta description", "Duplicate title"))
    assert diff["new"] == ["Duplicate title"] and diff["fixed"] == ["No sitemap.xml"] and diff["score"] == 80


def test_check_emails_only_when_something_changed(monkeypatch, fake_db):
    sites = fake_sites(monkeypatch)
    site = db.add_site(USER, "https://site.test/")
    results = iter([report("A"), report("A"), report("A", "B")])

    def scan(url, *, user_id=None, kind="scan"):
        run_id = f"{len(fake_db):032d}"
        fake_db[run_id] = {"id": run_id, "report": next(results)}
        return run_id, {"site": url, "report": fake_db[run_id]["report"]}

    sent = []
    monkeypatch.setattr(main, "run_scan", scan)
    monkeypatch.setattr(db, "user_email", lambda uid: "owner@site.test")
    monkeypatch.setattr(deliver, "send_watch", lambda to, s, link, diff: sent.append(diff))

    assert watch.check(site, "added")["baseline"] and sent == []  # first check is the baseline, never an email
    watch.check(sites[site["id"]])
    assert sent == []  # nothing changed, nothing sent
    diff = watch.check(sites[site["id"]], "deploy")
    assert diff["new"] == ["B"] and len(sent) == 1 and sent[0]["reason"] == "deploy"
    assert sites[site["id"]]["next_check_at"] > (datetime.now(UTC) + timedelta(days=6)).isoformat()


def test_watch_is_plus_only_with_limits_and_a_rate_limited_hook(monkeypatch, passes):
    sites = fake_sites(monkeypatch)
    checks = []
    monkeypatch.setattr(watch, "check", lambda site, reason="weekly": checks.append((site["site"], reason)))
    c = TestClient(app)
    assert c.post("/watch", json={"site": "https://example.com"}).status_code == 402
    grant(passes)
    added = c.post("/watch", json={"site": "https://example.com/pricing"}).json()
    assert added["site"] == "https://example.com/" and checks == [("https://example.com/", "added")]  # watched by origin, baseline queued
    assert c.post("/watch", json={"site": "https://example.com"}).status_code == 409
    for i in range(4):
        c.post("/watch", json={"site": f"https://example{i}.com"})
    assert c.post("/watch", json={"site": "https://one-too-many.com"}).status_code == 409  # Plus watches 5 sites

    hook = c.post(f"/watch/{added['id']}/hook").json()["url"]
    token = hook.rsplit("/", 1)[1]
    assert token.startswith("wh_") and sites[added["id"]]["hook_hash"] == watch.hook_hash(token)  # only the hash is stored
    assert c.post(f"/hooks/deploy/{token}").status_code == 202 and checks[-1] == ("https://example.com/", "deploy")
    assert c.post(f"/hooks/deploy/{token}").status_code == 429  # 10-minute limit
    assert c.post("/hooks/deploy/wh_unknown").status_code == 404
    passes.clear()
    sites[added["id"]]["last_hook_at"] = None
    assert c.post(f"/hooks/deploy/{token}").status_code == 402  # a lapsed pass stops the hook


def test_weekly_pass_skips_owners_who_left_plus(monkeypatch, passes):
    sites = fake_sites(monkeypatch)
    site = db.add_site(USER, "https://site.test/")
    checked = []
    monkeypatch.setattr(watch, "check", lambda s, reason="weekly": checked.append(s["id"]))
    assert watch.run_due() == 0 and checked == []  # free plan now: skipped and pushed a week out
    assert sites[site["id"]]["next_check_at"] > datetime.now(UTC).isoformat()


def test_compare_is_paid_and_survives_an_unreachable_competitor(monkeypatch, passes, fake_db):
    real_worker = main._compare
    c = TestClient(app)
    body = {"site": "https://mine.test", "competitors": ["https://rival.test", "https://gone.test"]}
    monkeypatch.setattr(main.fetch, "assert_public", lambda url: None)
    monkeypatch.setattr(db, "user_scans_today", lambda uid: 0)
    started = []
    monkeypatch.setattr(main, "_compare", lambda run_id, uid, urls: started.append(urls))
    assert c.post("/compare", json=body).status_code == 402  # free plan
    grant(passes, "pro")
    run_id = c.post("/compare", json=body).json()["run_id"]
    urls = ["https://mine.test", "https://rival.test", "https://gone.test"]
    assert fake_db[run_id]["kind"] == "compare" and started == [urls]

    def scan(url, *, user_id=None, kind="scan"):
        assert kind == "compare_part" and user_id == USER  # private sub-scans, kept out of the runs list
        if "gone" in url:
            raise ValueError("That site did not respond. Check the address and try again.")
        return url[8:12].ljust(32, "0"), {"site": url + "/", "report": report("A", score=90 if "rival" in url else 70)}

    monkeypatch.setattr(main, "run_scan", scan)
    real_worker(run_id, USER, urls)
    sites = fake_db[run_id]["report"]["compare"]
    assert fake_db[run_id]["status"] == "done" and [s.get("yours") for s in sites] == [True, None, None]
    assert [s.get("score") for s in sites] == [70, 90, None] and "did not respond" in sites[2]["error"]
    assert sites[1]["geo"] == 60 and sites[1]["findings"]["high"] == 1 and sites[1]["impression"] == "A notes app."
