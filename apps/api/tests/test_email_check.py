"""Signup email check: can this domain's signup and reset emails reach an inbox, and did a journey hit a mailer limit?"""

import httpx

from app.agent.report import mailer_findings
from app.scans import email

ANSWERS = {
    ("acme.test", "TXT"): ["v=spf1 include:_spf.google.com ~all", "google-site-verification=abc"],
    ("_dmarc.acme.test", "TXT"): ["v=DMARC1; p=none; rua=mailto:d@acme.test"],
    ("acme.test", "MX"): ["10 mx.acme.test."],
    ("bare.test", "TXT"): [],
    ("_dmarc.bare.test", "TXT"): [],
    ("bare.test", "MX"): [],
}


def fake_dns(request: httpx.Request) -> httpx.Response:
    name, kind = request.url.params["name"], request.url.params["type"]
    rtype = {"TXT": 16, "MX": 15}[kind]
    data = [{"name": name, "type": rtype, "data": f'"{v}"' if kind == "TXT" else v} for v in ANSWERS.get((name, kind), [])]
    return httpx.Response(200, json={"Status": 0, "Answer": data} if data else {"Status": 0})


def check(host, full=True):
    with httpx.Client(transport=httpx.MockTransport(fake_dns)) as c:
        return email.check(f"https://{host}/", c, full=full)


def titles(findings):
    return {f.title for f in findings}


def test_missing_spf_and_dmarc_are_reported_with_the_record_to_add():
    findings, _ = check("bare.test")
    assert {"No SPF record", "No DMARC policy"} <= titles(findings)
    spf = next(f for f in findings if f.title == "No SPF record")
    assert "v=spf1" in spf.fix and spf.evidence == "TXT bare.test"


def test_monitor_only_dmarc_is_a_low_finding_and_good_spf_is_quiet():
    findings, _ = check("acme.test")
    assert "No SPF record" not in titles(findings)
    assert any(f.title == "DMARC policy only monitors (p=none)" and f.severity == "low" for f in findings)


def test_free_plan_skips_the_mx_check():
    assert "Domain has no MX record" in titles(check("bare.test", full=True)[0])
    assert "Domain has no MX record" not in titles(check("bare.test", full=False)[0])


def test_shared_hosting_subdomains_and_local_hosts_are_not_judged():
    for host in ("portfolio-web-six-psi-43.vercel.app", "me.github.io", "127.0.0.1:8101", "localhost:5173"):
        findings, note = check(host)
        assert findings == [] and note


def test_www_is_checked_on_the_registrable_domain():
    findings, _ = check("www.acme.test")
    assert "No SPF record" not in titles(findings)


def test_supabase_mailer_limit_in_a_journey_becomes_a_fix():
    steps = [
        {"action": "type", "confusion": 0, "url": "https://trip.test/signup"},
        {"action": "click", "confusion": 2, "url": "https://trip.test/signup", "errors_after": ["email rate limit exceeded"]},
    ]
    [f] = mailer_findings(steps)
    assert f.kind == "ux" and f.severity == "high" and "SMTP" in f.fix and f.evidence.startswith("Step 2")
    assert mailer_findings([{"action": "click", "confusion": 0, "url": "x"}]) == []
