"""Offline audit reproductions, not application tests or a production implementation.

Run from repo root: apps/api/.venv/Scripts/python docs/ai-citation-diagnostic.py
Imports only the pure citation evidence module. Makes no network/provider calls.
"""

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))
from app.citation_evidence import analyze, groq_sources  # noqa: E402


def wilson(k, n):
    z = 1.959963984540054
    p = k / n
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return [round(100 * max(0, center - half), 2), round(100 * min(1, center + half), 2)]


collision = analyze("TripVerse is an iOS travel app by another publisher.", [],
                    "TripVerse", "tripverse-0.vercel.app", [], citation_status="not_applicable")
answer = "Choose [B](https://b.example/), then [A](https://a.example/)."
sources, status = groq_sources({"content": answer, "executed_tools": [{"type": "browser_search",
    "search_results": {"results": [{"url": "https://a.example/"}, {"url": "https://b.example/"}]}}]})
order = analyze(answer, sources, "A", "a.example", [{"name": "B", "domain": "b.example"}], citation_status=status)
output = {
    "scope": "offline current-code diagnostic; no real consumer observations",
    "name_collision": collision,
    "retrieval_order_vs_answer_order": order,
    "independent_bernoulli_examples_not_pooled_panel_intervals": [
        {"citations": k, "checks": n, "rate_pct": round(100 * k / n, 2), "wilson_95_pct": wilson(k, n)}
        for k, n in [(1, 30), (0, 30), (1, 14), (18, 100)]
    ],
    "collection_cost_estimates_usd": [
        {"runs": n, "dataforseo_standard": round(n * 0.0012, 3),
         "dataforseo_live": round(n * 0.004, 3), "bright_data_payg": round(n * 0.0015, 3)}
        for n in [280, 1200, 3600]
    ],
}
print(json.dumps(output, indent=2))
