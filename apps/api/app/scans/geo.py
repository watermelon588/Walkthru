"""GEO readiness: can AI search engines (ChatGPT Search, Claude, Perplexity, Google's AI answers) fetch,
understand and quote this site? Deterministic, from pages the site audit already fetched.

Scored as the percentage of measured points (SPEC.md "GEO readiness"): a check that could not run is left
out rather than given or taken. Category model adapted from geo-optimizer-skill (MIT), re-weighted toward
checks with evidence. Readiness only: this never promises citations or rankings.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

from selectolax.parser import HTMLParser

from app.agent.schema import Finding
from app.scans import agent_signals, fetch, geo_depth, geo_fixes

# Bots that fetch pages to answer and cite. Blocking any of these hides the site from that assistant.
CITATION_BOTS = ("OAI-SearchBot", "ChatGPT-User", "Claude-SearchBot", "ClaudeBot", "PerplexityBot", "Googlebot", "Bingbot", "Applebot")
# Bots that only collect training data. Blocking them is a legitimate choice and is not scored.
TRAINING_BOTS = ("GPTBot", "Google-Extended", "CCBot", "anthropic-ai")
PROBE_AGENT = "Mozilla/5.0 (compatible; OAI-SearchBot/1.0; +https://openai.com/searchbot)"
PAGE_TYPES = {"SoftwareApplication", "WebApplication", "Product", "FAQPage", "Article", "BlogPosting", "Service", "Course"}
BANDS = ((86, "excellent"), (68, "good"), (36, "foundation"), (0, "critical"))
MIN_WORDS = 150  # below this the homepage says too little for an assistant to describe the site


@dataclass
class GeoResult:
    score: int
    band: str
    categories: list[dict]
    findings: list[Finding]
    ai_words: int
    ai_view: str
    notes: list[str] = field(default_factory=list)
    fixes: list[dict] = field(default_factory=list)  # the GEO fix pack (app/scans/geo_fixes.py)
    full: bool = True
    pages: list[tuple[str, str, list[str]]] = field(default_factory=list)  # (kind, title, every affected page)
    citability: list[dict] = field(default_factory=list)
    trust: dict = field(default_factory=dict)
    discovery: dict = field(default_factory=dict)
    entities: dict = field(default_factory=dict)
    agent: dict = field(default_factory=dict)  # app/scans/agent_signals.py, for the agent readiness score (P1.7)

    def summary(self) -> dict:
        """The part stored in `report.geo`; findings go to the report's findings list. Free reports keep one fix and the count."""
        shown = self.fixes if self.full else self.fixes[:1]
        return {"score": self.score, "band": self.band, "categories": self.categories, "ai_words": self.ai_words, "ai_view": self.ai_view,
                "notes": self.notes, "fixes": shown, "fixes_total": len(self.fixes), "citability": self.citability,
                "trust": self.trust, "discovery": self.discovery, "entities": self.entities, "agent": self.agent}


def _f(severity: str, title: str, detail: str, fix: str, evidence: str | None = None) -> Finding:
    return Finding(kind="geo", severity=severity, title=title, detail=detail[:600], fix=fix[:400], evidence=evidence[:300] if evidence else None)


def _json_ld(tree: HTMLParser) -> tuple[list[dict], bool]:
    """Every JSON-LD object on the page (expanding @graph and lists), and whether any block failed to parse."""
    objects, broken = [], False
    for node in tree.css('script[type="application/ld+json"]'):
        try:
            data = json.loads(node.text() or "")
        except ValueError:
            broken = True
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            item = stack.pop()
            if isinstance(item, list):
                stack.extend(item)
            elif isinstance(item, dict):
                objects.append(item)
                stack.extend(item.get("@graph", []) if isinstance(item.get("@graph"), list) else [])
    return objects, broken


def _types(obj: dict) -> set[str]:
    t = obj.get("@type", [])
    return set(t if isinstance(t, list) else [t])


def _blocked_bots(robots_text: str | None, url: str, bots: tuple[str, ...]) -> list[str]:
    if not robots_text:
        return []
    rules = RobotFileParser()
    rules.parse(robots_text.splitlines())
    return [b for b in bots if not rules.can_fetch(b, url)]


def _challenged(status: int, headers: dict, body: str) -> bool:
    lowered = {k.lower(): v for k, v in headers.items()}
    return status in (401, 403, 429, 503) or lowered.get("cf-mitigated") == "challenge" or "challenge-platform" in body


def audit(root_url: str, pages: list[tuple[str, str]], robots_text: str | None, llms: tuple[int, str] | None,
          probe: tuple[int, str, dict] | None, *, full: bool, local: bool = False, sitemap_text: str = "",
          remote: dict | None = None) -> GeoResult:
    """`pages` starts with the homepage. `full` scores every page (paid plans); otherwise the homepage only.
    `local` skips checks that describe the host rather than the code (robots.txt and the bot probe on a dev server)."""
    scope = pages if full else pages[:1]
    root_html = pages[0][1] if pages else ""
    root = HTMLParser(root_html)
    cats: list[dict] = []
    findings: list[Finding] = []
    notes: list[str] = []
    page_map: list[tuple[str, str, list[str]]] = []

    def score(cat_id: str, label: str, parts: list[tuple[float, int]]) -> None:
        measured = [(e, m) for e, m in parts if m]
        if measured:
            cats.append({"id": cat_id, "label": label, "earned": round(sum(e for e, _ in measured)), "max": sum(m for _, m in measured)})

    # 1. AI crawler access (25)
    access: list[tuple[float, int]] = []
    blocked: list[str] = []
    llms_ok: bool | None = None
    if not local:
        blocked = _blocked_bots(robots_text, root_url, CITATION_BOTS)
        access.append((15 * (len(CITATION_BOTS) - len(blocked)) / len(CITATION_BOTS), 15))
        if blocked:
            findings.append(_f("high", "robots.txt blocks AI search assistants",
                               f"Your robots.txt tells these assistants not to read your site: {', '.join(blocked)}. They cannot quote or link to pages they may not fetch.",
                               "Allow them in robots.txt (User-agent: <name> / Allow: /). To opt out of AI training only, block GPTBot, Google-Extended and CCBot instead.",
                               f"{urlsplit(root_url).scheme}://{urlsplit(root_url).netloc}/robots.txt"))
        training = _blocked_bots(robots_text, root_url, TRAINING_BOTS)
        if training:
            notes.append(f"robots.txt blocks AI training crawlers ({', '.join(training)}). That is a choice and does not affect AI search answers.")
        if probe is not None:
            status, body, headers = probe
            if _challenged(status, headers, body):
                access.append((0, 10))
                findings.append(_f("high", "Your site blocks AI search user agents",
                                   f"When your homepage is requested with an AI search crawler's user agent it answers {status}"
                                   f"{' with a bot challenge' if 'challenge' in json.dumps(headers).lower() + body.lower() else ''}. Many hosts and CDNs block these crawlers by default.",
                                   "Allow verified AI search crawlers in your CDN or firewall bot settings (for example Cloudflare's AI crawler controls), then rescan.",
                                   f"HTTP {status} for {PROBE_AGENT.split(';')[1].strip()}"))
            else:
                access.append((10, 10))
                notes.append("Not blocked for an AI search user agent. Edge networks verify real crawlers by IP, so this cannot prove access.")
    score("access", "AI crawler access", access)

    # 2. Content before JavaScript (20)
    text = fetch.page_text(root_html, 20000) if pages else ""
    words = len(text.split())
    shell = bool(pages) and fetch.is_js_shell(root_html)
    content: list[tuple[float, int]] = []
    if pages:
        if shell:
            content.append((0, 15))
            findings.append(_f("high", "Homepage content only appears after JavaScript runs",
                               f"The server sends {len(root_html)} bytes of HTML with {len(text)} characters of visible text. Most AI crawlers do not run JavaScript, "
                               "so ChatGPT, Claude and Perplexity see an empty page. Link previews on WhatsApp, LinkedIn and Slack do too. Google runs JavaScript but indexes it later.",
                               "Prerender the homepage (static generation or server rendering), or at least put a real h1, description and a short paragraph about the product in index.html.",
                               root_url))
        elif words < MIN_WORDS:
            content.append((8, 15))
            findings.append(_f("medium", "The homepage says little before JavaScript runs",
                               f"AI crawlers read {words} words on your homepage. That is thin for an assistant to explain what you do and for whom.",
                               "Put a plain two or three sentence description of the product, who it is for and what it costs in the server-rendered HTML.", root_url))
        else:
            content.append((15, 15))
        if full and len(pages) > 1:
            shells = [u for u, h in pages[1:] if fetch.is_js_shell(h)]
            content.append((5 * (len(pages) - 1 - len(shells)) / (len(pages) - 1), 5))
            if shells:
                page_map.append(("geo", f"{len(shells)} more page{'s' if len(shells) > 1 else ''} only render with JavaScript", shells))
                findings.append(_f("medium", f"{len(shells)} more page{'s' if len(shells) > 1 else ''} only render with JavaScript",
                                   "AI crawlers see these pages as empty: " + ", ".join(shells[:5]),
                                   "Prerender these routes too, starting with pricing, features and docs.", ", ".join(shells[:3])))
    score("content", "Content before JavaScript", content)

    # 3. Structured data (15)
    objects, broken = [], False
    for _, html in scope:
        found, bad = _json_ld(HTMLParser(html))
        objects += found
        broken = broken or bad
    types = set().union(*(_types(o) for o in objects)) if objects else set()
    rich = any(len([k for k in o if not k.startswith("@")]) >= 5 for o in objects)
    score("schema", "Structured data", [(5 if objects else 0, 5), (4 if types & {"Organization", "WebSite"} else 0, 4),
                                        (4 if types & PAGE_TYPES else 0, 4), (2 if rich else 0, 2)])
    if broken:
        findings.append(_f("medium", "Structured data does not parse",
                           "A JSON-LD block on your site is not valid JSON, so search engines and AI assistants ignore it.",
                           "Validate the block (for example with Google's Rich Results Test) and fix the syntax.", root_url))
    if not objects:
        findings.append(_f("medium", "No structured data",
                           "Your pages have no JSON-LD. Structured data tells AI assistants exactly what your product is, who makes it and what it costs.",
                           "Add Organization and WebSite JSON-LD to the homepage, plus SoftwareApplication or Product where you describe the product.", root_url))
    else:
        if not types & {"Organization", "WebSite"}:
            findings.append(_f("low", "No Organization or WebSite structured data", "Assistants use it to tie your pages to one named company.",
                               "Add Organization JSON-LD (name, url, logo, sameAs) to the homepage.", root_url))
        if not types & PAGE_TYPES:
            findings.append(_f("low", "No structured data describing the product", "Nothing marks up what you sell (SoftwareApplication, Product, FAQPage or Article).",
                               "Add SoftwareApplication or Product JSON-LD with name, description, category and price.", root_url))

    # 4. Answerability (15): headings, an early plain answer, lists, numbers. H1 is scored here but reported by SEO.
    per_page = []
    for url, html in scope:
        tree = HTMLParser(html)
        if fetch.is_js_shell(html):
            continue
        paragraphs = [p.text(strip=True) for p in tree.css("p")[:3]]
        per_page.append((url, len(tree.css("h1")) == 1, len(tree.css("h2")) >= 2, any(len(p.split()) >= 25 for p in paragraphs),
                         bool(tree.css("ul, ol, table")), len(re.findall(r"\d[\d,.%$]*", fetch.page_text(html, 20000))) >= 3))
    if per_page:
        n = len(per_page)
        score("answers", "Easy to quote", [(3 * sum(p[i] for p in per_page) / n, 3) for i in range(1, 6)])
        no_h2 = [u for u, _, h2, *_ in per_page if not h2]
        if no_h2:
            page_map.append(("geo", "Few section headings", no_h2))
            findings.append(_f("low", "Few section headings",
                               "Pages with fewer than two h2 headings are harder for assistants to split into quotable answers.",
                               "Break each page into sections with descriptive h2 headings (for example 'How it works', 'Pricing', 'Who it is for').", ", ".join(no_h2[:3])))
        no_answer = [u for u, _, _, early, *_ in per_page if not early]
        if no_answer:
            page_map.append(("geo", "No plain answer near the top", no_answer))
            findings.append(_f("low", "No plain answer near the top",
                               "None of the first paragraphs is a full sentence or two about what the page offers. Assistants quote early, self-contained paragraphs.",
                               "Open with a 25 to 50 word paragraph that says what it is, who it is for and one concrete number.", ", ".join(no_answer[:3])))

    # 5. Entity and trust (10)
    if pages and not shell:
        site_name = next((m.attributes.get("content") for m in root.css('meta[property="og:site_name"]') if m.attributes.get("content")), None)
        site_name = site_name or next((o.get("name") for o in objects if _types(o) & {"Organization", "WebSite"} and isinstance(o.get("name"), str)), None)
        title = root.css_first("title").text(strip=True) if root.css_first("title") else ""
        links = " ".join(((a.attributes.get("href") or "") + " " + a.text(strip=True)).lower() for a in root.css("a"))
        groups = [any(w in links for w in ("about",)), any(w in links for w in ("contact", "support")), any(w in links for w in ("privacy", "pricing"))]
        same_as = any(o.get("sameAs") for o in objects)
        name_points = 0 if not site_name else 4 if site_name.lower() in title.lower() else 2
        score("entity", "Name and trust", [(name_points, 4), (4 * sum(groups) / 3, 4), (2 if same_as else 0, 2)])
        if not site_name:
            findings.append(_f("low", "Your site never states its name in a machine-readable way",
                               "There is no og:site_name and no Organization or WebSite name, so assistants have to guess what to call you.",
                               "Add <meta property=\"og:site_name\" content=\"Your name\"> and an Organization name in JSON-LD.", root_url))
        missing = [name for name, ok in (("about", groups[0]), ("contact", groups[1])) if not ok]
        if missing:
            findings.append(_f("low", f"No {' or '.join(missing)} link on the homepage",
                               "Assistants and people look for who is behind a product before recommending it.",
                               "Link to an about page and a contact page from the homepage header or footer.", root_url))

    # 6. Meta (10): scored only; the SEO section reports missing meta tags.
    if pages and not shell:
        has = lambda sel: bool(root.css_first(sel))
        score("meta", "Title and description", [(3 if has("title") else 0, 3), (3 if has('meta[name="description"]') else 0, 3),
                                                  (2 if has('link[rel="canonical"]') else 0, 2), (2 if has('meta[property^="og:"]') else 0, 2)])

    # 7. llms.txt (3) and AI discovery endpoints (2): low measured impact.
    if llms is not None and not local:
        status, body = llms
        ok = llms_ok = status == 200 and body.lstrip().startswith("# ")
        score("llms", "llms.txt", [(3 if ok else 1 if status == 200 else 0, 3)])
        if not ok:
            findings.append(_f("low", "No llms.txt" if status != 200 else "llms.txt is not in the expected format",
                               "llms.txt is a short Markdown map of your site for AI tools. It has low measured impact on AI search today, so fix the items above first.",
                               "Add /llms.txt: an H1 with your name, a one-line > summary, then sections of links to your key pages.",
                               f"{urlsplit(root_url).scheme}://{urlsplit(root_url).netloc}/llms.txt"))
    discovery = (remote or {}).get("discovery", {})
    measured = [present for present in discovery.values() if present is not None]
    if measured:
        score("discovery", "AI discovery files (low impact)", [(2 * sum(measured) / len(measured), 2)])
        for path, present in discovery.items():
            if present is False:
                findings.append(_f("low", f"No {path}",
                                   "This optional AI discovery file is absent or serves HTML. Its effect on AI search is not established; fix crawler access and content first.",
                                   f"Publish a plain-text {path} describing the site and linking to its key pages.",
                                   fetch.origin(root_url) + path))
    entities = (remote or {}).get("entities", {})
    for source, value in entities.items():
        if value.get("status") == "matched":
            notes.append(f"{source.replace('_', ' ').title()} has an entity whose official website matches this domain.")
        elif value.get("status") == "no_match":
            notes.append(f"No {source.replace('_', ' ')} entity with this domain was found. This is an advisory identity signal, not a ranking requirement.")

    earned, possible = sum(c["earned"] for c in cats), sum(c["max"] for c in cats)
    total = round(100 * earned / possible) if possible else 0
    band = next(name for floor, name in BANDS if total >= floor)
    view = "" if shell else " ".join(text.split()[:60])
    fixes = geo_fixes.build(root_url, list(scope), objects, root_objects=_json_ld(root)[0], blocked=blocked, shell=shell,
                            llms_ok=llms_ok, indexing=full and not local)
    depth = geo_depth.analyze(root_url, list(scope), sitemap_text)
    return GeoResult(total, band, cats, findings + depth["findings"], 0 if shell else words, view, notes, fixes, full,
                     page_map + depth["pages"], depth["citability"], depth["trust"], discovery, entities, agent_signals.homepage(root_html))
