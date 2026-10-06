"""R-S7a measurement: Instant Scan reuse on owned loopback fixtures, offline.

Real API route, real scanners and report graph against evals/fixtures; the two model calls per scan are scripted (no
provider), outbound DNS is refused for every non-loopback host, and the database is an in-memory stand-in with
fixed-window rate limits. Latencies therefore cover local scanning and Walkthru's own work only: no network, model or
production database time. They show relative cost and avoided work, not production latency or savings.

    apps/api/.venv/Scripts/python evals/scan_reuse_bench.py      -> evals/results/scan-reuse/bench.json
"""

import json
import os
import random
import socket
import statistics
import sys
import threading
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "apps/api"), str(ROOT / "evals")]
os.environ.update(ALLOW_LOCAL_SCANS="1", LANGSMITH_TRACING="false", PROVIDER_USAGE="off")

_resolve = socket.getaddrinfo


def _loopback_only(host, *args, **kwargs):
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise socket.gaierror(f"offline benchmark: {host} blocked")
    return _resolve(host, *args, **kwargs)


socket.getaddrinfo = _loopback_only

from app import abuse, db, main, scan_reuse
from app.agent import runtime
from app.agent.schema import FirstImpression, Synthesis
from fastapi.testclient import TestClient
from serve import start

rows: dict[str, dict] = {}
windows: dict[str, tuple[float, int]] = {}
lock = threading.Lock()
model_calls = {"count": 0}


def insert_run(run_id, user_id, site, goal, persona, tier, logged_in, *, kind="test", public=False, group_id=None):
    with lock:
        rows[run_id] = {"id": run_id, "user_id": user_id, "site": site, "kind": kind, "tier": tier, "public": public, "status": "running",
                        "report": None, "created_at": datetime.now(UTC).isoformat()}


def set_report(run_id, report, status=None):
    with lock:
        rows[run_id] |= {"report": report, "status": status or rows[run_id]["status"]}


def recent_public_scan(site):
    since = datetime.now(UTC) - timedelta(minutes=10)
    with lock:
        found = [r for r in rows.values() if r["site"] == site and r["kind"] == "scan" and r["tier"] == "free" and r["user_id"] is None
                 and r["public"] and r["status"] == "done" and r["report"] is not None and datetime.fromisoformat(r["created_at"]) > since]
    return max(found, key=lambda r: r["created_at"], default=None)


def latest_public_scan_id(site):
    with lock:
        found = [r for r in rows.values() if r["site"] == site and r["kind"] == "scan" and r["tier"] == "free" and r["user_id"] is None]
    return max(found, key=lambda r: (r["created_at"], r["id"]), default={}).get("id")


def hit_rate_limit(key, limit, seconds):
    """Fixed windows, like migrations/0001 hit_rate_limit: returns seconds to wait, or 0."""
    with lock:
        start, count = windows.get(key, (time.time(), 0))
        if time.time() - start >= seconds:
            start, count = time.time(), 0
        windows[key] = (start, count + 1)
        return 0 if count + 1 <= limit else max(1, int(seconds - (time.time() - start)))


def call(schema, messages, fast=False, paid=False):
    with lock:
        model_calls["count"] += 1
    if schema is FirstImpression:
        return FirstImpression(what="A sample product.", who="Small teams.", first_click="Sign up.", trust=[], clarity=1), 0
    return Synthesis(summary="Scripted summary.", ux_findings=[], top_fixes=[]), 0


for name, fn in {"insert_run": insert_run, "set_report": set_report, "recent_public_scan": recent_public_scan,
                 "latest_public_scan_id": latest_public_scan_id, "hit_rate_limit": hit_rate_limit,
                 "free_runs_today": lambda kind="test": 0, "get_run": lambda run_id: rows.get(run_id)}.items():
    setattr(db, name, fn)
abuse.active_blocks = list
runtime.call = call
main.SCAN_LIMIT = 10_000  # one test client address sends every request
main.TARGET_SCANS = 10_000


def pct(values, q):
    values = sorted(values)
    return round(values[min(len(values) - 1, max(0, round(q * (len(values) - 1))))], 1) if values else None


def run(client, samples, site, fresh=False):
    began = time.perf_counter()
    response = client.post("/scans", json={"site": site, "fresh": fresh})
    elapsed = (time.perf_counter() - began) * 1000
    assert response.status_code == 200, response.text
    samples.append({"status": response.json()["reuse"]["status"], "ms": elapsed, "run_id": response.json()["run_id"]})


def summarize(name, samples, scans_before, calls_before):
    scans = sum(1 for r in rows.values() if r["kind"] == "scan") - scans_before
    calls = model_calls["count"] - calls_before
    by = {}
    for s in samples:
        by.setdefault(s["status"], []).append(s["ms"])
    served = len(samples)
    reused = len(by.get("reused", [])) + len(by.get("coalesced", []))
    per_scan = calls / scans if scans else None
    return {"workload": name, "requests": served, "scans_executed": scans, "model_calls_executed": calls,
            "reuse_rate": round(reused / served, 3) if served else None,
            "scans_avoided": served - scans, "model_calls_avoided": round((served - scans) * per_scan) if per_scan else None,
            "latency_ms": {k: {"n": len(v), "p50": pct(v, 0.5), "p95": pct(v, 0.95), "mean": round(statistics.fmean(v), 1)} for k, v in sorted(by.items())}}


def main_bench():
    servers = [start("easy", 8141), start("hard", 8142)]
    sites = ["http://127.0.0.1:8141/", "http://127.0.0.1:8142/", "http://127.0.0.1:8141/?ref=newsletter", "http://127.0.0.1:8142/?ref=ads"]
    client = TestClient(main.app)
    results = []
    try:
        # 1. Repeat visitors: 60 sequential requests over four exact URLs inside the ten-minute window.
        rng = random.Random(7)
        samples, s0, c0 = [], len(rows), model_calls["count"]
        for _ in range(60):
            run(client, samples, rng.choice(sites))
        results.append(summarize("repeat visitors, 4 pages, sequential", samples, s0, c0))

        # 2. A deploy changes the model chain (new scan_version), then 8 visitors hit one page at the same moment.
        runtime.GROQ_MODELS = [*runtime.GROQ_MODELS, "bench/new-model"]
        scan_reuse.version.cache_clear()
        samples, s0, c0 = [], len(rows), model_calls["count"]
        threads = [threading.Thread(target=run, args=(client, samples, sites[1])) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        results.append(summarize("after a deploy, 8 simultaneous visitors, 1 page", samples, s0, c0))

        # 3. Fresh fix checks always scan, even with a current saved result.
        samples, s0, c0 = [], len(rows), model_calls["count"]
        for _ in range(3):
            run(client, samples, sites[0], fresh=True)
        results.append(summarize("owner re-checks a fix with fresh=true, 3 times", samples, s0, c0))
    finally:
        for s in servers:
            s.shutdown()
    out = ROOT / "evals/results/scan-reuse"
    out.mkdir(parents=True, exist_ok=True)
    payload = {"measured_at": datetime.now(UTC).isoformat(), "run": uuid.uuid4().hex[:8], "scan_version_after_deploy": scan_reuse.version(),
               "scope": "Loopback fixtures, offline, scripted model, in-memory storage. Excludes network, model and production database time.",
               "results": results}
    (out / "bench.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main_bench()
