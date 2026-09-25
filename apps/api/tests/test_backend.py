"""Backend exposure check (todo P1.1) against a recorded fake Supabase and Firebase."""

import base64
import json

import httpx

from app.scans import backend

PROJECT = "https://abcdefghijklmnopqrst.supabase.co"


def jwt(role: str) -> str:
    enc = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")
    return f"{enc({'alg': 'HS256', 'typ': 'JWT'})}.{enc({'role': role, 'iss': 'supabase'})}.signaturepart1234"


def client(bundle_js: str, calls: list[str]) -> httpx.Client:
    html = f"<html><head><script>const sb = createClient('{PROJECT}', '{jwt('anon')}')</script><script src='/assets/app.js'></script></head><body>Hi</body></html>"

    def handler(request: httpx.Request) -> httpx.Response:
        url, path = str(request.url), request.url.path
        calls.append(f"{request.method} {url}")
        if request.url.host == "site.test":
            return httpx.Response(200, text=html if path == "/" else bundle_js, headers={"content-type": "text/html" if path == "/" else "application/javascript"}, request=request)
        if path == "/rest/v1/":
            return httpx.Response(200, json={"paths": {"/": {}, "/profiles": {}, "/notes": {}, "/rpc/admin_reset": {}}}, request=request)
        if request.method == "HEAD" and path == "/rest/v1/profiles":
            return httpx.Response(206, headers={"content-range": "0-0/1203"}, request=request)
        if request.method == "HEAD" and path == "/rest/v1/notes":
            return httpx.Response(200, headers={"content-range": "*/0"}, request=request)  # RLS hides every row
        if path == "/storage/v1/bucket":
            return httpx.Response(200, json=[{"name": "avatars"}, {"name": "private"}], request=request)
        if path == "/storage/v1/object/list/avatars":
            return httpx.Response(200, json=[{"name": "me.png"}], request=request)
        if path == "/storage/v1/object/list/private":
            return httpx.Response(200, json=[], request=request)
        if "firebaseio.com" in url:
            return httpx.Response(200, text='{"users": true}', request=request)
        return httpx.Response(404, request=request)

    return httpx.Client(transport=httpx.MockTransport(handler))


def run(bundle: str, verified: bool, monkeypatch):
    monkeypatch.setenv("ALLOW_LOCAL_SCANS", "1")
    calls: list[str] = []
    with client(bundle, calls) as c:
        html = c.get("https://site.test/").text
        calls.clear()
        return {f.title: f for f in backend.check(html, "https://site.test/", c, verified=verified)}, calls


def test_verified_probe_counts_rows_without_reading_them(monkeypatch):
    found, calls = run("firebase.initializeApp({databaseURL: 'https://demo-default-rtdb.firebaseio.com'})", True, monkeypatch)
    tables = found["Anyone can read 1 of your database table"]
    assert tables.severity == "high" and tables.evidence == "profiles (1,203 rows)"  # notes (0 readable rows) is not flagged
    assert "alter table public.profiles enable row level security" in tables.fix
    assert found["1 database function is callable with the public key"].evidence == "admin_reset"
    assert found["Anyone can list the files in 1 storage bucket"].evidence == "avatars"
    assert found["Anyone can read your Firebase database"].severity == "high"
    assert "Your site reads Supabase straight from the browser" in found
    assert not any("/rpc/" in call for call in calls)  # functions are listed, never called
    assert not any(call.startswith(("PATCH", "DELETE", "PUT")) for call in calls)  # never writes
    assert all(call.startswith("HEAD") for call in calls if "/rest/v1/profiles" in call or "/rest/v1/notes" in call)  # counts only


def test_unverified_domains_get_the_explanation_but_no_probe(monkeypatch):
    found, calls = run("", False, monkeypatch)
    assert set(found) == {"Your site reads Supabase straight from the browser"}
    assert not any("supabase.co" in call or "firebaseio" in call for call in calls)


def test_a_secret_key_in_a_bundle_is_critical(monkeypatch):
    found, _ = run(f"const admin = '{jwt('service_role')}'", False, monkeypatch)
    assert found["Supabase secret key in the browser"].severity == "high"


def test_projects_that_hide_their_table_list_are_probed_by_the_names_the_code_uses():
    """Newer Supabase keys cannot read the OpenAPI list; the live check on Walkthru's own project found this."""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/rest/v1/":
            return httpx.Response(401, json={"message": "Secret API key required"}, request=request)
        if request.method == "HEAD" and request.url.path == "/rest/v1/profiles":
            return httpx.Response(206, headers={"content-range": "0-0/7"}, request=request)
        return httpx.Response(404, request=request)

    cfg = backend.find_config("supabase.from('profiles').select('*'); supabase.rpc('bump')")
    assert cfg["tables"] == ["profiles"] and cfg["rpcs"] == ["bump"]
    with httpx.Client(transport=httpx.MockTransport(handler)) as c:
        found = {f.title: f for f in backend.probe_supabase(PROJECT, "sb_publishable_x", c, 1e12, cfg["tables"], cfg["rpcs"])}
    assert found["Anyone can read 1 of your database table"].evidence == "profiles (7 rows)"
    assert found["1 database function is callable with the public key"].evidence == "bump"
