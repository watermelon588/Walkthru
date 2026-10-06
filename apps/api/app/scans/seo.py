"""SEO checks: deterministic code over the homepage, robots.txt and sitemap.xml, plus PageSpeed when a key exists.
Content and intent review happens in the first-impression LLM call, not here."""

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

    # Length and heading-count checks are advisory presentation checks, not ranking failures: Google sets no length
    # limit for titles or descriptions and no ideal heading count (app/scans/seo_guidance.py has the sources).
    title = (tree.css_first("title").text(strip=True) if tree.css_first("title") else "") or ""
    if not title:
        out.append(_f("high", "Missing page title", "The page has no <title>. Search results and browser tabs show the URL or other page text instead.", "Add a title that says what this page is and names the site.", url))
    elif len(title) < 15:
        out.append(_f("low", "Page title is too short", f'The title is "{title}" ({len(title)} characters). Advisory: a very short title may say little about the page.', "Describe this page and the brand in the title. There is no required length.", title))
    elif len(title) > 60:
        out.append(_f("low", "Page title is too long", f"The title is {len(title)} characters. Advisory: there is no length limit, but long titles are shortened in search results to fit the screen.", "Put the most important words first. Shortening is optional.", title))

    desc = tree.css_first('meta[name="description"]')
    content = (desc.attributes.get("content") or "").strip() if desc else ""
    if not content:
        out.append(_f("medium", "Missing meta description", "No meta description. Advisory: search engines usually build snippets from page text, and link previews often show the description when it exists.", "Add a short description of what this page offers and for whom. There is no required length.", url))
    elif len(content) < 50:
        out.append(_f("low", "Meta description is too short", f"{len(content)} characters. Advisory: a very short description is often replaced with text from the page.", "Say what the page offers and why to visit. There is no required length.", content))
    elif len(content) > 160:
        out.append(_f("low", "Meta description is too long", f"{len(content)} characters. Advisory: there is no length limit, but long snippets are shortened to fit the screen.", "Put the key point first. Shortening is optional.", content[:80]))

    h1s = [h.text(strip=True) for h in tree.css("h1")]
    if not h1s:
        out.append(_f("low", "No h1 heading", "The page has no top-level heading. Advisory: a clear main heading helps visitors and screen-reader users find the topic; search engines also read prominent headings.", "Add one main heading that states what the page is about.", url))
    elif len(h1s) > 1:
        out.append(_f("low", "More than one h1 heading", f"{len(h1s)} h1 elements: {', '.join(h1s[:3])}. Advisory: there is no ideal number of headings for search; several h1s can blur the main heading for screen-reader users.", "Optional: keep one main h1 and use h2 for section titles.", " | ".join(h1s[:3])))

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
    return check_html(html, url) + check_robots(robots_text) + check_sitemap(sitemap.status_code if sitemap else None, robots_text)
