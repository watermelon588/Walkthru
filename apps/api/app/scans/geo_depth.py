"""Advisory GEO signals over HTML already fetched by the site audit.

Adapted from the MIT geo-optimizer-skill's signal taxonomy; see THIRD_PARTY.md.
These checks describe evidence, not a prediction of citations or rankings.
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter
from datetime import UTC, date, datetime
from urllib.parse import urlencode, urljoin, urlsplit
from xml.etree import ElementTree

import httpx
from selectolax.parser import HTMLParser

from app.agent.schema import Finding
from app.scans import fetch

INSTRUCTION = re.compile(r"ignore (?:all )?(?:previous|prior) instructions|forget (?:all )?(?:previous|prior) instructions|"
                         r"you are (?:chatgpt|an ai|an assistant)|system prompt|developer message", re.IGNORECASE)
CTA = re.compile(r"\b(?:sign up|start free|try free|buy now|book a demo|join now|subscribe|get started)\b", re.IGNORECASE)
WORD = re.compile(r"[a-z][a-z'-]{3,}", re.IGNORECASE)
STOP = {"about", "after", "also", "been", "from", "have", "more", "that", "their", "there", "these", "this",
        "those", "with", "your", "what", "when", "where", "which", "will", "would"}
NUMBER = re.compile(r"(?:\$|€|£)\s?\d[\d,.]*|\b\d[\d,.]*\s?(?:%|percent|million|billion|users|customers|teams)\b", re.IGNORECASE)
DEFINITION = re.compile(r"\b[A-Z][\w -]{2,45}\s+(?:is|means|refers to)\s+(?:an?\s+|the\s+)?\w", re.IGNORECASE)
VISIBLE_DATE = re.compile(r"\b20\d\d-\d\d-\d\d\b")
DISCOVERY = ("/.well-known/ai.txt", "/llms-full.txt")


def _date(value: str | None) -> date | None:
    if not value:
        return None
    match = VISIBLE_DATE.search(value)
    if not match:
        return None
    try:
        return date.fromisoformat(match.group())
    except ValueError:
        return None


def _sitemap_dates(xml: str) -> dict[str, date]:
    if not xml:
        return {}
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        return {}
    result: dict[str, date] = {}
    for item in root.iter():
        if item.tag.rsplit("}", 1)[-1] != "url":
            continue
        fields = {child.tag.rsplit("}", 1)[-1]: child.text for child in item}
        changed = _date(fields.get("lastmod"))
        if fields.get("loc") and changed:
            result[fields["loc"]] = changed
    return result


def _json_dates(tree: HTMLParser) -> list[date]:
    dates: list[date] = []
    for node in tree.css('script[type="application/ld+json"]'):
        try:
            data = json.loads(node.text() or "")
        except ValueError:
            continue
        pending = [data]
        while pending:
            item = pending.pop()
            if isinstance(item, list):
                pending.extend(item)
            elif isinstance(item, dict):
                changed = _date(item.get("dateModified") if isinstance(item.get("dateModified"), str) else None)
                if changed:
                    dates.append(changed)
                pending.extend(item.values())
    return dates


def _external_sources(tree: HTMLParser, url: str) -> list[str]:
    host = (urlsplit(url).hostname or "").removeprefix("www.")
    sources = []
    for node in tree.css("main a[href], article a[href]"):
        target = urljoin(url, node.attributes.get("href") or "")
        other = (urlsplit(target).hostname or "").removeprefix("www.")
        if other and other != host and not other.endswith("." + host) and other not in sources:
            sources.append(other)
    return sources


def _same_domain(a: str, b: str) -> bool:
    return (urlsplit(a).hostname or "").lower().removeprefix("www.") == (urlsplit(b).hostname or "").lower().removeprefix("www.")


def _wikidata(name: str, root_url: str) -> dict:
    """Match a named entity by its P856 official website, never by a same-name search hit alone."""
    base = "https://www.wikidata.org/w/api.php"
    with fetch.client(timeout=3) as client:
        query = base + "?" + urlencode({"action": "wbsearchentities", "search": name, "language": "en", "format": "json", "limit": 5})
        found = fetch.get(client, query, same_origin=fetch.origin(base))
        if found is None or found.status_code != 200:
            return {"status": "unavailable"}
        ids = [item.get("id") for item in found.json().get("search", []) if isinstance(item.get("id"), str)]
        if not ids:
            return {"status": "no_match"}
        details = base + "?" + urlencode({"action": "wbgetentities", "ids": "|".join(ids), "props": "claims", "format": "json"})
        response = fetch.get(client, details, same_origin=fetch.origin(base))
        if response is None or response.status_code != 200:
            return {"status": "unavailable"}
        for entity_id, entity in response.json().get("entities", {}).items():
            for claim in entity.get("claims", {}).get("P856", []):
                website = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
                if isinstance(website, str) and _same_domain(website, root_url):
                    return {"status": "matched", "url": f"https://www.wikidata.org/wiki/{entity_id}"}
        return {"status": "no_match"}


def _knowledge_graph(name: str, root_url: str, key: str) -> dict:
    url = "https://kgsearch.googleapis.com/v1/entities:search?" + urlencode({"query": name, "limit": 5, "key": key})
    with fetch.client(timeout=3) as client:
        response = fetch.get(client, url, same_origin=fetch.origin(url))
        if response is None or response.status_code != 200:
            return {"status": "unavailable"}
        for item in response.json().get("itemListElement", []):
            entity = item.get("result", {})
            if isinstance(entity.get("url"), str) and _same_domain(entity["url"], root_url):
                return {"status": "matched", "url": entity.get("@id", "")}
        return {"status": "no_match"}


def collect_remote(root_url: str, html: str, client: httpx.Client, *, full: bool, local: bool) -> dict:
    """Two same-origin discovery reads and optional free entity lookups. Failures never affect readiness."""
    if local:
        return {"discovery": {}, "entities": {}}
    base = fetch.origin(root_url)
    tree = HTMLParser(html)
    named = tree.css_first('meta[property="og:site_name"]')
    name = (named.attributes.get("content") or "").strip() if named else ""
    discovery: dict[str, bool | None] = {}
    for path in DISCOVERY:
        response = fetch.get(client, base + path, same_origin=base)
        if response is None:
            discovery[path] = None
        else:
            content_type = response.headers.get("content-type", "")
            discovery[path] = response.status_code == 200 and "html" not in content_type.lower() and bool(response.text.strip())
    entities: dict[str, dict] = {}
    if full and not fetch.is_local_site(root_url) and name and name.lower() not in {"home", "your site", "untitled"}:
        try:
            entities["wikidata"] = _wikidata(name, root_url)
        except (ValueError, TypeError, AttributeError, httpx.HTTPError):
            entities["wikidata"] = {"status": "unavailable"}
        key = os.environ.get("GOOGLE_KG_API_KEY")
        if key:
            try:
                entities["knowledge_graph"] = _knowledge_graph(name, root_url, key)
            except (ValueError, TypeError, AttributeError, httpx.HTTPError):
                entities["knowledge_graph"] = {"status": "unavailable"}
    return {"discovery": discovery, "entities": entities}


def analyze(root_url: str, pages: list[tuple[str, str]], sitemap_text: str = "") -> dict:
    """Per-page citation evidence plus bounded, explainable advisory findings."""
    sitemap_dates = _sitemap_dates(sitemap_text)
    findings: list[Finding] = []
    page_map: list[tuple[str, str, list[str]]] = []
    citability: list[dict] = []
    issues: dict[str, tuple[str, str, str, list[str]]] = {}

    def issue(title: str, severity: str, detail: str, fix: str, url: str) -> None:
        if title not in issues:
            issues[title] = (severity, detail, fix, [])
        issues[title][3].append(url)

    for url, html in pages:
        if fetch.is_js_shell(html):
            continue
        tree = HTMLParser(html)
        body = tree.css_first("main") or tree.css_first("article") or tree.body
        if body is None:
            continue
        prose = body.text(separator=" ").strip()
        words = prose.split()
        sources = _external_sources(tree, url)
        stat = bool(NUMBER.search(prose)) and bool(sources)
        quote = any(node.attributes.get("cite") or node.css_first("cite") or node.parent and node.parent.css_first("cite")
                    for node in tree.css("blockquote"))
        definition = bool(tree.css("dfn")) or bool(DEFINITION.search(prose))
        comparison = any(len(table.css("tr")) >= 2 and table.css_first("th") for table in tree.css("table"))
        signals = {"statistics_with_sources": stat, "attributed_quote": quote, "definition": definition,
                   "comparison_table": comparison}
        headings = tree.css("h2, h3")
        question = any(h.text(strip=True).endswith("?") for h in headings)
        answer_first = any((h.next is not None and h.next.tag == "p" and 15 <= len(h.next.text().split()) <= 100)
                           for h in headings)
        rag = {"standalone_sections": len(headings) >= 2 and len(words) / len(headings) <= 300,
               "question_headings": question, "answer_first": answer_first}
        dated = _json_dates(tree)
        dated += [d for n in tree.css("time") if (d := _date(n.attributes.get("datetime") or n.text()))]
        dated += [d for n in tree.css("main, article") if (d := _date(n.text()[:20000]))]
        if url in sitemap_dates:
            dated.append(sitemap_dates[url])
        latest = max(dated) if dated else None
        citability.append({"url": url, "score": 25 * sum(signals.values()), "signals": signals, "rag": rag,
                           "last_updated": latest.isoformat() if latest else None})

        if len(words) >= 100:
            ctas = [n for n in body.css("a, button") if CTA.search(n.text(strip=True) or "")]
            if len(ctas) >= 8:
                issue("Too many calls to action", "low", f"The main content repeats {len(ctas)} calls to action, crowding out explanation.",
                      "Keep one clear primary action per section and give the product explanation room.", url)
            tokens = [w.lower() for w in WORD.findall(prose) if w.lower() not in STOP]
            if tokens:
                top, count = Counter(tokens).most_common(1)[0]
                if count / len(tokens) > 0.20:
                    issue("A keyword dominates the page", "low", f'"{top}" makes up more than one fifth of meaningful words.',
                          "Use plain, varied wording instead of repeating a keyword.", url)
            if tree.body and len(body.text(separator=" ").split()) < 0.25 * len(tree.body.text(separator=" ").split()):
                issue("Page is mostly boilerplate", "low", "Navigation and repeated framing outweigh the main content.",
                      "Add a self-contained explanation in the main content area.", url)
        if len(words) >= 250 and headings and not rag["answer_first"]:
            issue("Sections lack an answer near the heading", "low", "Long sections do not open with a self-contained answer.",
                  "Start important sections with a 15 to 100 word paragraph that answers the heading.", url)
        if latest and (datetime.now(UTC).date() - latest).days > 730 and re.search(r"article|blog|news|changelog|pricing", url, re.IGNORECASE):
            issue("Time-sensitive page has an old date", "low", f"The newest visible or structured date is {latest.isoformat()}.",
                  "Review the page, update changed claims and mark its real modification date.", url)
        hidden = [n.text(separator=" ") for n in tree.css("[hidden], [aria-hidden='true'], [style*='display:none'], [style*='display: none']")]
        comments = re.findall(r"<!--([\s\S]*?)-->", html)
        if any(INSTRUCTION.search(text) for text in hidden + comments):
            issue("Hidden instructions aimed at AI assistants", "medium", "Hidden text or an HTML comment tells an AI assistant to change its instructions.",
                  "Remove instructions aimed at crawlers or assistants from hidden content and comments.", url)

    for title, (severity, detail, fix, urls) in issues.items():
        unique = list(dict.fromkeys(urls))
        findings.append(Finding(kind="geo", severity=severity, title=title, detail=detail[:600], fix=fix[:400],
                                evidence=", ".join(unique[:3])[:300]))
        page_map.append(("geo", title, unique))

    root = HTMLParser(pages[0][1]) if pages else HTMLParser("")
    title = root.css_first("title")
    name = root.css_first('meta[property="og:site_name"]')
    brand = (name.attributes.get("content") or "").strip() if name else ""
    root_sources = _external_sources(root, root_url)
    root_text = root.body.text(separator=" ") if root.body else ""
    trust = {"identity": bool(brand or root.css_first('script[type="application/ld+json"]')),
             "social_proof": bool(re.search(r"testimonials?|reviews?|case studies|trusted by", root_text, re.IGNORECASE)),
             "external_sources": bool(root_sources),
             "name_consistency": bool(brand and title and brand.lower() in title.text(strip=True).lower())}
    return {"findings": findings, "pages": page_map, "citability": citability, "trust": trust}
