"""Safety rules enforced in code, not prompts. See ARCHITECTURE.md."""

import re

DANGER = re.compile(
    r"\b(delete|remove|cancel\s+subscription|pay|purchase|buy|checkout|send|invite|transfer|unsubscribe)\b",
    re.IGNORECASE,
)
MAX_STEPS = 25
LOOP_LIMIT = 3  # identical action on identical URL this many times = stuck


def is_dangerous(text: str) -> bool:
    return bool(DANGER.search(text or ""))


def same_origin(a: str, b: str) -> bool:
    from urllib.parse import urlsplit

    pa, pb = urlsplit(a), urlsplit(b)
    return (pa.scheme, pa.netloc) == (pb.scheme, pb.netloc)


if __name__ == "__main__":
    assert is_dangerous("Delete account") and is_dangerous("Cancel subscription")
    assert not is_dangerous("Sign up") and not is_dangerous("Payment history")
    assert same_origin("https://a.com/x", "https://a.com/y") and not same_origin("https://a.com", "https://b.com")
    print("ok")
