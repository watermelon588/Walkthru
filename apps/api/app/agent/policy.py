"""Where the agent may act, decided by the server before a run starts. Deterministic code, never a prompt: the model
cannot talk its way past it, and a modified extension still has to start its run here. See docs/agent-safety-plan.md,
sections 3 and 4.

Modes:
- owner: the user verified this domain. Everything a real visitor does; the step gates in persona._enforce still apply.
- visitor: any other public site, the default.
- blocked: banking, trading, social, webmail and similar hosts (blocklist.json). Refused before the run starts,
  unless the user verified that exact domain.

Goal rules run before the goal planner's model call: social and commerce actions only on an owner-mode site, and no
bulk goals anywhere. The planner's own refusal stays as a second layer.
"""

import json
import re
import unicodedata
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlsplit

from app.agent.safety import SIGNED_IN

OWNER, VISITOR = "owner", "visitor"

BLOCKLIST: dict[str, list[str]] = {k: v for k, v in json.loads((Path(__file__).parent / "blocklist.json").read_text(encoding="utf-8")).items()
                                   if not k.startswith("_")}


class Refused(Exception):
    """A run the policy will not start. `code` is the stop-reason code from the plan's section 11."""

    def __init__(self, code: str, status: int, message: str):
        super().__init__(message)
        self.code, self.status, self.message = code, status, message


def host(url: str) -> str:
    try:
        name = urlsplit(url).hostname or ""
    except ValueError:
        return ""
    return name.rstrip(".").lower()


def category(url: str) -> str | None:
    """The blocked category of this URL's host (the host itself or any parent domain listed), or None."""
    name = host(url)
    for cat, domains in BLOCKLIST.items():
        if any(name == d or name.endswith("." + d) for d in domains):
            return cat
    return None


def mode(verified: bool) -> str:
    return OWNER if verified else VISITOR


# ---------- goal rules ----------

_INVISIBLE = re.compile(r"[\u00ad\u200b-\u200f\u2060-\u2064\ufeff]")
# An imperative starts a clause: the start of the goal, after punctuation, or after "and", "then", "to" and the like
# ("where to buy" asks where something is, so it is not an imperative).
_CLAUSE = r"(?:^|[.,;:!?()\"']\s*|\b(?:and|then|please|also|now|just|try|go|(?<!where\s)(?<!how\s)(?<!what\s)to)\s+)"
# A verb followed by one of these is a noun ("Share button", "Checkout page", "Order history"), so it is not an action.
_NOUN = r"(?!\s+(?:buttons?|links?|pages?|flows?|forms?|sections?|options?|history|dialogs?|modals?|menus?|icons?|counts?|counters?|steps?|screens?|tabs?)\b)"
_END = r"(?![-'\w])"
_WHO = r"(?:users?|accounts?|people|profiles?|channels?|creators?|authors?|pages?|brands?|artists?|friends?|them|him|her|@\w+)"
_ACTIONS = "|".join([
    # social
    r"like|unlike|upvote|downvote|retweet|repost|reblog|unfollow|tweet|dm|subscribe|unsubscribe|endorse",
    rf"follow(?:\s+(?:the|this|that|these|those|a|an|some|all|every|\d+|[a-z]+'s))?\s+{_WHO}",
    r"share\s+(?:(?:the|this|that|it|a|an|my|your|them|some|\d+|every|all)\b|on\b|to\b)",
    r"post\s+(?:(?:a|an|the|this|that|it|my|your|some|\d+|something|photos?|comments?|reviews?|messages?|tweets?|stor(?:y|ies)|updates?|jobs?|ads?)\b|on\b|to\b)",
    r"comment\s+(?:on|under|below)\b|(?:leave|write|post|add|drop)\s+(?:a\s+|an\s+|\d+\s+)?comments?",
    r"reply\s+(?:to|under)\b",
    r"message\s+(?:the|this|that|a|an|them|him|her|someone|people|users?|sellers?|@\w+)\b",
    r"vote(?:\s+(?:for|on|up|down|in))?|react\s+(?:to|with)\b",
    r"connect\s+with\s+(?:\d+\s+)?(?:people|users?|them|him|her|someone|recruiters?)\b|add\s+(?:as\s+)?(?:a\s+)?friends?",
    r"(?:write|leave|post|submit|give)\s+(?:a\s+|an\s+|\d+\s+)?(?:[a-z-]+\s+)?(?:reviews?|ratings?)",
    # commerce and money
    r"buy|purchase|checkout|trade|invest|donate|bid|sell|transfer|deposit|withdraw|pay(?!\s+attention)",
    r"order\s+(?:a|an|the|some|this|that|it|them|one|two|three|\d+)\b",
    r"place\s+(?:a\s+|an\s+|the\s+|my\s+|\d+\s+)?(?:orders?|bets?|trades?|bids?)",
    r"send\s+(?:a\s+|an\s+|the\s+|my\s+|some\s+|\d+\s+)?(?:messages?|dms?|emails?|invites?|invitations?|friend\s+requests?|connection\s+requests?|money|payments?|tips?|gifts?|texts?|sms)\b",
])
# Social and commerce actions: allowed only on a site the user verified.
OWNER_ONLY = re.compile(rf"{_CLAUSE}(?:{_ACTIONS}){_END}{_NOUN}", re.IGNORECASE)
# Adding to a cart or list is an action wherever it appears in the goal.
_BASKET = re.compile(r"\badd\s+(?:[\w'-]+\s+){0,6}?to\s+(?:the\s+|my\s+|your\s+|a\s+)?(?:cart|basket|bag|wish\s?list|watch\s?list|portfolio)\b" + _NOUN, re.IGNORECASE)

_MANY = r"(?:\d{2,}|dozens?|hundreds?|thousands?|many|multiple|several|lots\s+of|a\s+lot\s+of|a\s+bunch\s+of|mass|bulk)"
_THINGS = r"(?:accounts?|users?|profiles?|sign-?ups?|registrations?|posts?|comments?|likes?|follows?|followers?|reviews?|messages?|dms?|emails?|invites?|orders?|votes?|requests?|tickets?|tweets?)"
_EVERY_THINGS = r"(?:posts?|comments?|photos?|videos?|users?|accounts?|messages?|reviews?|followers?|people|friends|members|contacts|connections|tweets?|reels?|stor(?:y|ies))"
_BULK = [
    re.compile(rf"\b{_MANY}\s+(?:[\w'-]+\s+){{0,2}}?{_THINGS}\b", re.IGNORECASE),
    re.compile(r"\b(?:create|make|register|sign\s*up|open)\s+(?:\d+|two|three|four|five|six|seven|eight|nine|ten|several|multiple|many|some)\s+(?:[\w-]+\s+)?accounts?\b", re.IGNORECASE),
    re.compile(r"\b(?:like|follow|unfollow|comment\s+on|reply\s+to|message|dm|invite|vote\s+on|review|report|block|share|repost|retweet|delete)\s+"
               rf"(?:every|all|each)(?:\s+(?:the|of\s+the|single|of\s+my|of\s+their|their|my))?\s+(?:[a-z-]+\s+)?{_EVERY_THINGS}\b", re.IGNORECASE),
]

BULK_MESSAGE = "Walkthru tests one journey at a time, like one person would. Bulk goals (many accounts, every post, dozens of messages) are not allowed."


def _normal(goal: str) -> str:
    """Fold look-alike characters and drop invisible ones, so "l\u200bike" or full-width letters read as plain words."""
    text = _INVISIBLE.sub("", unicodedata.normalize("NFKC", goal))
    return " ".join(text.split())


def owner_only(goal: str) -> bool:
    text = _normal(goal)
    return bool(OWNER_ONLY.search(text) or _BASKET.search(text))


def bulk(goal: str) -> bool:
    text = _normal(goal)
    return any(p.search(text) for p in _BULK)


# ---------- the check at run start ----------


def signed_in(observation: dict) -> bool:
    """The page shows someone's account: a sign-out or switch-account control is on screen."""
    return any(SIGNED_IN.search(e.get("text") or "") for e in observation.get("elements") or [])


SIGNED_IN_MESSAGE = "This page shows you are signed in. Verify your domain to test signed-in pages, or open the site signed out."


def check(site: str, goal: str, *, start_url: str, logged_in: bool, verified: Callable[[], bool], signed_in_page: bool = False) -> None:
    """Raise Refused when this run may not start. `verified` (the user verified `site`) is called only when the answer
    depends on it, so the domain check keeps running in the background for ordinary runs. `start_url` is the page the
    tested tab is on, which a modified extension could set apart from `site`."""
    if bulk(goal):
        raise Refused("goal_refused", 422, BULK_MESSAGE)
    name = host(site)
    for url in dict.fromkeys((site, start_url)):
        cat = category(url)
        if cat and not (host(url) == name and verified()):
            raise Refused("blocked_site", 403, f"Walkthru does not run on {cat} sites such as {host(url)}, to protect your accounts and theirs. "
                                               "Test your own site instead. If you own this domain, verify it in Settings first.")
    if owner_only(goal) and not verified():
        raise Refused("goal_refused", 422, "Liking, following, posting, messaging, buying and similar actions run only on a site you verified. "
                                           f"Verify {name} in Settings, or change the goal to what a visitor would check.")
    if logged_in and not verified():
        raise Refused("visitor_mode_limit", 403, f"Testing signed-in pages needs a domain you verified. Verify {name} in Settings, then start again.")
    if signed_in_page and not verified():
        raise Refused("signed_in_unverified", 403, SIGNED_IN_MESSAGE)


def left_for(url: str, site: str, verified: bool) -> str | None:
    """Mid-run: the category when the tested tab has reached a blocked host the user has not verified, else None.
    A verified owner may stay on their own host even when it is listed."""
    cat = category(url)
    if cat is None or (verified and host(url) == host(site)):
        return None
    return cat
