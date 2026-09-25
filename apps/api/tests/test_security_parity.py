"""P1.2 security parity: every new rule fires on the hard fixture (or on a recorded response when a local http fixture
cannot serve it: HSTS, TLS, CAA, takeover) and stays quiet on the easy fixture and on well-built pages."""

import datetime
import json
import os
import socket
import ssl
import sys
import threading

import httpx
import pytest

from app.scans import csp, libraries, secrets, security, site, takeover, tls

EVALS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "evals")
sys.path.insert(0, EVALS)
from serve import start

EASY, HARD = "http://127.0.0.1:8121", "http://127.0.0.1:8122"
NEW_TITLES = ("CSP ", "prefix rules", "has known vulnerabilities", "integrity check", "CORS", ".env.production", "/backup.sql",
              "Source maps", "SendGrid", "HSTS", "TLS", "CAA", "Subdomain")


@pytest.fixture(scope="module")
def fixtures():
    os.environ["ALLOW_LOCAL_SCANS"] = "1"
    servers = start("easy", 8121), start("hard", 8122)
    yield
    for s in servers:
        s.shutdown()


def audit(url):
    from app.scans import fetch

    with fetch.client() as c:
        return site.audit(url, c, verified=True, max_pages=5, time_limit=10)


def titles(findings):
    return [f.title for f in findings]


# ---------- the fixtures, end to end through the real site audit ----------


def test_hard_fixture_trips_every_new_rule(fixtures):
    found = " | ".join(titles(audit(HARD + "/").security))
    for expected in ("CSP allows inline scripts", "CSP allows eval", "CSP allows scripts from any site", "CSP has no object-src",
                     'Cookie "__Host-csrf" breaks its __Host- prefix rules', "jquery 1.12.4 has known vulnerabilities",
                     "Library from a public CDN loads without an integrity check", "CORS trusts any website with visitors' cookies",
                     "/.env.production is publicly readable", "/backup.sql is publicly readable", "Source maps are publicly readable",
                     "SendGrid API key in a JavaScript bundle", "Stripe live key in a JavaScript bundle", "AWS access key in a JavaScript bundle"):
        assert expected in found, expected


def test_easy_fixture_has_none_of_the_new_findings(fixtures):
    found = titles(audit(EASY + "/").security)
    assert not [t for t in found if any(n in t for n in NEW_TITLES)], found


def test_every_new_trap_is_matched_by_the_scorer(fixtures):
    """The eval scorer (evals/runner.py) finds X7 to X14 in the hard fixture's real findings."""
    from runner import load_traps, score_candidate

    report = {"summary": "", "top_fixes": [], "findings": [f.model_dump() for f in audit(HARD + "/").security]}
    traps = [t for t in load_traps(os.path.join(EVALS, "traps.json")) if t.id in {f"X{n}" for n in range(7, 15)}]
    assert score_candidate({"model": "scanner", "report": report}, traps).found == 8


def test_unverified_site_never_requests_exposed_paths_bundles_or_takeover(monkeypatch):
    asked = []

    def handler(request):
        asked.append(request.url.path)
        return httpx.Response(200, text='<html><head><script src="/app.js"></script></head><body><a href="https://old.site.test/">x</a></body></html>',
                              headers={"content-type": "text/html"})

    monkeypatch.setattr(takeover, "check", lambda *a, **k: pytest.fail("takeover ran on an unverified site"))
    monkeypatch.setattr("app.scans.fetch.assert_public", lambda url: None)
    monkeypatch.setattr(tls, "check", lambda url, **k: [])
    with httpx.Client(transport=httpx.MockTransport(handler)) as c:
        site.audit("https://site.test/", c, verified=False, max_pages=1, time_limit=5)
    # Bundles may be read on every plan for the Supabase check (P1.1); exposed paths and source maps never.
    assert not [p for p in asked if p in security.EXPOSED or p.endswith(".map")]


# ---------- CSP (csp-evaluator port) ----------


def weak(policy, meta=()):
    return titles(csp.check({"content-security-policy": policy} if policy else {}, list(meta), "https://s.test/"))


def test_strict_policies_are_clean():
    assert weak("default-src 'self'") == []
    assert weak("default-src 'none'; script-src 'self' https://cdn.example.com; object-src 'none'") == []
    assert weak("script-src 'nonce-abc123' 'strict-dynamic' 'unsafe-inline' https:; object-src 'none'; base-uri 'none'") == []


def test_weak_policies_name_the_directive():
    assert set(weak("script-src 'self' 'unsafe-inline' 'unsafe-eval' *")) == {"CSP allows inline scripts", "CSP allows eval", "CSP allows scripts from any site", "CSP has no object-src"}
    assert weak("frame-ancestors 'none'") == ["CSP does not restrict scripts", "CSP has no object-src"]
    assert "CSP has no base-uri" in weak("script-src 'nonce-r4nd0m'; object-src 'none'")
    assert "CSP allows plugins from any site" in weak("default-src 'self'; object-src data:")


def test_a_second_stricter_policy_wins():
    assert weak("script-src * 'unsafe-inline'; object-src 'none'", ["script-src 'self'"]) == []


def test_meta_policy_counts_as_a_csp():
    resp = httpx.Response(200, text="<head><meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'self'\"></head>",
                          headers={"content-type": "text/html"}, request=httpx.Request("GET", "https://s.test/"))
    assert not [t for t in titles(security.check_headers(resp)) if "Content-Security-Policy" in t or t.startswith("CSP")]


# ---------- HSTS and cookies ----------


def headers(**h):
    return titles(security.check_headers(httpx.Response(200, text="", headers={k.replace("_", "-"): v for k, v in h.items()}, request=httpx.Request("GET", "https://s.test/"))))


def test_hsts_quality():
    assert "HSTS max-age is too short" in headers(strict_transport_security="max-age=86400")
    assert "HSTS is switched off" in headers(strict_transport_security="max-age=0")
    assert "HSTS header is invalid" in headers(strict_transport_security="includeSubDomains")
    assert "HSTS preload requirements not met" in headers(strict_transport_security="max-age=31536000; preload")
    assert not [t for t in headers(strict_transport_security="max-age=63072000; includeSubDomains; preload") if "HSTS" in t]


def test_cookie_prefix_rules():
    resp = httpx.Response(200, request=httpx.Request("GET", "https://s.test/"), headers=[
        ("set-cookie", "__Host-a=1; Path=/; Secure; HttpOnly; SameSite=Lax"),
        ("set-cookie", "__Host-b=1; Path=/app; Domain=s.test; Secure; HttpOnly; SameSite=Lax"),
        ("set-cookie", "__Secure-c=1; HttpOnly; SameSite=Lax"),
    ])
    found = titles(security.check_headers(resp))
    assert 'Cookie "__Host-b" breaks its __Host- prefix rules' in found and 'Cookie "__Secure-c" breaks its __Secure- prefix rules' in found
    assert not [t for t in found if "__Host-a" in t]


# ---------- CORS, SRI ----------


def cors(answer):
    with httpx.Client(transport=httpx.MockTransport(answer)) as c:
        return titles(security.check_cors("https://s.test/", c))


def test_cors(monkeypatch):
    monkeypatch.setattr("app.scans.fetch.assert_public", lambda url: None)
    echo = lambda cred: lambda r: httpx.Response(200, headers={"access-control-allow-origin": r.headers["origin"], **({"access-control-allow-credentials": "true"} if cred else {})})
    assert cors(echo(True)) == ["CORS trusts any website with visitors' cookies"]
    assert cors(echo(False)) == ["CORS allows any origin"]
    assert cors(lambda r: httpx.Response(200, headers={"access-control-allow-origin": "*", "access-control-allow-credentials": "true"})) == ["CORS combines * with credentials"]
    assert cors(lambda r: httpx.Response(200, headers={"access-control-allow-origin": "*"})) == []
    assert cors(lambda r: httpx.Response(200, headers={"access-control-allow-origin": "https://app.s.test"})) == []


def test_sri_only_for_public_cdns():
    html = """<script src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.1/dist/cdn.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/htmx.org@2.0.0" integrity="sha384-x" crossorigin="anonymous"></script>
    <script src="https://www.googletagmanager.com/gtag/js?id=G-1"></script><script src="https://js.stripe.com/v3/"></script>"""
    found = security.check_content(html, "https://s.test/")
    sri = [f for f in found if "integrity" in f.title]
    assert len(sri) == 1 and "alpinejs" in sri[0].evidence and "htmx" not in sri[0].evidence


# ---------- vulnerable libraries (retire.js data) ----------


def test_library_versions_compare_like_retire():
    assert libraries.at_or_above("1.9.0", "1.9.0b1") and not libraries.at_or_above("1.9.0b1", "1.9.0")
    assert libraries.at_or_above("3.5.0", "3.5.0") and not libraries.at_or_above("1.12.4", "3.0.0")


@pytest.mark.parametrize("url, expected", [
    ("https://code.jquery.com/jquery-1.12.4.min.js", ("jquery", "1.12.4")),
    ("https://cdnjs.cloudflare.com/ajax/libs/jquery/1.12.4/jquery.min.js", ("jquery", "1.12.4")),
    ("https://cdn.jsdelivr.net/npm/bootstrap@3.3.7/dist/js/bootstrap.min.js", ("bootstrap", "3.3.7")),
    ("https://ajax.googleapis.com/ajax/libs/angularjs/1.5.8/angular.min.js", ("angularjs", "1.5.8")),
])
def test_library_urls(url, expected):
    assert libraries.detect_url(url) == [expected]
    assert libraries.check_scripts([url])[0].title == f"{expected[0]} {expected[1]} has known vulnerabilities"


def test_current_versions_and_own_scripts_are_clean():
    assert libraries.check_scripts(["https://code.jquery.com/jquery-3.7.1.min.js", "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js",
                                    "https://s.test/assets/index-4f2a1b.js"]) == []


def test_library_banner_in_a_bundle():
    finding = libraries.check_content("/*! jQuery v1.8.3 jquery.com | jquery.org/license */\n!function(){}", "https://s.test/app.js")[0]
    assert finding.title == "jquery 1.8.3 has known vulnerabilities" and "CVE-" in finding.detail and "3.5.0" in finding.fix


# ---------- secrets (gitleaks rules) ----------

SENDGRID = "SG." + "hF3kQ9zLm2Xw" + "Rt8Yp4Vb6N" + "." + "aZ3xQ7mK2pL9wR4tY8vB1nC6dF0gH5jS" + "3kE7uI2oW9q"


def test_gitleaks_rules_find_real_looking_keys():
    text = f'var a="{SENDGRID}"; var b="sk_' + 'live_' + 'q7XbR2mKp9LwZ4tN8vC1jH6d"; var c="ghp_' + "Aq9Zr4Lm7Xw2Kt8Np3Vb6Hd1Jf5Cs0Ge2Qyx" + '";'
    assert {rid for rid, _ in secrets.find(text)} == {"sendgrid-api-token", "stripe-access-token", "github-pat"}


def test_public_and_placeholder_values_are_not_secrets():
    anon_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYW5vbiJ9.c2lnbmF0dXJl"
    publishable, placeholder = "pk_" + "live_" + "q7XbR2mKp9LwZ4tN8vC1jH6d", "sk_" + "live_" + "x" * 24  # assembled: push protection
    text = f'var s="{anon_jwt}"; var pk="{publishable}"; var k="{placeholder}"; var t="AKIA' + 'FAKE' * 4 + '";'
    assert secrets.find(text) == []


def test_masking_keeps_four_characters():
    assert secrets.mask(SENDGRID) == "SG.h… (69 characters)"


def test_google_browser_key_is_low_with_restriction_advice(monkeypatch):
    key = "AIza" + "Sy" + "B7q2Zr4Lm7Xw2Kt8Np3Vb6Hd1Jf5Cs0Ge"  # AIza and 35 characters
    monkeypatch.setattr("app.scans.fetch.assert_public", lambda url: None)
    page = '<script src="/main.js"></script>'
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, text=f'const firebase={{apiKey:"{key}"}}'))) as c:
        found = security.check_bundles(page, "https://s.test/", c)
    assert [(f.severity, f.title) for f in found] == [("low", "Google API key in a JavaScript bundle")] and key not in found[0].evidence


# ---------- exposed paths and source maps (verified only) ----------


def peek_site(routes):
    def handler(request):
        body, ctype = routes.get(request.url.path, ("<!doctype html><div id=root></div>", "text/html"))  # SPA catch-all
        return httpx.Response(200, content=body if isinstance(body, bytes) else body.encode(), headers={"content-type": ctype})
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_single_page_app_catch_all_is_not_an_exposed_file(monkeypatch):
    monkeypatch.setattr("app.scans.security.assert_public", lambda url: None)
    with peek_site({}) as c:
        assert security.check_exposed("https://s.test", c) == []


def test_exposed_backups_dumps_and_status_pages(monkeypatch):
    monkeypatch.setattr("app.scans.security.assert_public", lambda url: None)
    routes = {"/backup.zip": (b"PK\x03\x04" + b"\0" * 100, "application/zip"), "/dump.sql": ("-- PostgreSQL database dump\nCREATE TABLE a();", "text/plain"),
              "/server-status": ("<h1>Apache Server Status for s.test</h1>", "text/html"), "/.git/index": (b"DIRC\0\0\0\2", "application/octet-stream"),
              "/.env.local": ("API_KEY=abc", "text/plain")}
    with peek_site(routes) as c:
        found = {f.title for f in security.check_exposed("https://s.test", c)}
    assert found == {f"{p} is publicly readable" for p in routes}


def test_source_maps(monkeypatch):
    monkeypatch.setattr("app.scans.security.assert_public", lambda url: None)
    monkeypatch.setattr("app.scans.fetch.assert_public", lambda url: None)
    routes = {"/a.js": ("x()\n//# sourceMappingURL=a.js.map", "text/javascript"), "/a.js.map": ('{"version":3,"sources":["a.ts"],"mappings":"AAAA"}', "application/json"),
              "/b.js": ("y()\n//# sourceMappingURL=b.js.map", "text/javascript"),  # the map path falls through to the SPA's HTML
              "/c.js": ("z()\n//# sourceMappingURL=https://sentry.example/c.js.map", "text/javascript")}
    page = '<script src="/a.js"></script><script src="/b.js"></script><script src="/c.js"></script>'
    with peek_site(routes) as c:
        maps = [f for f in security.check_bundles(page, "https://s.test/", c) if f.title == "Source maps are publicly readable"]
    assert len(maps) == 1 and maps[0].evidence == "https://s.test/a.js.map"


# ---------- TLS certificate and version (a local TLS server) ----------


def make_cert(days_valid, directory):
    crypto = pytest.importorskip("cryptography")  # noqa: F841 - installed with google-auth; only these tests need it
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.datetime.now(datetime.UTC)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=30)).not_valid_after(now + datetime.timedelta(days=days_valid))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False)
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True).sign(key, hashes.SHA256()))
    cert_path, key_path = os.path.join(directory, "c.pem"), os.path.join(directory, "k.pem")
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    with open(key_path, "wb") as f:
        f.write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    return cert_path, key_path


@pytest.fixture
def tls_server(tmp_path, monkeypatch):
    monkeypatch.setenv("ALLOW_LOCAL_SCANS", "1")

    def run(days_valid):
        cert_path, key_path = make_cert(days_valid, tmp_path)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.load_cert_chain(cert_path, key_path)
        listener = socket.create_server(("127.0.0.1", 0))
        port = listener.getsockname()[1]

        def serve():
            while True:
                try:
                    conn, _ = listener.accept()
                except OSError:
                    return
                try:
                    with ctx.wrap_socket(conn, server_side=True):
                        pass
                except (ssl.SSLError, OSError):
                    conn.close()

        threading.Thread(target=serve, daemon=True).start()
        client = ssl.create_default_context(cafile=cert_path)
        return f"https://localhost:{port}/", client, listener

    return run


def test_certificate_close_to_expiry(tls_server):
    url, client, listener = tls_server(10)
    try:
        found = tls.check(url, context=client)
    finally:
        listener.close()
    assert [(f.severity, f.title) for f in found] == [("medium", "TLS certificate expires in 9 days")] or \
        [(f.severity, f.title) for f in found] == [("medium", "TLS certificate expires in 10 days")]


def test_healthy_certificate_is_clean(tls_server):
    url, client, listener = tls_server(200)
    try:
        assert tls.check(url, context=client) == []
    finally:
        listener.close()


def test_untrusted_certificate(tls_server):
    url, _, listener = tls_server(200)
    try:
        found = tls.check(url, context=ssl.create_default_context())  # the self-signed test CA is not trusted here
    finally:
        listener.close()
    assert [f.title for f in found] == ["TLS certificate is not trusted"]


def test_plain_http_and_local_sites_are_skipped(monkeypatch):
    monkeypatch.delenv("ALLOW_LOCAL_SCANS", raising=False)
    assert tls.check("http://s.test/") == [] and tls.check("https://localhost:1/") == []


# ---------- DNS: CAA and takeover (recorded DNS-over-HTTPS answers) ----------


def doh(answers, pages=None):
    """answers: (name, type) -> (status, [data]). pages: host -> body for plain GETs."""
    def handler(request):
        if request.url.host == "cloudflare-dns.com":
            status, data = answers.get((request.url.params["name"], request.url.params["type"]), (0, []))
            code = {"CAA": 257, "CNAME": 5, "A": 1}[request.url.params["type"]]
            return httpx.Response(200, json={"Status": status, "Answer": [{"type": code, "data": d} for d in data]})
        return httpx.Response(404 if request.url.host not in (pages or {}) else 200, text=(pages or {}).get(request.url.host, ""))
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_caa_on_a_parent_domain_counts():
    with doh({("example.com", "CAA"): (0, ['0 issue "letsencrypt.org"'])}) as c:
        assert tls.check_caa("https://app.example.com/", c) == []
    with doh({}) as c:
        assert [f.title for f in tls.check_caa("https://app.example.com/", c)] == ["No CAA record"]
    with doh({}) as c:  # shared hosting and local sites do not own their DNS
        assert tls.check_caa("https://me.vercel.app/", c) == [] and tls.check_caa("http://127.0.0.1:8000/", c) == []


PAGES = [("https://example.com/", ('<a href="https://docs.example.com/">Docs</a><a href="https://blog.example.com/">Blog</a>'
                                   '<script src="https://cdn.example.com/a.js"></script><a href="https://other.com/">x</a>'
                                   '<a href="https://old.example.com/">Old</a><a href="https://www.example.com/">Home</a>'))]


def test_subdomains_come_from_the_crawl_and_stay_under_the_verified_host():
    assert sorted(takeover.subdomains(PAGES, "https://www.example.com/")) == ["blog.example.com", "cdn.example.com", "docs.example.com", "old.example.com"]


def test_takeover_fingerprints(monkeypatch):
    monkeypatch.setattr("app.scans.fetch.assert_public", lambda url: None)
    s3 = next(s for s in takeover._services() if s["service"] == "AWS/S3")
    nx = next(s for s in takeover._services() if s["nxdomain"])
    answers = {
        ("docs.example.com", "CNAME"): (0, [f"acme-docs.{s3['cname'][0]}."]),  # bucket deleted: S3 serves its "no such bucket" page
        ("blog.example.com", "CNAME"): (0, [f"acme-blog.{nx['cname'][0]}."]), (f"acme-blog.{nx['cname'][0]}", "A"): (3, []),
        ("cdn.example.com", "CNAME"): (0, ["gone.unknown-host.net."]), ("gone.unknown-host.net", "A"): (3, []),
        ("old.example.com", "CNAME"): (0, ["live.unknown-host.net."]), ("live.unknown-host.net", "A"): (0, ["203.0.113.9"]),
    }
    with doh(answers, pages={"docs.example.com": "<Error><Code>NoSuchBucket</Code><Message>The specified bucket does not exist</Message></Error>"}) as c:
        found = {(f.severity, f.title) for f in takeover.check(PAGES, "https://example.com/", c)}
    assert found == {("high", "Subdomain docs.example.com can be taken over"), ("high", "Subdomain blog.example.com can be taken over"),
                     ("medium", "Subdomain cdn.example.com points at a name that does not exist")}


def test_vendored_data_loads_and_compiles():
    assert len(secrets._rules()[0]) > 200 and len(libraries._repo()) > 50 and len(takeover._services()) > 20
    with open(os.path.join(os.path.dirname(security.__file__), "data", "gitleaks.json"), encoding="utf-8") as f:
        assert not {"generic-api-key", "jwt"} & {r["id"] for r in json.load(f)["rules"]}


def test_verified_checks_stay_on_the_verified_host(monkeypatch):
    """A verified site that redirects to another host must not get that host's files and bundles probed."""
    asked = []

    def handler(request):
        asked.append(f"{request.url.host}{request.url.path}")
        if request.url.host == "mine.test":
            return httpx.Response(301, headers={"location": "https://victim.test/"})
        return httpx.Response(200, text='<script src="/app.js"></script>', headers={"content-type": "text/html"})

    monkeypatch.setattr("app.scans.fetch.assert_public", lambda url: None)
    monkeypatch.setattr("app.scans.security.assert_public", lambda url: None)
    monkeypatch.setattr(tls, "check", lambda url, **k: [])
    with httpx.Client(transport=httpx.MockTransport(handler)) as c:
        site.audit("https://mine.test/", c, verified=True, max_pages=1, time_limit=5)
    assert not [a for a in asked if a.startswith("victim.test/.") or a.endswith((".sql", ".zip", "server-status"))]
    from app.scans import fetch

    assert fetch.same_site("https://example.com/", "https://www.example.com/") and not fetch.same_site("https://a.test/", "https://b.test/")
