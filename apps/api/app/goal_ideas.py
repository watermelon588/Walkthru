"""Goal suggestions for a site, from the links and buttons its own pages serve. Plain code: no model, no browser.

The same rules as the extension's side panel (apps/extension/lib/goals.ts), which reads the open tab. Here the
served HTML is read first with the scanners' client (public addresses only, polite, GET only), following a chooser
home page one level. Sites that draw their navigation with JavaScript are then read in a short-lived headless
browser, like a live run's first look at the page.
"""

import logging
import os
import re
import threading
import time
from urllib.parse import urljoin

from selectolax.parser import HTMLParser

from app import db
from app.runner import cdp, guard
from app.scans import fetch

log = logging.getLogger("walkthru.goal_ideas")

RULES: list[tuple[re.Pattern, str]] = [(re.compile(pattern, re.IGNORECASE), goal) for pattern, goal in [
    (r"\b(sign ?up|get started|start (for )?free|create (an )?account|register|join now)\b", "Sign up for an account"),
    (r"\b(log ?in|sign ?in)\b", "Log in and reach the dashboard"),
    (r"\b(pricing|plans)\b", "Find the pricing and pick the right plan"),
    (r"\b(book (a )?(demo|call)|request (a )?demo)\b", "Book a demo"),
    (r"\b(add to (cart|bag)|buy now|shop now|checkout)\b", "Add a product to the cart and reach checkout"),
    (r"\b(contact|get in touch|talk to us)\b", "Find a way to get in touch"),
    (r"\b(work|projects?|case stud(y|ies)|portfolio)\b", "Open a project and read about it"),
    (r"\b(docs|documentation|guides?)\b", "Find the getting-started documentation"),
    (r"\b(about|team|who we are)\b", "Work out who is behind this site and what they do"),
    (r"\b(blog|articles?|news)\b", "Find a recent article and open it"),
]]
MAX_IDEAS, MAX_EXTRA_PAGES = 4, 2


def labels(html: str, base: str) -> tuple[list[str], list[str]]:
    """(text of every link and button, same-site link addresses in page order)."""
    tree = HTMLParser(html)
    texts, links = [], []
    for node in tree.css("a, button, [role=button]"):
        text = " ".join((node.text(deep=True) or node.attributes.get("aria-label") or "").split())[:80]
        if text:
            texts.append(text)
        href = node.attributes.get("href") if node.tag == "a" else None
        if href and not href.startswith(("#", "mailto:", "tel:", "javascript:")):
            target = urljoin(base, href).split("#", 1)[0]
            if fetch.origin(target) == fetch.origin(base) and target.rstrip("/") != base.rstrip("/") and target not in links:
                links.append(target)
    return texts, links


def match(texts: list[str]) -> list[str]:
    return [goal for pattern, goal in RULES if any(pattern.search(text) for text in texts)][:MAX_IDEAS]


_lock = threading.Lock()
_recent: dict[str, tuple[float, list[str]]] = {}  # site -> (when, ideas), this process only
KEEP_S = 600


def rendered(site: str) -> list[str]:
    """Read the page the way a visitor's browser shows it. Most sites built with a JavaScript framework serve no
    links in their HTML, so this is the only way to see their navigation. One short-lived browser, same network
    rules as a live run, never while a live run's browser is open on this machine's queue.
    ponytail: a run claimed during these few seconds overlaps one extra browser; move this into the runner if memory is tight."""
    if not cdp.chrome_path() or not os.path.exists(cdp.INJECT) or db.running_cloud_runs() > 0 or not _lock.acquire(blocking=False):
        return []
    try:
        with cdp.browser() as tab:
            rules = guard.install(tab)
            tab.send("Page.navigate", url=site)
            tab.wait_loaded(10)
            if rules.blocked:
                return []
            obs = cdp.read(tab, 6)
            return match([e.get("text", "") for e in obs.get("elements", []) if e.get("tag") in ("a", "button")])
    except Exception:
        log.warning("could not read %s for goal ideas", fetch.origin(site), exc_info=True)
        return []
    finally:
        _lock.release()


def suggest(site: str) -> list[str]:
    """Up to four goals this site's own navigation supports, or [] when its pages could not be read."""
    key = site.rstrip("/")
    saved = _recent.get(key)
    if saved and time.monotonic() - saved[0] < KEEP_S:
        return saved[1]
    ideas = served(site)
    if len(ideas) < 2:
        ideas = rendered(site) or ideas
    if ideas:
        _recent[key] = (time.monotonic(), ideas)
    return ideas


def served(site: str) -> list[str]:
    """From the HTML the site serves, without running it."""
    with fetch.client(timeout=8) as c:
        home = fetch.get(c, site)
        if home is None or home.status_code >= 400 or "html" not in home.headers.get("content-type", ""):
            return []
        base = str(home.url)
        texts, links = labels(home.text[:fetch.MAX_TEXT], base)
        if len(match(texts)) < 2:  # a shell or a chooser page: read where it points
            for link in links[:MAX_EXTRA_PAGES]:
                page = fetch.get(c, link, same_origin=fetch.origin(base))
                if page is not None and page.status_code < 400 and "html" in page.headers.get("content-type", ""):
                    texts += labels(page.text[:fetch.MAX_TEXT], str(page.url))[0]
    return match(texts)
