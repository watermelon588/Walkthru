"""Bounded SEO depth checks over HTML already collected by the site crawl.

The rule inventory was reviewed against MIT Open SEO Crawler, LibreCrawl and
FreeCrawl; implementations follow Google Search Central's current guidance.
"""

from __future__ import annotations

import json
import re
import time
from collections import Counter
from urllib.parse import parse_qs, urldefrag, urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx
from selectolax.parser import HTMLParser

from app.agent.schema import Finding
from app.scans import fetch, seo

LANG = re.compile(r"^(?:[a-z]{2,3}(?:-[a-z0-9]{2,8})*|x-default)$", re.IGNORECASE)
GENERIC = {"click here", "read more", "learn more", "more", "here", "link", "view more"}
OLD_IMAGE = {".jpg", ".jpeg", ".png", ".gif", ".bmp"}


def _normal(url: str, base: str) -> str:
    parts = urlsplit(urldefrag(urljoin(base, url))[0])
    return urlunsplit((parts.scheme, parts.netloc, parts.path or "/", parts.query, ""))


def _schema_objects(tree: HTMLParser) -> list[dict]:
    objects: list[dict] = []
    for node in tree.css('script[type="application/ld+json"]'):
        try:
            value = json.loads(node.text() or "")
        except ValueError:
            continue  # the existing GEO check reports invalid JSON-LD once
        pending = [value]
        while pending:
            item = pending.pop()
            if isinstance(item, list):
                pending.extend(item)
            elif isinstance(item, dict):
                objects.append(item)
                graph = item.get("@graph")
                if isinstance(graph, list):
                    pending.extend(graph)
    return objects


def _required_schema(tree: HTMLParser, url: str) -> list[Finding]:
    """Only check Google's actual required fields for supported rich-result types.

    Article has no required properties in current Search Central docs, so it is
    deliberately absent here. Missing optional fields are not errors.
    """
    out: list[Finding] = []
    for item in _schema_objects(tree):
        raw_type = item.get("@type", [])
        types = {name for name in (raw_type if isinstance(raw_type, list) else [raw_type]) if isinstance(name, str)}
        missing: list[str] = []
        if "Product" in types:
            if not item.get("name"):
                missing.append("name")
            if not any(item.get(key) for key in ("offers", "review", "aggregateRating")):
                missing.append("offers, review or aggregateRating")
        elif types & {"SoftwareApplication", "WebApplication", "MobileApplication"}:
            if not item.get("name"):
                missing.append("name")
            offers = item.get("offers")
            offers_list = offers if isinstance(offers, list) else [offers]
            if not any(isinstance(offer, dict) and offer.get("price") is not None for offer in offers_list):
                missing.append("offers.price")
            if not (item.get("review") or item.get("aggregateRating")):
                missing.append("review or aggregateRating")
        elif "BreadcrumbList" in types:
            links = item.get("itemListElement")
            if not isinstance(links, list) or not links:
                missing.append("itemListElement")
            else:
                for index, crumb in enumerate(links):
                    if not isinstance(crumb, dict):
                        missing.append("each ListItem needs position and name")
                        break
                    nested = crumb.get("item")
                    name = crumb.get("name") or (nested.get("name") if isinstance(nested, dict) else None)
                    if not crumb.get("position") or not name:
                        missing.append("each ListItem needs position and name")
                        break
                    if index < len(links) - 1 and not crumb.get("item"):
                        missing.append("each non-final ListItem needs item")
                        break
        if missing:
            name = next((t for t in ("Product", "SoftwareApplication", "WebApplication", "MobileApplication", "BreadcrumbList") if t in types), "Structured data")
            out.append(seo._f("low", f"{name} rich-result fields are incomplete",
                              "The JSON-LD omits Google's required properties: " + ", ".join(missing) + ". This may prevent the rich result.",
                              "Add the missing properties with values that match the visible page, then use Google's Rich Results Test.", url))
    return out


def _page(url: str, html: str) -> tuple[list[Finding], dict[str, str], list[str], list[tuple[str, bool]]]:
    """Page findings, hreflang map, internal links, and image URLs to inspect."""
    tree = HTMLParser(html)
    findings = _required_schema(tree, url)
    alternates: dict[str, str] = {}
    for link in tree.css("link[hreflang]"):
        if "alternate" not in (link.attributes.get("rel") or "").lower().split():
            continue
        language = (link.attributes.get("hreflang") or "").strip().lower()
        href = (link.attributes.get("href") or "").strip()
        if not LANG.fullmatch(language) or urlsplit(href).scheme not in {"http", "https"}:
            findings.append(seo._f("low", "Invalid hreflang annotation", "A language code or target URL is invalid; Google expects a supported language code and an absolute URL.",
                                   "Use a valid language or region code, x-default for fallback, and a full https:// URL.", f"{url}: {language or '?'} -> {href or '?'}"))
            continue
        target = _normal(href, url)
        if language in alternates and alternates[language] != target:
            findings.append(seo._f("low", "Conflicting hreflang targets", f"The {language} variant points to two URLs on this page.",
                                   "Keep one target for each language or region on a page.", url))
        alternates[language] = target

    generic: list[str] = []
    internal: list[str] = []
    for link in tree.css("a[href]"):
        href = link.attributes.get("href") or ""
        target = _normal(href, url)
        if fetch.origin(target) != fetch.origin(url):
            continue
        internal.append(target)
        if link.text(strip=True).lower() in GENERIC:
            parent = link.parent
            while parent is not None and parent.tag not in {"header", "nav", "footer", "main", "article", "body"}:
                parent = parent.parent
            if parent is not None and parent.tag in {"main", "article"}:
                generic.append(href)
    if generic:
        findings.append(seo._f("low", "Generic internal link text", f"{len(generic)} content link(s) say only 'read more', 'click here' or similar, so their destination is unclear.",
                               "Name the destination or topic in each link's visible text.", f"{url}: {', '.join(generic[:3])}"))

    images: list[tuple[str, bool]] = []
    unsized: list[str] = []
    for image in tree.css("main img[src], article img[src]"):
        src = image.attributes.get("src") or ""
        target = _normal(src, url)
        if fetch.origin(target) != fetch.origin(url):
            continue
        modern_fallback = image.parent is not None and image.parent.tag == "picture" and any(
            (source.attributes.get("type") or "").lower() in {"image/webp", "image/avif"} for source in image.parent.css("source")
        )
        images.append((target, modern_fallback))
        style = (image.attributes.get("style") or "").lower()
        if (image.attributes.get("loading") or "").lower() == "lazy" and not (image.attributes.get("width") and image.attributes.get("height")) and not any(
            property_name in style for property_name in ("aspect-ratio", "width:", "height:")
        ):
            unsized.append(src)
    if unsized:
        findings.append(seo._f("low", "Lazy images lack intrinsic dimensions", f"{len(unsized)} lazy image(s) have no width and height in HTML. CSS may reserve space, but the scan cannot verify it.",
                               "Set width and height attributes, or verify that CSS reserves each image's aspect ratio.", f"{url}: {', '.join(unsized[:3])}"))

    pagination = [n for n in tree.css("nav") if "pagination" in (n.attributes.get("aria-label") or "").lower() or "pagination" in (n.attributes.get("class") or "").lower()]
    for nav in pagination:
        if any("next" in button.text(strip=True).lower() for button in nav.css("button")) and not any(
            "next" in link.text(strip=True).lower() and link.attributes.get("href") for link in nav.css("a")
        ):
            findings.append(seo._f("medium", "Pagination has no crawlable next link", "The next page is exposed as a button, which crawlers do not click to discover later pages.",
                                   "Add a normal <a href> link to the next page, with a distinct URL for that page.", url))
            break
    next_link = tree.css_first('link[rel="next"][href]')
    if next_link and _normal(next_link.attributes.get("href") or "", url) not in internal:
        findings.append(seo._f("medium", "Pagination next page lacks a crawlable link", "The page declares a next URL in metadata but has no ordinary content link to it. Google no longer uses rel=next for discovery.",
                               "Add an <a href> link to the next page in the visible pagination controls.", url))
    return findings, alternates, internal, images


def _image_sizes(client: httpx.Client, urls: dict[str, bool], base: str, robots: RobotFileParser, deadline: float) -> list[tuple[Finding, str]]:
    """HEAD at most 12 same-origin images; absent Content-Length means unmeasured."""
    output: list[tuple[Finding, str]] = []
    for url, modern_fallback in list(urls.items())[:12]:
        if time.monotonic() >= deadline:
            break
        if fetch.origin(url) != base or not robots.can_fetch("WalkthruBot", url):
            continue
        try:
            fetch.assert_public(url)
            response = client.head(url, timeout=2, follow_redirects=False)
            if response.status_code != 200 or not response.headers.get("content-type", "").lower().startswith("image/"):
                continue
            size = int(response.headers.get("content-length", "0"))
        except (httpx.HTTPError, ValueError):
            continue
        if size >= 500_000:
            output.append((seo._f("medium", "Large content image", f"This image is {round(size / 1000)} kB, which can slow the page on mobile.",
                                  "Resize and compress the image for its displayed size.", url), url))
        ext = urlsplit(url).path.lower().rsplit(".", 1)
        suffix = "." + ext[-1] if len(ext) == 2 else ""
        if size >= 150_000 and suffix in OLD_IMAGE and not modern_fallback:
            output.append((seo._f("low", "Large image uses an older format", f"This {suffix} image is {round(size / 1000)} kB; a modern format may reduce its transfer size.",
                                  "Try WebP or AVIF and compare the resulting quality and bytes.", url), url))
    return output


def audit(pages: list[tuple[str, httpx.Response]], base: str, client: httpx.Client, robots: RobotFileParser, *, truncated: bool,
          deadline: float) -> list[tuple[Finding, str | None]]:
    """Use only fetched pages plus bounded same-origin HEADs and canonical reads."""
    records: list[tuple[Finding, str | None]] = []
    parsed: dict[str, tuple[HTMLParser, dict[str, str], list[str]]] = {}
    images: dict[str, bool] = {}
    for url, response in pages:
        findings, alternates, links, page_images = _page(url, response.text)
        records.extend((finding, url) for finding in findings)
        parsed[url] = (HTMLParser(response.text), alternates, links)
        for image_url, modern_fallback in page_images:
            images[image_url] = images.get(image_url, False) or modern_fallback

    for url, (_, alternates, _) in parsed.items():
        if not alternates:
            continue
        if url not in alternates.values():
            records.append((seo._f("low", "Hreflang omits its own page", "Each localized page should list itself among its language variants.",
                                   "Add an alternate hreflang link for this page's own URL.", url), url))
        for language, target in alternates.items():
            if target in parsed and target != url and url not in parsed[target][1].values():
                records.append((seo._f("low", "Hreflang return link is missing", f"The audited {language} variant does not link back to this page.",
                                       "Include the same variant set on both localized pages.", f"{url} -> {target}"), url))

    # A few-page site normally has leaf pages with one link in. This becomes
    # useful only once the crawl is broad enough to represent a link graph.
    if not truncated and len(parsed) >= 10:
        incoming = Counter(target for source, (_, _, links) in parsed.items() for target in set(links) if target != source and target in parsed)
        for url in list(parsed)[1:]:
            if incoming[url] == 1:
                records.append((seo._f("low", "Page has one internal link in", "Only one audited page links to this page, so visitors and crawlers have a narrow path to it.",
                                       "Link to this page from another relevant page or navigation section.", url), url))

    checked: dict[str, httpx.Response] = {url: response for url, response in pages}
    probed: dict[str, httpx.Response | None] = {}
    extra = 0
    for url, (tree, _, _) in parsed.items():
        canonical = tree.css_first('link[rel="canonical"][href]')
        if canonical is None:
            continue
        target = _normal(canonical.attributes.get("href") or "", url)
        page_values = parse_qs(urlsplit(url).query).get("page", [])
        if page_values and page_values[0].isdigit() and int(page_values[0]) > 1 and target != url:
            records.append((seo._f("low", "Paginated page canonicalizes elsewhere", "Page two or later declares another page as canonical, so its unique items may not be indexed.",
                                   "Give each paginated page its own URL and a self-referencing canonical.", f"{url} -> {target}"), url))
        if fetch.origin(target) != base or target == url or not robots.can_fetch("WalkthruBot", target):
            continue
        if target not in probed and extra < 3 and time.monotonic() < deadline:
            probed[target] = fetch.get(client, target, same_origin=base, timeout=2)
            extra += 1
        response = probed.get(target) or checked.get(target)
        if response is None:
            continue
        if probed.get(target) is not None and (response.extensions.get("walkthru_hops", 0) or response.is_redirect):
            records.append((seo._f("medium", "Canonical points at a redirect", "The canonical URL redirects instead of serving the preferred page directly.",
                                   "Point rel=canonical at the final, indexable URL.", f"{url} -> {target}"), url))
        elif response.status_code == 200:
            target_tree = HTMLParser(response.text)
            robots_meta = target_tree.css_first('meta[name="robots"]')
            if robots_meta and "noindex" in (robots_meta.attributes.get("content") or "").lower():
                records.append((seo._f("medium", "Canonical points at a noindex page", "The preferred URL says search engines must not index it.",
                                       "Point rel=canonical at an indexable page, or remove noindex from the intended canonical.", f"{url} -> {target}"), url))

    records.extend(_image_sizes(client, images, base, robots, deadline))
    return records
