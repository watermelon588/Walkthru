"""GEO readiness: can AI search engines fetch, understand and quote the site? Pure checks on fetched HTML."""

import json

from app.scans import geo

GOOD = """<!doctype html><html lang="en"><head>
<title>Acme Notes: shared notes for small teams</title>
<meta name="description" content="Acme Notes keeps a team's notes in one place.">
<link rel="canonical" href="https://acme.test/">
<meta property="og:title" content="Acme Notes"><meta property="og:site_name" content="Acme Notes">
<script type="application/ld+json">{"@context":"https://schema.org","@graph":[
 {"@type":"Organization","name":"Acme Notes","url":"https://acme.test","logo":"https://acme.test/l.png","sameAs":["https://x.com/acme"],"email":"hi@acme.test"},
 {"@type":"SoftwareApplication","name":"Acme Notes","applicationCategory":"BusinessApplication","offers":{"price":"9"}}]}</script>
</head><body>
<nav><a href="/about">About</a> <a href="/contact">Contact</a> <a href="/pricing">Pricing</a> <a href="/privacy">Privacy</a></nav>
<h1>Shared notes for small teams</h1>
<p>Acme Notes is a note-taking app for teams of 2 to 20 people who want every decision written down in one searchable place, without setting up a wiki.</p>
<h2>How it works</h2><ul><li>Write</li><li>Share</li></ul>
<h2>Pricing</h2><p>Free for 3 people, then $9 per person a month. Used by 1,200 teams since 2024.</p>
</body></html>"""

SHELL = """<!doctype html><html><head><title>App</title></head><body><div id="root"></div>
<script type="module" src="/assets/index-abc123.js"></script></body></html>"""


def audit(pages, robots=None, llms=None, probe=(200, "", {}), full=True):
    return geo.audit("https://acme.test/", pages, robots, llms, probe, full=full)


def titles(result):
    return {f.title for f in result.findings}


def test_ready_page_scores_well_and_everything_is_geo_kind():
    r = audit([("https://acme.test/", GOOD)], llms=(200, "# Acme Notes\n> Notes for teams\n## Docs\n- [Start](https://acme.test/docs)"))
    assert r.score >= 86 and r.band == "excellent"
    assert all(f.kind == "geo" for f in r.findings)
    assert r.ai_words > 40 and "Shared notes for small teams" in r.ai_view


def test_javascript_shell_means_ai_search_sees_an_empty_page():
    r = audit([("https://acme.test/", SHELL)])
    assert "Homepage content only appears after JavaScript runs" in titles(r)
    assert r.ai_words == 0 and r.ai_view == ""
    content = next(c for c in r.categories if c["id"] == "content")
    assert content["earned"] == 0
    assert r.band in {"critical", "foundation"}


def test_robots_blocking_a_citation_bot_is_a_high_finding():
    robots = "User-agent: OAI-SearchBot\nDisallow: /\n\nUser-agent: *\nAllow: /"
    r = audit([("https://acme.test/", GOOD)], robots=robots)
    blocked = next(f for f in r.findings if f.title.startswith("robots.txt blocks AI search"))
    assert blocked.severity == "high" and "OAI-SearchBot" in blocked.detail


def test_blocking_training_bots_only_is_a_choice_not_a_fault():
    robots = "User-agent: GPTBot\nDisallow: /\n\nUser-agent: CCBot\nDisallow: /"
    r = audit([("https://acme.test/", GOOD)], robots=robots)
    assert not any("robots.txt" in t for t in titles(r))
    assert any("GPTBot" in n for n in r.notes)


def test_a_403_for_an_ai_search_user_agent_is_reported_as_a_user_agent_block():
    r = audit([("https://acme.test/", GOOD)], probe=(403, "Just a moment...", {"cf-mitigated": "challenge"}))
    f = next(f for f in r.findings if "user agent" in f.title.lower())
    assert f.severity == "high" and "403" in f.evidence


def test_probe_that_could_not_run_is_not_counted():
    r = audit([("https://acme.test/", GOOD)], probe=None)
    access = next(c for c in r.categories if c["id"] == "access")
    assert access["max"] == 15  # the 10 probe points are left out, not given or taken


def test_missing_and_broken_structured_data():
    plain = GOOD.split('<script type="application/ld+json">')[0] + "</head><body><h1>Hi</h1></body></html>"
    assert "No structured data" in titles(audit([("https://acme.test/", plain)]))
    broken = plain.replace("</head>", '<script type="application/ld+json">{"@type": "Organization",</script></head>')
    assert "Structured data does not parse" in titles(audit([("https://acme.test/", broken)]))


def test_missing_llms_txt_is_low_and_labelled_low_impact():
    f = next(f for f in audit([("https://acme.test/", GOOD)], llms=(404, "")).findings if "llms.txt" in f.title)
    assert f.severity == "low" and "low measured impact" in f.detail


def test_free_scope_scores_the_homepage_only():
    pricing_shell = ("https://acme.test/pricing", SHELL)
    paid = audit([("https://acme.test/", GOOD), pricing_shell], full=True)
    free = audit([("https://acme.test/", GOOD), pricing_shell], full=False)
    assert any("/pricing" in (f.evidence or "") for f in paid.findings)
    assert not any("/pricing" in (f.evidence or "") for f in free.findings)


def test_score_is_rounded_percentage_of_measured_points():
    r = audit([("https://acme.test/", GOOD)])
    earned, possible = sum(c["earned"] for c in r.categories), sum(c["max"] for c in r.categories)
    assert r.score == round(100 * earned / possible)
    json.dumps(r.summary())  # stored in the report as JSON


def test_showcase_fixture_is_ready_for_ai_search(monkeypatch):
    """The showcase site is built to score well; if this drops, the scanner or the fixture regressed."""
    import os
    import sys

    import httpx

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "evals"))
    from serve import start

    from app.scans import site

    monkeypatch.setenv("ALLOW_LOCAL_SCANS", "1")
    srv = start("showcase", 8133)
    try:
        with httpx.Client(timeout=10, headers={"Accept": "text/html"}) as c:
            result = site.audit("http://127.0.0.1:8133/", c, verified=False, geo_full=True)
    finally:
        srv.shutdown()
    assert result.geo.score >= 86, (result.geo.score, [f.title for f in result.geo.findings])
    assert not [f for f in result.geo.findings if f.severity == "high"]
