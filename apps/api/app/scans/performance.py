"""PageSpeed mobile lab score and URL-level Core Web Vitals field evidence."""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from math import isfinite
from time import monotonic
from urllib.parse import urlencode, urlsplit, urlunsplit

import httpx

from app.agent.schema import Finding, _context_text
from app.scans.fetch import get, origin

API = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
MAX_AUDITS = 12
MAX_RESOURCES = 5
METRICS = {"lcp_ms": "largest-contentful-paint", "cls": "cumulative-layout-shift",
           "fcp_ms": "first-contentful-paint", "tbt_ms": "total-blocking-time", "speed_index_ms": "speed-index"}
# Older Lighthouse versions do not always list diagnostic audits in auditRefs.
ATTRIBUTION = ("largest-contentful-paint-element", "layout-shift-elements", "render-blocking-resources",
               "unused-javascript", "unused-css-rules", "uses-optimized-images", "uses-responsive-images",
               "modern-image-formats", "server-response-time")


def _dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _number(value) -> float | int | None:
    try:
        return value if type(value) in (int, float) and isfinite(value) and value >= 0 else None
    except OverflowError:
        return None


def _text(value) -> str | None:
    return _context_text(value).replace("\u2014", ", ").replace("\u2013", "-") if isinstance(value, str) else None


def _url(value) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parts = urlsplit(value)
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            return None
        # Do not retain credentials, query values or fragments in public report evidence.
        return _text(urlunsplit((parts.scheme, parts.netloc.rsplit("@", 1)[-1], parts.path, "", "")))
    except ValueError:
        return None


def _resources(details: dict) -> tuple[list[dict], bool]:
    """Flatten bounded table/checklist/subitem locators; never retain HTML or node text."""
    found: list[dict] = []
    visited = 0
    truncated = False

    def visit(value, depth=0):
        nonlocal visited, truncated
        if not isinstance(value, (dict, list)):
            return
        if visited >= 80 or depth > 5:
            truncated = True
            return
        visited += 1
        if isinstance(value, list):
            for item in value[:40]:
                visit(item, depth + 1)
            truncated |= len(value) > 40
            return
        row = {}
        url = _url(value.get("url"))
        if url:
            row["url"] = url
        node = _dict(value.get("node")) or (value if value.get("type") == "node" else {})
        selector = _text(node.get("selector"))
        if selector:
            row["selector"] = selector
        for key in ("totalBytes", "wastedBytes", "wastedMs", "duration", "startTime"):
            number = _number(value.get(key))
            if number is not None:
                row[key] = number
        if (url or selector) and row not in found:
            if len(found) < MAX_RESOURCES:
                found.append(row)
            else:
                truncated = True
        for key in ("items", "subItems", "node", "value"):
            if key in value:
                visit(value[key], depth + 1)

    visit(details)
    return found, truncated


def _lab(lighthouse: dict) -> dict:
    audits = _dict(lighthouse.get("audits"))
    category = _dict(_dict(lighthouse.get("categories")).get("performance"))
    settings = _dict(lighthouse.get("configSettings"))
    refs = category.get("auditRefs")
    refs = refs if isinstance(refs, list) else []
    ids = list(dict.fromkeys([r["id"] for r in refs[:100] if isinstance(r, dict) and isinstance(r.get("id"), str)]
                            + list(METRICS.values()) + list(ATTRIBUTION)))
    selected = []
    for audit_id in ids:
        audit = _dict(audits.get(audit_id))
        if not audit:
            continue
        details = _dict(audit.get("details"))
        resources, omitted = _resources(details)
        savings = {k: v for k in ("LCP", "FCP", "TBT") if (v := _number(_dict(audit.get("metricSavings")).get(k))) is not None}
        score = _number(audit.get("score"))
        selected.append({"id": audit_id[:100], "title": _text(audit.get("title")) or audit_id[:100],
                         "description": _text(audit.get("description")), "display_value": _text(audit.get("displayValue")),
                         "score": score if score is not None and score <= 1 else None,
                         "mode": _text(audit.get("scoreDisplayMode")), "error": _text(audit.get("errorMessage")),
                         "value": _number(audit.get("numericValue")), "unit": _text(audit.get("numericUnit")),
                         "estimated_savings_ms": _number(details.get("overallSavingsMs")),
                         "estimated_savings_bytes": _number(details.get("overallSavingsBytes")),
                         "metric_savings_ms": savings, "resources": resources, "resources_truncated": omitted})
    # Preserve high-value attribution ahead of metrics/pass results when the audit cap is reached.
    selected.sort(key=lambda a: (not bool(a["resources"]), not (a["score"] is not None and a["score"] < 1)))
    score = _number(category.get("score"))
    failed = bool(lighthouse.get("runtimeError"))
    metrics = {}
    for name, audit_id in METRICS.items():
        audit = _dict(audits.get(audit_id))
        unavailable = audit.get("scoreDisplayMode") in {"error", "manual", "notApplicable"} or audit.get("errorMessage")
        metrics[name] = None if unavailable else _number(audit.get("numericValue"))
    throttling = _dict(settings.get("throttling"))
    measured = score is not None and score <= 1 or any(v is not None for v in metrics.values())
    return {"source": "lighthouse_lab", "status": "unavailable" if failed or not measured else "measured",
            "score": round(score * 100) if not failed and score is not None and score <= 1 else None,
            "metrics": {k: None if failed else v for k, v in metrics.items()},
            "requested_url": _url(lighthouse.get("requestedUrl")), "final_url": _url(lighthouse.get("finalUrl")),
            "measured_at": _text(lighthouse.get("fetchTime")), "version": _text(lighthouse.get("lighthouseVersion")),
            "device": _text(settings.get("formFactor") or settings.get("emulatedFormFactor")),
            "throttling_method": _text(settings.get("throttlingMethod")),
            "throttling": {k: n for k in ("rttMs", "throughputKbps", "requestLatencyMs", "downloadThroughputKbps", "uploadThroughputKbps", "cpuSlowdownMultiplier")
                           if (n := _number(throttling.get(k))) is not None},
            "duration_ms": _number(_dict(lighthouse.get("timing")).get("total")),
            "warnings": [_text(v) for v in lighthouse.get("runWarnings", [])[:5] if isinstance(v, str)] if isinstance(lighthouse.get("runWarnings"), list) else [],
            "error": _text(_dict(lighthouse.get("runtimeError")).get("message")),
            "audits": [] if failed else selected[:MAX_AUDITS], "audits_omitted": max(0, len(selected) - MAX_AUDITS)}


def _opportunity(lab: dict) -> dict | None:
    return next((a for a in lab["audits"] if a["id"] not in METRICS.values() and not a["error"] and a["mode"] not in {"error", "manual", "notApplicable"}
                 and (a["score"] is not None and a["score"] < 1 or (a["estimated_savings_ms"] or 0) > 0 or any(a["metric_savings_ms"].values()))), None)


def _fix(lab: dict) -> str:
    audit = _opportunity(lab)
    if not audit:
        return "Open PageSpeed Insights for this URL, inspect the reported audits, then rerun with the same device and throttling. No specific resource fix was measured."
    target = next((r.get("url") or r.get("selector") for r in audit["resources"]), "the recorded page")
    return f"Address Lighthouse audit {audit['id']} ({audit['title']}) for {target}. Rerun with the same device and throttling to verify the change."[:400]


def _metric(metrics: dict, key: str) -> int | None:
    item = metrics.get(key, {})
    value = item.get("percentile") if isinstance(item, dict) else None
    return value if type(value) is int and _number(value) is not None else None


def _one(url: str, client: httpx.Client, key: str) -> tuple[list[Finding], bool, dict]:
    request_url = API + "?" + urlencode({"url": url, "strategy": "mobile", "category": "performance", "key": key})
    started = monotonic()
    response = get(client, request_url, same_origin=origin(API), timeout=15)
    summary: dict = {"url": _url(url), "status": "unavailable", "lab_score": None, "lcp_ms": None, "cls": None, "inp_ms": None,
                     "source": "pagespeed_insights", "device": "mobile", "retrieved_at": datetime.now(UTC).isoformat(),
                     "request_duration_ms": round((monotonic() - started) * 1000), "field_status": "unavailable",
                     "field_scope": "url", "field_source": "crux_p75", "field_url": None, "lab": None}
    if response is None or response.status_code != 200:
        return [], False, summary
    try:
        data = response.json()
        lighthouse = _dict(data.get("lighthouseResult"))
        experience = _dict(data.get("loadingExperience"))
        metrics = _dict(experience.get("metrics"))
    except (ValueError, AttributeError, TypeError):
        return [], False, summary
    findings: list[Finding] = []
    lab = _lab(lighthouse)
    summary["lab"] = lab
    summary["analysis_at"] = _text(data.get("analysisUTCTimestamp"))
    summary["field_url"] = _url(experience.get("id"))
    summary["field_scope"] = "origin" if summary["field_url"] and urlsplit(summary["field_url"]).path in {"", "/"} and urlsplit(url).path not in {"", "/"} else "url"
    score = lab["score"]
    if score is not None:
        summary["lab_score"] = score
        if score < 90:
            lcp = lab["metrics"]["lcp_ms"]
            opportunity = _opportunity(lab)
            context = f" Audit {opportunity['id']}: {opportunity['title']}." if opportunity else " No specific resource opportunity was retained."
            if opportunity and opportunity["estimated_savings_ms"] is not None:
                context += f" Estimated opportunity savings: {opportunity['estimated_savings_ms']} ms, not measured gains."
            elif opportunity and opportunity["metric_savings_ms"]:
                context += " Estimated metric savings: " + ", ".join(f"{k} {v} ms" for k, v in opportunity["metric_savings_ms"].items()) + ", not measured gains."
            findings.append(Finding(kind="performance", severity="medium" if score < 50 else "low",
                                    title=f"Mobile performance score {score}/100",
                                    detail=(f"Lighthouse mobile lab run. Lab LCP: {str(lcp) + ' ms' if lcp is not None else 'unavailable'}." + context)[:600],
                                    fix=_fix(lab), evidence=f"PageSpeed Insights, mobile lab: {score}; {summary['url']}"[:300]))
    if isinstance(metrics, dict):
        summary["lcp_ms"] = _metric(metrics, "LARGEST_CONTENTFUL_PAINT_MS")
        cls_hundredths = _metric(metrics, "CUMULATIVE_LAYOUT_SHIFT_SCORE")
        summary["cls"] = round(cls_hundredths / 100, 2) if cls_hundredths is not None else None
        summary["inp_ms"] = _metric(metrics, "INTERACTION_TO_NEXT_PAINT")
    values = (summary["lcp_ms"], summary["cls"], summary["inp_ms"])
    if any(value is not None for value in values):
        summary["status"] = "field_data"
        summary["field_status"] = "complete" if all(value is not None for value in values) else "partial"
        bad = []
        if summary["lcp_ms"] is not None and summary["lcp_ms"] > 2500:
            bad.append(f"LCP {summary['lcp_ms']} ms")
        if summary["cls"] is not None and summary["cls"] > 0.1:
            bad.append(f"CLS {summary['cls']}")
        if summary["inp_ms"] is not None and summary["inp_ms"] > 200:
            bad.append(f"INP {summary['inp_ms']} ms")
        if bad:
            path = _text(urlsplit(url).path or "/") or "/"
            findings.append(Finding(kind="performance", severity="medium", title=f"Mobile Core Web Vitals need work on {path[:60]}",
                                    detail=f"CrUX {summary['field_scope']}-level 75th-percentile mobile population data exceeds the good threshold: " + ", ".join(bad) + ". Lab opportunities are separate evidence, not proven causes of field results.",
                                    fix=_fix(lab), evidence=f"CrUX p75 ({summary['field_scope']}): {summary['field_url'] or summary['url']}"[:300]))
    elif summary["lab_score"] is not None or any(v is not None for v in lab["metrics"].values()):
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
