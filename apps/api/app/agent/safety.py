"""Safety rules enforced in code, not prompts. See ARCHITECTURE.md."""

import re

# Never done for real, anywhere: money moves or data disappears.
DESTRUCTIVE = re.compile(r"\b(delete|remove|cancel\s+subscription|pay|purchase|buy|checkout|transfer|unsubscribe)\b", re.IGNORECASE)
# Reaches a real person. Allowed only on a domain the owner verified, after they confirm in the side panel.
SENDING = re.compile(r"\b(send|invite)\b", re.IGNORECASE)
# Visitor mode (a domain the user has not verified, app/agent/policy.py): these controls write something on the
# site or on the user's account there, so the test user stops at them. Buttons only: plain links just navigate.
SOCIAL = re.compile(r"\b(like|unlike|follow|unfollow|comment|reply|post|share|repost|retweet|reblog|subscribe|vote|upvote|downvote|react|"
                    r"message|connect|add\s+friend|send\s+request|join)\b", re.IGNORECASE)
COMMERCE = re.compile(r"\b(add\s+to\s+(cart|bag|basket)|buy|purchase|checkout|check\s+out|place\s+(your\s+)?order|order\s+now|pre-?order|"
                      r"trade|invest|bid|donate|pay|book\s+now|reserve)\b", re.IGNORECASE)
# Signing in with another account (Google, GitHub, Apple): stopped in Visitor mode on links too.
THIRD_PARTY_LOGIN = re.compile(r"\b(continue|sign\s?in|sign\s?up|log\s?in|register)\s+(with|using|via)\b", re.IGNORECASE)
# The only fields a visitor types into.
SEARCH = re.compile(r"\bsearch\b", re.IGNORECASE)
# A sign-out control means the page is showing someone's account.
SIGNED_IN = re.compile(r"\b(log\s?out|sign\s?out|switch\s+accounts?)\b", re.IGNORECASE)
MAX_STEPS = 30  # hard ceiling; each plan sets its own (app/plans.py)
LOOP_LIMIT = 3  # identical action on identical URL this many times = stuck


def is_destructive(text: str) -> bool:
    return bool(DESTRUCTIVE.search(text or ""))


def is_sending(text: str) -> bool:
    return bool(SENDING.search(text or ""))


def visitor_blocked(text: str, *, link: bool) -> bool:
    """A click Visitor mode does not make: social and commerce buttons, and signing in with another account anywhere."""
    text = text or ""
    return bool(THIRD_PARTY_LOGIN.search(text)) or (not link and bool(SOCIAL.search(text) or COMMERCE.search(text)))


def search_field(tag: str, input_type: str | None, label: str) -> bool:
    return tag == "input" and (input_type == "search" or (input_type in (None, "", "text") and bool(SEARCH.search(label or ""))))


def is_dangerous(text: str) -> bool:
    return is_destructive(text) or is_sending(text)


def same_origin(a: str, b: str) -> bool:
    from urllib.parse import urlsplit

    pa, pb = urlsplit(a), urlsplit(b)
    return (pa.scheme, pa.netloc) == (pb.scheme, pb.netloc)


if __name__ == "__main__":
    assert is_dangerous("Delete account") and is_dangerous("Cancel subscription")
    assert not is_dangerous("Sign up") and not is_dangerous("Payment history")
    assert is_sending("Submit contact form and send email") and not is_destructive("Send message")
    assert same_origin("https://a.com/x", "https://a.com/y") and not same_origin("https://a.com", "https://b.com")
    assert visitor_blocked("Like", link=False) and not visitor_blocked("Like", link=True) and visitor_blocked("Continue with Google", link=True)
    assert search_field("input", "search", "") and search_field("input", "text", "Search docs") and not search_field("input", "email", "Email")
    print("ok")
