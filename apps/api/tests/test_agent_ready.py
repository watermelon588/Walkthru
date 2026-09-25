"""Agent readiness score (P1.7): can AI agents use the site. Plain code over evidence the report already holds."""

import os

from app.agent import score
from app.scans import agent_signals

FIXTURES = os.path.join(os.path.dirname(__file__), "..", "..", "..", "evals", "fixtures")


def _html(site: str, page: str = "index.html") -> str:
    with open(os.path.join(FIXTURES, site, page), encoding="utf-8") as f:
        return f.read()


def test_homepage_signals_on_the_fixtures():
    showcase, hard = agent_signals.homepage(_html("showcase")), agent_signals.homepage(_html("hard"))
    assert showcase["search_action"] and showcase["fields"] == showcase["named_fields"] > 0 and not showcase["captcha"]
    assert not hard["search_action"] and hard["fields"] > hard["named_fields"]  # a placeholder is not a label


def test_labels_webmcp_and_captcha_are_read_from_html():
    html = ('<form toolname="subscribe"><label>Email <input type="email"></label><input id="n" name="name"><label for="n">Name</label>'
            '<input aria-label="Search"><input type="hidden" name="csrf"><button>Go</button></form>'
            '<script src="https://www.google.com/recaptcha/api.js"></script>')
    s = agent_signals.homepage(html)
    assert (s["forms"], s["fields"], s["named_fields"], s["webmcp"], s["captcha"]) == (1, 3, 3, True, True)


def _report(site: str, findings: list[dict], status: str) -> tuple[dict, str]:
    checks = {"accessibility": "complete", "geo": "complete"}
    return {"findings": findings, "checks": checks, "geo": {"score": 80, "agent": agent_signals.homepage(_html(site))}}, status


def test_showcase_and_hard_fixtures_score_differently_for_the_stated_reasons():
    good = score.agent_ready(*_report("showcase", [], "done"), steps=[{"action": "click"}] * 5)
    unnamed = {"kind": "accessibility", "severity": "high", "title": "Form control has no accessible name", "rule": "a11y.control.name_missing"}
    bad = score.agent_ready(*_report("hard", [unnamed], "gave_up"), steps=[{"action": "click"}] * 12)
    assert good["score"] >= 90 and bad["score"] <= 45, (good, bad)
    why = {p["id"]: p for p in bad["parts"]}
    assert why["goal"]["earned"] == 0 and why["names"]["earned"] < 25 and why["forms"]["earned"] < 12 and why["search"]["earned"] == 0
    assert {p["id"] for p in good["parts"]} == {"goal", "captcha", "names", "forms", "search"}  # no rerun yet: stability not measured


def test_captcha_and_rerun_stability():
    stopped = score.agent_ready({"findings": [], "checks": {}}, "captcha", [])
    assert stopped["score"] == 0 and {p["id"] for p in stopped["parts"]} == {"goal", "captcha"}
    steps = [{"action": "click"}] * 6
    same = score.agent_ready({"findings": [], "checks": {}}, "done", steps, previous={"status": "done", "steps": steps[:5]})
    changed = score.agent_ready({"findings": [], "checks": {}}, "done", steps, previous={"status": "gave_up", "steps": steps * 3})
    assert next(p for p in same["parts"] if p["id"] == "stable")["earned"] == 10
    assert next(p for p in changed["parts"] if p["id"] == "stable")["earned"] == 3


def test_nothing_measured_means_no_score():
    assert score.agent_ready({"findings": [], "checks": {}}, "scan", []) == {"score": None, "parts": []}


def test_browser_diagnostics_count_unnamed_controls():
    steps = [{"diagnostics": {"accessibility": {"issues": [{"rule": "button-name"}, {"rule": "label"}, {"rule": "color-contrast"}]}}}]
    result = score.agent_ready({"findings": [], "checks": {}}, "done", steps)
    assert next(p for p in result["parts"] if p["id"] == "names")["earned"] == 25 - 16
