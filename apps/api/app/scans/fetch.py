"""HTTP fetching for server-side scans. Public hosts only (SSRF guard), bounded size, short timeouts."""

import ipaddress
import os
import socket
from urllib.parse import urlsplit

import httpx
from selectolax.parser import HTMLParser

UA = "Mozilla/5.0 (compatible; WalkthruBot/0.1; +https://walkthru.dev/bot)"
MAX_TEXT = 300_000


def assert_public(url: str) -> None:
    """Refuse hosts that resolve to private, loopback or link-local addresses. ALLOW_LOCAL_SCANS=1 for fixtures."""
    if os.environ.get("ALLOW_LOCAL_SCANS") == "1":
        return
    host = urlsplit(url).hostname or ""
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        raise ValueError("site does not resolve") from e
    for info in infos:
        if not ipaddress.ip_address(info[4][0]).is_global:
            raise ValueError("site resolves to a private address")


def client() -> httpx.Client:
    return httpx.Client(follow_redirects=True, max_redirects=5, timeout=15, headers={"User-Agent": UA})


def get(c: httpx.Client, url: str) -> httpx.Response | None:
    try:
        return c.get(url)
    except httpx.HTTPError:
        return None


def page_text(html: str, limit: int = 6000) -> str:
    """Visible text, whitespace-collapsed, the same shape the extension sends."""
    tree = HTMLParser(html)
    for tag in tree.css("script, style, noscript, svg"):
        tag.decompose()
    body = tree.body
    text = body.text(separator=" ") if body is not None else ""
    return " ".join(text.split())[:limit]


def origin(url: str) -> str:
    p = urlsplit(url)
    return f"{p.scheme}://{p.netloc}"
