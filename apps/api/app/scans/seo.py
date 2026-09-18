"""SEO checks: deterministic code over the homepage, robots.txt and sitemap.xml, plus PageSpeed when a key exists.
Content and intent review happens in the first-impression LLM call, not here."""

import os
import re

import httpx
from selectolax.parser import HTMLParser

from app.agent.schema import Finding
from app.scans.fetch import get, origin


def _f(severity: str, title: str, detail: str, fix: str, evidence: str | None = None) -> Finding:
    return Finding(kind="seo", severity=severity, title=title, detail=detail, fix=fix, evidence=evidence)


def check_html(html: str, url: str) -> list[Finding]:
    tree = HTMLParser(html)
    out: list[Finding] = []

    title = (tree.css_first("title").text(strip=True) if tree.css_first("title") else "") or ""
    if not title:
        out.append(_f("high", "Missing page title", "The page has no <title>. Search results and browser tabs show the URL instead.", "Add a title of 15 to 60 characters that says what the page is.", url))
    elif len(title) < 15:
        out.append(_f("medium", "Page title is too short", f'The title is "{title}" ({len(title)} characters).', "Use 15 to 60 characters that describe the page and the brand.", title))
    elif len(title) > 60:
        out.append(_f("low", "Page title is too long", f"The title is {len(title)} characters and will be cut off in search results.", "Keep the title under 60 characters.", title))

    desc = tree.css_first('meta[name="description"]')
    content = (desc.attributes.get("content") or "").strip() if desc else ""
    if not content:
        out.append(_f("high", "Missing meta description", "Search engines will pick a random snippet of page text as the summary.", "Add a meta description of 50 to 160 characters that says what the site does and for whom.", url))
    elif len(content) > 160:
        out.append(_f("low", "Meta description is too long", f"{len(content)} characters; it will be truncated in results.", "Keep it under 160 characters.", content[:80]))

    h1s = [h.text(strip=True) for h in tree.css("h1")]
    if not h1s:
        out.append(_f("medium", "No h1 heading", "The page has no top-level heading, so the main topic is unclear to search engines and screen readers.", "Add exactly one h1 that states what the page is about.", url))
    elif len(h1s) > 1:
        out.append(_f("low", "More than one h1 heading", f"{len(h1s)} h1 elements: {', '.join(h1s[:3])}.", "Keep one h1 per page; use h2 for sections.", " | ".join(h1s[:3])))

    if not tree.css_first('link[rel="canonical"]'):
        out.append(_f("low", "No canonical link", "Without a canonical URL, variants like ?utm= or trailing slashes can split ranking signals.", 'Add <link rel="canonical" href="..."> pointing at the preferred URL.', url))
    if not tree.css_first('meta[name="viewport"]'):
        out.append(_f("high", "No viewport meta tag", "The page will render at desktop width on phones.", 'Add <meta name="viewport" content="width=device-width, initial-scale=1">.', url))
    html_tag = tree.css_first("html")
    if html_tag is None or not html_tag.attributes.get("lang"):
        out.append(_f("low", "No language attribute", "The <html> element has no lang attribute; screen readers and search engines guess the language.", 'Add lang="en" (or the page language) to <html>.', url))
    robots_meta = tree.css_first('meta[name="robots"]')
    if robots_meta and "noindex" in (robots_meta.attributes.get("content") or "").lower():
        out.append(_f("high", "Page is set to noindex", "A robots meta tag tells search engines not to index this page.", "Remove noindex from the robots meta tag if the page should rank.", robots_meta.attributes.get("content")))

    imgs = tree.css("img")
    missing_alt = [i for i in imgs if i.attributes.get("alt") is None]
    if missing_alt:
        srcs = ", ".join((i.attributes.get("src") or "?")[:40] for i in missing_alt[:3])
        out.append(_f("medium", f"{len(missing_alt)} of {len(imgs)} images have no alt text", "Images without alt text are invisible to search engines and screen readers.", "Describe each meaningful image in its alt attribute; use alt=\"\" for decorative ones.", srcs))

    if not tree.css_first('meta[property="og:title"]'):
        out.append(_f("low", "No Open Graph tags", "Links shared on social apps will show no preview title or image.", "Add og:title, og:description and og:image meta tags.", url))
    return out


def check_robots(text: str | None) -> list[Finding]:
    if text is None:
        return [_f("low", "No robots.txt", "Crawlers fall back to defaults and cannot find your sitemap.", "Add /robots.txt with a Sitemap line.")]
    block = re.search(r"user-agent:\s*\*\s*(?:\n.*?)*?disallow:\s*/\s*$", text, re.IGNORECASE | re.MULTILINE)
    if block and not re.search(r"^allow:\s*/\s*$", text, re.IGNORECASE | re.MULTILINE):
        return [_f("high", "robots.txt blocks all crawlers", "User-agent: * with Disallow: / hides the whole site from search engines.", "Remove the blanket Disallow or limit it to private paths.", "Disallow: /")]
    return []


def check_sitemap(status: int | None, robots: str | None) -> list[Finding]:
    if status == 200:
        return []
    if robots and re.search(r"^sitemap:", robots, re.IGNORECASE | re.MULTILINE):
        return []
    return [_f("low", "No sitemap.xml", "Search engines discover pages slower without a sitemap.", "Generate /sitemap.xml and reference it from robots.txt.")]


def pagespeed(url: str, c: httpx.Client) -> list[Finding]:
    key = os.environ.get("PAGESPEED_API_KEY")
    if not key:
        return []
    r = get(c, f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={url}&strategy=mobile&category=performance&key={key}")
    if r is None or r.status_code != 200:
        return []
    lh = r.json().get("lighthouseResult", {})
    score = round((lh.get("categories", {}).get("performance", {}).get("score") or 0) * 100)
    lcp = lh.get("audits", {}).get("largest-contentful-paint", {}).get("displayValue", "?")
    if score >= 90:
        return []
    return [_f("medium" if score < 50 else "low", f"Mobile performance score {score}/100", f"Largest Contentful Paint: {lcp}. Slow pages lose visitors before the first click.", "Compress images, defer non-critical scripts, and serve static assets from a CDN.", f"PageSpeed Insights, mobile: {score}")]


def scan(url: str, c: httpx.Client, html: str | None = None) -> list[Finding]:
    """All SEO findings for a homepage. `html` avoids a second fetch when the caller already has it."""
    if html is None:
        r = get(c, url)
        if r is None or r.status_code >= 400:
            return [_f("high", "Homepage did not load", f"Status {r.status_code if r else 'no response'}.", "Make sure the homepage returns 200.", url)]
        html, url = r.text, str(r.url)
    base = origin(url)
    robots = get(c, f"{base}/robots.txt")
    robots_text = robots.text if robots is not None and robots.status_code == 200 else None
    sitemap = get(c, f"{base}/sitemap.xml")
    return check_html(html, url) + check_robots(robots_text) + check_sitemap(sitemap.status_code if sitemap else None, robots_text) + pagespeed(url, c)
