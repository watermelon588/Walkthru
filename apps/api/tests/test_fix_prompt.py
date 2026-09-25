"""Agent fix plan (paid, P1.3): one Markdown prompt for Cursor, Claude Code, Lovable or Bolt, built in code from the report."""

import re

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


def test_every_finding_appears_once_in_batch_order_with_a_check():
    text = fix_prompt.build(RUN, REPORT, {}, "full")
    order = [text.index(t) for t in ("### 1.1 Stripe live key", "### 2.1 Signup emails hit", "### 3.1 No structured data", "### 4.1 Missing meta description")]
    assert order == sorted(order)
    for f in REPORT["findings"]:
        assert len(re.findall(rf"^### \d+\.\d+ {re.escape(f['title'])}$", text, re.MULTILINE)) == 1  # one section per finding
    assert text.count("**Stop and verify batch") == 4 and "Check locally:" in text
    assert "<script>{}</script>" in text and "Ask before adding a new dependency" in text
    assert "## Manual steps" in text and "Rotate the leaked key" in text  # the secret's provider step is listed apart


def test_secrets_are_never_pasted_into_the_prompt():
    text = fix_prompt.build(RUN, REPORT, {}, "full")
    assert LEAK not in text and "sk_live_" in text


def test_ignored_findings_are_left_out():
    ignored = {compare.fingerprint(REPORT["findings"][0]): "handled by the CMS"}
    text = fix_prompt.build(RUN, REPORT, ignored, "full")
    assert "Missing meta description" not in text


def test_chat_version_is_split_into_parts_that_fit_a_chat_box_and_keep_every_finding():
    many = {"findings": [dict(f, title=f"{f['title']} {i}") for i in range(30) for f in REPORT["findings"]], "geo": REPORT["geo"]}
    parts = fix_prompt.chat_parts(fix_prompt.build(RUN, many, {}, "chat"))
    assert len(parts) > 1 and all(len(p) <= fix_prompt.CHAT_LIMIT for p in parts)
    assert all(f"part {i} of {len(parts)}" in p for i, p in enumerate(parts, start=1))
    joined = "\n".join(parts)
    assert all(f["title"] in joined for f in many["findings"]) and "more" not in joined.split("part 1")[0]
    assert LEAK not in joined


VERCEL = {"hosting": "vercel", "framework": None, "backend": None, "evidence": {"hosting": "x-vercel-id header"}}
NETLIFY = {"hosting": "netlify", "framework": None, "backend": None, "evidence": {"hosting": "x-nf-request-id header"}}
HSTS = {"kind": "security", "severity": "medium", "title": "No HSTS header", "detail": "No header.", "fix": "Send HSTS.", "evidence": "https://site.test/"}


def test_vercel_and_netlify_get_different_recipes_for_the_same_rule():
    on_vercel = fix_prompt.build(RUN, {"findings": [HSTS], "stack": VERCEL}, {}, "full")
    on_netlify = fix_prompt.build(RUN, {"findings": [HSTS], "stack": NETLIFY}, {}, "full")
    assert "`vercel.json`" in on_vercel and '"key": "Strict-Transport-Security"' in on_vercel and "netlify.toml" not in on_vercel
    assert "`netlify.toml`" in on_netlify and 'Strict-Transport-Security = "max-age=63072000' in on_netlify and "vercel.json" not in on_netlify
    assert "curl -sI https://site.test/ | grep -i strict-transport-security" in on_vercel  # {url} filled in
    nextjs = fix_prompt.build(RUN, {"findings": [HSTS], "stack": {**VERCEL, "framework": "nextjs"}}, {}, "full")
    assert "`next.config.js`" in nextjs and "Next.js on Vercel" in nextjs
    generic = fix_prompt.build(RUN, {"findings": [HSTS]}, {}, "full")
    assert "could not tell" in generic and "add_header Strict-Transport-Security" in generic


def test_csp_starts_report_only_and_dns_work_is_manual():
    csp = {"kind": "security", "severity": "medium", "title": "No Content-Security-Policy", "detail": "d", "fix": "Add a CSP.", "evidence": None}
    caa = {"kind": "security", "severity": "low", "title": "No CAA record", "detail": "d", "fix": "Add CAA.", "evidence": None}
    text = fix_prompt.build(RUN, {"findings": [csp, caa], "stack": NETLIFY}, {}, "full")
    assert "Content-Security-Policy-Report-Only" in text and "report-only mode" in text
    manual = text.split("## Manual steps")[1]
    assert "**DNS: No CAA record.**" in manual and "### 1.2 No CAA record" not in text  # DNS-only: listed once, outside the batches


def test_stack_detection_from_headers_and_html():
    from app.scans import stack

    s = stack.detect({"x-vercel-id": "iad1::x"}, '<script src="/_next/static/a.js"></script>', "https://a.com/")
    assert (s["hosting"], s["framework"], s["backend"]) == ("vercel", "nextjs", None)
    s = stack.detect({"server": "Netlify", "x-nf-request-id": "1"}, '<script type="module" src="/assets/index-Ab12.js"></script><script src="https://cdn.gpteng.co/gptengineer.js"></script>'
                     "<script>createClient('https://abc.supabase.co')</script>", "https://a.com/")
    assert (s["hosting"], s["framework"], s["backend"]) == ("netlify", "lovable", "supabase") and stack.label(s) == "Lovable (Vite and React) on Netlify with Supabase"
    s = stack.detect({"server": "cloudflare", "cf-ray": "x"}, "<html><head><meta name=generator content=\"Astro v4\"></head>", "https://a.pages.dev/")
    assert (s["hosting"], s["framework"]) == ("cloudflare", "astro")
    s = stack.detect({"server": "nginx"}, "<html><body>hi</body></html>", "https://a.com/")
    assert (s["hosting"], s["framework"], s["backend"]) == (None, None, None) and stack.label(s) == "an unknown stack"


def test_every_scanner_rule_on_the_hard_fixture_has_a_recipe():
    rules = ["sec.hsts.missing", "sec.no_content_security_policy", "sec.csp_allows_eval", "sec.no_referrer_policy", "sec.page_can_be_framed",
             "sec.cookie.flags_missing", "sec.stripe_live_key_in_a_javascript_bundle", "sec.env_is_publicly_readable", "sec.source_maps_are_publicly_readable",
             "sec.jquery_n_n_has_known_vulnerabilities", "sec.no_caa_record", "sec.no_spf_record", "sec.no_dmarc_policy", "sec.supabase.public_table",
             "geo.robots.blocks_search_bot", "geo.no_llms_txt", "seo.missing_meta_description", "a11y.control.name_missing", "perf.mobile.lab_score_low"]
    missing = [r for r in rules if not fix_prompt.recipe({"kind": "security", "title": "x", "rule": r})]
    assert missing == []


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


def test_every_affected_page_is_listed_not_just_three():
    pages = [f"https://site.test/p{i}" for i in range(7)]
    report = {"findings": [{"kind": "geo", "severity": "low", "title": "Few section headings", "detail": "d", "fix": "x",
                            "evidence": ", ".join(pages[:3])}],
              "pages": {compare.fingerprint({"kind": "geo", "title": "Few section headings"}): pages}}
    text = fix_prompt.build(RUN, report, {}, "full")
    assert all(p in text for p in pages) and "7 pages" in text
