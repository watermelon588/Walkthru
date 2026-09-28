"""Deterministic citation evidence. Retrieval is not attribution; unknown stays unknown."""

import ipaddress
import re
from urllib.parse import urlsplit, urlunsplit

VERSION = 2
MARKERS = re.compile(r"[【〖]([^】〗]+)[】〗]|\[(\d+)\]")
URLS = re.compile(r"https?://[^\s<>\[\]{}\"`]+", re.IGNORECASE)
DOMAINS = re.compile(r"(?<![\w@.-])(?:[a-z0-9-]+\.)+[a-z]{2,}(?![\w.-])", re.IGNORECASE)


def domain_of(url: str) -> str:
    try:
        host = (urlsplit(url if "://" in url else f"https://{url}").hostname or "").rstrip(".").encode("idna").decode().lower()
        if not host or any(c.isspace() for c in host):
            return ""
        return host.removeprefix("www.")
    except (ValueError, UnicodeError):
        return ""


def source_url(value: str) -> str:
    """Safe link syntax, without fetching provider URLs or following redirects."""
    if not isinstance(value, str) or len(value) > 2000:
        return ""
    try:
        p = urlsplit(value)
        host = p.hostname or ""
        if p.scheme not in ("http", "https") or p.username or p.password or not host or any(c.isspace() for c in value):
            return ""
        try:
            if not ipaddress.ip_address(host).is_global:
                return ""
        except ValueError:
            if "." not in host or host.endswith((".localhost", ".local", ".internal")):
                return ""
        return urlunsplit((p.scheme, p.netloc, p.path or "/", p.query, ""))
    except ValueError:
        return ""


def clean(answer: str) -> str:
    return re.sub(r"[ \t]+\n", "\n", MARKERS.sub("", answer or "")).strip()


def first(text: str, name: str, domain: str) -> int | None:
    """Match names in prose, and exact hosts/subdomains, never a URL path or suffix."""
    urls = list(URLS.finditer(text))
    prose = URLS.sub(lambda m: " " * len(m.group()), text)
    domains = list(DOMAINS.finditer(prose))
    prose = DOMAINS.sub(lambda m: " " * len(m.group()), prose)
    spots = []
    if name:
        match = re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", prose, re.IGNORECASE)
        if match:
            spots.append(match.start())
    if domain:
        domain = domain_of(domain)
        for match in urls + domains:
            host = domain_of(match.group().rstrip(".,;:!?)"))
            if host == domain or host.endswith("." + domain):
                spots.append(match.start())
    return min(spots) if spots else None


def source(url: str, title: str = "") -> dict | None:
    url = source_url(url)
    if not url:
        return None
    host = domain_of(url)
    redirect = host == "vertexaisearch.cloud.google.com"
    return {"url": url, "title": str(title or "")[:200], "domain": "" if redirect else host,
            "attribution": "unresolved" if redirect else "url", "cited": False, "evidence": []}


def groq_sources(message: dict) -> tuple[list[dict], str]:
    """Only explicit provider IDs or an answer URL establish a source reference.

    Groq's documented browser markers are not guaranteed array indices. Without an
    explicit ID mapping they remain unresolved rather than guessing from position.
    """
    answer = message.get("content") or ""
    sources: dict[str, dict] = {}
    ids: dict[str, set[str]] = {}
    searched = False
    for tool in message.get("executed_tools") or []:
        if tool.get("type") == "browser_search":
            searched = True
        for row in (tool.get("search_results") or {}).get("results") or []:
            item = source(row.get("url") or "", row.get("title") or "")
            if not item:
                continue
            sources.setdefault(item["url"], item)
            # Preserve IDs when supplied; never infer them from result order.
            for key in ("id", "citation_id"):
                if isinstance(row.get(key), (str, int)):
                    ids.setdefault(str(row[key]), set()).add(item["url"])
    # Unknown provider marker families cannot be interpreted as an absent citation.
    unresolved = "" in answer or "" in answer
    for marker in MARKERS.finditer(answer):
        reference = (marker.group(1) or marker.group(2)).split("†")[0]
        matches = ids.get(reference, set())
        if len(matches) != 1:
            unresolved = True
            continue
        item = sources[next(iter(matches))]
        item["cited"] = True
        item["evidence"].append({"kind": "provider_reference", "reference": marker.group(), "start": marker.start(), "end": marker.end()})
    for match in URLS.finditer(answer):
        url = source_url(match.group().rstrip(".,;:!?)"))
        if url in sources:
            sources[url]["cited"] = True
            sources[url]["evidence"].append({"kind": "answer_link", "reference": match.group(), "start": match.start(), "end": match.end()})
        else:
            unresolved = True
    status = "unresolved" if unresolved else "measured" if searched else "unavailable"
    return list(sources.values()), status


def gemini_sources(candidate: dict, grounded: bool) -> tuple[list[dict], str]:
    if not grounded:
        return [], "not_applicable"
    metadata = candidate.get("groundingMetadata") or {}
    chunks = metadata.get("groundingChunks") or []
    sources, by_index = [], {}
    for i, chunk in enumerate(chunks):
        web = chunk.get("web") or {}
        item = source(web.get("uri") or "", web.get("title") or "")
        if item:
            existing = next((s for s in sources if s["url"] == item["url"]), None)
            if existing is None:
                sources.append(item)
            by_index[i] = existing or item
    unresolved = False
    answer = "".join(p.get("text") or "" for p in (candidate.get("content") or {}).get("parts", []) if not p.get("thought"))
    supports = metadata.get("groundingSupports") or []
    for support in supports:
        segment = support.get("segment") or {}
        quote = segment.get("text") or ""
        # The quoted claim must actually occur in the saved answer.
        if not quote or quote not in answer:
            unresolved = True
            continue
        for index in support.get("groundingChunkIndices") or []:
            item = by_index.get(index) if type(index) is int else None
            if item is None:
                unresolved = True
                continue
            item["cited"] = True
            item["evidence"].append({"kind": "grounding_support", "reference": str(index), "quote": quote[:1000],
                                     "start": segment.get("startIndex"), "end": segment.get("endIndex")})
            if not item["domain"]:
                unresolved = True
        if not support.get("groundingChunkIndices"):
            unresolved = True
    status = "unresolved" if unresolved or (chunks and not supports) else "measured" if metadata else "unavailable"
    return sources, status


def analyze(answer: str, sources: list[dict], brand: str, domain: str, competitors: list[dict], *, citation_status: str = "unresolved") -> dict:
    rows = [{"name": brand, "domain": domain, "you": True}] + [dict(c, you=False) for c in competitors]
    positions = [first(clean(answer), r["name"], r.get("domain", "")) for r in rows]
    order = sorted((pos, i) for i, pos in enumerate(positions) if pos is not None)
    cited_domains = list(dict.fromkeys(s["domain"] for s in sources if s.get("cited") is True and s.get("domain")))
    for i, row in enumerate(rows):
        host = domain_of(row.get("domain", ""))
        rank = next((n for n, d in enumerate(cited_domains, 1) if host and (d == host or d.endswith("." + host))), None)
        row.update(mentioned=positions[i] is not None, mention_rank=next((n for n, (_, idx) in enumerate(order, 1) if idx == i), None),
                   cited=True if rank else False if citation_status == "measured" and host else None, source_rank=rank)
    return {"brands": rows, "sources": len(cited_domains), "citation_status": citation_status,
            "citation_eligible": citation_status == "measured", "measurement_version": VERSION}
