"""PageSpeed's five-page cap, field-vs-lab distinction and report wiring."""

import httpx

from app.agent import report
from app.scans import performance


def test_paid_pagespeed_checks_at_most_five_pages_and_real_user_vitals(monkeypatch):
    monkeypatch.setenv("PAGESPEED_API_KEY", "test-key")
    monkeypatch.setattr(performance.get.__globals__["socket"], "getaddrinfo", lambda host, port: [(None, None, None, None, ("8.8.8.8", 0))])
    requested = []

    def handle(request):
        requested.append(request.url.params["url"])
        assert request.url.params["strategy"] == "mobile"
        return httpx.Response(200, json={
            "lighthouseResult": {"categories": {"performance": {"score": 0.91}}},
            "loadingExperience": {"metrics": {
                "LARGEST_CONTENTFUL_PAINT_MS": {"percentile": 3100},
                "CUMULATIVE_LAYOUT_SHIFT_SCORE": {"percentile": 18},
                "INTERACTION_TO_NEXT_PAINT": {"percentile": 230},
            }},
        })

    urls = [f"https://site.test/page/{n}" for n in range(6)]
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        findings, measured, rows = performance.scan_pages(urls, client)
    assert measured and len(rows) == 5 and set(requested) == set(urls[:5])
    assert rows[0] == {"url": urls[0], "status": "field_data", "lab_score": 91, "lcp_ms": 3100, "cls": 0.18, "inp_ms": 230}
    assert len([f for f in findings if "Core Web Vitals" in f.title]) == 5


def test_pagespeed_preserves_lab_only_and_unavailable_states(monkeypatch):
    monkeypatch.setenv("PAGESPEED_API_KEY", "test-key")
    monkeypatch.setattr(performance.get.__globals__["socket"], "getaddrinfo", lambda host, port: [(None, None, None, None, ("8.8.8.8", 0))])

    def handle(request):
        if request.url.params["url"].endswith("/missing"):
            return httpx.Response(429)
        return httpx.Response(200, json={"lighthouseResult": {"categories": {"performance": {"score": 0.95}}}})

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        findings, measured, rows = performance.scan_pages(["https://site.test/okay", "https://site.test/missing"], client)
    assert measured and findings == []
    assert [row["status"] for row in rows] == ["lab_only", "unavailable"]


def test_report_paid_performance_uses_audited_urls_and_stores_vitals(monkeypatch):
    chosen = []

    def fake_scan(urls, client, *, limit):
        chosen.extend(urls)
        return [], True, [{"url": url, "status": "lab_only", "lab_score": 95, "lcp_ms": None, "cls": None, "inp_ms": None} for url in urls]

    monkeypatch.setattr(report.performance, "scan_pages", fake_scan)
    monkeypatch.setattr(report.fetch, "assert_public", lambda url: None)
    urls = [f"https://site.test/{n}" for n in range(7)]
    state = {"site": urls[0], "paid": True, "site_audit": {"urls": urls, "pages_scanned": 7}}
    result = report.performance_scan(state)
    assert chosen == urls[:5]
    assert result["site_audit"]["mobile_vitals"][0]["url"] == urls[0]
    assert len(result["site_audit"]["mobile_vitals"]) == 5
