"""Bounded, same-origin launch audit with root-cause aggregation."""

from __future__ import annotations

import time
from collections import OrderedDict, deque
from dataclasses import dataclass
from urllib.parse import urldefrag, urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx
from selectolax.parser import HTMLParser

from app.agent.schema import Finding
from app.scans import fetch, security, seo

USER_AGENT = "WalkthruBot"
DEFAULT_MAX_PAGES = 10
MAX_MAX_PAGES = 20
DEFAULT_TIME_LIMIT = 20.0


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


def _robots(text: str | None, url: str) -> RobotFileParser:
    parser = RobotFileParser(url)
    parser.parse((text or "").splitlines())
    return parser


def _aggregate(records: list[tuple[Finding, str | None]], pages_scanned: int) -> list[Finding]:
    groups: OrderedDict[tuple[str, str, str], list[tuple[Finding, str | None]]] = OrderedDict()
    for finding, page_url in records:
        groups.setdefault((finding.kind, finding.title, finding.fix), []).append((finding, page_url))

    severity_rank = {"low": 0, "medium": 1, "high": 2}
    output: list[Finding] = []
    for items in groups.values():
        first = items[0][0]
        urls = list(dict.fromkeys(page for _, page in items if page))
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

    seo_records: list[tuple[Finding, str | None]] = []
    security_records: list[tuple[Finding, str | None]] = []
    for page_url, response in pages:
        seo_records.extend((finding, page_url) for finding in seo.check_html(response.text, page_url))
        security_records.extend((finding, page_url) for finding in security.check_headers(response))
        security_records.extend((finding, page_url) for finding in security.check_content(response.text, page_url))

    seo_records.extend((finding, None) for finding in seo.check_robots(robots_text))
    sitemap_status = sitemap_response.status_code if sitemap_response is not None else None
    seo_records.extend((finding, None) for finding in seo.check_sitemap(sitemap_status, robots_text))
    security_records.extend((finding, root_url) for finding in security.check_transport(url, root, client))
    if verified:
        security_records.extend((finding, None) for finding in security.check_exposed(base, client))
        security_records.extend((finding, None) for finding in security.check_bundles(root.text, root_url, client))

    duration_ms = round((time.monotonic() - started) * 1000)
    truncated = bool(queue) or (time.monotonic() >= deadline and len(pages) < len(queued))
    coverage = AuditCoverage(len(pages), max_pages, duration_ms, truncated, [page_url for page_url, _ in pages])
    return SiteAudit(_aggregate(seo_records, len(pages)), _aggregate(security_records, len(pages)), coverage)
