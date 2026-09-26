"""Site modes, the blocklist and goal rules (app/agent/policy.py, docs/agent-safety-plan.md sections 3 and 4)."""

import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import MemorySaver

from app import db, main
from app.agent import goal, policy, runtime
from app.agent.persona import build_graph
from app.agent.schema import PersonaStep
from app.main import app
from tests.conftest import USER


class Script:
    def __init__(self, steps):
        self.steps = list(steps)

    def invoke(self, messages):
        return self.steps.pop(0) if self.steps else PersonaStep(thought="done", action="done", confusion=0)


@pytest.fixture
def agent(monkeypatch):
    g = build_graph(Script([PersonaStep(thought="look", action="scroll", confusion=0)] * 5), MemorySaver())
    monkeypatch.setattr(runtime, "graph", lambda tier: g)


def page(url):
    return {"url": url, "title": "t", "elements": [], "text": "hello"}


def start(site="https://fixture.test", goal_text="sign up", url=None, **kw):
    return TestClient(app).post("/runs", json={"site": site, "goal": goal_text, "observation": page(url or site + "/")} | kw)


# ---------- the rules on their own ----------

ACTIONS = [
    "Scroll 5 posts and like all of them", "like 5 posts", "Follow 3 creators", "follow @nasa", "Share the article on Twitter", "Post a photo",
    "Comment on the latest post", "leave a comment", "Reply to the first comment", "Message the seller", "Buy the cheapest shoes",
    "Add the red shirt to cart", "add to cart", "Checkout", "Place an order", "Send a friend request", "Write a review of the product",
    "Subscribe to the newsletter", "vote for the best answer", "donate $5", "Pay the invoice", "Order a pizza", "Find the product, then buy it",
    "connect with 3 recruiters", "Transfer money to John", "Retweet it", "please upvote",
    "li\u200bke the post", "\uff4c\uff49\uff4b\uff45 the post",  # an invisible character or full-width letters change nothing
]
VISITOR_GOALS = [
    "Sign up for a free account", "Find the pricing page", "Check the checkout page loads", "Check the Share button opens a dialog",
    "Order history page shows orders", "Read the latest blog post", "Follow the signup flow to the dashboard", "Pay attention to the pricing table",
    "Find a plan like the one on the homepage", "Check that the comment section loads", "Post-signup onboarding should explain the dashboard",
    "Review the pricing page", "Checkout page should show taxes", "Find where to buy", "I'd like to see the docs", "Open the Subscribe page",
    "Start the free trial", "Find the error message on the login form", "Book a demo", "Check out the pricing page", "Find how to buy a plan",
]
BULK = ["create 50 accounts", "Like every post on the feed", "sign up 3 accounts", "send hundreds of messages", "follow all the users",
        "post 20 comments", "make several accounts"]
NOT_BULK = ["Check all the pricing plans", "Look at every page in the docs", "Sign up for an account", "like 5 posts", "Compare 3 plans"]


@pytest.mark.parametrize("text", ACTIONS)
def test_social_and_commerce_goals_need_a_verified_site(text):
    assert policy.owner_only(text)


@pytest.mark.parametrize("text", VISITOR_GOALS)
def test_ordinary_test_goals_are_not_mistaken_for_actions(text):
    assert not policy.owner_only(text)


@pytest.mark.parametrize("text", BULK)
def test_bulk_goals(text):
    assert policy.bulk(text)


@pytest.mark.parametrize("text", NOT_BULK)
def test_not_bulk(text):
    assert not policy.bulk(text)


@pytest.mark.parametrize(("url", "category"), [
    ("https://www.instagram.com/p/x", "social networks"),
    ("https://m.facebook.com", "social networks"),
    ("https://INSTAGRAM.COM./", "social networks"),
    ("https://irs.gov", "government and tax"),
    ("https://www.gov.uk/x", "government and tax"),
    ("https://mybank.bank", "banking and payments"),
    ("https://mail.google.com", "webmail"),
    ("https://example.com", None),
    ("https://notinstagram.com", None),
    ("https://instagram.com.evil.io", None),
    ("https://www.google.com", None),
    ("http://127.0.0.1:8101", None),
    ("not a url", None),
])
def test_blocked_hosts_match_the_domain_and_its_subdomains_only(url, category):
    assert policy.category(url) == category


def test_every_blocklist_entry_is_a_bare_lowercase_host():
    for domains in policy.BLOCKLIST.values():
        for d in domains:
            assert d == d.strip().lower() and "/" not in d and not d.startswith(("www.", ".")), d


def test_verification_is_only_asked_for_when_it_decides_the_answer():
    asked = []
    policy.check("https://fixture.test", "Find the pricing page", start_url="https://fixture.test/", logged_in=False, verified=lambda: asked.append(1) or False)
    assert asked == []
    with pytest.raises(policy.Refused) as e:
        policy.check("https://fixture.test", "create 50 accounts", start_url="https://fixture.test/", logged_in=False, verified=lambda: True)
    assert e.value.code == "goal_refused"  # bulk goals are refused even on a verified site


# ---------- at run start ----------


def test_blocked_site_is_refused_before_any_model_call_or_run(monkeypatch, fake_db, agent):
    monkeypatch.setattr(goal, "plan", lambda *a, **k: pytest.fail("the goal planner must not run"))
    r = start("https://www.instagram.com", "Find the explore page")
    assert r.status_code == 403 and r.headers["X-Walkthru-Code"] == "blocked_site"
    assert "social networks" in r.json()["detail"] and "instagram.com" in r.json()["detail"]
    assert fake_db == {}  # no run was stored, so none was used


def test_the_instagram_goal_is_refused_on_any_unverified_site(monkeypatch, fake_db, agent):
    monkeypatch.setattr(goal, "plan", lambda *a, **k: pytest.fail("the goal planner must not run"))
    r = start(goal_text="scroll 5 posts and like all of them")
    assert r.status_code == 422 and r.headers["X-Walkthru-Code"] == "goal_refused" and "fixture.test" in r.json()["detail"]
    assert fake_db == {}


def test_a_tab_on_a_blocked_host_is_refused_whatever_site_is_claimed(fake_db, agent, monkeypatch):
    monkeypatch.setattr(main, "_verified", lambda site, user_id: True)  # verified fixture.test proves nothing about instagram.com
    r = start("https://fixture.test", "Find the pricing page", url="https://www.instagram.com/")
    assert r.status_code == 403 and r.headers["X-Walkthru-Code"] == "blocked_site"


def test_signed_in_pages_need_a_verified_domain(passes, fake_db, agent):
    passes.append({"user_id": USER, "plan": "pro", "starts_at": "2000-01-01T00:00:00+00:00", "expires_at": "2999-01-01T00:00:00+00:00", "runs_granted": 40})
    r = start(logged_in=True)
    assert r.status_code == 403 and r.headers["X-Walkthru-Code"] == "visitor_mode_limit"


def test_an_ordinary_run_starts_in_visitor_mode(fake_db, agent):
    r = start(goal_text="Find the pricing page")
    assert r.status_code == 200 and r.json()["mode"] == "visitor" and r.json()["verified"] is False


def test_a_verified_owner_may_test_their_own_listed_domain_and_act_on_it(monkeypatch, fake_db, agent):
    monkeypatch.setattr(main, "_verified", lambda site, user_id: True)
    r = start("https://www.instagram.com", "like the first post")
    assert r.status_code == 200 and r.json()["mode"] == "owner"


# ---------- during a run ----------


def test_reaching_a_blocked_host_mid_run_stops_the_run_truthfully(monkeypatch, fake_db, agent):
    monkeypatch.setattr(db, "mark_run_stopped", lambda run_id, steps, tokens=0: fake_db[run_id].update(status="stopped", steps=steps) or True)
    monkeypatch.setattr(main, "finish_run", lambda run_id, values: None)
    run_id = start(goal_text="Find the pricing page").json()["run_id"]
    r = TestClient(app).post(f"/runs/{run_id}/observe", json={"observation": page("https://www.facebook.com/sharer")})
    assert r.status_code == 200 and r.json()["status"] == "stopped" and r.json()["code"] == "blocked_site"
    assert "facebook.com" in fake_db[run_id]["steps"][-1]["note_after"]
