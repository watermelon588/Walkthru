"""Safety rules enforced in code, not prompts. See ARCHITECTURE.md."""

import re

# Never done for real, anywhere: money moves or data disappears.
DESTRUCTIVE = re.compile(r"\b(delete|remove|cancel\s+subscription|pay|purchase|buy|checkout|transfer|unsubscribe)\b", re.IGNORECASE)
# Reaches a real person. Allowed only on a domain the owner verified, after they confirm in the side panel.
SENDING = re.compile(r"\b(send|invite)\b", re.IGNORECASE)
# Visitor mode (a site the user has not verified): social and commerce controls are never pressed. A label counts when a
# verb starts it or one of its parts ("123 Likes. Like"), so "Products you might like" or a "Posts" tab stays clickable.
# Mirrored in apps/extension/lib/safety.ts; keep both lists identical.
SOCIAL_VERBS = (r"like|unlike|love|upvote|downvote|follow|unfollow|comment|reply|post|publish|tweet|retweet|repost|reblog|share|"
                r"subscribe|vote|react|message|send\s+(?:a\s+)?(?:message|request|friend\s+request|connection\s+request)|connect|add\s+friend|endorse")
COMMERCE_VERBS = (r"add\s+to\s+(?:cart|bag|basket|wish\s?list|watch\s?list|portfolio)|buy(?:\s+now)?|check\s?out|place\s+(?:an\s+)?order|"
                  r"order\s+now|pre-?order|trade|invest|bid|donate")
_START = r"(?:^|[.|·:;]\s*)\W*(?:\d[\d.,]*\s*[kKmM]?\s+)?"
SOCIAL = re.compile(rf"{_START}(?:{SOCIAL_VERBS})\b(?!-)", re.IGNORECASE)
COMMERCE = re.compile(rf"{_START}(?:{COMMERCE_VERBS})\b(?!-)", re.IGNORECASE)
SEARCH = re.compile(r"\bsearch\b", re.IGNORECASE)
# A control only a signed-in person sees. Used to stop visitor-mode runs on a page that shows the user's own account.
SIGNED_IN = re.compile(r"^\W*(?:sign\s*out|log\s*out|logout|switch\s+accounts?|your\s+profile|my\s+profile|view\s+profile|"
                       r"(?:open\s+)?(?:user|account|profile)\s+(?:navigation\s+)?menu)\b", re.IGNORECASE)
MAX_STEPS = 30  # hard ceiling; each plan sets its own (app/plans.py)
LOOP_LIMIT = 3  # identical action on identical URL this many times = stuck


def is_destructive(text: str) -> bool:
    return bool(DESTRUCTIVE.search(text or ""))


def is_sending(text: str) -> bool:
    return bool(SENDING.search(text or ""))


def is_dangerous(text: str) -> bool:
    return is_destructive(text) or is_sending(text)


def is_social(label: str) -> bool:
    return bool(SOCIAL.search(label or ""))


def is_commerce(label: str) -> bool:
    return bool(COMMERCE.search(label or ""))


BASKET = re.compile(r"\badd\s+to\s+(?:cart|bag|basket|wish\s?list|watch\s?list|portfolio)\b", re.IGNORECASE)


def is_basket(label: str) -> bool:
    return bool(BASKET.search(label or ""))


def is_search_field(element: dict) -> bool:
    """The one field a visitor-mode run may type into: a site search box."""
    return element.get("type") == "search" or bool(SEARCH.search(element.get("text") or ""))


def shows_signed_in(elements: list[dict]) -> bool:
    return any(SIGNED_IN.search(e.get("text") or "") for e in elements)


def same_origin(a: str, b: str) -> bool:
    from urllib.parse import urlsplit

    pa, pb = urlsplit(a), urlsplit(b)
    return (pa.scheme, pa.netloc) == (pb.scheme, pb.netloc)


if __name__ == "__main__":
    assert is_dangerous("Delete account") and is_dangerous("Cancel subscription")
    assert not is_dangerous("Sign up") and not is_dangerous("Payment history")
    assert is_sending("Submit contact form and send email") and not is_destructive("Send message")
    assert is_social("Like") and is_social("123 Likes. Like") and is_social("Follow") and is_social("Share")
    assert not is_social("Products you might like") and not is_social("Posts") and not is_social("Likes") and not is_social("Liked by 3")
    assert is_commerce("Add to cart") and is_commerce("Buy now") and not is_commerce("Buying guide") and not is_commerce("Pricing")
    assert is_search_field({"type": "search"}) and is_search_field({"type": "text", "text": "Search products"}) and not is_search_field({"type": "email", "text": "Email"})
    assert shows_signed_in([{"text": "Sign out"}]) and not shows_signed_in([{"text": "Sign in"}, {"text": "My account"}])
    assert same_origin("https://a.com/x", "https://a.com/y") and not same_origin("https://a.com", "https://b.com")
    print("ok")
