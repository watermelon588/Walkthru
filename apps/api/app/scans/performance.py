"""PageSpeed mobile lab score and URL-level Core Web Vitals field evidence."""

import os
from concurrent.futures import ThreadPoolExecutor
from math import isfinite
from urllib.parse import urlencode, urlsplit

import httpx

from app.agent.schema import Finding
from app.scans.fetch import get, origin

API = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"


def _metric(metrics: dict, key: str) -> int | None:
    item = metrics.get(key, {})
    value = item.get("percentile") if isinstance(item, dict) else None
    return value if isinstance(value, int) and value >= 0 else None


def _one(url: str, client: httpx.Client, key: str) -> tuple[list[Finding], bool, dict]:
    request_url = API + "?" + urlencode({"url": url, "strategy": "mobile", "category": "performance", "key": key})
    response = get(client, request_url, same_origin=origin(API), timeout=15)
    summary: dict = {"url": url, "status": "unavailable", "lab_score": None, "lcp_ms": None, "cls": None, "inp_ms": None}
    if response is None or response.status_code != 200:
        return [], False, summary
    try:
        data = response.json()
        lighthouse = data.get("lighthouseResult", {})
        raw_score = lighthouse.get("categories", {}).get("performance", {}).get("score")
        metrics = data.get("loadingExperience", {}).get("metrics", {})
    except (ValueError, AttributeError, TypeError):
        return [], False, summary
    findings: list[Finding] = []
    if isinstance(raw_score, (int, float)) and isfinite(raw_score):
        score = round(raw_score * 100)
        summary["lab_score"] = score
        if score < 90:
            lcp = str(lighthouse.get("audits", {}).get("largest-contentful-paint", {}).get("displayValue", "not reported"))[:120]
            findings.append(Finding(kind="performance", severity="medium" if score < 50 else "low",
                                    title=f"Mobile performance score {score}/100",
                                    detail=f"Largest Contentful Paint: {lcp}. Slow pages lose visitors before the first click.",
                                    fix="Compress images, defer non-critical scripts, and serve static assets from a CDN.",
                                    evidence=f"PageSpeed Insights, mobile: {score}"))
    if isinstance(metrics, dict):
        summary["lcp_ms"] = _metric(metrics, "LARGEST_CONTENTFUL_PAINT_MS")
        cls_hundredths = _metric(metrics, "CUMULATIVE_LAYOUT_SHIFT_SCORE")
        summary["cls"] = round(cls_hundredths / 100, 2) if cls_hundredths is not None else None
        summary["inp_ms"] = _metric(metrics, "INTERACTION_TO_NEXT_PAINT")
    values = (summary["lcp_ms"], summary["cls"], summary["inp_ms"])
    if any(value is not None for value in values):
        summary["status"] = "field_data"
        bad = []
        if summary["lcp_ms"] is not None and summary["lcp_ms"] > 2500:
            bad.append(f"LCP {summary['lcp_ms']} ms")
        if summary["cls"] is not None and summary["cls"] > 0.1:
            bad.append(f"CLS {summary['cls']}")
        if summary["inp_ms"] is not None and summary["inp_ms"] > 200:
            bad.append(f"INP {summary['inp_ms']} ms")
        if bad:
            path = urlsplit(url).path or "/"
            findings.append(Finding(kind="performance", severity="medium", title=f"Mobile Core Web Vitals need work on {path[:60]}",
                                    detail="Real-user 75th-percentile mobile data exceeds the good threshold: " + ", ".join(bad) + ".",
                                    fix="Open PageSpeed Insights for this URL and address its LCP, CLS or INP recommendations.",
                                    evidence=url))
    elif summary["lab_score"] is not None:
        summary["status"] = "lab_only"
    return findings, summary["status"] != "unavailable", summary


def scan_pages(urls: list[str], client: httpx.Client, *, limit: int = 5) -> tuple[list[Finding], bool, list[dict]]:
    """At most five free-quota PSI calls. HTTPX's sync Client supports sharing across worker threads."""
    key = os.environ.get("PAGESPEED_API_KEY")
    if not key:
        return [], False, []
    chosen = list(dict.fromkeys(urls))[:max(1, min(limit, 5))]
    if not chosen:
        return [], False, []
    with ThreadPoolExecutor(max_workers=min(3, len(chosen))) as pool:
        results = list(pool.map(lambda target: _one(target, client, key), chosen))
    return [finding for findings, _, _ in results for finding in findings], any(ok for _, ok, _ in results), [row for _, _, row in results]


def scan(url: str, c: httpx.Client) -> tuple[list[Finding], bool]:
    """Homepage compatibility path for existing callers."""
    findings, measured, _ = scan_pages([url], c, limit=1)
    return findings, measured
