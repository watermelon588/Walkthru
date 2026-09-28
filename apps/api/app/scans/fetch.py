"""HTTP fetching for server-side scans. Public hosts only (SSRF guard), bounded size, short timeouts."""

import ipaddress
import os
import socket
import threading
import time
from urllib.parse import urljoin, urlsplit

import httpcore
import httpx
from selectolax.parser import HTMLParser

# Identifiable, with the page that explains the bot and how to opt out (apps/web/src/pages/Bot.tsx).
UA = f"Mozilla/5.0 (compatible; WalkthruBot/0.1; +{os.environ.get('WEB_URL', 'https://walkthru.dev').rstrip('/')}/bot)"
ACCEPT = "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8"
MAX_TEXT = 300_000
MAX_REDIRECTS = 5


# Cloud metadata endpoints (AWS, ECS, AWS IPv6, Alibaba). None is a public address anyway; listed so that stays true.
METADATA = {ipaddress.ip_address(a) for a in ("169.254.169.254", "169.254.170.2", "fd00:ec2::254", "100.100.100.200")}
NAT64 = ipaddress.ip_network("64:ff9b::/96")


def is_public_ip(address: str) -> bool:
    """True only for a globally routable unicast address. IPv6 forms that carry an IPv4 address inside (mapped,
    6to4, Teredo, NAT64) must carry a public one, or ::ffff:127.0.0.1 would reach this machine."""
    ip = ipaddress.ip_address(address.split("%", 1)[0])  # drop an IPv6 zone id such as fe80::1%eth0
    if ip in METADATA or ip.is_multicast:
        return False
    if ip.version == 6:
        inner = ip.ipv4_mapped or ip.sixtofour or (ip.teredo[1] if ip.teredo else None)
        if ip in NAT64:
            inner = ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF)
        if inner is not None and not is_public_ip(str(inner)):
            return False
    return ip.is_global


def public_addresses(host: str, port: int) -> list[str]:
    """Resolve once. Every address must be public, and the caller connects only to these (DNS rebinding, SD-4.5).
    ALLOW_LOCAL_SCANS=1 (fixtures) returns the name unresolved."""
    if os.environ.get("ALLOW_LOCAL_SCANS") == "1":
        return [host]
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError) as e:
        raise ValueError("site does not resolve") from e
    addresses = list(dict.fromkeys(info[4][0] for info in infos))
    if not addresses or not all(is_public_ip(a) for a in addresses):
        raise ValueError("site resolves to a private address")
    return addresses


def assert_public(url: str) -> None:
    """Refuse hosts that resolve to private, loopback or link-local addresses: the early, friendly check. The pinned
    connection below is what enforces it. ALLOW_LOCAL_SCANS=1 for fixtures."""
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("site must use http or https")
    public_addresses(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))


class _PublicOnly(httpcore.SyncBackend):
    """Opens every connection of a scan client: resolves the host once, refuses any non-public address, and connects to
    the checked address itself, so a second DNS answer (rebinding) can never be used. TLS SNI and the Host header still
    carry the name, because httpcore takes them from the request, not from this socket."""

    def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        try:
            addresses = public_addresses(host, port)
        except ValueError as e:
            raise httpcore.ConnectError(str(e)) from e
        error: Exception | None = None
        for address in addresses:  # like socket.create_connection: an unreachable IPv6 answer falls back to IPv4
            try:
                return super().connect_tcp(address, port, timeout, local_address, socket_options)
            except (httpcore.ConnectError, httpcore.ConnectTimeout) as e:
                error = e
        raise error or httpcore.ConnectError("no address to connect to")


PER_HOST = 2  # simultaneous requests to one host from this process, whoever asked (SD-2.3)
_slots: dict[str, threading.BoundedSemaphore] = {}
_slots_lock = threading.Lock()


def _slot(host: str) -> threading.BoundedSemaphore:
    with _slots_lock:  # ponytail: one small semaphore per host ever seen; a few thousand hosts is a few hundred kB
        return _slots.setdefault(host, threading.BoundedSemaphore(PER_HOST))


class _Release(httpx.SyncByteStream):
    """The response body, giving the host's slot back when it is closed (after a normal read, or a streamed one)."""

    def __init__(self, inner, slot: threading.BoundedSemaphore):
        self._inner, self._slot, self._held = inner, slot, True

    def __iter__(self):
        yield from self._inner

    def close(self) -> None:
        try:
            self._inner.close()
        finally:
            if self._held:
                self._held = False
                self._slot.release()


class _Polite(httpx.HTTPTransport):
    """At most PER_HOST requests in flight to one host, so many users scanning one site at once never hammer it."""

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        slot = _slot(request.url.host.lower())
        wait = (request.extensions.get("timeout") or {}).get("pool") or 15
        if not slot.acquire(timeout=wait):
            raise httpx.PoolTimeout("too many requests to this site at once; try again shortly", request=request)
        try:
            response = super().handle_request(request)
        except BaseException:
            slot.release()
            raise
        response.stream = _Release(response.stream, slot)
        return response


def client(timeout: float = 15) -> httpx.Client:
    """The client for every request to a user's site. trust_env=False: an environment proxy would resolve the name again."""
    transport = _Polite()
    # ponytail: httpx has no public hook for the network backend; tests/test_fetch_pinning.py fails if this attribute moves.
    transport._pool._network_backend = _PublicOnly()
    # Ask for HTML like a browser: some hosts (Vercel "markdown for agents") serve Markdown to clients that do not.
    return httpx.Client(transport=transport, trust_env=False, follow_redirects=False, timeout=timeout, headers={"User-Agent": UA, "Accept": ACCEPT})


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
