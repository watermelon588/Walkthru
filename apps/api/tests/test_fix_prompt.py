"""Agent fix prompt (paid): one Markdown prompt for Cursor, Claude Code, Lovable or Bolt, built in code from the report."""

from fastapi.testclient import TestClient

from app.agent import compare, fix_prompt
from app.main import app
from tests.conftest import USER

LEAK = "sk_" + "live_" + "51FAKEFAKEFAKEFAKEFAKE00"
REPORT = {
    "findings": [
        {"kind": "seo", "severity": "low", "title": "Missing meta description", "detail": "No description.", "fix": "Add one.", "evidence": "https://site.test/"},
        {"kind": "security", "severity": "high", "title": "Stripe live key in a JavaScript bundle", "detail": "A live key is public.",
         "fix": "Rotate it and load it on the server.", "evidence": f"/app.js: {LEAK}"},
        {"kind": "ux", "severity": "high", "title": "Signup emails hit your auth provider's sending limit", "detail": "Supabase's mailer.",
         "fix": "Use your own SMTP.", "evidence": "Step 5: page then showed: email rate limit exceeded"},
        {"kind": "geo", "severity": "medium", "title": "No structured data", "detail": "No JSON-LD.", "fix": "Add JSON-LD.", "evidence": "https://site.test/"},
    ],
    "geo": {"fixes": [{"id": "schema", "title": "Tell AI search who you are", "file": "index.html <head>", "code": "<script>{}</script>", "note": "Add in head."}],
            "fixes_total": 1},
}
RUN = {"id": "r1", "site": "https://site.test/", "goal": "Sign up for an account", "kind": "test", "created_at": "2026-09-24T10:00:00+00:00"}


def test_every_finding_appears_once_security_first_with_a_check():
    text = fix_prompt.build(RUN, REPORT, {}, "full")
    order = [text.index(t) for t in ("Stripe live key", "Signup emails hit", "No structured data", "Missing meta description")]
    assert order == sorted(order)
    assert all(text.count(f["title"]) == 3 for f in REPORT["findings"])  # its heading, its "Done when" line and the Verify list
    assert "Done when:" in text and "<script>{}</script>" in text and "Ask before adding a new dependency" in text


def test_secrets_are_never_pasted_into_the_prompt():
    text = fix_prompt.build(RUN, REPORT, {}, "full")
    assert LEAK not in text and "sk_live_" in text


def test_ignored_findings_are_left_out():
    ignored = {compare.fingerprint(REPORT["findings"][0]): "handled by the CMS"}
    text = fix_prompt.build(RUN, REPORT, ignored, "full")
    assert "Missing meta description" not in text


def test_chat_version_fits_a_chat_box():
    many = {"findings": REPORT["findings"] * 30, "geo": REPORT["geo"]}
    text = fix_prompt.build(RUN, many, {}, "chat")
    assert len(text) <= fix_prompt.CHAT_LIMIT and "download the full prompt" in text.lower()


def _owned(fake_db):
    fake_db["r1"] = RUN | {"user_id": USER, "status": "done", "steps": [], "tier": "paid", "report": REPORT}


def test_free_plan_gets_402_and_paid_gets_markdown(fake_db, passes):
    _owned(fake_db)
    c = TestClient(app)
    assert c.get("/runs/r1/fix-prompt").status_code == 402
    passes.append({"user_id": USER, "plan": "pro", "starts_at": "2000-01-01T00:00:00+00:00", "expires_at": "2999-01-01T00:00:00+00:00", "runs_granted": 40})
    r = c.get("/runs/r1/fix-prompt")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/markdown") and "Stripe live key" in r.text
    d = c.get("/runs/r1/fix-prompt", params={"download": 1})
    assert "walkthru-fixes.md" in d.headers["content-disposition"]
