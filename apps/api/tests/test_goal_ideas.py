"""Goal suggestions come from a site's own links and buttons, in code (app/goal_ideas.py)."""

import httpx
import pytest

from app import goal_ideas
from app.scans import fetch

HOME = "<a href='/pricing'>Pricing</a><a href='/login'>Log in</a><button>Start free</button><a href='https://other.example/x'>Partner</a>"
SHELL = "<title>Pick a theme</title><a href='/paper/'>Paper</a><a href='/ledger/'>Ledger</a><a href='/signal/'>Signal</a>"
PAPER = "<nav><a href='projects.html'>02.Projects</a><a href='about.html'>03.About</a><a href='contact.html'>contact</a></nav>"


def test_rules_match_link_and_button_text_and_keep_page_order_of_rules():
    texts, links = goal_ideas.labels(HOME, "https://shop.example/")
    assert sorted(texts) == ["Log in", "Partner", "Pricing", "Start free"]
    assert links == ["https://shop.example/pricing", "https://shop.example/login"]  # same site only
    assert goal_ideas.match(texts) == ["Sign up for an account", "Log in and reach the dashboard", "Find the pricing and pick the right plan"]


def test_nothing_recognised_gives_no_ideas_rather_than_guesses():
    assert goal_ideas.match(["Paper", "Ledger", "Signal"]) == []


@pytest.fixture
def site(monkeypatch):
    pages = {"https://folio.example/": SHELL, "https://folio.example/paper/": PAPER, "https://folio.example/ledger/": "<a href='x'>Blog</a>"}
    asked = []

    def get(c, url, **kw):
        asked.append(url)
        if url not in pages:
            return None
        return httpx.Response(200, headers={"content-type": "text/html"}, text=pages[url], request=httpx.Request("GET", url))

    monkeypatch.setattr(fetch, "get", get)
    monkeypatch.setattr(goal_ideas, "rendered", lambda site: [])
    goal_ideas._recent.clear()
    return asked


def test_a_chooser_home_page_is_followed_one_level_to_at_most_two_pages(site):
    ideas = goal_ideas.suggest("https://folio.example/")
    assert ideas == ["Find a way to get in touch", "Open a project and read about it", "Work out who is behind this site and what they do", "Find a recent article and open it"]
    assert site == ["https://folio.example/", "https://folio.example/paper/", "https://folio.example/ledger/"]  # never the third link


def test_an_unreadable_site_gives_no_ideas(site):
    assert goal_ideas.suggest("https://down.example/") == []


def test_a_site_with_no_links_in_its_html_is_read_as_rendered_and_remembered(site, monkeypatch):
    looks = []
    monkeypatch.setattr(goal_ideas, "rendered", lambda url: looks.append(url) or ["Find a way to get in touch", "Open a project and read about it"])
    assert goal_ideas.suggest("https://spa.example/") == ["Find a way to get in touch", "Open a project and read about it"]
    assert goal_ideas.suggest("https://spa.example") == ["Find a way to get in touch", "Open a project and read about it"]
    assert looks == ["https://spa.example/"]  # the browser opened once


def test_no_second_browser_while_a_live_run_is_walking(monkeypatch):
    from app import db
    from app.runner import cdp

    monkeypatch.setattr(db, "running_cloud_runs", lambda: 1)
    monkeypatch.setattr(cdp, "browser", lambda *a, **k: pytest.fail("no browser should start"))
    assert goal_ideas.rendered("https://spa.example/") == []
