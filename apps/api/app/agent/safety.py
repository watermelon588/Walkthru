"""Safety rules enforced in code, not prompts. See ARCHITECTURE.md."""

import re

# Never done for real, anywhere: money moves or data disappears.
DESTRUCTIVE = re.compile(r"\b(delete|remove|cancel\s+subscription|pay|purchase|buy|checkout|transfer|unsubscribe)\b", re.IGNORECASE)
# Reaches a real person. Allowed only on a domain the owner verified, after they confirm in the side panel.
SENDING = re.compile(r"\b(send|invite)\b", re.IGNORECASE)
MAX_STEPS = 30  # hard ceiling; each plan sets its own (app/plans.py)
LOOP_LIMIT = 3  # identical action on identical URL this many times = stuck


def is_destructive(text: str) -> bool:
    return bool(DESTRUCTIVE.search(text or ""))


def is_sending(text: str) -> bool:
    return bool(SENDING.search(text or ""))


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
    print("ok")
