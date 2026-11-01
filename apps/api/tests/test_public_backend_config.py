"""Browser-safe backend configuration is context; exposed privileged keys are defects."""

import httpx
import pytest

from app.agent import score
from app.scans import backend
from tests.test_backend import PROJECT, jwt

PAGE = "https://site.test/"
PUBLIC_KEYS = [jwt("anon"), "sb_publishable_synthetic_public_key_1234567890"]
# Construct the fake credential so repository scanners do not mistake the fixture for a leaked key.
SECRET_KEYS = [jwt("service_role"), "sb_" + "secret_" + "synthetic_server_key_1234567890"]


def check_public_code(code, location, monkeypatch):
    """Only synthetic page/bundle requests can reach this transport; probes are unauthorized."""
    monkeypatch.setenv("ALLOW_LOCAL_SCANS", "1")
    html = (f"<html><script>{code}</script></html>" if location == "inline" else
            '<html><script src="/assets/app.js"></script></html>')

    def handler(request):
        assert str(request.url) == PAGE + "assets/app.js"
        assert request.method == "GET"
        return httpx.Response(200, text=code, headers={"content-type": "application/javascript"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        return backend.check(html, PAGE, client, verified=False)


def security_score(findings):
    report = {"findings": [finding.model_dump() for finding in findings], "checks": {"security": "complete"}}
    return score.launch_ready(report, "scan")["areas"]["security"]


@pytest.mark.parametrize("public_key", PUBLIC_KEYS, ids=["anon-jwt", "publishable"])
@pytest.mark.parametrize("location", ["inline", "bundle"])
def test_public_supabase_config_creates_no_security_findings_or_fix_tasks(public_key, location, monkeypatch):
    code = f"const client = createClient('{PROJECT}', '{public_key}');"
    findings = check_public_code(code, location, monkeypatch)
    # Findings supply the downstream fix list; ordinary public config supplies no defect to fix.
    assert findings == []


@pytest.mark.parametrize("public_key", PUBLIC_KEYS, ids=["anon-jwt", "publishable"])
@pytest.mark.parametrize("location", ["inline", "bundle"])
def test_public_supabase_config_does_not_reduce_a_measured_security_score(public_key, location, monkeypatch):
    findings = check_public_code(f"createClient('{PROJECT}', '{public_key}');", location, monkeypatch)
    assert security_score(findings) == 100


@pytest.mark.parametrize("secret_key", SECRET_KEYS, ids=["service-role-jwt", "secret"])
@pytest.mark.parametrize("location", ["inline", "bundle"])
def test_public_config_does_not_hide_a_browser_exposed_privileged_key(secret_key, location, monkeypatch):
    code = f"createClient('{PROJECT}', '{PUBLIC_KEYS[0]}'); const adminKey = '{secret_key}';"
    findings = check_public_code(code, location, monkeypatch)
    assert len(findings) == 1
    assert findings[0].kind == "security" and findings[0].severity == "high"
    assert findings[0].fix
    assert security_score(findings) == 75


@pytest.mark.parametrize("public_key", PUBLIC_KEYS, ids=["anon-jwt", "publishable"])
def test_public_supabase_config_remains_detectable(public_key):
    config = backend.find_config(f"createClient('{PROJECT}', '{public_key}');")
    assert config["supabase"] == PROJECT
    assert config["anon_key"] == public_key
    assert config["secret_key"] is None
