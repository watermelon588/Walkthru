"""PageSpeed-backed mobile performance evidence."""

import os
from math import isfinite

import httpx

from app.agent.schema import Finding
from app.scans.fetch import get


def scan(url: str, c: httpx.Client) -> tuple[list[Finding], bool]:
    key = os.environ.get("PAGESPEED_API_KEY")
    if not key:
        return [], False
    response = get(c, f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={url}&strategy=mobile&category=performance&key={key}")
    if response is None or response.status_code != 200:
        return [], False
    try:
        lighthouse = response.json().get("lighthouseResult", {})
    except ValueError:
        return [], False
    raw_score = lighthouse.get("categories", {}).get("performance", {}).get("score")
    if not isinstance(raw_score, (int, float)) or not isfinite(raw_score):
        return [], False
    score = round(raw_score * 100)
    if score >= 90:
        return [], True
    lcp = str(lighthouse.get("audits", {}).get("largest-contentful-paint", {}).get("displayValue", "not reported"))[:120]
    finding = Finding(
        kind="performance",
        severity="medium" if score < 50 else "low",
        title=f"Mobile performance score {score}/100",
        detail=f"Largest Contentful Paint: {lcp}. Slow pages lose visitors before the first click.",
        fix="Compress images, defer non-critical scripts, and serve static assets from a CDN.",
        evidence=f"PageSpeed Insights, mobile: {score}",
    )
    return [finding], True
