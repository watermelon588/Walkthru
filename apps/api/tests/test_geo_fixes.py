"""GEO fix pack: copy-paste fixes built in code from the audited pages. No model, so nothing is invented."""

import json
from pathlib import Path

from app.scans import geo

SHELL = """<!doctype html><html><head><title>Tripverse: plan trips in 3D</title>
<meta name="description" content="Describe a trip and get a 3D plan with routes and costs.">
<script type="module" crossorigin src="/assets/index-D4f9a1.js"></script></head><body><div id="root"></div></body></html>"""

READY = Path(__file__).with_name("test_geo.py").read_text(encoding="utf-8").split('GOOD = """')[1].split('"""')[0]


def fixes(pages, robots=None, llms=(404, "")):
    return geo.audit("https://trip.test/", pages, robots, llms, (200, "", {}), full=True).fixes


def by_id(result):
    return {f["id"]: f for f in result}


def test_blocked_ai_crawlers_get_a_robots_block_that_allows_them():
    f = by_id(fixes([("https://trip.test/", READY)], robots="User-agent: *\nDisallow: /"))["robots"]
    assert "User-agent: OAI-SearchBot\nAllow: /" in f["code"] and f["file"] == "robots.txt"


def test_missing_structured_data_gets_valid_json_ld_with_the_real_name():
    f = by_id(fixes([("https://trip.test/", SHELL)]))["schema"]
    data = json.loads(f["code"].split(">", 1)[1].rsplit("<", 1)[0])
    names = {o["name"] for o in data["@graph"]}
    assert names == {"Tripverse"} and {o["@type"] for o in data["@graph"]} >= {"Organization", "WebSite"}


def test_missing_llms_txt_gets_a_draft_listing_the_audited_pages():
    f = by_id(fixes([("https://trip.test/", SHELL), ("https://trip.test/pricing", READY)]))["llms"]
    assert f["code"].startswith("# Tripverse\n\n> Describe a trip") and "https://trip.test/pricing" in f["code"]


def test_a_vite_shell_gets_a_framework_specific_rendering_fix():
    f = by_id(fixes([("https://trip.test/", SHELL)]))["render"]
    assert "Vite" in f["title"] + f["note"] and "<h1>" in f["code"] and "Describe a trip" in f["code"]


def test_a_ready_site_needs_no_fixes():
    assert fixes([("https://trip.test/", READY)], llms=(200, "# Acme Notes\n> x\n## Docs\n- [a](https://acme.test/)")) == []


def test_free_reports_keep_one_fix_and_the_count():
    result = geo.audit("https://trip.test/", [("https://trip.test/", SHELL)], None, (404, ""), (200, "", {}), full=False)
    summary = result.summary()
    assert len(summary["fixes"]) == 1 and summary["fixes_total"] == len(result.fixes) > 1
