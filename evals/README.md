# Walkthru evaluations

`traps.json` is the versioned source of truth for the 18 seeded problems on the hard fixture. Each trap includes conservative `match` phrases used by the deterministic scorer.

## Score captured runs

Export each candidate as JSON:

```json
{
  "model": "free-pool",
  "report": {
    "summary": "...",
    "findings": [],
    "top_fixes": []
  },
  "steps": [],
  "usage": {
    "input_tokens": 0,
    "output_tokens": 0,
    "cost_usd": 0.0
  }
}
```

`cost_usd` is preferred when LangSmith or the provider supplies it. Otherwise pass separate token counts and current provider rates:

```powershell
apps/api/.venv/Scripts/python evals/runner.py free.json paid.json --input-per-million 1 --output-per-million 5
```

Use `--format json` for machine-readable output. The default is a Markdown comparison table.

The scorer searches only the captured report and steps. It never searches model names, reference answers, or fixture descriptions, which prevents reference leakage from inflating recall.

## Publish to LangSmith

Set `LANGSMITH_API_KEY`, then add `--langsmith`. The runner creates an immutable dataset name from the trap-manifest hash and publishes one code-evaluator experiment per candidate:

```powershell
apps/api/.venv/Scripts/python evals/runner.py free.json --langsmith --experiment-prefix walkthru-t9
```

LangSmith receives one example per trap, row-level found/not-found feedback, overall trap recall, and cost only when the captured usage can support an exact value.

## Quality gates

- All traps found: at least 80%
- Free run cost: at most $0.02
- Paid run cost: at most $0.20
- Reported cost must not be inferred from total tokens alone because input and output prices differ
