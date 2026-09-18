"""Every seeded trap in evals/traps.json is present on the hard site and absent on the easy one."""

import json
import os
import re
import sys

import httpx
import pytest

EVALS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "evals")
sys.path.insert(0, EVALS)
from serve import HEADERS, start

EASY, HARD = "http://127.0.0.1:8111", "http://127.0.0.1:8112"


@pytest.fixture(scope="module", autouse=True)
def servers():
    a, b = start("easy", 8111), start("hard", 8112)
    yield
    a.shutdown()
    b.shutdown()


def get(base, path):
    return httpx.get(base + path, follow_redirects=False)


def test_traps_manifest_is_valid():
    with open(os.path.join(EVALS, "traps.json")) as f:
        traps = json.load(f)
    assert len(traps) >= 15 and len({t["id"] for t in traps}) == len(traps)
    assert {t["kind"] for t in traps} == {"ux", "seo", "security"}


def test_easy_flow_is_reachable():
    home = get(EASY, "/").text
    assert 'href="/signup.html"' in home and "Sign up" in home
    signup = get(EASY, "/signup.html").text
    assert "<h1>Create your account</h1>" in signup and "at least 8 characters" in signup
    assert get(EASY, "/welcome.html").status_code == 200
    assert get(EASY, "/pricing.html").text.count("$") >= 1


def test_ux_traps():
    home = get(HARD, "/").text
    assert 'class="tiny"' in home and "Sign up" not in home  # U1 hidden signup
    assert get(HARD, "/plans.html").status_code == 404  # U3 broken pricing link
    assert home.count("Continue") == 1 and home.count("Proceed") == 1  # U4 twin CTAs
    assert "$" not in get(HARD, "/pricing.html").text  # U5 no prices
    signup = get(HARD, "/signup.html").text
    assert "if (!this.terms.checked) { return; }" in signup  # U2 silent failure
    visible = re.sub(r"<script>.*</script>", "", signup, flags=re.DOTALL)
    assert "pw.length < 12" in signup and "character" not in visible  # U6 rule not stated


def test_seo_traps():
    home = get(HARD, "/").text
    assert 'name="description"' not in home and 'name="description"' in get(EASY, "/").text  # S1
    assert home.count("<h1>") == 2 and "<h1>" not in get(HARD, "/signup.html").text  # S2
    assert re.search(r"<img [^>]*>", home) and "alt=" not in home  # S3
    assert all("<title>Home</title>" in get(HARD, p).text for p in ("/", "/signup.html", "/pricing.html"))  # S4
    assert 'rel="canonical"' not in home and 'rel="canonical"' in get(EASY, "/").text
    assert "Disallow: /" in get(HARD, "/robots.txt").text and "Allow: /" in get(EASY, "/robots.txt").text  # S5
    assert get(HARD, "/sitemap.xml").status_code == 404 and get(EASY, "/sitemap.xml").status_code == 200  # S6


def test_security_traps():
    hard, easy = get(HARD, "/"), get(EASY, "/")
    for h in ("strict-transport-security", "content-security-policy", "x-content-type-options", "x-frame-options"):
        assert h not in hard.headers and h in easy.headers  # X1
    assert "httponly" not in hard.headers["set-cookie"].lower() and "httponly" in easy.headers["set-cookie"].lower()  # X2
    assert get(HARD, "/.env").status_code == 200 and get(EASY, "/.env").status_code == 404  # X3
    assert get(HARD, "/.git/config").status_code == 200 and get(EASY, "/.git/config").status_code == 404
    assert re.search(r"sk_live_[A-Za-z0-9]{20,}", get(HARD, "/app.js").text)  # X4
    assert 'action="http://' in get(HARD, "/signup.html").text and 'action="https://' in get(EASY, "/signup.html").text  # X5
    assert hard.headers["server"].startswith("Apache/2.2") and HEADERS["hard"]["Server"] == hard.headers["server"]  # X6
