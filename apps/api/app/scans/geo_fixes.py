"""GEO fix pack: copy-paste fixes built in code from the audited pages (SPEC.md). No model call, so every
value comes from the site itself and nothing is invented. Each fix: id, title, file, code, note."""

import json
import re
import secrets
from urllib.parse import urlsplit

from selectolax.parser import HTMLParser

CITATION_BOTS = ("OAI-SearchBot", "ChatGPT-User", "Claude-SearchBot", "ClaudeBot", "PerplexityBot", "Googlebot", "Bingbot", "Applebot")


def _meta(tree: HTMLParser, selector: str) -> str | None:
    node = tree.css_first(selector)
    return (node.attributes.get("content") or "").strip() or None if node else None


def site_name(tree: HTMLParser, objects: list[dict]) -> str:
    """og:site_name, then a schema name, then the title before its separator ("Tripverse: plan trips" -> "Tripverse")."""
    name = _meta(tree, 'meta[property="og:site_name"]')
    name = name or next((o["name"] for o in objects if isinstance(o.get("name"), str)), None)
    title = tree.css_first("title").text(strip=True) if tree.css_first("title") else ""
    return name or re.split(r"\s*[:|\-–—]\s*", title)[0].strip() or "Your site"


def framework(html: str) -> str | None:
    lowered = html.lower()
    if "__next_data__" in lowered or "/_next/" in lowered:
        return "Next.js"
    if "lovable" in lowered or "gptengineer" in lowered:
        return "Lovable (Vite and React)"
    if "astro-island" in lowered or "/_astro/" in lowered:
        return "Astro"
    if 'id="root"' in lowered or 'id="app"' in lowered or re.search(r'src="/assets/index-[\w-]+\.js"', lowered):
        return "Vite single-page app"
    return None


def build(root_url: str, pages: list[tuple[str, str]], objects: list[dict], *, root_objects: list[dict], blocked: list[str],
          shell: bool, llms_ok: bool | None, indexing: bool = False) -> list[dict]:
    """Fixes for what the GEO audit found, most valuable first. `objects` is JSON-LD from every audited page, `root_objects`
    from the homepage only (the site's name comes from there). llms_ok is None when llms.txt was not checked."""
    root_html = pages[0][1] if pages else ""
    tree = HTMLParser(root_html)
    base = f"{urlsplit(root_url).scheme}://{urlsplit(root_url).netloc}"
    name = site_name(tree, root_objects)
    description = _meta(tree, 'meta[name="description"]') or _meta(tree, 'meta[property="og:description"]') or ""
    types = {t for o in objects for t in (o.get("@type") if isinstance(o.get("@type"), list) else [o.get("@type")])}
    out = []

    if shell:
        stack = framework(root_html) or "your framework"
        body = f"<h1>{name}</h1>\n" + (f"<p>{description}</p>\n" if description else "<p>[Two or three sentences: what it does, who it is for, what it costs.]</p>\n")
        out.append({
            "id": "render", "title": f"Put real content in the HTML ({stack})", "file": "index.html (inside the root element)",
            "code": body,
            "note": f"AI crawlers do not run JavaScript. Best: prerender or statically generate your pages ({stack} supports it). "
                    "Quick fix: put this inside the root element in index.html; your app replaces it when it loads.",
        })
    if blocked:
        rules = "\n\n".join(f"User-agent: {bot}\nAllow: /" for bot in CITATION_BOTS)
        out.append({
            "id": "robots", "title": "Let AI search assistants read your site", "file": "robots.txt",
            "code": f"# Let AI search assistants read and cite your site\n{rules}\n",
            "note": "Add at the top of robots.txt at your site root. To opt out of AI training only, block GPTBot, Google-Extended and CCBot instead.",
        })
    if not types & {"Organization", "WebSite"}:
        graph = [{"@type": "Organization", "name": name, "url": base + "/"}, {"@type": "WebSite", "name": name, "url": base + "/"}]
        if description:
            graph.append({"@type": "SoftwareApplication", "name": name, "description": description, "url": base + "/"})
        code = json.dumps({"@context": "https://schema.org", "@graph": graph}, indent=2)
        out.append({
            "id": "schema", "title": "Tell AI search who you are (structured data)", "file": "index.html <head>",
            "code": f'<script type="application/ld+json">\n{code}\n</script>',
            "note": "Add inside <head> on the homepage. Then add your logo URL and sameAs links to your public profiles.",
        })
    if not _meta(tree, 'meta[property="og:site_name"]'):
        out.append({
            "id": "name", "title": "State your name for machines", "file": "every page <head>",
            "code": f'<meta property="og:site_name" content="{name}">', "note": "Add inside <head> on every page.",
        })
    if llms_ok is False:
        lines = [f"# {name}", "", f"> {description or '[One sentence about what the site offers.]'}", "", "## Pages"]
        for url, html in pages[:20]:
            page = HTMLParser(html)
            label = page.css_first("title").text(strip=True) if page.css_first("title") else url
            lines.append(f"- [{label}]({url})")
        out.append({
            "id": "llms", "title": "Add an llms.txt map (low impact)", "file": "llms.txt",
            "code": "\n".join(lines) + "\n", "note": "Save as /llms.txt at your site root. Low measured impact today, so do it after the fixes above.",
        })
    if indexing:
        key = secrets.token_hex(16)
        out.append({
            "id": "indexnow", "title": "Optional: add an IndexNow key file", "file": f"public/{key}.txt",
            "code": key + "\n",
            "note": f"Publish at {base}/{key}.txt. Keep this key for future URL submissions. IndexNow announces changes to supporting search engines; it does not guarantee indexing.",
        })
        out.append({
            "id": "bing", "title": "Optional: submit the sitemap to Bing Webmaster Tools", "file": "Bing Webmaster Tools",
            "code": f"{base}/sitemap.xml",
            "note": "Verify this site in Bing Webmaster Tools, then submit the sitemap URL above. This is a manual owner step, not an automatic submission.",
        })
    return out
