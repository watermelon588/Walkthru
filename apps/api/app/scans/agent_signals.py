"""What an AI agent needs to use a page (P1.7), read from the homepage HTML the GEO scan already fetched. Plain parsing:
forms and whether every field has a name an agent can read, WebMCP-style declared tools, a WebSite SearchAction in
JSON-LD, and a CAPTCHA widget on the page."""

import json

from selectolax.parser import HTMLParser

CAPTCHA_MARKERS = ("recaptcha", "hcaptcha", "challenges.cloudflare.com/turnstile", "cf-turnstile", "friendlycaptcha", "arkoselabs", "funcaptcha")
FIELDS = "input:not([type=hidden]):not([type=submit]):not([type=button]):not([type=image]):not([type=reset]), select, textarea"


def _named(tree: HTMLParser, field) -> bool:
    """A field an agent can identify: a <label for>, a wrapping <label>, aria-label, aria-labelledby or a title."""
    attrs = field.attributes
    if any((attrs.get(a) or "").strip() for a in ("aria-label", "aria-labelledby", "title")):
        return True
    fid = (attrs.get("id") or "").strip()
    if fid and any((label.attributes.get("for") or "") == fid and label.text(strip=True) for label in tree.css("label")):
        return True
    parent = field.parent
    while parent is not None and parent.tag not in ("form", "body"):
        if parent.tag == "label" and parent.text(strip=True):
            return True
        parent = parent.parent
    return False


def _search_action(tree: HTMLParser) -> bool:
    for node in tree.css('script[type="application/ld+json"]'):
        try:
            data = json.loads(node.text() or "null")
        except ValueError:
            continue
        stack = [data]
        while stack:
            item = stack.pop()
            if isinstance(item, list):
                stack.extend(item)
            elif isinstance(item, dict):
                action = item.get("potentialAction")
                actions = action if isinstance(action, list) else [action]
                if any(isinstance(a, dict) and "SearchAction" in str(a.get("@type")) for a in actions):
                    return True
                stack.extend(v for v in item.values() if isinstance(v, (dict, list)))
    return False


def homepage(html: str) -> dict:
    """{"forms", "fields", "named_fields", "webmcp", "search_action", "captcha"} for one page."""
    tree = HTMLParser(html or "")
    fields = [f for f in tree.css(FIELDS)]
    low = (html or "").lower()
    return {
        "forms": len(tree.css("form")),
        "fields": len(fields),
        "named_fields": sum(_named(tree, f) for f in fields),
        # WebMCP's declarative form (a form that declares itself a tool) or the imperative navigator.modelContext API.
        "webmcp": bool(tree.css("form[toolname], form[tool-name]")) or "navigator.modelcontext" in low,
        "search_action": _search_action(tree),
        "captcha": any(m in low for m in CAPTCHA_MARKERS),
    }
