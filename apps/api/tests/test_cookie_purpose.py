"""Cookie advice follows observed attributes without assuming every cookie authenticates a user."""

import httpx
import pytest

from app.agent import fix_prompt, score
from app.scans import security

PAGE = "https://example.test/"
RUN = {"site": PAGE, "kind": "scan", "created_at": "2026-10-31T00:00:00+00:00"}


def scan_cookie(raw):
    response = httpx.Response(200, request=httpx.Request("GET", PAGE), headers={
        "strict-transport-security": "max-age=63072000; includeSubDomains",
        "content-security-policy": "default-src 'self'",
        "x-content-type-options": "nosniff", "x-frame-options": "DENY",
        "referrer-policy": "strict-origin-when-cross-origin", "set-cookie": raw,
    })
    return security.check_headers(response)


def scanned_report(raw, stack=None):
    return {"findings": [finding.model_dump() for finding in scan_cookie(raw)],
            "checks": {"security": "complete"}, "stack": stack}


@pytest.mark.parametrize("name", ["_ga", "csrf", "csrftoken", "XSRF-TOKEN", "theme", "cookie_consent", "unknown_widget"])
def test_client_and_unknown_cookies_do_not_require_httponly(name):
    assert scan_cookie(f"{name}=synthetic; Path=/; Secure; SameSite=Lax") == []


def test_audit_analytics_cookie_does_not_reduce_security_score():
    report = scanned_report("_ga=GA1.1.1234.5678; Path=/; Secure; SameSite=Lax")
    assert score.launch_ready(report, "scan")["areas"]["security"] == 100


@pytest.mark.parametrize("name", ["_ga", "unknown_widget"])
@pytest.mark.parametrize("attributes,missing", [
    ("SameSite=Lax", ["Secure"]), ("Secure", ["SameSite"]), ("Path=/", ["Secure", "SameSite"]),
])
def test_non_session_cookies_retain_lower_severity_attribute_advice(name, attributes, missing):
    findings = scan_cookie(f"{name}=synthetic; {attributes}")
    assert findings
    assert all(finding.severity == "low" for finding in findings)
    assert all("httponly" not in finding.title.lower() for finding in findings)
    assert all(any(attribute.lower() in (finding.title + " " + finding.detail).lower() for finding in findings)
               for attribute in missing)


@pytest.mark.parametrize("style", ["full", "chat"])
@pytest.mark.parametrize("stack", [None, {"framework": "nextjs"}, {"backend": "supabase"}], ids=["generic", "nextjs", "supabase"])
@pytest.mark.parametrize("name", ["_ga", "csrf"])
def test_real_scanner_findings_do_not_generate_unrelated_session_mutations(name, stack, style):
    report = scanned_report(f"{name}=synthetic; Path=/", stack)
    assert report["findings"]
    prompt = fix_prompt.build(RUN, report, {}, style)
    assert name in prompt
    for mutation in ("Set-Cookie: session=", "cookies().set('session'", "httpOnly: true", "createServerClient("):
        assert mutation not in prompt


@pytest.mark.parametrize("name", ["session", "sessionid"])
def test_session_like_names_still_flag_httponly_with_explicit_purpose_uncertainty(name):
    findings = scan_cookie(f"{name}=synthetic; Path=/; Secure; SameSite=Lax")
    missing = [finding for finding in findings if "httponly" in finding.title.lower()]
    assert missing
    assert all(finding.severity == "medium" for finding in missing)
    # A familiar name is a reason to inspect its purpose, not proof that this cookie authenticates a user.
    assert any(any(word in finding.detail.lower() for word in
                   ("unknown", "unconfirmed", "confirm", "suggest", "cannot determine", "not proof", "not prove", "heuristic", "verify"))
               for finding in missing)


@pytest.mark.parametrize("raw,prefix", [
    ("__Host-csrf=synthetic; Secure; Domain=example.test; Path=/app; SameSite=Lax", "__Host-"),
    ("__Secure-theme=synthetic; Path=/; SameSite=Lax", "__Secure-"),
])
def test_client_cookie_purpose_does_not_disable_prefix_enforcement(raw, prefix):
    findings = scan_cookie(raw)
    assert any(prefix in finding.title and "prefix" in finding.title.lower() for finding in findings)
