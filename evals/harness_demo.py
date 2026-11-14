"""Export a scripted graph demonstration, without providers, API accounts or site traffic.

From the repository root: apps/api/.venv/Scripts/python evals/harness_demo.py
The snapshots are synthetic test inputs, explicitly not live-run evidence.
"""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from app.agent.persona import build_graph
from app.agent.schema import PersonaStep
from app.agent.typesafe import JevDecision


class Scripted:
    calls = 0

    def decide(self, state, messages):
        self.calls += 1
        return JevDecision(PersonaStep(action="click", target_id=1, thought="Open the workspace", confusion=0), 0,
                           {"provider": "scripted_fixture"})


def observation(*, visible=True, created=False, revision="initial"):
    return {"url": "https://fixture.invalid/", "title": "Synthetic workspace fixture", "navigation_version": 3,
            "revision": revision, "text": "Workspace created" if created else "Create your workspace",
            "elements": [{"id": 1, "tag": "button", "text": "Create workspace", "in_view": visible}]}


def run(name, checkpoint, before, replies):
    model = Scripted()
    graph = build_graph(model, MemorySaver())
    config = {"configurable": {"thread_id": name}}
    initial = {"run_id": name, "goal": 'Create a workspace and show "Workspace created"', "site": "https://fixture.invalid/",
               "start_url": "https://fixture.invalid/", "persona": "skeptic", "verified": True, "status": "running",
               "steps": [], "observation": before, "plan": {"intent": "Create workspace", "checkpoints": [checkpoint]}}
    state = graph.invoke(initial, config)
    transitions = [{"observation": before, "pending_action": state["steps"][-1], "context": state["harness_context"]}]
    for reply in replies:
        state = graph.invoke(Command(resume={"observation": reply}), config)
        transitions.append({"observation": reply, "status": state["status"], "confirmed": state.get("plan_done", 0),
                            "pending_action": state["steps"][-1] if "__interrupt__" in state else None,
                            "context": state.get("harness_context")})
    return {"scenario": name, "status": state["status"], "model_calls": model.calls, "transitions": transitions,
            "steps": state["steps"], "harness_worklog": state["harness_worklog"]}


if __name__ == "__main__":
    examples = [run("transient_target", {"description": "Workspace created", "kind": "outcome", "text_contains": "Workspace created"},
                    observation(visible=False), [observation(revision="fresh"), observation(created=True, revision="done")]),
                run("missing_finish_condition", {"description": "Create workspace", "kind": "outcome", "text_contains": None},
                    observation(), [observation(created=True, revision=f"after-{i}") for i in range(3)])]
    output = {"evidence_type": "scripted graph fixture; no live site or account", "scenarios": examples}
    path = ROOT / "docs/harness-rebuild-demo.json"
    path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"artifact": str(path), "results": [{"scenario": e["scenario"], "status": e["status"], "model_calls": e["model_calls"]} for e in examples]}))
