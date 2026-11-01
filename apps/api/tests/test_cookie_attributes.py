"""Attribute requirements remain distinct from guesses about a cookie's application purpose."""

import pytest

from app.scans import security


def test_same_site_none_requires_secure_even_when_purpose_is_unknown():
    findings = security._cookie("widget=synthetic; Path=/; SameSite=None", True)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.severity == "medium" and "Secure" in finding.title
    assert "HttpOnly" not in finding.title and "HttpOnly" not in finding.fix
    assert "SameSite=None" in finding.detail


@pytest.mark.parametrize("same_site", ["", "unsupported"])
def test_unknown_cookie_gets_policy_advice_for_empty_or_invalid_same_site(same_site):
    findings = security._cookie(f"custom=synthetic; Secure; SameSite={same_site}", True)
    assert len(findings) == 1
    assert "SameSite" in findings[0].title and "HttpOnly" not in findings[0].title
    assert findings[0].severity == "low"


@pytest.mark.parametrize("name", ["__Http-custom", "__Host-Http-custom"])
def test_http_prefix_requires_http_only_regardless_of_cookie_purpose(name):
    findings = security._cookie(f"{name}=synthetic; Secure; Path=/; SameSite=Lax", True)
    assert any("prefix rules" in f.title and "HttpOnly" in f.fix for f in findings)
    assert security._cookie(f"{name}=synthetic; Secure; HttpOnly; Path=/; SameSite=Lax", True) == []


@pytest.mark.parametrize("raw", ["session=private-cookie-value; Path=/", "__Host-custom=private-cookie-value; Domain=example.test"])
def test_cookie_findings_retain_attributes_without_retaining_cookie_values(raw):
    findings = security._cookie(raw, True)
    assert findings
    assert all("private-cookie-value" not in f.model_dump_json() for f in findings)
    assert all("[hidden]" in f.evidence for f in findings)
