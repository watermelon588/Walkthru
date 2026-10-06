"""The MCP tools that reach the rest of the web app (verification, GitHub, AI answers, watch, compare, findings,
sharing). Each calls the web route as the key's owner, so these check the wiring and the plan rules reaching the agent."""

from fastapi.testclient import TestClient

from app import db, github, main
from app.main import app
from tests.conftest import USER
from tests.test_citations import store  # noqa: F401 - the in-memory citation tables, a fixture
from tests.test_mcp import _call, fake_keys, fresh_transport, plus  # noqa: F401 - fresh_transport is an autouse fixture
from tests.test_watch_compare import fake_sites, grant

RUN = "d" * 32
FINDING = {"kind": "security", "severity": "low", "rule": "sec.nosniff", "title": "No X-Content-Type-Options", "detail": "d",
           "fix": "Send nosniff.", "evidence": "e"}


def _session(monkeypatch, passes, fake_db, plan="plus"):
    fake_keys(monkeypatch)
    plus(passes) if plan == "plus" else grant(passes, plan)
    fake_db[RUN] = {"id": RUN, "user_id": USER, "site": "https://site.test/", "kind": "scan", "status": "done", "goal": "Instant Scan",
                    "public": False, "report": {"summary": "", "top_fixes": [], "findings": [FINDING], "launch_ready": {"score": 77}}}


def _key(c) -> str:
    return c.post("/me/api-keys", json={"name": "agent"}).json()["key"]


def test_verification_gives_the_head_tag_then_confirms(monkeypatch, passes, fake_db):
    _session(monkeypatch, passes, fake_db)
    monkeypatch.setattr(main.fetch, "assert_public", lambda url: None)
    with TestClient(app) as c:
        key = _key(c)
        error, text = _call(c, key, "get_site_verification", {"site": "site.test/pricing"})
        assert not error and "Not verified yet: https://site.test/" in text
        assert '<meta name="walkthru-verification" content="wt-' in text and "app/layout.tsx" in text and "_walkthru.site.test" in text
        monkeypatch.setattr(main, "_verified", lambda site, uid: True)  # the owner deployed the tag
        assert "Verified: https://site.test/" in _call(c, key, "get_site_verification", {"site": "https://site.test"})[1]


def test_github_tools_preview_before_opening_and_only_known_repos(monkeypatch, passes, fake_db):
    _session(monkeypatch, passes, fake_db)
    monkeypatch.setattr(github, "configured", lambda: True)
    monkeypatch.setattr(github, "install_url", lambda uid: "https://github.com/apps/walkthru/installations/new?state=s")
    installs: list[dict] = []
    monkeypatch.setattr(db, "github_installations", lambda uid: installs)
    monkeypatch.setattr(github, "repositories", lambda iid: [{"full_name": "acme/site", "private": True, "default_branch": "main", "installation_id": iid}])
    opened = []

    def open_pr(iid, repo, run, report, *, confirm):
        opened.append(confirm)
        preview = {"repo": repo, "base": "main", "changes": [{"path": "vercel.json", "summary": "security headers", "lines": 9}], "left": ["Missing alt text"]}
        return preview | ({"url": "https://github.com/acme/site/pull/4", "number": 4, "branch": "walkthru/fixes"} if confirm else {})

    monkeypatch.setattr(github, "open_fix_pr", open_pr)
    with TestClient(app) as c:
        key = _key(c)
        assert "installations/new" in _call(c, key, "list_github_repos", {})[1]  # not connected: the link to connect
        installs.append({"installation_id": 42, "account_login": "acme"})
        assert "acme/site (default branch main, private)" in _call(c, key, "list_github_repos", {})[1]
        error, text = _call(c, key, "open_fix_pull_request", {"run_id": RUN, "repo": "Acme/Site"})
        assert not error and "Nothing was written" in text and "vercel.json" in text and "Missing alt text" in text
        assert "pull/4" in _call(c, key, "open_fix_pull_request", {"run_id": RUN, "repo": "acme/site", "confirm": True})[1]
        assert opened == [False, True]
        error, text = _call(c, key, "open_fix_pull_request", {"run_id": RUN, "repo": "someone/else"})
        assert error and "list_github_repos" in text


def test_ai_answers_track_edit_and_check(store, monkeypatch, passes, fake_db):  # noqa: F811 - the imported fixture
    _session(monkeypatch, passes, fake_db)
    with TestClient(app) as c:
        key = _key(c)
        assert "No sites tracked yet" in _call(c, key, "list_ai_answer_sites", {})[1]
        error, text = _call(c, key, "get_ai_answers", {"site": "acmenotes.app"})
        assert error and "track_ai_answers first" in text
        error, text = _call(c, key, "track_ai_answers", {"site": "acmenotes.app", "competitors": ["Notion (notion.so)"]})
        assert not error and "# AI answers for https://acmenotes.app (brand 'Acme Notes')" in text and "Not measured: Google AI Overviews" in text
        text = _call(c, key, "set_ai_prompts", {"site": "https://www.acmenotes.app/", "prompts": ["best notes app for teams"]})[1]
        assert "1. best notes app for teams" in text and "2." not in text.split("## Prompts")[1]
        assert "Queued 2 answers" in _call(c, key, "check_ai_answers_now", {"site": "acmenotes.app"})[1]
        error, text = _call(c, key, "check_ai_answers_now", {"site": "acmenotes.app"})
        assert error and "last day" in text  # the website's own once-a-day rule reaches the agent
        assert error and _call(c, key, "set_ai_prompts", {"site": "acmenotes.app"})[0]  # nothing to change


def test_watch_and_deploy_hook(monkeypatch, passes, fake_db):
    sites = fake_sites(monkeypatch)
    checks = []
    monkeypatch.setattr(main.watch, "check", lambda site, reason="weekly": checks.append(reason))
    monkeypatch.setattr(main.fetch, "assert_public", lambda url: None)
    _session(monkeypatch, passes, fake_db)
    with TestClient(app) as c:
        key = _key(c)
        assert "Watching https://site.test/" in _call(c, key, "watch_site", {"site": "site.test"})[1] and checks == ["added"]
        error, text = _call(c, key, "create_deploy_hook", {"site": "https://site.test"})
        hook = next(line for line in text.splitlines() if "/hooks/deploy/wh_" in line)
        assert not error and hook.startswith("http://testserver/hooks/deploy/") and next(iter(sites.values()))["hook_hash"]
        assert "Checking https://site.test/" in _call(c, key, "check_watched_site_now", {"site": "site.test"})[1]
        error, text = _call(c, key, "check_watched_site_now", {"site": "site.test"})
        assert error and "10 minutes" in text
        assert "https://site.test/: first check pending" in _call(c, key, "list_watched_sites", {})[1]
        assert _call(c, key, "check_watched_site_now", {"site": "elsewhere.test"})[1].endswith("Call watch_site first.")


def test_compare_accept_and_share(monkeypatch, passes, fake_db):
    _session(monkeypatch, passes, fake_db)
    monkeypatch.setattr(main.fetch, "assert_public", lambda url: None)
    started = []
    monkeypatch.setattr(main, "_compare", lambda run_id, uid, urls, *_: started.append(urls))
    with TestClient(app) as c:
        key = _key(c)
        error, text = _call(c, key, "compare_sites", {"site": "site.test", "competitors": ["rival.test"]})
        assert not error and "Comparison queued as run" in text and started == [["https://site.test", "https://rival.test"]]
        text = _call(c, key, "accept_finding", {"run_id": RUN, "rule": "sec.nosniff", "reason": "Served by our CDN"})[1]
        assert "Accepted as won't fix" in text and db.ignored_fingerprints(USER, "https://site.test")
        _call(c, key, "reopen_finding", {"run_id": RUN, "rule": "sec.nosniff"})
        assert not db.ignored_fingerprints(USER, "https://site.test")
        text = _call(c, key, "share_report", {"run_id": RUN})[1]
        assert fake_db[RUN]["public"] and f"/r/{RUN}" in text and f"(http://testserver/badge/{RUN}.svg)" in text and "score: 77 of 100" in text
        assert "Plan: plus" in _call(c, key, "get_plan", {})[1]


def test_comparison_reports_read_as_a_table(monkeypatch, passes, fake_db):
    _session(monkeypatch, passes, fake_db)
    fake_db[RUN]["report"] = {"compare": [{"site": "https://site.test/", "yours": True, "score": 70, "geo": 50, "findings": {"high": 1, "medium": 0, "low": 2}, "run_id": "x"},
                                          {"site": "https://gone.test", "error": "That site did not respond."}]}
    with TestClient(app) as c:
        text = _call(c, _key(c), "get_report", {"run_id": RUN})[1]
    assert "https://site.test/ (yours): Launch Ready 70, AI search readiness 50, findings high 1 / medium 0 / low 2" in text
    assert "https://gone.test: not scanned: That site did not respond." in text
