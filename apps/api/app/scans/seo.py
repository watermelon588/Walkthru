"""SEO checks: deterministic code over the homepage, robots.txt and sitemap.xml, plus PageSpeed when a key exists.
Content and intent review happens in the first-impression LLM call, not here."""

import re
from urllib.robotparser import RobotFileParser

import httpx
from selectolax.parser import HTMLParser

from app.agent.schema import Finding
from app.scans.fetch import get, origin, text_file


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
        # One title on every page, so a crawl merges them into one finding; the count lives in the detail.
        out.append(_f("medium", "Images have no alt text", f"{len(missing_alt)} of {len(imgs)} images on {url} have no alt text. Images without alt text are invisible to search engines and screen readers.", "Describe each meaningful image in its alt attribute; use alt=\"\" for decorative ones.", srcs))

    if not tree.css_first('meta[property="og:title"]'):
        out.append(_f("low", "No Open Graph tags", "Links shared on social apps will show no preview title or image.", "Add og:title, og:description and og:image meta tags.", url))
    return out


def check_robots(text: str | None) -> list[Finding]:
    if text is None:
        return [_f("low", "No robots.txt", "Crawlers fall back to defaults and cannot find your sitemap.", "Add /robots.txt with a Sitemap line.")]
    rules = RobotFileParser()
    rules.parse(text.splitlines())  # groups are respected: a Disallow: / for one named bot does not block everyone
    if not rules.can_fetch("*", "/"):
        return [_f("high", "robots.txt blocks all crawlers", "User-agent: * with Disallow: / hides the whole site from search engines.", "Remove the blanket Disallow or limit it to private paths.", "Disallow: /")]
    return []


MISSING_PATH = "/walkthru-missing-page-check"  # one read-only GET to an address no site has


def check_missing_page(response) -> list[Finding]:
    """W2: a made-up address that answers 200 with a page is a soft 404."""
    if response is None or response.status_code != 200 or "html" not in response.headers.get("content-type", "").lower():
        return []
    return [_f("medium", "Missing pages return 200", f"A made-up address ({MISSING_PATH}) answered 200 with a page instead of 404. Search engines "
               "treat these as soft 404s, and broken links look like working pages to visitors and crawlers.",
               "Return a 404 status for unknown paths: serve a real 404 page, and rewrite only your app's known routes to index.html.",
               str(response.url))]


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
    robots_text = text_file(robots)
    sitemap = get(c, f"{base}/sitemap.xml")
    return (check_html(html, url) + check_robots(robots_text) + check_sitemap(200 if text_file(sitemap) is not None else None, robots_text)
            + check_missing_page(get(c, f"{base}{MISSING_PATH}")))
