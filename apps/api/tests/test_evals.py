"""Deterministic scoring for seeded-trap evaluation reports."""

import json
import os
import sys
from types import SimpleNamespace

import pytest

EVALS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "evals")
sys.path.insert(0, EVALS)

from runner import calculate_cost, format_markdown, load_traps, publish_to_langsmith, score_candidate


def test_score_candidate_reports_overall_and_per_kind_recall():
    traps = load_traps(os.path.join(EVALS, "traps.json"))
    candidate = {
        "model": "fixture-model",
        "report": {
            "summary": "Signup is hard to find and the form submit gives no feedback.",
            "findings": [
                {"kind": "seo", "title": "Missing meta description", "detail": "No description was found."},
                {"kind": "security", "title": "No Content-Security-Policy", "detail": "The header is absent."},
            ],
            "top_fixes": [],
        },
        "steps": [],
        "usage": {"cost_usd": 0.0123},
    }

    result = score_candidate(candidate, traps)

    assert result.model == "fixture-model"
    assert result.found_ids == ["U1", "U2", "S1", "X1"]
    assert result.found == 4
    assert result.total == 18
    assert result.recall == pytest.approx(4 / 18)
    assert result.by_kind["ux"].found == 2
    assert result.by_kind["seo"].found == 1
    assert result.by_kind["security"].found == 1
    assert result.cost_usd == pytest.approx(0.0123)


def test_score_candidate_does_not_search_reference_or_model_metadata():
    traps = load_traps(os.path.join(EVALS, "traps.json"))
    candidate = {
        "model": "missing meta description and exposed sensitive file",
        "report": {"summary": "Everything looked good.", "findings": [], "top_fixes": []},
        "reference": {"expected": "missing meta description"},
    }

    result = score_candidate(candidate, traps)

    assert result.found == 0
    assert result.cost_usd is None


def test_calculate_cost_uses_explicit_cost_before_token_rates():
    assert calculate_cost({"cost_usd": 0.25, "input_tokens": 1_000_000, "output_tokens": 1_000_000}, 1, 1) == pytest.approx(0.25)


def test_calculate_cost_uses_separate_input_and_output_rates():
    usage = {"input_tokens": 2_000_000, "output_tokens": 500_000}

    assert calculate_cost(usage, input_per_million=1.0, output_per_million=4.0) == pytest.approx(4.0)


def test_calculate_cost_returns_none_without_enough_usage_data():
    assert calculate_cost({"total_tokens": 1000}, input_per_million=1.0, output_per_million=4.0) is None


def test_calculate_cost_rejects_negative_usage():
    with pytest.raises(ValueError, match="non-negative"):
        calculate_cost({"input_tokens": -1, "output_tokens": 10}, input_per_million=1.0, output_per_million=4.0)


def test_load_traps_rejects_empty_match_phrases(tmp_path):
    manifest = tmp_path / "traps.json"
    manifest.write_text(json.dumps([{"id": "U1", "kind": "ux", "match": [""]}]), encoding="utf-8")

    with pytest.raises(ValueError, match="non-empty match phrases"):
        load_traps(manifest)


def test_format_markdown_makes_unknown_cost_explicit():
    traps = load_traps(os.path.join(EVALS, "traps.json"))
    result = score_candidate({"model": "free", "report": {"summary": "", "findings": []}}, traps)

    table = format_markdown([result])

    assert "| free | 0/18 (0%) |" in table
    assert table.endswith("| unknown |")


def test_langsmith_publish_omits_unknown_cost_metric(monkeypatch):
    traps = load_traps(os.path.join(EVALS, "traps.json"))
    result = score_candidate({"model": "free", "report": {"summary": "", "findings": []}}, traps)

    class FakeClient:
        def __init__(self):
            self.examples = []
            self.evaluate_kwargs = {}

        def has_dataset(self, **kwargs):
            return False

        def create_dataset(self, *args, **kwargs):
            return None

        def create_examples(self, **kwargs):
            self.examples = kwargs["examples"]

        def evaluate(self, *args, **kwargs):
            self.evaluate_kwargs = kwargs

    client = FakeClient()
    monkeypatch.setitem(sys.modules, "langsmith", SimpleNamespace(Client=lambda: client))

    publish_to_langsmith(traps, result, "walkthru-test")

    assert len(client.examples) == 18
    assert [evaluator.__name__ for evaluator in client.evaluate_kwargs["summary_evaluators"]] == ["trap_recall"]
