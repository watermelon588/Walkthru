"""Report graph with the LLM faked: parallel branches merge, findings sort by severity, tokens add up."""

import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "evals"))
from serve import start

from app import main
from app.agent import report, runtime
from app.agent.schema import Finding, FirstImpression, Synthesis
from app.main import app

HARD = "http://127.0.0.1:8132"


@pytest.fixture(scope="module", autouse=True)
def server():
    os.environ["ALLOW_LOCAL_SCANS"] = "1"
    s = start("hard", 8132)
    yield
    s.shutdown()


@pytest.fixture(autouse=True)
def fake_llm(monkeypatch):
    def call(schema, messages):
        if schema is FirstImpression:
            return FirstImpression(what="A vague platform for synergy.", who="Unclear, maybe enterprises.", first_click="Log in, since there is no sign-up.", trust=["no pricing shown"], clarity=3), 100
        return Synthesis(
            summary="The test user could not find sign-up and the page says nothing concrete.",
            ux_findings=[Finding(kind="ux", severity="high", title="Sign-up is hidden in the footer", detail="The user looked for it in the nav first.", fix="Add a Sign up button to the nav.", evidence="step 2")],
            top_fixes=["Add a Sign up button to the nav.", "Add a meta description.", "Send security headers."],
        ), 200

    monkeypatch.setattr(runtime, "call", call)


def test_run_report_merges_branches():
    steps = [{"thought": "Looking for sign up", "action": "scroll", "target_id": None, "text": None, "confusion": 2, "url": HARD + "/"}]
    rep = report.run_report(HARD + "/", "Zentrix The platform for modern synergy", goal="sign up", persona="first_timer", status="gave_up", steps=steps)
    kinds = {f.kind for f in rep.findings}
    assert kinds == {"ux", "accessibility", "seo", "security"}
    assert rep.findings[0].severity == "high" and rep.findings[-1].severity == "low"  # sorted
    assert rep.first_impression and rep.first_impression.clarity == 3
    assert rep.top_fixes[0].startswith("Add a Sign up")
    assert rep.tokens == 300  # 100 (first impression) + 200 (synthesis)
    assert rep.verified is False and not any("publicly readable" in f.title for f in rep.findings)
    assert rep.checks == {"accessibility": "complete", "performance": "unavailable", "seo": "complete", "security": "complete"}
    assert rep.site_audit is not None
    assert rep.site_audit.pages_scanned == 1  # hard fixture blocks crawling beyond the supplied homepage
    assert rep.site_audit.robots_respected is True


def test_instant_scan_endpoint_creates_public_run(fake_db):
    c = TestClient(app)
    r = c.post("/scans", json={"site": HARD + "/"})
    assert r.status_code == 200, r.text
    body = r.json()
    row = fake_db[body["run_id"]]
    assert row["kind"] == "scan" and row["public"] is True and row["user_id"] is None and row["status"] == "done"
    assert body["url"].endswith(f"/r/{body['run_id']}")
    assert body["report"]["first_impression"]["what"].startswith("A vague")
    assert any(f["title"] == "Missing meta description" for f in body["report"]["findings"])


def test_instant_scan_rejects_bad_input_and_rate_limits(fake_db, monkeypatch):
    c = TestClient(app)
    assert c.post("/scans", json={"site": "not a url"}).status_code == 422
    monkeypatch.setattr(main, "SCAN_LIMIT", 1)
    main._scan_hits.clear()
    assert c.post("/scans", json={"site": HARD + "/"}).status_code == 200
    assert c.post("/scans", json={"site": HARD + "/"}).status_code == 429


def test_share_and_email(fake_db, monkeypatch):
    from tests.conftest import USER

    fake_db["r1"] = {"id": "r1", "user_id": USER, "site": "https://x.io", "tier": "free", "status": "done", "steps": [], "report": None, "email": "tester@example.com", "public": False}
    c = TestClient(app)
    assert c.post("/runs/r1/share").json()["url"].endswith("/r/r1") and fake_db["r1"]["public"] is True
    assert c.post("/runs/r1/email").status_code == 409  # no report yet
    fake_db["r1"]["report"] = {"summary": "s", "top_fixes": [], "findings": []}
    sent = []
    monkeypatch.setattr(main.deliver, "send_report", lambda to, link, site, rep: sent.append((to, link)) or True)
    assert c.post("/runs/r1/email").json() == {"sent": True, "to": "tester@example.com"}
    assert sent[0][1].endswith("/app/runs/r1")
    monkeypatch.setattr(main.deliver, "send_report", lambda *args: False)
    assert c.post("/runs/r1/email").json() == {"sent": False, "to": "tester@example.com"}
    token = c.get("/verification").json()
    assert token["token"].startswith("wt-") and token["token"] in token["meta"]


def test_empty_page_text_skips_first_impression(monkeypatch):
    from app.agent import report as report_module

    called = []
    monkeypatch.setattr(runtime, "call", lambda schema, messages: called.append(schema) or (None, 0))
    out = report_module.first_impression({"site": "https://spa.test/", "page_text": "  "})
    assert out["first_impression"] == {} and called == []


def test_grounded_ux_drops_unsupported_and_restated_findings():
    from app.agent.report import grounded_ux

    code = [Finding(kind="security", severity="medium", title="Page can be framed", detail="d", fix="f")]
    ux = [
        Finding(kind="ux", severity="high", title="Email link did nothing", detail="d", fix="f", evidence="step 2"),
        Finding(kind="ux", severity="medium", title="Page can be embedded in a frame", detail="d", fix="f", evidence="step 1"),
        Finding(kind="ux", severity="medium", title="Unclear navigation", detail="d", fix="f", evidence=None),
        Finding(kind="ux", severity="high", title="Contact form cannot be submitted", detail="blocked by safe mode", fix="f", evidence="step 7"),
    ]
    assert [f.title for f in grounded_ux(ux, code, has_steps=True)] == ["Email link did nothing"]
