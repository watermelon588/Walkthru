from copy import deepcopy

import pytest

from app import citations
from app.citation_evidence import analyze, first, gemini_sources, groq_sources, source_url


def message(answer, results):
    return {"content": answer, "executed_tools": [{"type": "browser_search", "search_results": {"results": results}}]}


def test_retrieved_but_uncited_page_is_not_a_citation():
    sources, status = groq_sources(message("Use OtherApp.", [{"url": "https://acme.example"}]))
    result = analyze("Use OtherApp.", sources, "Acme", "acme.example", [], citation_status=status)
    assert status == "measured" and result["brands"][0]["cited"] is False


def test_provider_ids_are_not_array_positions_and_unmatched_markers_remain_unknown():
    rows = [{"id": 7, "url": "https://acme.example"}, {"id": 1, "url": "https://other.example"}]
    sources, status = groq_sources(message("Acme【7†L1-L2】. Other〖1†L2-L4〗.", rows))
    assert status == "measured" and all(s["cited"] for s in sources)
    sources, status = groq_sources(message("Acme【2†L1-L2】.", rows))
    assert status == "unresolved" and not any(s["cited"] for s in sources)
    assert analyze("Acme", sources, "Acme", "acme.example", [], citation_status=status)["brands"][0]["cited"] is None


def test_direct_answer_links_must_match_retrieved_sources():
    sources, status = groq_sources(message("Use [Acme](https://acme.example/).", [{"url": "https://acme.example/"}, {"url": "https://other.example/"}]))
    assert status == "measured" and [s["cited"] for s in sources] == [True, False]
    assert sources[0]["evidence"][0]["kind"] == "answer_link"
    _, status = groq_sources(message("Use https://invented.example/.", [{"url": "https://acme.example/"}]))
    assert status == "unresolved"


@pytest.mark.parametrize("answer", ["notacme.example", "acme.example.evil.com", "https://evil.com/acme.example", "https://evil.com/?q=acme.example", "https://acme.example@evil.com"])
def test_domains_in_larger_hosts_paths_queries_or_userinfo_do_not_match(answer):
    assert first(answer, "Acme", "acme.example") is None


@pytest.mark.parametrize("answer", ["ACME.EXAMPLE", "https://www.acme.example/page", "docs.acme.example", "Acme makes this."])
def test_explicit_names_and_domain_boundaries_match(answer):
    assert first(answer, "Acme", "acme.example") is not None


def test_same_brand_names_do_not_share_mention_rank_state():
    result = analyze("https://a.example", [], "Acme", "a.example", [{"name": "Acme", "domain": "b.example"}])
    assert [b["mentioned"] for b in result["brands"]] == [True, False]


def test_grounding_uses_claim_supports_and_url_hosts_never_titles():
    candidate = {"content": {"parts": [{"text": "Acme is useful."}]}, "groundingMetadata": {
        "groundingChunks": [{"web": {"uri": "https://acme.example/", "title": "A normal page title"}},
                            {"web": {"uri": "https://other.example/", "title": "acme.example"}}],
        "groundingSupports": [{"segment": {"text": "Acme is useful.", "startIndex": 0, "endIndex": 15}, "groundingChunkIndices": [0]}]}}
    sources, status = gemini_sources(candidate, True)
    assert status == "measured" and [s["domain"] for s in sources] == ["acme.example", "other.example"]
    assert [s["cited"] for s in sources] == [True, False]
    assert sources[0]["evidence"][0]["quote"] == "Acme is useful."
    candidate["groundingMetadata"]["groundingChunks"][0]["web"]["uri"] = "https://vertexaisearch.cloud.google.com/grounding-api-redirect/example"
    sources, status = gemini_sources(candidate, True)
    assert status == "unresolved" and sources[0]["domain"] == ""
    assert gemini_sources(candidate, False) == ([], "not_applicable")


@pytest.mark.parametrize("url", ["javascript:alert(1)", "https://user:pass@site.example", "http://127.0.0.1/", "file:///tmp/a", "https://localhost", "https://169.254.169.254"])
def test_unsafe_source_links_are_rejected(url):
    assert source_url(url) == ""


def test_legacy_citations_are_unknown_and_historical_labels_ignore_config(monkeypatch):
    check = {"engine": "memory", "answer": "notacme.example", "sources": [], "result": {"brands": [
        {"name": "Acme", "domain": "acme.example", "you": True, "mentioned": True, "cited": True}]}}
    original = deepcopy(check)
    before = citations.observed(check)
    monkeypatch.setenv("GEMINI_GROUNDING", "1")
    assert citations.observed(check) == before and check == original
    assert before["result"]["brands"][0]["cited"] is None
    assert before["result"]["brands"][0]["mentioned"] is False
    assert before["result"]["citation_status"] == "legacy"


def test_memory_does_not_dilute_share_of_voice_citation_denominator():
    measured = {"result": analyze("Acme", [{"domain": "acme.example", "cited": True}], "Acme", "acme.example", [], citation_status="measured")}
    memory = {"result": analyze("Acme", [], "Acme", "acme.example", [], citation_status="not_applicable")}
    row = citations.share_of_voice([measured, memory])[0]
    assert (row["mentions"], row["citations"], row["citation_answers"]) == (2, 1, 1)


def test_unknown_marker_format_and_incomplete_grounding_are_not_negative_measurements():
    assert groq_sources(message("Acme citeturn0search0", [{"url": "https://acme.example"}]))[1] == "unresolved"
    candidate = {"content": {"parts": [{"text": "Acme is useful."}]}, "groundingMetadata": {
        "groundingChunks": [{"web": {"uri": "https://acme.example"}}],
        "groundingSupports": [{"segment": {"text": "Acme is useful."}, "groundingChunkIndices": []}]}}
    assert gemini_sources(candidate, True)[1] == "unresolved"


def test_legacy_source_title_never_supplies_the_domain():
    check = {"engine": "memory", "sources": [{"url": "https://vertexaisearch.cloud.google.com/redirect/x",
              "title": "acme.example", "domain": "acme.example"}]}
    assert citations.observed(check)["sources"][0]["domain"] == ""


def test_capacity_and_history_reads_page_past_server_row_caps(monkeypatch):
    import httpx

    from app import db
    rows = [{"id": i, "engine": "memory"} for i in range(1201)]
    counted = []

    def head(req):
        counted.append(dict(req.url.params))
        assert req.method == "HEAD" and req.url.path == "/rest/v1/citation_checks"
        assert req.headers["Prefer"] == "count=exact" and req.url.params["limit"] == "0"
        assert req.url.params["status"] == "eq.queued" and req.url.params["select"] == "id"
        count = len(rows) if req.url.params["engine"] == "eq.memory" else 0
        return httpx.Response(200, headers={"Content-Range": f"*/{count}"})

    def select(table, params):
        if table == "citation_quota":
            return []
        start = int(params["offset"])
        return rows[start:start + min(100, int(params["limit"]))]
    monkeypatch.setattr(db, "_select", select)
    with httpx.Client(base_url="https://database.test", transport=httpx.MockTransport(head)) as client:
        monkeypatch.setattr(db, "client", lambda: client)
        assert db.citation_capacity()["queued"] == {"web": 0, "memory": 1201}
    assert [params["engine"] for params in counted] == ["eq.web", "eq.memory"]
    assert len(db.citation_checks_for("test", limit=1100)) == 1100


def test_editor_summary_uses_mentions_and_measurable_denominators():
    from app.mcp_server import _answers
    view = {"site": {"site": "https://acme.example", "brand": "Acme"}, "status": {"done": 3, "queued": 0, "failed": 0},
            "engines": [], "not_measured": [], "share_of_voice": [{"name": "Acme", "you": True, "share": 50,
            "mentions": 1, "answers": 3, "citations": 0, "citation_answers": 0}]}
    text = _answers(view)
    assert "name matched in 1 of 3 answers" in text and "citations not measured" in text


# Identity (AI citation research 2026-11-13, Phase A): a matching name is a lexical mention, not proof it is this business.

def _you(answer, sources=(), status="not_applicable", domain="tripverse-0.vercel.app"):
    return analyze(answer, list(sources), "TripVerse", domain, [], citation_status=status)["brands"][0]


def test_a_shared_name_about_another_business_is_not_credited_as_you():
    retrieved = [{"url": "https://tripverse.app/", "domain": "tripverse.app", "cited": False, "evidence": []}]
    you = _you("TripVerse is an iOS travel app by another publisher.", retrieved, "measured")
    assert you["mentioned"] is True and you["entity_status"] == "other"
    assert you["entity_evidence"] == {"kind": "same_name_domain", "host": "tripverse.app"}


def test_a_bare_name_with_no_domain_evidence_stays_ambiguous():
    you = _you("TripVerse is an iOS travel app by another publisher.")
    assert you["mentioned"] is True and you["entity_status"] == "ambiguous" and you["entity_evidence"] is None


def test_the_owned_domain_in_the_answer_or_a_citation_confirms_identity():
    assert _you("Try TripVerse (tripverse-0.vercel.app).")["entity_status"] == "verified"
    cited = [{"url": "https://tripverse-0.vercel.app/", "domain": "tripverse-0.vercel.app", "cited": True, "evidence": []},
             {"url": "https://tripverse.app/", "domain": "tripverse.app", "cited": False, "evidence": []}]
    you = _you("TripVerse plans trips on a globe.", cited, "measured")
    assert you["entity_status"] == "verified" and you["entity_evidence"] == {"kind": "owned_domain_cited", "host": "tripverse-0.vercel.app"}
    # A retrieved-only owned page is retrieval, not identity.
    retrieved = [dict(cited[0], cited=False)]
    assert _you("TripVerse plans trips on a globe.", retrieved, "measured")["entity_status"] == "ambiguous"


def test_no_match_is_absent():
    assert _you("Use Wanderlog.")["entity_status"] == "absent"


def test_source_rank_follows_citation_order_in_the_answer_not_retrieval_order():
    answer = "Choose [B](https://b.example/), then [A](https://a.example/)."
    sources, status = groq_sources(message(answer, [{"url": "https://a.example/"}, {"url": "https://b.example/"}]))
    a, b = analyze(answer, sources, "A", "a.example", [{"name": "B", "domain": "b.example"}], citation_status=status)["brands"]
    assert (a["source_rank"], b["source_rank"]) == (2, 1) and a["cited"] and b["cited"]
    # Without answer positions the order is unknown: cited stays proven, rank is not invented.
    plain = [{"domain": "a.example", "cited": True}, {"domain": "b.example", "cited": True}]
    a, b = analyze("A and B.", plain, "A", "a.example", [{"name": "B", "domain": "b.example"}], citation_status="measured")["brands"]
    assert a["cited"] is True and a["source_rank"] is None and b["source_rank"] is None


def test_saved_v2_answers_gain_identity_without_losing_citation_verdicts():
    sources = [{"url": "https://tripverse.app/", "title": "", "domain": "tripverse.app", "attribution": "url", "cited": False, "evidence": []}]
    check = {"engine": "web", "status": "done", "answer": "TripVerse is an iOS app.", "sources": sources,
             "result": {"measurement_version": 2, "citation_status": "measured", "citation_eligible": True, "prompt_group": "branded",
                        "provenance": {"label": "Groq web search", "mode": "search"}, "sources": 1,
                        "brands": [{"name": "TripVerse", "domain": "tripverse-0.vercel.app", "you": True, "mentioned": True,
                                    "mention_rank": 1, "cited": False, "source_rank": None}]}}
    original = deepcopy(check)
    seen = citations.observed(check)
    assert check == original
    you = seen["result"]["brands"][0]
    assert you["entity_status"] == "other" and you["cited"] is False
    assert seen["result"]["citation_eligible"] is True and seen["result"]["prompt_group"] == "branded" and seen["result"]["provenance"]["mode"] == "search"
