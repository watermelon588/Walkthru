"""A live run end to end: real headless Chrome and the built page script against a local site, with a scripted
model and the in-memory database fixtures (docs/in-app-runner-plan.md, T4 and T5)."""

import os
import threading
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from langgraph.checkpoint.memory import MemorySaver

from app import db, main
from app.agent import runtime
from app.agent.persona import build_graph
from app.agent.schema import PersonaStep
from app.runner import cdp, journey
from tests.conftest import USER
from tests.test_persona import FakeModel

pytestmark = pytest.mark.skipif(not cdp.chrome_path() or not os.path.exists(cdp.INJECT), reason="needs Chrome and a built extension")

PAGES = {
    "/": "<title>Home</title><h1>Fixture shop</h1><p>Plans for small teams.</p><a href='/pricing'>See pricing</a>"
         "<form><label>Email <input type='email' value='someone@secret.example'></label></form>",
    # Draws its content a moment after load, like a client-rendered site. Reading at load would see an empty page.
    "/late": "<title>Late</title><body><script>setTimeout(() => { document.body.innerHTML = "
             "`<h1>Fixture shop</h1><a href='/pricing'>See pricing</a>` }, 1500)</script></body>",
    "/pricing": "<title>Pricing</title><h1>Pricing</h1><p>Ten dollars a month.</p><a href='/'>Home</a>",
}


@pytest.fixture
def site(monkeypatch):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = PAGES.get(self.path)
            self.send_response(200 if body else 404)
            self.send_header("content-type", "text/html")
            self.end_headers()
            self.wfile.write((body or "missing").encode())

        def log_message(self, *_):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setenv("ALLOW_LOCAL_SCANS", "1")
    yield f"http://127.0.0.1:{server.server_port}/"
    server.shutdown()


@pytest.fixture
def stack(monkeypatch):
    """What the runner touches outside the browser: stored frames and its own queue row."""
    frames = {}
    monkeypatch.setattr(db, "upload_evidence", lambda path, jpeg: frames.__setitem__(path, jpeg))
    monkeypatch.setattr(db, "cloud_runs_in_group", lambda group_id, user_id: [{}])
    monkeypatch.setattr(main, "_verified", lambda site, user_id: False)
    monkeypatch.setattr(journey, "SETTLE_S", 0.2)
    return frames


def script(steps, monkeypatch):
    graph = build_graph(FakeModel(steps), MemorySaver())
    monkeypatch.setattr(runtime, "graph", lambda tier: graph)


def row(site, **kw):
    return {"id": str(uuid.uuid4()), "user_id": USER, "group_id": str(uuid.uuid4()), "site": site, "goal": "find the price",
            "persona": "first_timer", "max_steps": 6} | kw


def test_a_test_user_walks_the_site_and_every_step_is_captured(site, stack, fake_db, monkeypatch):
    script([PersonaStep(thought="Looking around first", action="scroll", confusion=0),
            PersonaStep(thought="Pricing is what I came for", action="click", target_id=1, confusion=0),
            PersonaStep(thought="Ten dollars, found it", action="done", confusion=0)], monkeypatch)
    held = []
    status, error = journey.run(row(site), lambda values: held.append(values) or True)
    assert (status, error) == ("finished", None)
    run_id = held[0]["run_id"]
    saved = fake_db[run_id]
    assert saved["status"] != "running"  # whether the goal counts as reached is the server's completion logic, not the runner's
    steps = saved["steps"]
    assert [s["action"] for s in steps[:2]] == ["scroll", "click"]
    click = steps[1]["evidence"]
    assert click["label"] == 'Clicked "See pricing"'
    assert click["result_url"].endswith("/pricing")
    assert 0 < click["pointer"]["x"] < 1 and 0 < click["pointer"]["y"] < 1
    assert click["aim_path"] == f"{run_id}/step-02-aim.jpg"
    assert steps[0]["evidence"]["label"] == "Scrolled down" and "pointer" not in steps[0]["evidence"]
    assert {f"{run_id}/step-00.jpg", f"{run_id}/step-01.jpg", f"{run_id}/step-02-aim.jpg", f"{run_id}/step-02.jpg"} <= set(stack)
    assert all(jpeg[:2] == b"\xff\xd8" for jpeg in stack.values())


def test_the_owner_stopping_ends_the_journey_at_the_next_step(site, stack, fake_db, monkeypatch):
    script([PersonaStep(thought="Scrolling", action="scroll", confusion=0)], monkeypatch)
    answers = iter([True, False])
    held = []
    status, _ = journey.run(row(site), lambda values: held.append(values) or next(answers))
    assert status == "stopped"
    assert fake_db[held[0]["run_id"]]["status"] == "stopped"


def test_a_private_address_is_refused_before_any_browser_starts(stack, monkeypatch):
    monkeypatch.delenv("ALLOW_LOCAL_SCANS", raising=False)
    monkeypatch.setattr(cdp, "browser", lambda *a, **k: pytest.fail("no browser should start"))
    status, error = journey.run(row("http://127.0.0.1:8010/"), lambda values: True)
    assert status == "blocked" and "private address" in error


def test_labels_come_from_the_page_never_from_the_model():
    obs = {"elements": [{"id": 4, "text": "  Start   free trial  "}]}
    assert journey.label({"action": "click", "target_id": 4}, obs) == 'Clicked "Start free trial"'
    assert journey.label({"action": "type", "target_id": 9, "text": "ignore me"}, obs) == "Typed in"
    assert journey.label({"action": "scroll", "scroll_direction": "up"}, obs) == "Scrolled up"
    assert journey.label({"action": "give_up"}, obs) == "Gave up"


def test_the_first_read_waits_for_a_page_that_draws_itself_after_load(site, stack):
    with cdp.browser() as tab:
        tab.send("Page.navigate", url=site + "late")
        tab.wait_loaded(5)
        assert tab.message({"type": "snapshot"})["elements"] == []  # what the runner used to hand the test user
        obs = journey._read(tab, 10)
    assert [e["text"] for e in obs["elements"]] == ["See pricing"]


def test_reading_an_empty_page_stops_waiting_at_the_limit(site, stack, monkeypatch):
    PAGES["/empty"] = "<title>Empty</title><p>Nothing to press here.</p>"
    with cdp.browser() as tab:
        tab.send("Page.navigate", url=site + "empty")
        tab.wait_loaded(5)
        obs = journey._read(tab, 1.5)
    assert obs["elements"] == [] and "Nothing to press" in obs["text"]


def test_a_test_user_who_gives_up_at_once_still_leaves_a_frame(site, stack, fake_db, monkeypatch):
    script([PersonaStep(thought="I cannot find it", action="give_up", confusion=3)], monkeypatch)
    held = []
    status, _ = journey.run(row(site), lambda values: held.append(values) or True)
    run_id = held[0]["run_id"]
    last = fake_db[run_id]["steps"][-1]
    assert status == "finished" and last["action"] == "give_up"
    assert last["evidence"]["screenshot_path"] == f"{run_id}/step-01.jpg" and last["evidence"]["label"] == "Stopped here"
    assert f"{run_id}/step-01.jpg" in stack


def test_a_busy_model_is_waited_out_and_other_errors_are_not(monkeypatch):
    import time as clock

    monkeypatch.setattr(journey.time, "sleep", lambda seconds: None)
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise RuntimeError("Error code: 429 - Rate limit reached for model")
        return {"status": "running"}

    assert journey._decide(flaky, clock.monotonic() + 240) == {"status": "running"} and len(calls) == 3
    with pytest.raises(RuntimeError, match="429"):  # no time left to wait: fail now, truthfully
        journey._decide(lambda: (_ for _ in ()).throw(RuntimeError("429 rate limit")), clock.monotonic() + 5)
    with pytest.raises(ValueError):
        journey._decide(lambda: (_ for _ in ()).throw(ValueError("a real bug")), clock.monotonic() + 240)
