"""Bounded, same-origin launch audit with root-cause aggregation."""

from __future__ import annotations

import re
import time
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from urllib.parse import urldefrag, urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx
from selectolax.parser import HTMLParser

from app.agent.schema import Finding
from app.scans import fetch, geo, security, seo

USER_AGENT = "WalkthruBot"
DEFAULT_MAX_PAGES = 10
DEFAULT_TIME_LIMIT = 20.0
PAID_MAX_PAGES = 50  # paid run reports; they are written in a background task, so the longer budget waits on no one
PAID_TIME_LIMIT = 60.0
MAX_MAX_PAGES = PAID_MAX_PAGES
MAX_VISITED = 5  # pages the test user visited, audited on top of the crawl
SIGNUP = re.compile(r"\b(sign ?up|get started|start (for )?free|create (an )?account|register|join now)\b", re.IGNORECASE)


@dataclass(frozen=True)
class AuditCoverage:
    pages_scanned: int
    page_limit: int
    duration_ms: int
    truncated: bool
    urls: list[str]


@dataclass(frozen=True)
class SiteAudit:
    seo: list[Finding]
    security: list[Finding]
    coverage: AuditCoverage
    production_like: bool = False  # a local host that deliberately serves production headers (the eval fixtures)
    geo: geo.GeoResult | None = None
    pages: list[tuple[str, str, list[str]]] = field(default_factory=list)  # (kind, title, every affected page)


def _normal_url(raw: str, page_url: str, base: str) -> str | None:
    joined, _ = urldefrag(urljoin(page_url, raw))
    parsed = urlsplit(joined)
    if parsed.scheme not in {"http", "https"} or fetch.origin(joined) != base:
        return None
    # Query variants create effectively unbounded crawl spaces and rarely represent
    # a separate launch-readiness page. Audit the stable path once.
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path or "/", "", ""))


def _links(html: str, page_url: str, base: str) -> list[str]:
    tree = HTMLParser(html)
    links: list[str] = []
    seen: set[str] = set()
    for node in tree.css("a[href]"):
        candidate = _normal_url(node.attributes.get("href") or "", page_url, base)
        if candidate and candidate not in seen:
            seen.add(candidate)
            links.append(candidate)
    return links


def _in_footer(node) -> bool:
    while node is not None:
        if node.tag == "footer" or node.attributes.get("role") == "contentinfo":
            return True
        node = node.parent
    return False


def _signup_hidden(html: str, url: str) -> Finding | None:
    """A homepage whose only sign-up link sits in the footer: visitors look for it in the header or first screen."""
    links = [n for n in HTMLParser(html).css("a, button") if SIGNUP.search(n.text(strip=True) or "")]
    if not links or not all(_in_footer(n) for n in links):
        return None
    label = links[0].text(strip=True)[:60]
    return Finding(kind="ux", severity="medium", title="Sign-up is hidden in the footer",
                   detail=f"The only sign-up link on the homepage is \"{label}\" in the footer. Visitors look for it in the header or the first screen, and many leave before scrolling that far.",
                   fix="Add a clear Sign up button to the header and to the first screen of the homepage.", evidence=f"{url}: footer link \"{label}\"")


def _robots(text: str | None, url: str) -> RobotFileParser:
    parser = RobotFileParser(url)
    parser.parse((text or "").splitlines())
    return parser


def _aggregate(records: list[tuple[Finding, str | None]], pages_scanned: int, page_map: list | None = None) -> list[Finding]:
    groups: OrderedDict[tuple[str, str, str], list[tuple[Finding, str | None]]] = OrderedDict()
    for finding, page_url in records:
        groups.setdefault((finding.kind, finding.title, finding.fix), []).append((finding, page_url))

    severity_rank = {"low": 0, "medium": 1, "high": 2}
    output: list[Finding] = []
    for items in groups.values():
        first = items[0][0]
        urls = list(dict.fromkeys(page for _, page in items if page))
        if page_map is not None and urls:
            page_map.append((first.kind, first.title, urls))  # the full list; evidence below shows only 3
        severity = max((item.severity for item, _ in items), key=severity_rank.__getitem__)
        if len(urls) <= 1:
            output.append(first.model_copy(update={"severity": severity}))
            continue
        shown = ", ".join(urls[:3])
        more = f" +{len(urls) - 3} more" if len(urls) > 3 else ""
        output.append(
            first.model_copy(
                update={
                    "severity": severity,
                    "detail": f"{first.detail} Found on {len(urls)} of {pages_scanned} audited pages."[:600],
                    "evidence": f"{len(urls)} pages: {shown}{more}"[:300],
                }
            )
        )
    return output


def audit(
    url: str,
    client: httpx.Client,
    *,
    verified: bool,
    geo_full: bool = False,
    visited: list[str] | tuple[str, ...] = (),
    max_pages: int = DEFAULT_MAX_PAGES,
    time_limit: float = DEFAULT_TIME_LIMIT,
) -> SiteAudit:
    """Audit a small same-origin page set. No forms, probes or browser actions."""
    max_pages = max(1, min(max_pages, MAX_MAX_PAGES))
    started = time.monotonic()
    deadline = started + max(0.5, time_limit)

    root = fetch.get(client, url)
    if root is None or root.status_code >= 400:
        failure = Finding(kind="seo", severity="high", title="Homepage did not load", detail="The homepage could not be fetched.", fix="Make sure the homepage returns 200.", evidence=url)
        coverage = AuditCoverage(0, max_pages, round((time.monotonic() - started) * 1000), False, [])
        return SiteAudit([failure], [], coverage)

    root_url = str(root.url)
    shell = fetch.is_js_shell(root.text)
    base = fetch.origin(root_url)
    robots_response = fetch.get(client, f"{base}/robots.txt", same_origin=base)
    robots_text = robots_response.text if robots_response is not None and robots_response.status_code == 200 else None
    robot_rules = _robots(robots_text, f"{base}/robots.txt")
    sitemap_response = fetch.get(client, f"{base}/sitemap.xml", same_origin=base)

    queue = deque([root_url])
    queued = {root_url}
    pages: list[tuple[str, httpx.Response]] = []
    while queue and len(pages) < max_pages and time.monotonic() < deadline:
        page_url = queue.popleft()
        if page_url != root_url and not robot_rules.can_fetch(USER_AGENT, page_url):
            continue
        response = root if page_url == root_url else fetch.get(client, page_url, same_origin=base)
        if response is None or response.status_code >= 400:
            continue
        content_type = response.headers.get("content-type", "")
        if content_type and "html" not in content_type.lower():
            continue
        final_url = str(response.url)
        pages.append((final_url, response))
        for link in _links(response.text, final_url, base):
            if link not in queued and robot_rules.can_fetch(USER_AGENT, link):
                queued.add(link)
                queue.append(link)

    # Pages the owner's test user just visited are audited too (a signup form the crawl never reached). Past a
    # robots.txt block only on a verified domain, where the owner asked for them to be tested.
    audited = {page_url for page_url, _ in pages}
    for page_url in list(dict.fromkeys(urldefrag(u)[0] for u in visited))[:MAX_VISITED]:
        if page_url in audited or fetch.origin(page_url) != base or (not verified and not robot_rules.can_fetch(USER_AGENT, page_url)):
            continue
        response = fetch.get(client, page_url, same_origin=base)
        if response is None or response.status_code >= 400 or "html" not in response.headers.get("content-type", "text/html").lower():
            continue
        pages.append((str(response.url), response))
        audited.add(str(response.url))

    seo_records: list[tuple[Finding, str | None]] = []
    security_records: list[tuple[Finding, str | None]] = []
    for page_url, response in pages:
        seo_records.extend((finding, page_url) for finding in seo.check_html(response.text, page_url))
        security_records.extend((finding, page_url) for finding in security.check_headers(response))
        security_records.extend((finding, page_url) for finding in security.check_content(response.text, page_url))

    hidden = _signup_hidden(root.text, root_url)
    if hidden:  # a UX finding from the served HTML; it travels with the SEO list, the report sorts by kind
        seo_records.append((hidden, root_url))
    seo_records.extend((finding, None) for finding in seo.check_robots(robots_text))
    sitemap_status = sitemap_response.status_code if sitemap_response is not None else None
    seo_records.extend((finding, None) for finding in seo.check_sitemap(sitemap_status, robots_text))
    security_records.extend((finding, root_url) for finding in security.check_transport(url, root, client))
    if verified:
        security_records.extend((finding, None) for finding in security.check_exposed(base, client))
        security_records.extend((finding, None) for finding in security.check_bundles(root.text, root_url, client))

    if shell:
        # Page-level checks read the served HTML. On a JavaScript-built page that is not what visitors or
        # screen readers get, so say exactly what was checked.
        seo_records = [
            (f.model_copy(update={"detail": ("In the HTML sent before JavaScript runs: " + f.detail.replace(" and screen readers", ""))[:600]}), page)
            if page == root_url else (f, page)
            for f, page in seo_records
        ]
        # The shell itself is reported once, by the GEO section ("Homepage content only appears after JavaScript runs").

    if not pages:  # never report a clean audit when nothing was actually checked
        kind = root.headers.get("content-type", "unknown")
        seo_records.append((Finding(kind="seo", severity="medium", title="No HTML pages could be audited", detail=f"The homepage answered with {kind} instead of HTML, so page-level SEO and security checks did not run.", fix="Serve text/html to browsers and crawlers that request it.", evidence=root_url), root_url))

    duration_ms = round((time.monotonic() - started) * 1000)
    truncated = bool(queue) or (time.monotonic() >= deadline and len(pages) < len(queued))
    coverage = AuditCoverage(len(pages), max_pages, duration_ms, truncated, [page_url for page_url, _ in pages])
    production_like = root.headers.get("x-walkthru-fixture") == "production"
    local = fetch.is_local_site(root_url) and not production_like
    llms = fetch.get(client, f"{base}/llms.txt", same_origin=base)
    probe = fetch.get(client, root_url, headers={"User-Agent": geo.PROBE_AGENT})
    readiness = geo.audit(
        root_url,
        [(page_url, response.text) for page_url, response in pages] or [(root_url, root.text)],
        robots_text,
        # Single-page hosts answer every path with index.html; that is not an llms.txt.
        (llms.status_code if "html" not in llms.headers.get("content-type", "") else 404, llms.text[:20000]) if llms is not None else None,
        (probe.status_code, probe.text[:5000], dict(probe.headers)) if probe is not None else None,
        full=geo_full,
        local=local,
    )
    page_map: list[tuple[str, str, list[str]]] = []
    return SiteAudit(_aggregate(seo_records, len(pages), page_map), _aggregate(security_records, len(pages), page_map), coverage,
                     production_like, readiness, page_map + readiness.pages)
