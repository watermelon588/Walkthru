"""Score saved Walkthru runs against the seeded fixture traps.

The runner is deliberately offline-first: a captured run stays the source of truth,
so comparing models never reruns a browser flow by accident. Pass --langsmith to
publish the same deterministic code evaluation as an experiment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

KINDS = ("ux", "seo", "security")


@dataclass(frozen=True)
class Trap:
    id: str
    kind: str
    match: tuple[str, ...]


@dataclass(frozen=True)
class KindScore:
    found: int
    total: int

    @property
    def recall(self) -> float:
        return self.found / self.total if self.total else 0.0


@dataclass(frozen=True)
class EvaluationResult:
    model: str
    found_ids: list[str]
    missed_ids: list[str]
    found: int
    total: int
    recall: float
    by_kind: dict[str, KindScore]
    cost_usd: float | None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["by_kind"] = {kind: asdict(score) | {"recall": score.recall} for kind, score in self.by_kind.items()}
        return data


def load_traps(path: str | Path) -> list[Trap]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise TypeError("trap manifest must be a JSON array")
    traps: list[Trap] = []
    for item in raw:
        aliases = item.get("match") if isinstance(item, dict) else None
        trap_id = item.get("id") if isinstance(item, dict) else None
        valid_aliases = isinstance(aliases, list) and aliases and all(isinstance(alias, str) and alias.strip() for alias in aliases)
        if not isinstance(trap_id, str) or not trap_id.strip() or item.get("kind") not in KINDS or not valid_aliases:
            raise ValueError("every trap needs a non-empty id, a valid kind and non-empty match phrases")
        traps.append(Trap(id=str(item["id"]), kind=item["kind"], match=tuple(str(alias) for alias in aliases)))
    ids = [trap.id for trap in traps]
    if len(ids) != len(set(ids)):
        raise ValueError("trap ids must be unique")
    return traps


def _text_values(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for nested in value.values():
            yield from _text_values(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _text_values(nested)


def _candidate_text(candidate: dict[str, Any]) -> str:
    report = candidate.get("report")
    if not isinstance(report, dict):
        report = candidate if "findings" in candidate or "summary" in candidate else {}
    selected = {
        "summary": report.get("summary", ""),
        "first_impression": report.get("first_impression", {}),
        "findings": report.get("findings", []),
        "top_fixes": report.get("top_fixes", []),
        "steps": candidate.get("steps", []),
    }
    text = "\n".join(_text_values(selected)).casefold()
    return re.sub(r"\s+", " ", text)


def calculate_cost(usage: dict[str, Any], input_per_million: float | None, output_per_million: float | None) -> float | None:
    explicit = usage.get("cost_usd")
    if isinstance(explicit, int | float) and not isinstance(explicit, bool) and explicit >= 0:
        return float(explicit)
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    if not isinstance(input_tokens, int | float) or not isinstance(output_tokens, int | float):
        return None
    if input_per_million is None or output_per_million is None:
        return None
    if input_tokens < 0 or output_tokens < 0 or input_per_million < 0 or output_per_million < 0:
        raise ValueError("token counts and rates must be non-negative")
    return (float(input_tokens) * input_per_million + float(output_tokens) * output_per_million) / 1_000_000


def score_candidate(
    candidate: dict[str, Any],
    traps: list[Trap],
    *,
    input_per_million: float | None = None,
    output_per_million: float | None = None,
) -> EvaluationResult:
    text = _candidate_text(candidate)
    found_ids = [trap.id for trap in traps if any(alias.casefold() in text for alias in trap.match)]
    found_set = set(found_ids)
    by_kind = {}
    for kind in KINDS:
        kind_traps = [trap for trap in traps if trap.kind == kind]
        by_kind[kind] = KindScore(found=sum(trap.id in found_set for trap in kind_traps), total=len(kind_traps))
    usage = candidate.get("usage") if isinstance(candidate.get("usage"), dict) else {}
    return EvaluationResult(
        model=str(candidate.get("model") or "unknown"),
        found_ids=found_ids,
        missed_ids=[trap.id for trap in traps if trap.id not in found_set],
        found=len(found_ids),
        total=len(traps),
        recall=len(found_ids) / len(traps) if traps else 0.0,
        by_kind=by_kind,
        cost_usd=calculate_cost(usage, input_per_million, output_per_million),
    )


def format_markdown(results: list[EvaluationResult]) -> str:
    lines = [
        "| Model | Overall | UX | SEO | Security | Cost / run |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        cells = [f"{score.found}/{score.total} ({score.recall:.0%})" for score in result.by_kind.values()]
        cost = "unknown" if result.cost_usd is None else f"${result.cost_usd:.4f}"
        lines.append(f"| {result.model} | {result.found}/{result.total} ({result.recall:.0%}) | {' | '.join(cells)} | {cost} |")
    return "\n".join(lines)


def publish_to_langsmith(traps: list[Trap], result: EvaluationResult, experiment_prefix: str) -> None:
    """Publish one captured candidate as an offline code-evaluator experiment."""
    from langsmith import Client

    fingerprint = hashlib.sha256(json.dumps([asdict(trap) for trap in traps], sort_keys=True).encode()).hexdigest()[:10]
    dataset_name = f"walkthru-seeded-traps-{fingerprint}"
    client = Client()
    if not client.has_dataset(dataset_name=dataset_name):
        client.create_dataset(dataset_name, description="Walkthru hard-fixture traps. Versioned by manifest hash.")
        client.create_examples(
            dataset_name=dataset_name,
            examples=[
                {"inputs": {"trap_id": trap.id}, "outputs": {"found": True}, "metadata": {"kind": trap.kind, "match": list(trap.match)}}
                for trap in traps
            ],
        )

    found = set(result.found_ids)

    def target(inputs: dict) -> dict:
        return {"found": inputs["trap_id"] in found, "model": result.model, "cost_usd": result.cost_usd}

    def trap_found(outputs: dict, reference_outputs: dict) -> bool:
        return outputs["found"] == reference_outputs["found"]

    def trap_recall(outputs: list[dict]) -> dict:
        return {"key": "trap_recall", "score": sum(item["found"] for item in outputs) / len(outputs)}

    def run_cost(outputs: list[dict]) -> dict:
        return {"key": "cost_usd", "score": outputs[0]["cost_usd"]}

    summary_evaluators = [trap_recall]
    if result.cost_usd is not None:
        summary_evaluators.append(run_cost)

    client.evaluate(
        target,
        data=dataset_name,
        evaluators=[trap_found],
        summary_evaluators=summary_evaluators,
        experiment_prefix=experiment_prefix,
        description=f"Captured Walkthru hard-fixture run for {result.model}.",
        metadata={"model": result.model, "cost_usd": result.cost_usd},
        max_concurrency=1,
    )


def _load_candidates(paths: list[Path]) -> list[dict[str, Any]]:
    candidates = []
    for path in paths:
        raw = json.loads(path.read_text(encoding="utf-8"))
        rows = raw if isinstance(raw, list) else [raw]
        for row in rows:
            if not isinstance(row, dict):
                raise TypeError(f"{path} must contain a JSON object or array of objects")
            row.setdefault("model", path.stem)
            candidates.append(row)
    return candidates


def main() -> None:
    parser = argparse.ArgumentParser(description="Score captured Walkthru runs against the seeded hard-site traps.")
    parser.add_argument("inputs", nargs="+", type=Path, help="Captured run/report JSON files")
    parser.add_argument("--traps", type=Path, default=Path(__file__).with_name("traps.json"))
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--input-per-million", type=float, help="USD per million input tokens")
    parser.add_argument("--output-per-million", type=float, help="USD per million output tokens")
    parser.add_argument("--langsmith", action="store_true", help="Publish each result as a LangSmith experiment")
    parser.add_argument("--experiment-prefix", default="walkthru-t9")
    args = parser.parse_args()

    traps = load_traps(args.traps)
    candidates = _load_candidates(args.inputs)
    results = [
        score_candidate(candidate, traps, input_per_million=args.input_per_million, output_per_million=args.output_per_million)
        for candidate in candidates
    ]
    if args.langsmith:
        for candidate, result in zip(candidates, results, strict=True):
            publish_to_langsmith(traps, result, f"{args.experiment_prefix}-{result.model}")
    if args.format == "json":
        print(json.dumps([result.to_dict() for result in results], indent=2))
    else:
        print(format_markdown(results))


if __name__ == "__main__":
    main()
