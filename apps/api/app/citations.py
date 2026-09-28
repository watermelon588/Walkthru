"""AI citation tracking (P3.2): ask AI the owner's prompts, then measure in code whether the answer names the site,
cites it, and how it stands against named competitors (mentions, citations, share of voice).

Engines, on free quotas only (ROADMAP build rule 2), measured on 2026-09-26:
- web: Groq gpt-oss-120b with its built-in browser_search tool. One search per prompt, about 3 s.
  Retrieved pages count as citations only when an answer reference can be matched to them.
- memory: Gemini without web search (Google Search grounding needs a billed key; free keys get quota 0 for it).
  It shows whether the model knows the brand, so mentions and share of voice only, labelled as such.
  With GEMINI_GROUNDING=1 and a billed key it searches Google and returns sources too.
ChatGPT and Perplexity are "not measured" until revenue pays for their APIs (SPEC.md).

Nothing here promises citations or rankings: it reports what those engines said on the day (SPEC.md honesty rule).
Data model adapted from ai-search-guru/getcito (MIT): prompts, answers, mentions, citations, share of voice.
"""

from __future__ import annotations

import logging
import math
import os
import re
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx
from selectolax.parser import HTMLParser

from app import db, notify, plans
from app.citation_evidence import VERSION, analyze, clean, domain_of, first, gemini_sources, groq_sources, source

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
ENGINE_LABEL = {"web": "Groq with web search", "memory": "Gemini, from memory"}
NOT_MEASURED = ["Google AI Overviews", "Google AI Mode", "ChatGPT", "Perplexity", "Claude"]


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


def provenance(engine: str) -> dict:
    return {"provider": "groq" if engine == "web" else "google", "label": label(engine),
            "mode": "web_search" if engine == "web" else "google_search" if grounded() else "memory",
            "locale": "unspecified", "prompt_version": 2, "measurement_version": VERSION}


# ---------- names and domains ----------


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

def share_of_voice(checks: list[dict]) -> list[dict]:
    """Per brand: share of all brand mentions across these answers, and how many answers named or cited it."""
    tally: dict[tuple, dict] = {}
    for c in checks:
        for b in (c.get("result") or {}).get("brands", []):
            t = tally.setdefault((b["name"], b["domain"], b["you"]), {"name": b["name"], "domain": b["domain"], "you": b["you"], "mentions": 0, "citations": 0, "citation_answers": 0})
            t["mentions"] += 1 if b["mentioned"] else 0
            eligible = (c.get("result") or {}).get("citation_eligible") is True and b.get("cited") is not None
            t["citations"] += 1 if eligible and b["cited"] else 0
            t["citation_answers"] += int(eligible)
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
              "from the results only. Do not open pages. Cite each source you use with its full URL in a markdown link. "
              "Recommend specific products or companies by name. Keep it under 150 words.")
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
    if not (msg.get("content") or "").strip():
        raise RuntimeError("empty Groq answer")
    sources, status = groq_sources(msg)
    return {"answer": msg["content"], "sources": sources, "citation_status": status, "provenance": provenance("web"),
            "tokens": (body.get("usage") or {}).get("total_tokens", 0), "model": WEB_MODEL}


def ask_memory(prompt: str, *, mode: str | None = None) -> dict:
    key = gemini_key()
    if not key:
        raise RuntimeError("no Gemini key")
    use_search = mode == "google_search" if mode is not None else grounded()
    observation = provenance("memory") | {"mode": "google_search" if use_search else "memory",
                                           "label": "Gemini with Google Search" if use_search else "Gemini, from memory"}
    body = {"systemInstruction": {"parts": [{"text": MEMORY_SYSTEM}]}, "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 700}} | ({"tools": [{"google_search": {}}]} if use_search else {})
    busy = False
    # One provider request per reserved quota slot, including failures.
    for model in GEMINI_MODELS[:1]:
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
        sources, status = gemini_sources(cand, use_search)
        return {"answer": answer, "sources": sources, "citation_status": status, "provenance": observation,
                "tokens": (data.get("usageMetadata") or {}).get("totalTokenCount", 0), "model": model}
    if busy:
        raise Busy("gemini quota")
    raise RuntimeError("no Gemini model answered")


ENGINES = {"web": ask_web, "memory": ask_memory}


# ---------- batches, the queue and the schedule ----------


class QueueFull(Exception):
    pass


def queue_batch(site: dict, prompts: list[dict], engines: tuple[str, ...], *, weekly: bool = False) -> str:
    batch = str(uuid.uuid4())
    context = {"brand": site["brand"], "domain": domain_of(site["site"]), "competitors": site.get("competitors") or []}
    rows = [{"prompt_id": p["id"], "prompt": p["prompt"], "engine": e,
             "result": {"provenance": provenance(e), "context": context,
                        "prompt_group": "branded" if first(p["prompt"], context["brand"], context["domain"]) is not None else "unbranded"}}
            for p in prompts for e in engines]
    outcome = db.queue_citation_batch(site["id"], batch, rows, DAILY, weekly)
    if outcome != "ok":
        messages = {"pending": "This site already has answers waiting. Let that batch finish first.",
                    "recent": "These prompts were queued in the last day. Try again tomorrow.",
                    "capacity": "The shared free-provider queue is full for the next seven daily quota windows. Try again after capacity clears.",
                    "missing": "This tracked site is no longer available."}
        raise QueueFull(messages.get(outcome, "Could not reserve space in the answer queue."))
    return batch


def _day_start() -> str:
    return datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


def process(max_checks: int = 30, sleep=time.sleep) -> int:
    """Run queued checks in order, within each engine's daily cap. Returns how many finished."""
    done = 0
    started = 0
    busy: set[str] = set()
    for check in db.queued_citation_checks(limit=5000):
        engine = check["engine"]
        if started >= max_checks:
            break
        if engine in busy or engine not in ENGINES:
            continue  # stays queued: tomorrow's quota, or the next pass
        token = str(uuid.uuid4())
        if not db.claim_citation_check(check["id"], check["attempts"], engine, DAILY[engine], WEB_GAP_S if engine == "web" else 1, token):
            busy.add(engine)  # Avoid one RPC per queued row when quota or spacing is exhausted.
            continue
        started += 1
        site = db.citation_site(check["site_id"])
        if site is None:
            continue
        saved = check.get("result") or {}
        try:
            lim = limit_for(site["user_id"])
            if not lim or engine not in lim.engines:
                db.finish_citation_check(check["id"], {"status": "failed", "answer": "This engine is no longer included in the current plan."}, token)
                _maybe_announce(check)
                continue
            mode = (saved.get("provenance") or {}).get("mode", "memory")
            # Do not silently upgrade an already queued memory request to web search.
            got = ask_memory(check["prompt"], mode=mode) if ENGINES[engine] is ask_memory else ENGINES[engine](check["prompt"])
            context = saved.get("context") or {"brand": site["brand"], "domain": domain_of(site["site"]), "competitors": site.get("competitors") or []}
            result = analyze(got["answer"], got["sources"], **context, citation_status=got.get("citation_status", "unresolved"))
            result.update(provenance=got.get("provenance") or saved.get("provenance") or provenance(engine), context=context,
                          prompt_group=saved.get("prompt_group", "unknown"))
            finished = db.finish_citation_check(check["id"], {"status": "done", "answer": clean(got["answer"]), "sources": got["sources"],
                                                   "tokens": got["tokens"], "model": got["model"], "last_error": None,
                                                   "result": result | {"raw_answer": got["answer"]}}, token)
            done += int(finished)
        except Busy:
            busy.add(engine)
            db.defer_citation_engine(engine, (datetime.now(UTC) + timedelta(hours=1)).isoformat())
            db.finish_citation_check(check["id"], {"next_attempt_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
                                                  "last_error": "Provider quota is busy; retry scheduled in one hour."}, token)
        except Exception:  # one broken answer must not stop the queue
            log.warning("citation check %s failed", check["id"], exc_info=True)
            failures = saved.get("failures", 0) + 1
            values = {"result": saved | {"failures": failures}, "last_error": "Provider did not answer; retry scheduled.",
                      "next_attempt_at": (datetime.now(UTC) + timedelta(minutes=min(60, 2 ** failures))).isoformat()}
            if failures >= MAX_ATTEMPTS:
                values.update(status="failed", answer="The engine did not return an answer after repeated attempts.")
            db.finish_citation_check(check["id"], values, token)
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
                queue_batch(site, prompts, lim.engines, weekly=True)
                queued += 1
            db.update_citation_site(site["id"], {"next_check_at": (now + EVERY).isoformat()})
        except QueueFull:
            db.update_citation_site(site["id"], {"next_check_at": (now + timedelta(hours=6)).isoformat()})
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


def capacity() -> list[dict]:
    state = db.citation_capacity()
    today = datetime.now(UTC).date().isoformat()
    out = []
    for engine, cap in DAILY.items():
        quota = next((q for q in state["quotas"] if q["engine"] == engine), {})
        used = quota.get("used", 0) if quota.get("day") == today else 0
        pending = state["queued"].get(engine, 0)
        remaining = max(0, cap - used)
        windows = 1 + math.ceil(max(0, pending - remaining) / cap) if cap > 0 and pending else 0 if not pending else None
        out.append({"engine": engine, "label": label(engine), "daily_limit": cap, "used": used, "remaining": remaining,
                    "queued": pending, "quota_windows": windows, "next_attempt_at": quota.get("next_at"),
                    "configured": bool(os.environ.get("GROQ_API_KEY") if engine == "web" else gemini_key())})
    return out


def observed(check: dict) -> dict:
    """Do not relabel old answers or reuse the old, incorrect citation verdicts."""
    result = check.get("result") or {}
    if result.get("measurement_version") == VERSION:
        return check
    brands = result.get("brands") or []
    own = next((b for b in brands if b.get("you")), None)
    if own:
        result = analyze(check.get("answer") or "", [], own["name"], own["domain"],
                         [{"name": b["name"], "domain": b["domain"]} for b in brands if not b.get("you")], citation_status="legacy")
    else:
        result = {"brands": [], "citation_eligible": False, "citation_status": "legacy"}
    result["provenance"] = {"label": "Groq web search (legacy)" if check["engine"] == "web" else "Gemini (historical mode unknown)", "mode": "unknown"}
    # Existing records had their answer markers removed. A new check is required.
    sources = [item for s in check.get("sources") or [] if (item := source(s.get("url", ""), s.get("title", "")))]
    return check | {"result": result, "sources": sources}


def summary(site: dict) -> dict:
    checks = [observed(c) if c["status"] == "done" else c for c in db.citation_checks_for(site["id"], since=(datetime.now(UTC) - timedelta(days=120)).isoformat(), limit=5000)]
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
        eligible = [c for c in ok if (c.get("result") or {}).get("citation_eligible") is True]
        trend.append({"at": min(c["created_at"] for c in b), "answers": len(ok),
                      "mentioned": sum(1 for y in you if y and y["mentioned"]), "citation_answers": len(eligible),
                      "cited": sum(1 for c in eligible if any(y.get("you") and y.get("cited") for y in c["result"]["brands"]))})
    return {
        "site": {k: site.get(k) for k in ("id", "site", "brand", "competitors", "next_check_at", "last_batch_at")},
        "engines": [{"engine": e, "label": label(e), "cites": e == "web" or grounded()} for e in ENGINES],
        "not_measured": NOT_MEASURED,
        "capacity": capacity(),
        "history_limited": len(checks) >= 5000,
        "status": {"queued": sum(1 for c in latest if c["status"] == "queued"), "done": len(done), "failed": sum(1 for c in latest if c["status"] == "failed")},
        "share_of_voice": share_of_voice(done),
        "answers": [{k: c.get(k) for k in ("id", "prompt", "engine", "status", "model", "answer", "sources", "result", "checked_at", "next_attempt_at", "last_error")} for c in latest],
        "trend": trend,
    }
