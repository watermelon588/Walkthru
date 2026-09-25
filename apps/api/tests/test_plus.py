"""Plus: custom test users and several test users per report (P4.2), report branding for the PDF (P4.3)."""

import base64
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import MemorySaver

from app import db, plus
from app.agent import runtime
from app.agent.persona import build_graph
from app.agent.schema import PersonaStep
from app.main import app
from tests.conftest import USER

OTHER = "00000000-0000-0000-0000-000000000002"
PNG = "data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\0" * 64).decode()


class Recorder:
    """A fake test user that scrolls and remembers the prompts it was given."""

    def __init__(self):
        self.prompts: list[str] = []

    def invoke(self, messages):
        self.prompts.append(messages[0].content if hasattr(messages[0], "content") else str(messages[0]))
        return PersonaStep(thought="looking around", action="scroll", confusion=0)


@pytest.fixture
def model(monkeypatch):
    rec = Recorder()
    g = build_graph(rec, MemorySaver())
    monkeypatch.setattr(runtime, "graph", lambda tier: g)
    return rec


def grant(passes, plan="plus", user=USER):
    now = datetime.now(UTC)
    passes.append({"user_id": user, "plan": plan, "starts_at": (now - timedelta(days=1)).isoformat(),
                   "expires_at": (now + timedelta(days=29)).isoformat(), "runs_granted": 150})


@pytest.fixture
def tables(monkeypatch):
    t = {"test_users": {}, "brands": {}}

    def create(user_id, name, description):
        row = {"id": str(uuid.uuid4()), "user_id": user_id, "name": name, "description": description, "created_at": datetime.now(UTC).isoformat()}
        t["test_users"][row["id"]] = row
        return row

    def delete(user_id, test_user_id):
        row = t["test_users"].get(test_user_id)
        if row and row["user_id"] == user_id:
            del t["test_users"][test_user_id]
            return True
        return False

    monkeypatch.setattr(db, "test_users_for", lambda user_id: [r for r in t["test_users"].values() if r["user_id"] == user_id])
    monkeypatch.setattr(db, "get_test_user", lambda user_id, tid: next((r for r in t["test_users"].values() if r["id"] == tid and r["user_id"] == user_id), None))
    monkeypatch.setattr(db, "create_test_user", create)
    monkeypatch.setattr(db, "delete_test_user", delete)
    monkeypatch.setattr(db, "get_brand", lambda user_id: t["brands"].get(user_id))
    monkeypatch.setattr(db, "save_brand", lambda user_id, values: t["brands"].__setitem__(user_id, values))
    monkeypatch.setattr(db, "delete_brand", lambda user_id: t["brands"].pop(user_id, None))
    return t


def start(client, **kw):
    obs = {"url": "https://fixture.test/", "title": "t", "elements": [], "text": "hello"}
    return client.post("/runs", json={"site": "https://fixture.test", "goal": "sign up", "observation": obs} | kw)


AGENCY = {"name": "Agency owner on a train", "description": "Runs a small design agency, reads on a phone between meetings, wants pricing and a case study fast."}


# ---------- custom test users ----------


def test_custom_test_users_are_plus_only(tables, passes):
    c = TestClient(app)
    assert c.post("/me/test-users", json=AGENCY).status_code == 402
    grant(passes, "pro")
    r = c.post("/me/test-users", json=AGENCY)
    assert r.status_code == 402 and "Plus plan" in r.json()["detail"]


def test_create_list_and_delete_test_users(tables, passes):
    grant(passes)
    c = TestClient(app)
    made = c.post("/me/test-users", json={"name": "  Agency   owner ", "description": AGENCY["description"]}).json()
    assert made["name"] == "Agency owner"
    assert [t["name"] for t in c.get("/me/test-users").json()] == ["Agency owner"]
    assert c.post("/me/test-users", json={"name": "agency owner", "description": AGENCY["description"]}).status_code == 409
    assert c.delete(f"/me/test-users/{made['id']}").status_code == 200
    assert c.delete(f"/me/test-users/{made['id']}").status_code == 404
    assert c.get("/me/test-users").json() == []


@pytest.mark.parametrize("body, status", [
    ({"name": "", "description": AGENCY["description"]}, 422),
    ({"name": "x" * 41, "description": AGENCY["description"]}, 422),
    ({"name": "Buyer", "description": AGENCY["description"]}, 422),  # a built-in test user's key
    ({"name": "Phone user", "description": AGENCY["description"]}, 422),  # a built-in test user's label
    ({"name": "Busy", "description": "short"}, 422),
    ({"name": "Busy", "description": "x" * 301}, 422),
    ({"name": "Busy", "description": AGENCY["description"], "user_id": OTHER}, 422),  # no extra fields
])
def test_test_user_validation(tables, passes, body, status):
    grant(passes)
    assert TestClient(app).post("/me/test-users", json=body).status_code == status


def test_at_most_ten_custom_test_users(tables, passes):
    grant(passes)
    c = TestClient(app)
    for i in range(plus.MAX_TEST_USERS):
        assert c.post("/me/test-users", json={"name": f"User {i}", "description": AGENCY["description"]}).status_code == 200
    assert c.post("/me/test-users", json={"name": "One more", "description": AGENCY["description"]}).status_code == 409


def test_a_run_with_a_custom_test_user_uses_its_words(tables, passes, fake_db, model):
    grant(passes)
    c = TestClient(app)
    made = c.post("/me/test-users", json=AGENCY).json()
    r = start(c, persona=f"custom:{made['id']}")
    assert r.status_code == 200, r.text
    assert fake_db[r.json()["run_id"]]["persona"] == "Agency owner on a train"  # every page shows the name
    assert "You are Agency owner on a train, Runs a small design agency" in model.prompts[0]


def test_custom_test_users_are_refused_off_plus_and_across_accounts(tables, passes, model):
    c = TestClient(app)
    grant(passes)
    made = c.post("/me/test-users", json=AGENCY).json()
    tables["test_users"][made["id"]]["user_id"] = OTHER  # now it belongs to someone else
    assert start(c, persona=f"custom:{made['id']}").status_code == 404
    assert start(c, persona="custom:not-a-uuid").status_code == 404
    passes.clear()
    grant(passes, "pro")
    assert start(c, persona=f"custom:{uuid.uuid4()}").status_code == 403


# ---------- several test users per report ----------


def test_runs_of_one_group_share_its_id(passes, fake_db, model):
    grant(passes)
    c = TestClient(app)
    group = str(uuid.uuid4())
    first = start(c, persona="first_timer", group_id=group).json()["run_id"]
    second = start(c, persona="skeptic", group_id=group).json()["run_id"]
    assert fake_db[first]["group_id"] == fake_db[second]["group_id"] == group
    assert start(c, persona="buyer").status_code == 200  # a single run needs no group


def test_groups_are_plus_only_owned_and_small(passes, fake_db, model):
    c = TestClient(app)
    grant(passes, "pro")
    assert start(c, group_id=str(uuid.uuid4())).status_code == 403
    passes.clear()
    grant(passes)
    theirs = str(uuid.uuid4())
    db.insert_run("f" * 32, OTHER, "https://fixture.test", "sign up", "buyer", "paid", False, group_id=theirs)
    assert start(c, group_id=theirs).status_code == 409  # never join another account's group
    full = str(uuid.uuid4())
    for i in range(plus.MAX_GROUP):
        assert start(c, group_id=full).status_code == 200
    assert start(c, group_id=full).status_code == 409
    assert start(c, group_id="not-a-uuid").status_code == 422


# ---------- branding for the printed report ----------


def test_branding_is_plus_only_and_turns_off_when_plus_lapses(tables, passes):
    c = TestClient(app)
    body = {"name": "Acme Studio", "color": "#1F4E79", "footer": "Prepared for Northwind by Acme Studio", "logo": PNG}
    assert c.post("/me/branding", json=body).status_code == 402
    grant(passes)
    saved = c.post("/me/branding", json=body).json()
    assert saved["active"] and saved["brand"]["color"] == "#1f4e79" and saved["brand"]["logo"] == PNG
    assert c.get("/me/branding").json()["active"] is True
    passes.clear()
    grant(passes, "pro")
    got = c.get("/me/branding").json()
    assert got["active"] is False and got["brand"]["name"] == "Acme Studio"  # kept, but not applied
    assert c.delete("/me/branding").json() == {"active": False, "brand": None}


@pytest.mark.parametrize("change, message", [
    ({"color": "#ffe066"}, "too light"),
    ({"color": "red"}, "hex value"),
    ({"name": " "}, "company or agency name"),
    ({"footer": "x" * 121}, "120 characters"),
    ({"logo": "data:image/svg+xml;base64," + base64.b64encode(b"<svg onload='alert(1)'/>").decode()}, "PNG, JPEG or WebP"),
    ({"logo": "data:image/png;base64," + base64.b64encode(b"GIF89a....").decode()}, "not the image type"),
    ({"logo": "data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\0" * 200_001).decode()}, "larger than 200 kB"),
    ({"logo": "data:image/png;base64,@@@"}, "PNG, JPEG or WebP"),
])
def test_branding_validation(tables, passes, change, message):
    grant(passes)
    body = {"name": "Acme Studio", "color": "#1b1b1f", "footer": "", "logo": None} | change
    r = TestClient(app).post("/me/branding", json=body)
    assert r.status_code == 422 and message in r.json()["detail"], r.text


def test_brand_color_contrast():
    assert plus.contrast_on_white("#1b1b1f") > 15 and plus.contrast_on_white("#ffffff") == pytest.approx(1)
    assert plus.contrast_on_white("#4d7274") >= 3  # Walkthru's own accent passes


def test_export_includes_test_users_and_branding(tables, passes, monkeypatch):
    monkeypatch.setattr(db, "runs_for_user", lambda user_id: [])
    grant(passes)
    c = TestClient(app)
    c.post("/me/test-users", json=AGENCY)
    c.post("/me/branding", json={"name": "Acme Studio"})
    body = c.get("/account/export").json()
    assert body["test_users"][0]["name"] == AGENCY["name"] and body["report_branding"]["name"] == "Acme Studio"
