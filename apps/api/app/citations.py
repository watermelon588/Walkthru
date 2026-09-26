"""AI citation tracking (P3.2): ask AI the owner's prompts, then measure in code whether the answer names the site,
cites it, and how it stands against named competitors (mentions, citations, share of voice).

Engines, on free quotas only (ROADMAP build rule 2), measured on 2026-09-26:
- web: Groq gpt-oss-120b with its built-in browser_search tool. One search per prompt, about 3 s.
  The answer comes with the pages it searched, so citations are real. 1,600 to 7,600 tokens per answer.
- memory: Gemini without web search (Google Search grounding needs a billed key; free keys get quota 0 for it).
  It shows whether the model knows the brand, so mentions and share of voice only, labelled as such.
  With GEMINI_GROUNDING=1 and a billed key it searches Google and returns sources too.
ChatGPT and Perplexity are "not measured" until revenue pays for their APIs (SPEC.md).

Nothing here promises citations or rankings: it reports what those engines said on the day (SPEC.md honesty rule).
Data model adapted from ai-search-guru/getcito (MIT): prompts, answers, mentions, citations, share of voice.
"""

from __future__ import annotations

import logging
import os
import re
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit

import httpx
from selectolax.parser import HTMLParser

from app import db, notify, plans

log = logging.getLogger("walkthru.citations")

WEB_MODEL = os.environ.get("CITATION_WEB_MODEL", "openai/gpt-oss-120b")
GEMINI_MODELS = [m.strip() for m in os.environ.get("CITATION_GEMINI_MODELS", "gemini-3.1-flash-lite,gemini-3.5-flash").split(",") if m.strip()]
GEMINI_URL = os.environ.get("CITATION_GEMINI_URL", "https://generativelanguage.googleapis.com/v1beta")
GROQ_URL = os.environ.get("CITATION_GROQ_URL", "https://api.groq.com/openai/v1")
# Shared free quotas: journeys use the same Groq model, so tracking takes a capped share (counted in the database).
# A web answer measured 1,600 to 7,600 tokens (2026-09-26); Groq's free tier allows 8,000 tokens a minute per model and
# a daily token budget that journeys need most, so web checks run a minute apart and 20 a day by default. Raise both
# when the Groq plan does.
DAILY = {"web": int(os.environ.get("CITATION_WEB_PER_DAY", "20")), "memory": int(os.environ.get("CITATION_MEMORY_PER_DAY", "300"))}
WEB_GAP_S = float(os.environ.get("CITATION_WEB_GAP_S", "60"))
MAX_ATTEMPTS = 4
EVERY = timedelta(days=7)
MANUAL_EVERY = timedelta(hours=20)  # one "Check now" a day per site
MAX_COMPETITORS = 5
ENGINE_LABEL = {"web": "AI with web search (gpt-oss-120b)", "memory": "Gemini, from memory"}
NOT_MEASURED = ["ChatGPT", "Perplexity"]


@dataclass(frozen=True)
class Limit:
    sites: int
    prompts: int
    engines: tuple[str, ...]
    weekly: bool
    batches_per_pass: int | None = None  # Launch Pack: one snapshot per pass


# Proposed in tasks/todo.md P3.2 (founder confirms plan allocation): none on Free.
LIMITS = {
    "launch": Limit(sites=1, prompts=10, engines=("web",), weekly=False, batches_per_pass=1),
    "pro": Limit(sites=2, prompts=10, engines=("web",), weekly=True),
    "plus": Limit(sites=5, prompts=25, engines=("web", "memory"), weekly=True),
}


def limit_for(user_id: str) -> Limit | None:
    return LIMITS.get(plans.current(user_id)["plan"].name)


def gemini_key() -> str | None:
    return os.environ.get("CITATION_GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or None


def grounded() -> bool:
    return os.environ.get("GEMINI_GROUNDING") == "1"


def label(engine: str) -> str:
    return "Gemini with Google Search" if engine == "memory" and grounded() else ENGINE_LABEL[engine]


# ---------- names and domains ----------


def domain_of(url: str) -> str:
    host = (urlsplit(url if "://" in url else f"https://{url}").hostname or "").lower().rstrip(".")
    return host.removeprefix("www.")


_DOMAIN = re.compile(r"\b((?:[a-z0-9-]+\.)+[a-z]{2,})\b", re.IGNORECASE)


def parse_competitor(text: str) -> dict | None:
    """ "Notion (notion.so)", "notion.so" or "Notion": a name and, when given, a domain. """
    text = " ".join(text.split())[:120]
    if not text:
        return None
    found = _DOMAIN.search(text)
    domain = domain_of(found.group(1)) if found else ""
    name = re.sub(r"\(.*?\)|https?://\S+", "", text).strip(" -,") if found else text
    if not name or name.lower() == domain or (found and name == found.group(1)):
        name = domain.split(".")[0].capitalize() if domain else text
    return {"name": name[:60], "domain": domain}


# ---------- analysis, all in code ----------

_MARKERS = re.compile(r"【[^】]*】|\[\d+\]")  # gpt-oss citation marks like 【1†L35-L43】


def clean(answer: str) -> str:
    return re.sub(r"[ \t]+\n", "\n", _MARKERS.sub("", answer or "")).strip()


def _first(text: str, name: str, domain: str) -> int | None:
    """Where the answer first names this brand (its name as a word, or its domain), or None."""
    spots = []
    if name:
        m = re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", text, re.IGNORECASE)
        if m:
            spots.append(m.start())
    if domain:
        i = text.lower().find(domain)
        if i >= 0:
            spots.append(i)
    return min(spots) if spots else None


def _source_rank(sources: list[dict], domain: str) -> int | None:
    if not domain:
        return None
    seen: list[str] = []
    for s in sources:
        d = s.get("domain") or ""
        if d and d not in seen:
            seen.append(d)
    for i, d in enumerate(seen, start=1):
        if d == domain or d.endswith("." + domain):
            return i
    return None


def analyze(answer: str, sources: list[dict], brand: str, domain: str, competitors: list[dict]) -> dict:
    """Mention, citation and rank for the site and each competitor, from the answer text and the sources."""
    text = clean(answer)
    rows = [{"name": brand, "domain": domain, "you": True}] + [{"name": c["name"], "domain": c.get("domain", ""), "you": False} for c in competitors]
    first = {r["name"]: _first(text, r["name"], r["domain"]) for r in rows}
    order = sorted((pos, name) for name, pos in first.items() if pos is not None)
    out = []
    for r in rows:
        rank = _source_rank(sources, r["domain"])
        out.append({"name": r["name"], "domain": r["domain"], "you": r["you"], "mentioned": first[r["name"]] is not None,
                    "mention_rank": next((i for i, (_, n) in enumerate(order, start=1) if n == r["name"]), None),
                    "cited": rank is not None, "source_rank": rank})
    return {"brands": out, "sources": len({s.get("domain") for s in sources if s.get("domain")})}


def share_of_voice(checks: list[dict]) -> list[dict]:
    """Per brand: share of all brand mentions across these answers, and how many answers named or cited it."""
    tally: dict[str, dict] = {}
    for c in checks:
        for b in (c.get("result") or {}).get("brands", []):
            t = tally.setdefault(b["name"], {"name": b["name"], "domain": b["domain"], "you": b["you"], "mentions": 0, "citations": 0})
            t["mentions"] += 1 if b["mentioned"] else 0
            t["citations"] += 1 if b["cited"] else 0
    total = sum(t["mentions"] for t in tally.values())
    for t in tally.values():
        t["share"] = round(100 * t["mentions"] / total) if total else 0
        t["answers"] = len(checks)
    return sorted(tally.values(), key=lambda t: (-t["mentions"], not t["you"], t["name"]))


def brand_from(html: str, domain: str) -> str:
    """The site's own name: og:site_name, else the title part that matches the domain, else the domain's first label."""
    tree = HTMLParser(html or "")
    og = tree.css_first('meta[property="og:site_name"]')
    if og and (og.attributes.get("content") or "").strip():
        return (og.attributes.get("content") or "").strip()[:80]
    label = domain.split(".")[0]
    title = (tree.css_first("title").text() if tree.css_first("title") else "").strip()
    for part in re.split(r"\s[|\-:–—]\s|\s*[|–—]\s*", title):
        if part.strip() and label.replace("-", "") in part.lower().replace(" ", "").replace("-", ""):
            return part.strip()[:80]
    return label.replace("-", " ").title()[:80] or domain


# ---------- prompt suggestions, in code ----------


def suggest(html: str, brand: str, competitors: list[dict]) -> list[str]:
    """Questions a buyer would ask an AI, built from the homepage's own words. The owner edits them."""
    tree = HTMLParser(html or "")
    title = (tree.css_first("title").text() if tree.css_first("title") else "").strip()
    h1 = (tree.css_first("h1").text() if tree.css_first("h1") else "").strip()
    meta = tree.css_first('meta[name="description"]')
    description = ((meta.attributes.get("content") if meta else "") or "").strip()
    # The category is the title or h1 without the brand name: "Acme | Notes for small teams" -> "notes for small teams".
    category = ""
    for text in (title, h1, description):
        parts = [p.strip() for p in re.split(r"\s[|\-:–—]\s|\s*[|–—]\s*", text) if p.strip()]
        parts = [p for p in parts if brand.lower() not in p.lower()] or parts
        if parts and 2 <= len(parts[0].split()) <= 10:
            category = parts[0].rstrip(".").lower()
            break
    category = category or "tools like this"
    prompts = [f"What are the best {category}?", f"Which {category} do people recommend, and why?", f"How do I choose {category}?",
               f"What is {brand}?", f"Is {brand} worth it?"]
    for c in competitors[:3]:
        prompts += [f"What are the best alternatives to {c['name']}?", f"{brand} vs {c['name']}: which is better?"]
    return list(dict.fromkeys(p[:300] for p in prompts))


# ---------- engines ----------


class Busy(Exception):
    """The engine's free quota is used up for now: the check stays queued and runs later."""


WEB_SYSTEM = ("Answer the person's question the way an AI search assistant would. Search the web once with browser_search, then answer "
              "from the results only. Do not open pages. Recommend specific products or companies by name. Keep it under 150 words.")
MEMORY_SYSTEM = ("Answer the person's question the way an AI assistant would, from what you know. Recommend specific products or "
                 "companies by name. Keep it under 150 words.")


def ask_web(prompt: str) -> dict:
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY is not set")
    r = httpx.post(f"{GROQ_URL}/chat/completions", headers={"Authorization": f"Bearer {key}"}, timeout=httpx.Timeout(60, connect=5),
                   json={"model": WEB_MODEL, "reasoning_effort": "low", "tools": [{"type": "browser_search"}],
                         "messages": [{"role": "system", "content": WEB_SYSTEM}, {"role": "user", "content": prompt}]})
    if r.status_code == 429:
        raise Busy("groq rate limit")
    r.raise_for_status()
    body = r.json()
    msg = body["choices"][0]["message"]
    sources, seen = [], set()
    for tool in msg.get("executed_tools") or []:
        for res in ((tool.get("search_results") or {}).get("results") or []):
            url = res.get("url") or ""
            if url.startswith("http") and url not in seen:
                seen.add(url)
                sources.append({"url": url[:500], "title": (res.get("title") or "")[:200], "domain": domain_of(url)})
    return {"answer": (msg.get("content") or "")[:6000], "sources": sources[:20], "tokens": (body.get("usage") or {}).get("total_tokens", 0), "model": WEB_MODEL}


def ask_memory(prompt: str) -> dict:
    key = gemini_key()
    if not key:
        raise RuntimeError("no Gemini key")
    body = {"systemInstruction": {"parts": [{"text": MEMORY_SYSTEM}]}, "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 700}} | ({"tools": [{"google_search": {}}]} if grounded() else {})
    busy = False
    for model in GEMINI_MODELS:
        r = httpx.post(f"{GEMINI_URL}/models/{model}:generateContent", headers={"x-goog-api-key": key}, json=body, timeout=httpx.Timeout(45, connect=5))
        if r.status_code == 429:
            busy = True
            continue
        if r.status_code >= 400:
            log.warning("citations: %s answered %s", model, r.status_code)
            continue
        data = r.json()
        cand = (data.get("candidates") or [{}])[0]
        answer = "".join(str(p.get("text") or "") for p in ((cand.get("content") or {}).get("parts") or []) if not p.get("thought")).strip()
        if not answer:
            continue
        sources = [{"url": (ch.get("web") or {}).get("uri", "")[:500], "title": (ch.get("web") or {}).get("title", "")[:200],
                    "domain": domain_of((ch.get("web") or {}).get("title", ""))} for ch in (cand.get("groundingMetadata") or {}).get("groundingChunks", [])]
        return {"answer": answer[:6000], "sources": [s for s in sources if s["domain"]][:20],
                "tokens": (data.get("usageMetadata") or {}).get("totalTokenCount", 0), "model": model}
    if busy:
        raise Busy("gemini quota")
    raise RuntimeError("no Gemini model answered")


ENGINES = {"web": ask_web, "memory": ask_memory}


# ---------- batches, the queue and the schedule ----------


def queue_batch(site: dict, prompts: list[dict], engines: tuple[str, ...]) -> str:
    batch = str(uuid.uuid4())
    db.add_citation_checks([{"site_id": site["id"], "batch_id": batch, "prompt_id": p["id"], "prompt": p["prompt"], "engine": e}
                            for p in prompts for e in engines])
    db.update_citation_site(site["id"], {"last_batch_at": datetime.now(UTC).isoformat()})
    return batch


def _day_start() -> str:
    return datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


def process(max_checks: int = 30, sleep=time.sleep) -> int:
    """Run queued checks in order, within each engine's daily cap. Returns how many finished."""
    done = 0
    used = {e: db.citation_checks_done_since(e, _day_start()) for e in ENGINES}
    busy: set[str] = set()
    last_web = 0.0
    for check in db.queued_citation_checks(limit=max_checks * 2):
        engine = check["engine"]
        if done >= max_checks or engine in busy or used[engine] >= DAILY[engine]:
            continue  # stays queued: tomorrow's quota, or the next pass
        if not db.claim_citation_check(check["id"], check["attempts"]):
            continue
        site = db.citation_site(check["site_id"])
        if site is None:
            continue
        if engine == "web" and last_web:
            sleep(max(0.0, WEB_GAP_S - (time.monotonic() - last_web)))
        try:
            got = ENGINES[engine](check["prompt"])
            if engine == "web":
                last_web = time.monotonic()
            result = analyze(got["answer"], got["sources"], site["brand"], domain_of(site["site"]), site.get("competitors") or [])
            db.finish_citation_check(check["id"], {"status": "done", "answer": clean(got["answer"]), "sources": got["sources"], "result": result,
                                                   "tokens": got["tokens"], "model": got["model"]})
            used[engine] += 1
            done += 1
        except Busy:
            busy.add(engine)  # keep it queued; this engine rests until the next pass
            if check["attempts"] + 1 >= MAX_ATTEMPTS:
                db.finish_citation_check(check["id"], {"status": "failed", "answer": "The engine's free quota was busy every time we tried."})
        except Exception:  # one broken answer must not stop the queue
            log.warning("citation check %s failed", check["id"], exc_info=True)
            if check["attempts"] + 1 >= MAX_ATTEMPTS:
                db.finish_citation_check(check["id"], {"status": "failed", "answer": "The engine did not answer."})
        _maybe_announce(check)
    return done


def _maybe_announce(check: dict) -> None:
    """When the last check of a batch finishes, tell the owner (sidebar count and a toast)."""
    try:
        batch = [c for c in db.citation_checks_for(check["site_id"], limit=200) if c["batch_id"] == check["batch_id"]]
        if batch and all(c["status"] != "queued" for c in batch):
            site = db.citation_site(check["site_id"])
            done = [c for c in batch if c["status"] == "done"]
            named = sum(1 for c in done if any(b["you"] and b["mentioned"] for b in (c.get("result") or {}).get("brands", [])))
            notify.send(site["user_id"], "visibility", "citations.done", f"AI answers checked for {site['brand']}"[:200],
                        f"Named in {named} of {len(done)} answers.", "/app/visibility")
    except Exception:
        log.warning("citation batch notice failed", exc_info=True)


def run_due() -> int:
    """Queue the weekly batch for every site whose week is up, while the owner's plan includes weekly checks."""
    queued = 0
    now = datetime.now(UTC)
    for site in db.due_citation_sites(now.isoformat()):
        try:
            lim = limit_for(str(site["user_id"]))
            if not lim or not lim.weekly:
                db.update_citation_site(site["id"], {"next_check_at": None})  # lapsed plan: keep the data, stop checking
                continue
            prompts = db.citation_prompts(site["id"])[: lim.prompts]
            if prompts:
                queue_batch(site, prompts, lim.engines)
                queued += 1
            db.update_citation_site(site["id"], {"next_check_at": (now + EVERY).isoformat()})
        except Exception:
            log.warning("citation schedule failed for %s", site.get("site"), exc_info=True)
    return queued


def start_background() -> None:
    """Every minute: queue due weekly batches, then work the queue. ponytail: one thread per API process, like watch."""
    def loop() -> None:
        stop = threading.Event()
        stop.wait(30)
        while True:
            try:
                run_due()
                process()
            except Exception:
                log.warning("citation pass failed", exc_info=True)
            stop.wait(60)

    threading.Thread(target=loop, name="citations", daemon=True).start()


# ---------- what the page shows ----------


def summary(site: dict) -> dict:
    checks = db.citation_checks_for(site["id"], since=(datetime.now(UTC) - timedelta(days=120)).isoformat())
    batches: dict[str, list[dict]] = {}
    for c in checks:
        batches.setdefault(c["batch_id"], []).append(c)
    ordered = sorted(batches.values(), key=lambda b: min(c["created_at"] for c in b), reverse=True)
    latest = ordered[0] if ordered else []
    done = [c for c in latest if c["status"] == "done"]
    trend = []
    for b in reversed(ordered[:12]):
        ok = [c for c in b if c["status"] == "done"]
        if not ok:
            continue
        you = [next((x for x in (c.get("result") or {}).get("brands", []) if x["you"]), None) for c in ok]
        trend.append({"at": min(c["created_at"] for c in b), "answers": len(ok),
                      "mentioned": sum(1 for y in you if y and y["mentioned"]), "cited": sum(1 for y in you if y and y["cited"])})
    return {
        "site": {k: site.get(k) for k in ("id", "site", "brand", "competitors", "next_check_at", "last_batch_at")},
        "engines": [{"engine": e, "label": label(e), "cites": e == "web" or grounded()} for e in ENGINES],
        "not_measured": NOT_MEASURED,
        "status": {"queued": sum(1 for c in latest if c["status"] == "queued"), "done": len(done), "failed": sum(1 for c in latest if c["status"] == "failed")},
        "share_of_voice": share_of_voice(done),
        "answers": [{k: c.get(k) for k in ("id", "prompt", "engine", "status", "model", "answer", "sources", "result", "checked_at")} for c in latest],
        "trend": trend,
    }
