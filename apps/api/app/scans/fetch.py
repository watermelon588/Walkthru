"""HTTP fetching for server-side scans. Public hosts only (SSRF guard), bounded size, short timeouts."""

import ipaddress
import os
import socket
from urllib.parse import urljoin, urlsplit

import httpx
from selectolax.parser import HTMLParser

UA = "Mozilla/5.0 (compatible; WalkthruBot/0.1; +https://walkthru.dev/bot)"
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


def client() -> httpx.Client:
    # Ask for HTML like a browser: some hosts (Vercel "markdown for agents") serve Markdown to clients that do not.
    return httpx.Client(follow_redirects=False, timeout=15, headers={"User-Agent": UA, "Accept": ACCEPT})


def get(c: httpx.Client, url: str, *, same_origin: str | None = None) -> httpx.Response | None:
    """Fetch with every redirect revalidated before the next network request."""
    current = url
    try:
        for _ in range(MAX_REDIRECTS + 1):
            assert_public(current)
            if same_origin is not None and origin(current) != same_origin:
                return None
            response = c.get(current)
            if not response.is_redirect:
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


def origin(url: str) -> str:
    p = urlsplit(url)
    return f"{p.scheme}://{p.netloc}"
