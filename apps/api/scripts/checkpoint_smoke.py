"""Two-process restart drill using the real persona graph and synthetic observations. No model or site calls.

From apps/api: python -m scripts.checkpoint_smoke start smoke-<UUID hex>
Restart the API, then: python -m scripts.checkpoint_smoke resume smoke-<same UUID hex>
Uses CHECKPOINTER=postgres and the configured checkpoint database. Resume deletes only this smoke thread.
"""

import argparse
import json
import re

from langgraph.types import Command

from app.agent import runtime
from app.agent.persona import build_graph
from app.agent.schema import PersonaStep


class ScriptedModel:
    def __init__(self, phase: str):
        self.phase = phase
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        return PersonaStep(thought="Read the guide" if self.phase == "start" else "The guide is open",
                           action="click" if self.phase == "start" else "done",
                           target_id=1 if self.phase == "start" else None, confusion=0)


def run(phase: str, thread: str) -> None:
    if phase not in {"start", "resume"} or not re.fullmatch(r"smoke-[a-f0-9]{32}", thread):
        raise ValueError("Use start or resume and a smoke- prefix followed by 32 UUID hex characters")
    from langgraph.checkpoint.postgres import PostgresSaver

    saver = runtime.checkpointer()
    if not isinstance(saver, PostgresSaver):
        raise TypeError("The restart drill requires CHECKPOINTER=postgres")
    model = ScriptedModel(phase)
    graph = build_graph(model, saver)
    config = {"configurable": {"thread_id": thread}}
    observation = {"url": "https://fixture.invalid/", "title": "Guide", "text": "Synthetic restart evidence",
                   "elements": [{"id": 1, "tag": "a", "text": "Guide", "href": "https://fixture.invalid/guide"}]}
    if phase == "start":
        if graph.get_state(config).values:
            raise RuntimeError("This smoke thread already exists; use a fresh UUID")
        graph.invoke({"run_id": thread, "site": observation["url"], "goal": "read the guide", "persona": "first_timer",
                      "logged_in": False, "verified": False, "observation": observation, "first_text": observation["text"],
                      "steps": [], "status": "running", "tokens": 0, "max_steps": 4}, config)
        state = graph.get_state(config)
        assert state.next and len(state.values["steps"]) == 1 and model.calls == 1
    else:
        state = graph.get_state(config)
        assert state.next and len(state.values["steps"]) == 1 and model.calls == 0, "Pending action was not recovered"
        graph.invoke(Command(resume={"observation": observation | {"url": "https://fixture.invalid/guide", "elements": []}}), config)
        state = graph.get_state(config)
        assert not state.next and state.values["status"] == "done" and len(state.values["steps"]) == 2 and model.calls == 1
        assert state.values["first_text"] == observation["text"]
        assert state.values["steps"][0]["thought"] == "Read the guide"
        saver.delete_thread(thread)
        assert not graph.get_state(config).values
    print(json.dumps({"thread": thread, "phase": phase, "steps": len(state.values["steps"]), "status": state.values["status"]}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("start", "resume"))
    parser.add_argument("thread")
    args = parser.parse_args()
    try:
        run(args.phase, args.thread)
    finally:
        runtime.close_checkpointer()
