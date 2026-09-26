"""HTTP fetching for server-side scans. Public hosts only (SSRF guard), bounded size, short timeouts."""

import ipaddress
import os
import socket
import time
from urllib.parse import urljoin, urlsplit

import httpx
from selectolax.parser import HTMLParser

# Identifiable, with the page that explains the bot and how to opt out (apps/web/src/pages/Bot.tsx).
UA = f"Mozilla/5.0 (compatible; WalkthruBot/0.1; +{os.environ.get('WEB_URL', 'https://walkthru.dev').rstrip('/')}/bot)"
ACCEPT = "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8"
MAX_TEXT = 300_000
MAX_REDIRECTS = 5


def assert_public(url: str) -> None:
    """Refuse hosts that resolve to private, loopback or link-local addresses. ALLOW_LOCAL_SCANS=1 for fixtures."""
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("site must use http or https")
    if os.environ.get("ALLOW_LOCAL_SCANS") == "1":
        return
    host = parsed.hostname
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        raise ValueError("site does not resolve") from e
    for info in infos:
        if not ipaddress.ip_address(info[4][0]).is_global:
            raise ValueError("site resolves to a private address")


def client(timeout: float = 15) -> httpx.Client:
    # Ask for HTML like a browser: some hosts (Vercel "markdown for agents") serve Markdown to clients that do not.
    return httpx.Client(follow_redirects=False, timeout=timeout, headers={"User-Agent": UA, "Accept": ACCEPT})


def get(c: httpx.Client, url: str, *, same_origin: str | None = None, headers: dict | None = None,
        timeout: float | None = None) -> httpx.Response | None:
    """Fetch with every redirect revalidated before the next network request."""
    current = url
    try:
        for hops in range(MAX_REDIRECTS + 1):
            assert_public(current)
            if same_origin is not None and origin(current) != same_origin:
                return None
            started = time.monotonic()
            response = c.get(current, headers=headers, **({"timeout": timeout} if timeout is not None else {}))
            if not response.is_redirect:
                response.extensions["walkthru_hops"] = hops  # redirect chains are an SEO finding (site.py)
                response.extensions["walkthru_seconds"] = time.monotonic() - started  # the final page only (slow-response check)
                return response
            location = response.headers.get("location")
            if not location:
                return response
            current = urljoin(str(response.url), location)
    except (httpx.HTTPError, ValueError):
        return None
    return None


def page_text(html: str, limit: int = 6000) -> str:
    """Visible text, whitespace-collapsed, the same shape the extension sends."""
    tree = HTMLParser(html)
    for tag in tree.css("script, style, noscript, svg"):
        tag.decompose()
    body = tree.body
    text = body.text(separator=" ") if body is not None else ""
    return " ".join(text.split())[:limit]


MIN_TEXT = 20  # JS-only shells serve ~0 visible characters (noscript is stripped); real pages serve more


def is_js_shell(html: str) -> bool:
    """True for single-page apps whose served HTML is an empty shell filled in by JavaScript."""
    tree = HTMLParser(html)
    return len(page_text(html)) < MIN_TEXT and tree.css_first("script[src]") is not None


def is_local_site(url: str) -> bool:
    """Local development servers: production transport, headers and speed cannot be judged there."""
    host = (urlsplit(url).hostname or "").lower()
    if host == "localhost" or host.endswith(".localhost"):
        return True
    try:
        return not ipaddress.ip_address(host).is_global
    except ValueError:
        return False


def same_site(a: str, b: str) -> bool:
    """Same host, ignoring a leading www. and the scheme. Verification covers the host the owner proved, so a
    redirect to another host must not carry the owner-only checks with it."""
    first, second = ((urlsplit(u).hostname or "").lower().removeprefix("www.") for u in (a, b))
    return bool(first) and first == second


def origin(url: str) -> str:
    p = urlsplit(url)
    return f"{p.scheme}://{p.netloc}"
