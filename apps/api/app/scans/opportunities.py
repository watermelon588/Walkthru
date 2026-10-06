"""Keyword and content direction in prelaunch advisory mode (R-S17): a page/intent map built only from the audited
public pages' own copy. Contract: docs/keyword-opportunities.md.

No search demand data exists in this mode, so nothing here states search volume, keyword difficulty, rank, traffic
or a forecast. Intents are hypotheses read from each page's main heading or title, quoted exactly. Proposed titles,
descriptions and outlines only rearrange the page's own words; they add no product claims. A page's lack of search
data is expected before launch, not a defect, so this map never creates findings or lowers a score.
"""

import re

from selectolax.parser import HTMLParser

MODE = "prelaunch_advisory"
MAX_PAGES = 10
BASIS = ("Built from the audited public pages' own copy. No search volume, keyword difficulty, rank or traffic data "
         "was used or estimated; intents are hypotheses to confirm against what customers actually search.")
MEASUREMENT = ("After a change ships, compare clicks and impressions for that page over the 28 days before and after, "
               "once Search Console is connected. Until then, check that the page is indexed and its snippet reads well.")
_STOP = {  # common words; shorter ones never match the 4-letter minimum
    "about", "after", "again", "also", "another", "because", "been", "before", "being", "both", "could", "does",
    "each", "free", "from", "have", "having", "here", "home", "into", "just", "made", "make", "more", "most", "much",
    "need", "only", "other", "ours", "over", "page", "same", "should", "some", "such", "than", "that", "their",
    "them", "then", "there", "these", "they", "this", "those", "through", "under", "using", "very", "welcome",
    "what", "when", "where", "which", "while", "with", "without", "would", "your", "yours",
}
_SPACE = re.compile(r"\s+")


def _text(node) -> str:
    return _SPACE.sub(" ", node.text(separator=" ", strip=True)).strip() if node else ""


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9][a-z0-9'-]{3,}", text.lower()) if w not in _STOP}


def _sentence(text: str, limit: int = 200) -> str:
    """The first sentence of page copy, cut at a word boundary. Quoted, never rewritten."""
    first = re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0]
    if len(first) <= limit:
        return first
    return first[:limit].rsplit(" ", 1)[0]


def facts(url: str, html: str, links: list[str]) -> dict:
    """What one page says about itself: title, description, headings, first paragraph, internal links, body words."""
    tree = HTMLParser(html)
    robots = tree.css_first('meta[name="robots"]')
    noindex = "noindex" in ((robots.attributes.get("content") or "").lower() if robots else "")
    desc = tree.css_first('meta[name="description"]')
    for node in tree.css("script, style, noscript, template, svg"):
        node.decompose()
    paragraph = next((t for t in (_text(p) for p in tree.css("main p, article p, p")) if len(t) >= 40), "")
    return {
        "url": url, "noindex": noindex,
        "title": _text(tree.css_first("title"))[:300] or None,
        "description": ((desc.attributes.get("content") or "").strip()[:500] or None) if desc else None,
        "h1": [t[:200] for t in (_text(h) for h in tree.css("h1")) if t][:3],
        "h2": [t[:200] for t in (_text(h) for h in tree.css("h2")) if t][:6],
        "paragraph": paragraph[:600],
        "links": links,
        "words": _words(_text(tree.body)[:6000]) if tree.body else set(),
    }


def _key(text: str | None) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", (text or "").lower()))


def build(pages: list[tuple[str, str, list[str]]]) -> dict:
    """The advisory map for the audited pages: (url, html, internal links on that page), in crawl order."""
    seen = [facts(url, html, links) for url, html, links in pages]
    eligible = [p for p in seen if not p["noindex"]]
    inbound = {p["url"]: [q["url"] for q in eligible if q is not p and p["url"] in q["links"]] for p in eligible}
    titles: dict[str, list[str]] = {}
    for p in eligible:
        if p["title"]:
            titles.setdefault(_key(p["title"]), []).append(p["url"])
    intents: dict[str, list[str]] = {}
    entries = []
    for order, p in enumerate(eligible):
        heading = p["h1"][0] if p["h1"] else None
        intent = {"text": heading, "source": "h1"} if heading else {"text": p["title"], "source": "title"} if p["title"] else None
        if intent:
            intents.setdefault(_key(intent["text"]), []).append(p["url"])
        duplicate_title = bool(p["title"]) and len(titles.get(_key(p["title"]), [])) > 1
        gaps, score = [], 0
        if not p["title"]:
            gaps.append("No title element.")
            score += 3
        if not heading:
            gaps.append("No main heading (h1) stating the page topic.")
            score += 2
        if duplicate_title:
            gaps.append(f'The title "{p["title"]}" is shared with {len(titles[_key(p["title"])]) - 1} other audited page(s).')
            score += 2
        if not p["description"]:
            gaps.append("No meta description; search engines and link previews will pick page text.")
            score += 1
        if not p["h2"]:
            gaps.append("No section headings (h2), so the page has no outline of what it answers.")
            score += 1
        if order and not inbound[p["url"]]:
            gaps.append("No other audited page links here.")
            score += 2
        target = _words(intent["text"]) if intent else set()
        suggested = [q["url"] for q in eligible if q is not p and p["url"] not in q["links"] and len(target & q["words"]) >= 2][:3]
        if order and eligible[0] is not p and p["url"] not in eligible[0]["links"] and eligible[0]["url"] not in suggested:
            suggested = [eligible[0]["url"], *suggested][:3]  # the homepage is the strongest internal link source
        proposed_title = heading if not p["title"] and heading else (f"{heading} | {p['title']}" if duplicate_title and heading and _key(heading) != _key(p["title"]) else None)
        proposed_description = _sentence(p["paragraph"]) if not p["description"] and p["paragraph"] else None
        entries.append({
            "url": p["url"], "score": score, "order": order,
            "primary_intent": intent,
            "supporting": [{"text": h, "source": "h2"} for h in p["h2"] if _key(h) != _key(heading)][:5],
            "current": {"title": p["title"], "description": p["description"], "h1": p["h1"]},
            "proposed": {"title": proposed_title, "description": proposed_description, "outline": ([heading] if heading else []) + p["h2"][:6],
                         "basis": "Rearranged from this page's own title, headings and first paragraph; confirm it describes the page accurately."},
            "gaps": gaps,
            "internal_links": {"inbound_from": inbound[p["url"]], "suggested_from": suggested},
            "next_action": _next_action(p, intent, gaps, suggested, proposed_title, proposed_description),
            "effort": "low" if all(g.startswith(("No title", "The title", "No meta")) for g in gaps) else "medium",
        })
    entries.sort(key=lambda e: (-e["score"], e["order"]))
    for e in entries:
        del e["score"], e["order"]
    overlaps = [{"intent": next(e["primary_intent"]["text"] for e in entries if e["url"] == urls[0]), "pages": urls,
                 "note": "These pages share the same main heading or title. Decide which one should answer it before treating this as competition between them."}
                for urls in intents.values() if len(urls) > 1]
    return {"mode": MODE, "demand_data": "none", "basis": BASIS, "measurement": MEASUREMENT,
            "pages_considered": len(eligible), "excluded_noindex": [p["url"] for p in seen if p["noindex"]],
            "pages": entries[:MAX_PAGES], "overlaps": overlaps}


def _next_action(page, intent, gaps, suggested, proposed_title, proposed_description) -> str:
    if not intent:
        return "Add a title and one main heading that say what this page is for; the map cannot read a topic without them."
    if proposed_title:
        return f'Set the title to "{proposed_title}", built from this page\'s own heading.'
    if proposed_description:
        return f'Add a meta description using the page\'s first sentence: "{proposed_description}".'
    if suggested:
        return f'Link to this page from {suggested[0]} with words from its heading, "{intent["text"]}".'
    if not page["h2"]:
        return "Add section headings (h2) for the questions this page answers."
    return f'Keep this page as the answer for "{intent["text"]}" and measure it once search data exists.'


def lines(advice: dict) -> list[str]:
    """The map as text, shared by the Keywords chapter prompt and MCP get_report(section="keywords")."""
    out = [f"Mode: {advice['mode']} (no search demand data). {advice['basis']}", f"Measurement: {advice['measurement']}", ""]
    for n, page in enumerate(advice["pages"], start=1):
        intent = page["primary_intent"]
        current = page["current"]
        out += [f"### {n}. {page['url']}",
                f"Intent hypothesis: \"{intent['text']}\" (from its {intent['source']})" if intent else "Intent hypothesis: none readable on this page",
                f"Current title: \"{current['title']}\"" if current["title"] else "Current title: none",
                f"Current description: \"{current['description']}\"" if current["description"] else "Current description: none"]
        out += [f"Proposed title: \"{page['proposed']['title']}\"" for _ in [0] if page["proposed"]["title"]]
        out += [f"Proposed description: \"{page['proposed']['description']}\"" for _ in [0] if page["proposed"]["description"]]
        out += [f"Outline from its headings: {' / '.join(page['proposed']['outline'])}" for _ in [0] if page["proposed"]["outline"]]
        out += [f"Gap: {gap}" for gap in page["gaps"]]
        links = page["internal_links"]
        out += [f"Linked from: {', '.join(links['inbound_from']) or 'no other audited page'}"
                + (f". Suggested link sources: {', '.join(links['suggested_from'])}" if links["suggested_from"] else ""),
                f"Next action ({page['effort']} effort): {page['next_action']}", ""]
    out += [f"Same main topic on several pages: \"{o['intent']}\" on {', '.join(o['pages'])}. {o['note']}" for o in advice["overlaps"]]
    return out
