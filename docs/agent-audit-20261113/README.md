# Walkthru live agent audit

Read [the illustrated paper](walkthru-live-agent-audit.pdf) or open [the complete trace appendix](trace-appendix.html).

6 saved runs · 32 saved steps · 64 screenshots · 1302 recorded events.

## Main finding

The portfolio reached its project detail on baseline step 2, but an unprovable checkpoint kept progress at zero. The matched-route diagnostic completed in 2 steps. Reusing a stale route on a different theme failed, so the fix must ground predicates in each run. Scribb reproduced outcome misclassification even for an available Demo Journal flow.

Product fixes are specified, not shipped. Internal handlers and the local headless runner were exercised; deployed HTTP authentication and queue leasing were not.

## Saved account reports

- [portfolio](http://localhost:5173/app/runs/82b4b12715f84cee95a3644d83a59c95): looping, 5 steps. ID `82b4b12715f84cee95a3644d83a59c95`.
- [scribb](http://localhost:5173/app/runs/6cf033c601a74461ab9bad048bb07d07): agent_lost, 3 steps. ID `6cf033c601a74461ab9bad048bb07d07`.
- [tripverse](http://localhost:5173/app/runs/18012b2c8f0f46b08eed68c14226dd57): stuck, 10 steps. ID `18012b2c8f0f46b08eed68c14226dd57`.
- [portfolio-grounded](http://localhost:5173/app/runs/df76f76f5ab4435cbd29375459d577f9): agent_lost, 6 steps. ID `df76f76f5ab4435cbd29375459d577f9`.
- [scribb-supported](http://localhost:5173/app/runs/25544b01979342a7af25dbd701845ec0): agent_lost, 6 steps. ID `25544b01979342a7af25dbd701845ec0`.
- [portfolio-fixed-route](http://localhost:5173/app/runs/7f4bfdcb6ad84e2f8565b2d421564cb6): done, 2 steps. ID `7f4bfdcb6ad84e2f8565b2d421564cb6`.

Open those links in the local Walkthru app while signed into the requested account. Reports and uploaded frames remain private. Longer temporary development passes created by the audit were revoked; the prior Pro pass is active.

## Diagram source and exports

- [Complete graph source](walkthru-agent-flowchart.excalidraw) · [SVG](walkthru-agent-flowchart.svg)
- [Detailed state/context source](walkthru-agent.excalidraw) · [SVG](walkthru-agent.svg)
- [Observed traces source](live-traces.excalidraw) · [SVG](live-traces.svg) · [PNG](live-traces.png)

## Reproduction

Run `build_paper.py` using the existing bundled Python with reportlab/Pillow, then `verify_package.py` to add PDF navigation and validate/render outputs. Raw capture, controlled interventions and replay checks are in `evals/results/publishable-agent-audit-20261113/`. No new project dependency was installed.

Publication copy redacts the requested account email and provider organization identifiers. Original frame bytes are preserved. The package has not been published externally.
The sanitized [capture harness](harness/README.md) is included. [Account verification](account-verification.json) confirms all six reports belong to the requested account without disclosing its identifier.
