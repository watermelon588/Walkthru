"""AI citation tracking (P3.2, app/citations.py): parsing recorded engine answers, the analysis done in code, prompt
suggestions, plan limits, the queue with its daily caps, and the notification when a set of checks is done."""

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app import citations, db
from app.main import app
from app.scans import fetch
from tests.conftest import USER

HOME = """<html><head><title>Acme Notes | Notes app for small teams</title>
<meta name="description" content="Shared notes your whole team can find."><meta property="og:site_name" content="Acme Notes"></head>
<body><h1>Notes your team can actually find</h1></body></html>"""

# Recorded from Groq on 2026-09-26 (trimmed): gpt-oss-120b with browser_search, one search, no page opened.
GROQ = {"choices": [{"message": {"content": "- **Notion** is the flexible pick【1†L4-L9】.\n- **Acme Notes** suits small teams【3†L2-L5】.\n- Evernote for search.",
                                 "executed_tools": [{"type": "browser_search", "search_results": {"results": [
                                     {"title": "The best note taking apps", "url": "https://www.pcmag.com/picks/notes"},
                                     {"title": "Acme Notes for teams", "url": "https://acmenotes.app/teams"},
                                     {"title": "Notion", "url": "https://www.notion.so/product"},
                                     {"title": "The best note taking apps", "url": "https://www.pcmag.com/picks/notes"}]}}]}}],
        "usage": {"total_tokens": 1580}}
# Gemini with Google Search grounding: sources are redirect links titled with the domain.
GEMINI = {"candidates": [{"content": {"parts": [{"text": "Try Notion or Obsidian. Acme Notes is newer."}]},
                          "groundingMetadata": {"groundingChunks": [{"web": {"uri": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/x", "title": "acmenotes.app"}}]}}],
          "usageMetadata": {"totalTokenCount": 420}}


class Resp:
    def __init__(self, status, body):
        self.status_code, self._body = status, body

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


def test_analysis_names_cites_and_ranks_in_code():
    got = [{"url": u, "domain": citations.domain_of(u)} for u in ("https://www.pcmag.com/x", "https://acmenotes.app/teams", "https://www.notion.so/p")]
    answer = citations.clean(GROQ["choices"][0]["message"]["content"])
    assert "【" not in answer
    result = citations.analyze(answer, got, "Acme Notes", "acmenotes.app", [{"name": "Notion", "domain": "notion.so"}, {"name": "Coda", "domain": "coda.io"}])
    you, notion, coda = result["brands"]
    assert you == {"name": "Acme Notes", "domain": "acmenotes.app", "you": True, "mentioned": True, "mention_rank": 2, "cited": True, "source_rank": 2}
    assert notion["mentioned"] and notion["mention_rank"] == 1 and notion["cited"] and notion["source_rank"] == 3
    assert not coda["mentioned"] and not coda["cited"] and coda["mention_rank"] is None
    # A word inside another word is not a mention.
    assert not citations.analyze("A notional plan.", [], "Notion", "notion.so", [])["brands"][0]["mentioned"]


def test_share_of_voice_counts_mentions_across_answers():
    def check(names):
        return {"result": {"brands": [{"name": n, "domain": "", "you": n == "Acme", "mentioned": n in names, "cited": False} for n in ("Acme", "Notion")]}}
    sov = citations.share_of_voice([check({"Acme", "Notion"}), check({"Notion"}), check({"Notion"})])
    assert [(s["name"], s["mentions"], s["share"]) for s in sov] == [("Notion", 3, 75), ("Acme", 1, 25)]


def test_competitors_brand_and_prompts_come_from_what_the_owner_and_site_say():
    assert citations.parse_competitor("Notion (notion.so)") == {"name": "Notion", "domain": "notion.so"}
    assert citations.parse_competitor("https://www.coda.io") == {"name": "Coda", "domain": "coda.io"}
    assert citations.parse_competitor("Evernote") == {"name": "Evernote", "domain": ""}
    assert citations.brand_from(HOME, "acmenotes.app") == "Acme Notes"
    assert citations.brand_from("<title>Home</title>", "acme-notes.app") == "Acme Notes"
    prompts = citations.suggest(HOME, "Acme Notes", [{"name": "Notion", "domain": "notion.so"}])
    assert prompts[0] == "What are the best notes app for small teams?"
    assert "What are the best alternatives to Notion?" in prompts and "Is Acme Notes worth it?" in prompts
    assert len(prompts) == len(set(prompts))


def test_web_engine_reads_groq_sources_and_rests_on_429(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setattr(citations.httpx, "post", lambda url, **k: Resp(200, GROQ))
    got = citations.ask_web("best notes app")
    assert [s["domain"] for s in got["sources"]] == ["pcmag.com", "acmenotes.app", "notion.so"]  # duplicates dropped
    assert got["tokens"] == 1580 and got["model"] == citations.WEB_MODEL
    monkeypatch.setattr(citations.httpx, "post", lambda url, **k: Resp(429, {}))
    with pytest.raises(citations.Busy):
        citations.ask_web("best notes app")


def test_memory_engine_has_sources_only_when_grounded(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "g_test")
    seen = []
    monkeypatch.setattr(citations.httpx, "post", lambda url, json, **k: seen.append(json) or Resp(200, GEMINI))
    monkeypatch.delenv("GEMINI_GROUNDING", raising=False)
    got = citations.ask_memory("best notes app")
    assert "tools" not in seen[-1] and got["answer"].startswith("Try Notion") and citations.label("memory") == "Gemini, from memory"
    monkeypatch.setenv("GEMINI_GROUNDING", "1")
    got = citations.ask_memory("best notes app")
    assert seen[-1]["tools"] == [{"google_search": {}}] and got["sources"][0]["domain"] == "acmenotes.app"
    assert citations.label("memory") == "Gemini with Google Search"


# ---------- the API, the queue and the caps, over an in-memory store ----------


@pytest.fixture
def store(monkeypatch):
    sites, prompts, checks = {}, {}, []

    def add_site(row):
        row = row | {"id": str(uuid.uuid4()), "created_at": datetime.now(UTC).isoformat(), "last_batch_at": None}
        sites[row["id"]] = row
        return row

    def replace(site_id, texts):
        prompts[site_id] = [{"id": str(uuid.uuid4()), "prompt": t, "created_at": "x"} for t in texts]
        return prompts[site_id]

    def add_checks(rows):
        for r in rows:
            checks.append(r | {"id": len(checks) + 1, "status": "queued", "attempts": 0, "answer": "", "sources": [], "result": {},
                               "created_at": datetime.now(UTC).isoformat(), "checked_at": None, "model": "", "tokens": 0})

    def claim(check_id, attempts):
        c = next(c for c in checks if c["id"] == check_id)
        if c["status"] != "queued" or c["attempts"] != attempts:
            return False
        c["attempts"] += 1
        return True

    def finish(check_id, values):
        next(c for c in checks if c["id"] == check_id).update(values | {"checked_at": datetime.now(UTC).isoformat()})

    monkeypatch.setattr(db, "citation_sites", lambda uid: [s for s in sites.values() if s["user_id"] == uid])
    monkeypatch.setattr(db, "citation_site", lambda sid: sites.get(sid))
    monkeypatch.setattr(db, "add_citation_site", add_site)
    monkeypatch.setattr(db, "update_citation_site", lambda sid, v: sites[sid].update(v))
    monkeypatch.setattr(db, "delete_citation_site", lambda sid: sites.pop(sid, None))
    monkeypatch.setattr(db, "citation_prompts", lambda sid: prompts.get(sid, []))
    monkeypatch.setattr(db, "replace_citation_prompts", replace)
    monkeypatch.setattr(db, "add_citation_checks", add_checks)
    monkeypatch.setattr(db, "queued_citation_checks", lambda limit=20: [dict(c) for c in checks if c["status"] == "queued"][:limit])
    monkeypatch.setattr(db, "claim_citation_check", claim)
    monkeypatch.setattr(db, "finish_citation_check", finish)
    monkeypatch.setattr(db, "citation_checks_for", lambda sid, since=None, limit=500: [c for c in reversed(checks) if c["site_id"] == sid][:limit])
    monkeypatch.setattr(db, "citation_checks_done_since", lambda engine, since: sum(1 for c in checks if c["engine"] == engine and c["checked_at"]))
    monkeypatch.setattr(db, "citation_batches_since", lambda sid, since: len({c["batch_id"] for c in checks if c["site_id"] == sid}))
    monkeypatch.setattr(fetch, "assert_public", lambda url: None)
    monkeypatch.setattr(fetch, "get", lambda c, url, **k: type("R", (), {"status_code": 200, "text": HOME})())
    return sites, prompts, checks


def plan(passes, name):
    passes.append({"user_id": USER, "plan": name, "starts_at": "2000-01-01T00:00:00+00:00", "expires_at": "2999-01-01T00:00:00+00:00", "runs_granted": 150})


def test_free_accounts_see_the_upgrade_and_plus_starts_with_suggested_prompts(store, passes):
    c = TestClient(app)
    assert c.post("/citations", json={"site": "https://acmenotes.app"}).status_code == 402
    plan(passes, "plus")
    body = c.post("/citations", json={"site": "https://acmenotes.app/pricing", "competitors": ["Notion (notion.so)", "acmenotes.app", "coda.io"]}).json()
    assert body["site"]["site"] == "https://acmenotes.app" and body["site"]["brand"] == "Acme Notes"
    assert [x["domain"] for x in body["site"]["competitors"]] == ["notion.so", "coda.io"]  # its own domain is not a competitor
    assert 5 <= len(body["prompts"]) <= 25 and body["limit"]["engines"] == ["web", "memory"]
    assert body["not_measured"] == ["ChatGPT", "Perplexity"]
    assert c.post("/citations", json={"site": "https://acmenotes.app"}).status_code == 409


def test_prompt_limits_check_now_and_one_check_a_day(store, passes):
    _, _, checks = store
    plan(passes, "pro")
    c = TestClient(app)
    site = c.post("/citations", json={"site": "https://acmenotes.app"}).json()["site"]
    assert c.post(f"/citations/{site['id']}", json={"prompts": [f"prompt number {i}" for i in range(11)]}).status_code == 409  # Pro: 10
    c.post(f"/citations/{site['id']}", json={"prompts": ["best notes app for teams", "what is Acme Notes", "what is Acme Notes"]})
    r = c.post(f"/citations/{site['id']}/check")
    assert r.status_code == 200 and r.json()["queued"] == 2  # duplicates dropped; Pro runs the web engine only
    assert {x["engine"] for x in checks} == {"web"}
    assert c.post(f"/citations/{site['id']}/check").status_code == 429


def test_the_launch_pack_gets_one_snapshot(store, passes):
    plan(passes, "launch")
    c = TestClient(app)
    site = c.post("/citations", json={"site": "https://acmenotes.app"}).json()["site"]
    assert site["next_check_at"] is None  # no weekly schedule
    assert c.post(f"/citations/{site['id']}/check").status_code == 200
    store[0][site["id"]]["last_batch_at"] = None  # even a day later
    assert c.post(f"/citations/{site['id']}/check").status_code == 402


def test_the_queue_runs_within_caps_keeps_busy_checks_and_announces_the_finished_set(store, passes, monkeypatch, fake_db):
    _, _, checks = store
    plan(passes, "plus")
    c = TestClient(app)
    site = c.post("/citations", json={"site": "https://acmenotes.app", "competitors": ["Notion (notion.so)"]}).json()["site"]
    c.post(f"/citations/{site['id']}", json={"prompts": ["best notes app", "notes for small teams"]})
    c.post(f"/citations/{site['id']}/check")
    assert len(checks) == 4  # 2 prompts x 2 engines
    def busy(prompt):
        raise citations.Busy("quota")

    web = {"answer": "Acme Notes and Notion.", "sources": [{"url": "https://acmenotes.app", "domain": "acmenotes.app"}], "tokens": 10, "model": "m"}
    monkeypatch.setattr(citations, "ENGINES", {"web": lambda p: web, "memory": busy})
    assert citations.process(sleep=lambda s: None) == 2
    assert all(x["status"] == "done" and x["result"]["brands"][0]["cited"] for x in checks if x["engine"] == "web")
    assert all(x["status"] == "queued" for x in checks if x["engine"] == "memory")  # the busy engine waits
    assert not fake_db.notes  # the set is not finished yet

    monkeypatch.setitem(citations.DAILY, "memory", 0)  # today's memory quota is used up
    assert citations.process(sleep=lambda s: None) == 0 and all(x["status"] == "queued" for x in checks if x["engine"] == "memory")

    monkeypatch.setitem(citations.DAILY, "memory", 300)
    monkeypatch.setitem(citations.ENGINES, "memory", lambda p: {"answer": "Notion.", "sources": [], "tokens": 5, "model": "g"})
    assert citations.process(sleep=lambda s: None) == 2
    note = fake_db.notes[-1]
    assert note["section"] == "visibility" and note["body"] == "Named in 2 of 4 answers." and note["link"] == "/app/visibility"
    view = c.get(f"/citations/{site['id']}").json()
    assert view["status"] == {"queued": 0, "done": 4, "failed": 0}
    assert [(s["name"], s["mentions"]) for s in view["share_of_voice"]] == [("Notion", 4), ("Acme Notes", 2)]


def test_weekly_schedule_queues_due_sites_and_stops_when_the_plan_lapses(store, passes, monkeypatch):
    sites, prompts, checks = store
    plan(passes, "plus")
    c = TestClient(app)
    site = c.post("/citations", json={"site": "https://acmenotes.app"}).json()["site"]
    monkeypatch.setattr(db, "due_citation_sites", lambda now, limit=20: [s for s in sites.values() if s["next_check_at"] and s["next_check_at"] <= "9999"])
    assert citations.run_due() == 1 and len(checks) == 2 * len(prompts[site["id"]])
    passes.clear()  # the pass ended
    assert citations.run_due() == 0 and sites[site["id"]]["next_check_at"] is None
