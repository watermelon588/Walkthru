"""Offline transport tests for slim owner history and counts beyond PostgREST row caps."""

import base64
import json
import re

import httpx
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from app import db, mcp_server, plans
from tests.conftest import USER

OTHER = "00000000-0000-0000-0000-000000000002"
STAMP = "2026-10-05T12:30:00.123456+00:00"
REAL = {name: getattr(db, name) for name in ("free_runs_today", "test_run_count_since", "test_runs_since")}


@pytest.fixture
def rest(monkeypatch):
    seen = []
    box = {"handler": lambda req: httpx.Response(200, json=[])}

    def handle(req):
        seen.append(req)
        return box["handler"](req)

    client = httpx.Client(base_url="https://database.test", transport=httpx.MockTransport(handle))
    monkeypatch.setattr(db, "client", lambda: client)
    yield box, seen
    client.close()


def test_exact_count_ignores_row_cap_and_has_no_body(rest):
    box, seen = rest
    box["handler"] = lambda req: httpx.Response(200, headers={"Content-Range": "*/123456"})
    assert REAL["free_runs_today"]("scan") == 123456
    req = seen[-1]
    assert req.method == "HEAD" and req.headers["Prefer"] == "count=exact"
    assert req.url.params["limit"] == "0" and req.url.params["kind"] == "eq.scan"
    assert req.url.params["tier"] == "eq.free" and req.url.params["created_at"].startswith("gte.")
    assert req.content == b""


@pytest.mark.parametrize("header", [None, "*/*", "*/-1", "0-9/*", "12", "0-2/3 garbage", "*/" + "9" * 100])
def test_missing_or_malformed_count_refuses_admission(rest, header):
    box, _ = rest
    box["handler"] = lambda req: httpx.Response(200, headers={"Content-Range": header} if header else {})
    with pytest.raises(db.DatabaseUnavailable, match="exact count"):
        REAL["test_run_count_since"](USER, STAMP)


def test_exact_zero_and_partial_range_are_valid(rest):
    box, _ = rest
    for header, wanted in [("*/0", 0), ("0-0/9999", 9999)]:
        box["handler"] = lambda req, header=header: httpx.Response(206, headers={"Content-Range": header})
        assert db.user_scans_today(USER) == wanted


def test_count_transport_retries_then_fails_closed(rest):
    box, seen = rest
    replies = iter([httpx.Response(503), httpx.Response(200, headers={"Content-Range": "*/2001"})])
    box["handler"] = lambda req: next(replies)
    assert db.paid_founding_offers() == 2001 and len(seen) == 2

    def timeout(req):
        raise httpx.ReadTimeout("offline fixture")

    box["handler"] = timeout
    with pytest.raises(db.DatabaseUnavailable):
        db.citation_checks_done_since("web", STAMP)
    assert len(seen) == 4


def test_count_permission_error_is_not_zero_or_retried(rest):
    box, seen = rest
    box["handler"] = lambda req: httpx.Response(403)
    with pytest.raises(httpx.HTTPStatusError):
        db.user_scans_today(USER)
    assert len(seen) == 1


def test_each_admission_count_keeps_its_scope(rest):
    box, seen = rest
    box["handler"] = lambda req: httpx.Response(200, headers={"Content-Range": "*/1001"})
    assert REAL["test_run_count_since"](USER, STAMP) == 1001
    assert dict(seen[-1].url.params) == {"user_id": f"eq.{USER}", "kind": "eq.test", "created_at": f"gte.{STAMP}", "select": "id", "limit": "0"}
    assert db.user_scans_today(USER) == 1001
    assert seen[-1].url.params["kind"] == "in.(scan,compare_part)"
    assert seen[-1].url.params["user_id"] == f"eq.{USER}"
    assert db.paid_founding_offers() == 1001
    assert seen[-1].url.params["founding"] == "eq.true" and seen[-1].url.params["status"] == "eq.paid"
    assert db.citation_checks_done_since("memory", STAMP) == 1001
    assert seen[-1].url.params["engine"] == "eq.memory" and seen[-1].url.params["checked_at"] == f"gte.{STAMP}"


def test_citation_capacity_is_exact_past_old_5000_row_limit(rest):
    box, seen = rest

    def handler(req):
        if req.url.path.endswith("citation_quota"):
            return httpx.Response(200, json=[{"engine": "web", "used": 3}])
        assert req.method == "HEAD" and req.url.params["status"] == "eq.queued"
        total = "10001" if req.url.params["engine"] == "eq.web" else "7002"
        return httpx.Response(200, headers={"Content-Range": f"*/{total}"})

    box["handler"] = handler
    assert db.citation_capacity() == {"quotas": [{"engine": "web", "used": 3}], "queued": {"web": 10001, "memory": 7002}}
    assert len(seen) == 3


def history_rows(count):
    return [{"id": f"{i:032x}", "site": "https://owned.test", "created_at": STAMP, "goal": "sign up", "status": "done",
             "kind": "test", "launch_score": 81} for i in range(count, 0, -1)]


def test_history_tied_timestamps_and_newest_insert_do_not_repeat_or_skip(rest):
    box, seen = rest
    rows = history_rows(107)

    def handler(req):
        query = req.url.params
        assert query["user_id"] == f"eq.{USER}"
        assert query["order"] == "created_at.desc,id.desc"
        assert "steps" not in query["select"] and "report," not in query["select"]
        assert "launch_score:report->launch_ready->score" in query["select"]
        upper = re.search(r"id\.lt\.([a-f0-9]{32})", query.get("or", ""))
        eligible = [r for r in rows if not upper or r["id"] < upper[1]]
        return httpx.Response(200, json=eligible[:int(query["limit"])])

    box["handler"] = handler
    page = db.run_history_page(USER, limit=50)
    assert len(page["runs"]) == 50 and page["next_cursor"]
    wanted = [r["id"] for r in rows]
    rows.insert(0, history_rows(200)[0])  # a newly created row above the saved boundary
    collected = [r["id"] for r in page["runs"]]
    while page["next_cursor"]:
        page = db.run_history_page(USER, limit=50, cursor=page["next_cursor"])
        collected.extend(r["id"] for r in page["runs"])
    assert collected == wanted
    assert all("user_id" in req.url.params for req in seen)
    assert max(int(req.url.params["limit"]) for req in seen) == 51


def encode(item):
    return base64.urlsafe_b64encode(json.dumps(item).encode()).rstrip(b"=").decode()


def cursor(**updates):
    return encode({"v": 1, "user": USER, "site": "", "created_at": STAMP, "id": "a" * 32} | updates)


@pytest.mark.parametrize("bad", ["", "!", "x" * 2049, encode([]), cursor(v=2), cursor(v=True), cursor(user=OTHER), cursor(site="other"),
                                  cursor(created_at="2026-10-05"), cursor(created_at="x"), cursor(created_at="0001-01-01T00:00:00+12:00"),
                                  cursor(created_at="9999-12-31T23:59:59-12:00"), cursor(id="a),user_id.neq.x"), cursor(id="f" * 33)])
def test_invalid_cursor_never_reaches_database(rest, bad):
    _, seen = rest
    with pytest.raises(ValueError, match="Invalid run history cursor"):
        db.run_history_page(USER, cursor=bad)
    assert seen == []


@pytest.mark.parametrize("limit", [0, 51, -1, 1.5, True])
def test_history_bounds_are_validated_before_database(rest, limit):
    _, seen = rest
    with pytest.raises(ValueError):
        db.run_history_page(USER, limit=limit)
    assert seen == []


def test_history_filter_is_a_database_literal_substring(rest):
    _, seen = rest
    site = 'A%_*),"or=(user_id.neq.x)\\path'
    assert db.run_history_page(USER, site=site)["runs"] == []
    req = seen[-1]
    assert "or" not in req.url.params
    assert req.url.params["user_id"] == f"eq.{USER}"
    assert req.url.params["site"].startswith('imatch."a%_')
    assert '\\\\*' in req.url.params["site"] and '\\"' in req.url.params["site"]


def test_history_fills_page_and_sentinel_under_smaller_server_row_cap(rest):
    box, seen = rest
    rows = history_rows(42)

    def handler(req):
        upper = re.search(r"id\.lt\.([a-f0-9]{32})", req.url.params.get("or", ""))
        found = [r for r in rows if not upper or r["id"] < upper[1]]
        return httpx.Response(200, json=found[:min(10, int(req.url.params["limit"]))])

    box["handler"] = handler
    first = db.run_history_page(USER, limit=20)
    second = db.run_history_page(USER, limit=20, cursor=first["next_cursor"])
    third = db.run_history_page(USER, limit=20, cursor=second["next_cursor"])
    assert [*first["runs"], *second["runs"], *third["runs"]] == rows
    assert third["next_cursor"] is None and len(seen) == 8


def test_usage_sites_continue_below_response_row_cap(rest):
    box, seen = rest
    rows = [{"id": f"{i:032x}", "site": f"https://site{i}.test"} for i in range(1, 1003)]

    def handler(req):
        after = req.url.params.get("id", "gt.0")[3:]
        eligible = [r for r in rows if r["id"] > after]
        return httpx.Response(200, json=eligible[:100])  # server response cap is lower than requested 500

    box["handler"] = handler
    assert REAL["test_runs_since"](USER, STAMP) == rows
    assert len(seen) == 12 and seen[-1].url.params["select"] == "id,site"


def test_nonadvancing_usage_page_fails_closed(rest):
    box, _ = rest
    box["handler"] = lambda req: httpx.Response(200, json=[{"id": "a" * 32, "site": "https://one.test"}])
    with pytest.raises(db.DatabaseUnavailable, match="did not advance"):
        REAL["test_runs_since"](USER, STAMP)


def test_citation_distinct_batches_page_beyond_row_cap(rest):
    box, seen = rest
    rows = [{"id": i, "batch_id": str(i // 3)} for i in range(1, 1011)]

    def handler(req):
        after = int(req.url.params.get("id", "gt.0")[3:])
        assert req.url.params["site_id"] == "eq.owned-site"
        return httpx.Response(200, json=[r for r in rows if r["id"] > after][:100])

    box["handler"] = handler
    assert db.citation_batches_since("owned-site", STAMP) == len({r["batch_id"] for r in rows})
    assert len(seen) == 12


def test_plan_usage_uses_exact_count_not_returned_site_rows(monkeypatch):
    monkeypatch.setattr(db, "test_runs_since", lambda *args: [{"site": "https://one.test"}])
    monkeypatch.setattr(db, "test_run_count_since", lambda *args: 5000)
    state = plans.current(USER)
    assert state["used"] == 5000 and state["sites"] == {"one.test"}
    assert plans.summary(state)["runs_left"] == 0


def test_mcp_history_uses_bounded_database_query_and_continuation(monkeypatch):
    calls = []

    def page(user, **kw):
        calls.append((user, kw))
        return {"runs": history_rows(2), "next_cursor": "next"}

    monkeypatch.setattr(db, "run_history_page", page)
    monkeypatch.setattr(db, "runs_for_user", lambda *args: pytest.fail("MCP must not download the export"))
    token = mcp_server._user.set(USER)
    try:
        text = mcp_server.list_runs(site="owned", limit=999, cursor="prior")
        assert "score 81" in text and "Next cursor: next" in text
        assert calls == [(USER, {"site": "owned", "limit": 50, "cursor": "prior"})]
    finally:
        mcp_server._user.reset(token)


def test_mcp_bad_cursor_is_a_clear_tool_error(rest):
    _, seen = rest
    token = mcp_server._user.set(USER)
    try:
        with pytest.raises(ToolError, match="Invalid run history cursor"):
            mcp_server.list_runs(cursor="!")
    finally:
        mcp_server._user.reset(token)
    assert seen == []


def test_mcp_empty_continuation_does_not_claim_account_has_no_runs(monkeypatch):
    monkeypatch.setattr(db, "run_history_page", lambda *args, **kw: {"runs": [], "next_cursor": None})
    token = mcp_server._user.set(USER)
    try:
        assert mcp_server.list_runs(cursor="prior") == "No more runs."
        assert mcp_server.list_runs() == "No runs yet. Use scan_site to start."
    finally:
        mcp_server._user.reset(token)
