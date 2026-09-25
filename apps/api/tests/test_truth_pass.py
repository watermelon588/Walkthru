"""P0.1: stable rule ids, honest local transport severity, and PageSpeed availability."""

import re

import httpx

from app.agent import report
from app.agent.schema import Finding
from app.scans import security


def test_finding_contract_assigns_a_rule_to_every_kind_and_stabilizes_variable_titles():
    for kind in ("ux", "accessibility", "performance", "seo", "security", "geo"):
        finding = Finding(kind=kind, severity="low", title="A check found 3 issues", detail="detail", fix="fix")
        assert finding.rule and re.fullmatch(r"[a-z0-9_.]+", finding.rule)
        assert Finding.model_validate(finding.model_dump()).rule == finding.rule

    def rule(kind, title):
        return Finding(kind=kind, severity="low", title=title, detail="detail", fix="fix").rule

    assert rule("security", "No HSTS header") == "sec.hsts.missing"
    assert rule("geo", "robots.txt blocks AI search assistants") == "geo.robots.blocks_search_bot"
    assert rule("accessibility", "Image is missing text alternative") == rule("accessibility", "3 images are missing text alternatives")
    assert rule("security", 'Cookie "a" is missing HttpOnly') == rule("security", 'Cookie "b" is missing SameSite')
    assert rule("performance", "Mobile performance score 32/100") == rule("performance", "Mobile performance score 71/100")


def test_plain_http_on_local_or_private_addresses_is_only_a_development_note():
    with httpx.Client() as client:
        for url in ("http://localhost:8101/", "http://127.0.0.1:8101/", "http://192.168.1.2/", "http://10.2.3.4/", "http://[::1]/"):
            response = httpx.Response(200, request=httpx.Request("GET", url))
            findings = security.check_transport(url, response, client)
            assert len(findings) == 1 and findings[0].severity == "low"
            assert findings[0].title == "Local development uses plain http" and findings[0].rule == "sec.http.local"
        public = "http://public.example/"
        findings = security.check_transport(public, httpx.Response(200, request=httpx.Request("GET", public)), client)
        assert findings[0].severity == "high" and findings[0].rule == "sec.http.plain"

    local_form = security.check_content('<form action="http://localhost:8101/signup"></form>', "http://localhost:8101/")
    assert len(local_form) == 1 and local_form[0].severity == "low"


def test_missing_pagespeed_key_keeps_a_specific_not_measured_reason(monkeypatch):
    monkeypatch.delenv("PAGESPEED_API_KEY", raising=False)
    monkeypatch.setattr(report.fetch, "assert_public", lambda url: None)
    result = report.performance_scan({"site": "https://site.test/"})
    assert result["performance_measured"] is False
    assert result["performance_reason"] == "PageSpeed is not configured for this run."
