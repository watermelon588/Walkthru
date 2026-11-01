"""Public backend discovery survives scan/report synthesis without becoming a repair task."""

import httpx
import pytest

from app.agent import fix_prompt, report, runtime
from app.agent.schema import Synthesis
from app.scans import fetch, geo_depth, performance, stack, tls
from tests.test_backend import client, jwt

PAGE = "https://site.test/"
PROJECT = "https://abcdefghijklmnopqrst.supabase.co"
PUBLIC_KEY = "sb_publishable_" + "syntheticpublickey123456789"


@pytest.mark.parametrize("stack_available", [True, False])
def test_bundle_config_reaches_report_stack_without_a_security_finding(monkeypatch, stack_available):
    calls = []
    html = '<html lang="en"><head><title>A useful application</title><script src="/app.js"></script></head><body><h1>Welcome</h1></body></html>'

    def handler(request):
        calls.append(request)
        if request.url.path == "/":
            return httpx.Response(200, text=html, headers={"content-type": "text/html", "x-vercel-id": "test"})
        if request.url.path == "/app.js":
            return httpx.Response(200, text=f"createClient('{PROJECT}', '{PUBLIC_KEY}')", headers={"content-type": "application/javascript"})
        return httpx.Response(404)

    monkeypatch.setenv("ALLOW_LOCAL_SCANS", "1")
    monkeypatch.setattr(fetch, "client", lambda **kwargs: httpx.Client(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(tls, "check", lambda *args: [])
    monkeypatch.setattr(tls, "check_caa", lambda *args: [])
    monkeypatch.setattr(geo_depth, "collect_remote", lambda *args, **kwargs: {})
    monkeypatch.setattr(report.email, "check", lambda *args, **kwargs: ([], None))
    monkeypatch.setattr(performance, "scan_pages", lambda *args, **kwargs: ([], False, []))
    monkeypatch.setattr(runtime, "call", lambda *args, **kwargs: (Synthesis(summary="Measured page checks.", ux_findings=[], top_fixes=[]), 0))
    if not stack_available:
        def unavailable(*args, **kwargs):
            raise RuntimeError("Stack response unavailable")
        monkeypatch.setattr(stack, "detect", unavailable)

    result = report.run_report(PAGE, "", verified=False).model_dump()
    assert result["stack"]["backend"] == "supabase"
    context = result["stack"]["evidence"]["backend"]
    assert "public" in context.lower() and "normal" in context.lower()
    assert result["stack"].get("hosting") == ("vercel" if stack_available else None)
    assert not any("supabase" in f["title"].lower() for f in result["findings"])
    prompt = fix_prompt.build({"site": PAGE, "kind": "scan", "created_at": "2026-10-31T00:00:00+00:00"}, result, {}, "full")
    assert "with Supabase" in prompt and context in prompt
    assert "Your site reads Supabase straight from the browser" not in prompt
    assert PUBLIC_KEY not in str(result) and PUBLIC_KEY not in prompt
    assert calls and all(r.url.host == "site.test" for r in calls)


def test_real_backend_findings_keep_project_specific_fix_checks(monkeypatch):
    from app.scans import backend

    monkeypatch.setenv("ALLOW_LOCAL_SCANS", "1")
    calls, context = [], {}
    with client("", calls) as c:
        html = c.get(PAGE).text
        findings = backend.check(html, PAGE, c, verified=True, context=context)
    payload = {"findings": [f.model_dump() for f in findings],
               "stack": report._with_backend(stack.detect({}, html, PAGE), findings, context)}
    prompt = fix_prompt.build({"site": PAGE, "kind": "scan", "created_at": "2026-10-31T00:00:00+00:00"}, payload, {}, "full")
    for path in ("/rest/v1/<table>", "/rest/v1/rpc/<name>", "/storage/v1/object/list/<bucket>"):
        assert PROJECT + path in prompt
    assert "https://<project>.supabase.co" not in prompt
    assert jwt("anon") not in prompt
