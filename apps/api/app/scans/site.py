"""Bounded, same-origin launch audit with root-cause aggregation."""

from __future__ import annotations

import logging
import re
import time
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urldefrag, urlencode, urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx
from selectolax.parser import HTMLParser

from app.agent.schema import Finding
from app.scans import backend, fetch, geo, geo_depth, security, seo, seo_depth

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
    # Query variants create unbounded crawl spaces. The one exception is a small,
    # numeric pagination URL: Google treats each page in a sequence as a URL.
    params = parse_qs(parsed.query)
    page = (params.get("page") or params.get("paged") or [""])[0]
    query = urlencode({"page": page}) if page.isdigit() and 1 <= int(page) <= 100 else ""
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path or "/", query, ""))


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


CHALLENGE = re.compile(r"just a moment|challenge-platform|cf-chl|captcha|access denied", re.IGNORECASE)
SLOW_SECONDS, THIN_WORDS, DEEP_CLICKS = 1.5, 100, 5


def _site_checks(pages: list[tuple[str, httpx.Response]], failed: list[tuple[str, httpx.Response]], linked_from: dict[str, str],
                 depth: dict[str, int], sitemap_text: str, base: str, *, truncated: bool, local: bool) -> list[tuple[Finding, str | None]]:
    """Checks that need the whole crawl, not one page (adapted from OpenSEO's audit, MIT; see docs/decisions.md)."""
    out: list[tuple[Finding, str | None]] = []
    for url, r in failed:
        source = linked_from.get(url, "the crawl")
        if r.status_code == 429:
            out.append((seo._f("medium", "Rate limited, so not checked", "The server answered 429 Too Many Requests, so Walkthru could not check this page. Search engine crawlers can hit the same limit.", "Raise the rate limit for crawlers, then run the check again.", url), url))
        elif r.status_code == 403 or r.headers.get("cf-mitigated") or (r.status_code == 503 and CHALLENGE.search(r.text[:3000])):
            out.append((seo._f("medium", "Crawler was blocked, so not checked", f"The page answered {r.status_code} or a bot challenge instead of the page, so it was not checked. Search and AI crawlers may be blocked the same way.", "If this page should be found, let known crawlers through your bot protection (for example a firewall rule for verified bots).", url), url))
        elif r.status_code >= 500:
            out.append((seo._f("high", "Server error on a linked page", f"{url} answered {r.status_code}. Crawlers that keep seeing server errors crawl the site less and can drop the page.", "Check the server logs for this URL and fix the error, or return 404 and remove the links if the page is gone.", f"{url} ({r.status_code}), linked from {source}"), url))
        else:
            out.append((seo._f("high", "Broken internal link", f"A page links to {url}, which answers {r.status_code}. Visitors hit a dead end and crawlers waste their visit.", "Point the link at the live page, or remove it. If the page moved, add a redirect.", f"{url} ({r.status_code}), linked from {source}"), url))

    titles: dict[str, list[str]] = {}
    descriptions: dict[str, list[str]] = {}
    bodies: dict[str, list[str]] = {}
    for url, r in pages:
        tree = HTMLParser(r.text)
        title = tree.css_first("title")
        if title is not None and title.text(strip=True):
            titles.setdefault(title.text(strip=True), []).append(url)
        desc = tree.css_first('meta[name="description"]')
        if desc is not None and (desc.attributes.get("content") or "").strip():
            descriptions.setdefault((desc.attributes.get("content") or "").strip(), []).append(url)
        text = fetch.page_text(r.text, limit=200000)
        words = len(text.split())
        if words >= 20:
            bodies.setdefault(text, []).append(url)
        if 20 <= words < THIN_WORDS:  # empty JavaScript shells are reported once by the GEO section
            out.append((seo._f("low", "Thin content", f"About {words} words of text before JavaScript runs. Pages this short rarely rank.", "Add useful content, merge the page into a stronger one, or mark it noindex.", url), url))
        if tree.css_first("a[href]") is None and not fetch.is_js_shell(r.text):
            out.append((seo._f("low", "Page has no links", "A dead end: visitors and crawlers have nowhere to go next.", "Link to related pages, the parent section or the homepage.", url), url))
        if r.extensions.get("walkthru_hops", 0) >= 2:
            out.append((seo._f("low", "Redirect chain", f"Reaching this page takes {r.extensions['walkthru_hops']} redirects. Each one adds delay and some crawlers stop following.", "Link and redirect straight to the final URL, so there is at most one redirect.", url), url))
        html_canonical = tree.css_first('link[rel="canonical"]')
        header_canonical = re.search(r"<([^>]+)>\s*;\s*rel=\"?canonical", r.headers.get("link", ""))
        if html_canonical is not None and header_canonical and urljoin(url, html_canonical.attributes.get("href") or "") != urljoin(url, header_canonical.group(1)):
            out.append((seo._f("medium", "Conflicting canonical URLs", "The HTML canonical tag and the HTTP Link header name different URLs, so search engines may ignore both.", "Declare one canonical URL in one place.", url), url))
        if not local and r.extensions.get("walkthru_seconds", 0) > SLOW_SECONDS:
            out.append((seo._f("low", "Slow server response", f"The HTML took {r.extensions['walkthru_seconds']:.1f} s to arrive. Every later speed metric waits on it.", "Cache or pre-render this page's HTML.", url), url))
        if depth.get(url, 0) >= DEEP_CLICKS:
            out.append((seo._f("low", "Page is deep in the site", f"{depth[url]} clicks from the homepage. Deep pages are crawled less often.", "Link to it from the navigation or a higher-level page.", url), url))

    for label, groups in (("title", titles), ("meta description", descriptions), ("text", bodies)):
        for urls in groups.values():
            if len(urls) > 1:
                name = "Duplicate page content" if label == "text" else f"Duplicate {label}"
                out.extend((seo._f("medium" if label == "text" else "low", name, f"Several pages share the same {label}, so search engines cannot tell them apart and may show only one.", f"Give each page its own {label}; for true duplicates, pick one URL and point the others at it with rel=canonical or a redirect.", url), url) for url in urls)

    # Orphans are only knowable when the crawl finished: a truncated crawl may simply not have reached the linking page.
    if not truncated:
        listed = {u for raw in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", sitemap_text) if (u := _normal_url(raw, base + "/", base))}
        for url in sorted(listed - set(linked_from) - {u for u, _ in pages[:1]}):
            out.append((seo._f("low", "Orphan page", "Listed in the sitemap, but no crawled page links to it, so visitors cannot find it by browsing.", "Link to it from a related page or the navigation, or remove it from the sitemap.", url), url))
    return out


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
    failed: list[tuple[str, httpx.Response]] = []  # linked pages that answered 4xx/5xx: reported, never silently skipped
    linked_from: dict[str, str] = {}  # first crawled page linking to each URL
    depth = {root_url: 0}  # clicks from the homepage
    while queue and len(pages) < max_pages and time.monotonic() < deadline:
        page_url = queue.popleft()
        if page_url != root_url and not robot_rules.can_fetch(USER_AGENT, page_url):
            continue
        response = root if page_url == root_url else fetch.get(client, page_url, same_origin=base)
        if response is None or response.status_code >= 400:
            if response is not None:
                failed.append((page_url, response))
            continue
        content_type = response.headers.get("content-type", "")
        if content_type and "html" not in content_type.lower():
            continue
        final_url = str(response.url)
        pages.append((final_url, response))
        depth.setdefault(final_url, depth.get(page_url, 0))
        for link in _links(response.text, final_url, base):
            linked_from.setdefault(link, final_url)
            if link not in queued and robot_rules.can_fetch(USER_AGENT, link):
                queued.add(link)
                queue.append(link)
                depth[link] = depth[final_url] + 1

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
    try:  # Supabase or Firebase from the browser: explained on every plan, probed read-only on verified domains (P1.1)
        security_records.extend((finding, root_url) for finding in backend.check(root.text, root_url, client, verified=verified))
    except Exception:
        logging.getLogger("walkthru").warning("backend exposure check failed for %s", root_url, exc_info=True)

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
    sitemap_text = sitemap_response.text if sitemap_response is not None and sitemap_response.status_code == 200 else ""
    seo_records.extend(_site_checks(pages, failed, linked_from, depth, sitemap_text, base, truncated=truncated, local=local))
    seo_records.extend(seo_depth.audit(pages, base, client, robot_rules, truncated=truncated, deadline=deadline))
    llms = fetch.get(client, f"{base}/llms.txt", same_origin=base)
    probe = fetch.get(client, root_url, headers={"User-Agent": geo.PROBE_AGENT})
    with fetch.client(timeout=2.5) as geo_client:
        remote = geo_depth.collect_remote(root_url, root.text, geo_client, full=geo_full, local=local)
    readiness = geo.audit(
        root_url,
        [(page_url, response.text) for page_url, response in pages] or [(root_url, root.text)],
        robots_text,
        # Single-page hosts answer every path with index.html; that is not an llms.txt.
        (llms.status_code if "html" not in llms.headers.get("content-type", "") else 404, llms.text[:20000]) if llms is not None else None,
        (probe.status_code, probe.text[:5000], dict(probe.headers)) if probe is not None else None,
        full=geo_full,
        local=local,
        sitemap_text=sitemap_text,
        remote=remote,
    )
    page_map: list[tuple[str, str, list[str]]] = []
    return SiteAudit(_aggregate(seo_records, len(pages), page_map), _aggregate(security_records, len(pages), page_map), coverage,
                     production_like, readiness, page_map + readiness.pages)
