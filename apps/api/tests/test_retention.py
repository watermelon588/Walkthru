"""Evidence retention, run deletion, account export and account deletion. Storage and Supabase Admin are faked."""

import httpx
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import MemorySaver

from app import db, retention
from app.agent import runtime
from app.main import app
from tests.conftest import USER

STEP = {"thought": "t", "action": "click", "target_id": 1, "text": None, "confusion": 0, "url": "https://x.io/"}


def fake_supabase(monkeypatch, objects: dict[str, list[str]]):
    """objects: run_id -> storage names. Records every admin call in order."""
    calls: list[tuple[str, str]] = []
    monkeypatch.setenv("SUPABASE_URL", "https://sb.test")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "secret")

    def request(method, url, headers, json, timeout):
        assert headers["Authorization"] == "Bearer secret"
        calls.append(("storage-delete", ",".join(json["prefixes"])))
        for names in objects.values():
            names[:] = [n for n in names if n not in json["prefixes"]]
        return httpx.Response(200, json=[], request=httpx.Request(method, url))

    def delete(url, headers, timeout):
        calls.append(("auth-delete", url.rsplit("/", 1)[-1]))
        return httpx.Response(200, request=httpx.Request("DELETE", url))

    monkeypatch.setattr(retention.httpx, "request", request)
    monkeypatch.setattr(retention.httpx, "delete", delete)
    monkeypatch.setattr(db, "evidence_objects", lambda ids: [n for i in ids for n in objects.get(i, [])])
    saver = MemorySaver()
    monkeypatch.setattr(runtime, "checkpointer", lambda: saver)  # never the real Postgres saver
    return calls


def test_purge_removes_screenshots_keeps_run_and_report(monkeypatch):
    objects = {"old": ["old/step-01.jpg", "old/step-02.jpg"]}
    calls = fake_supabase(monkeypatch, objects)
    steps = [STEP | {"evidence": {"screenshot_path": "old/step-01.jpg"}}, STEP]
    marked, forgot = {}, []
    monkeypatch.setattr(db, "expired_evidence_runs", lambda days: [{"id": "old", "steps": steps}])
    monkeypatch.setattr(db, "mark_evidence_purged", lambda run_id, s: marked.__setitem__(run_id, s))
    monkeypatch.setattr(db, "forget_scan_emails", lambda days: forgot.append(days))

    assert retention.purge_expired(30) == {"runs": 1, "objects": 2}
    assert objects["old"] == [] and calls == [("storage-delete", "old/step-01.jpg,old/step-02.jpg")]
    assert marked["old"] == [STEP, STEP]  # evidence links stripped, steps kept
    assert forgot == [30]


def test_storage_failure_keeps_rows(monkeypatch):
    fake_supabase(monkeypatch, {"r": ["r/a.jpg"]})
    monkeypatch.setattr(retention.httpx, "request", lambda *a, **k: httpx.Response(500, request=httpx.Request("DELETE", "https://sb.test")))
    deleted = []
    monkeypatch.setattr(db, "delete_runs", deleted.extend)
    try:
        retention.delete_runs(["r"])
    except httpx.HTTPStatusError:
        pass
    assert deleted == []  # rows survive so the files stay reachable and the delete can be retried


def test_delete_run_is_owner_only_and_removes_everything(monkeypatch, fake_db):
    objects = {"mine": ["mine/step-01.jpg"]}
    fake_supabase(monkeypatch, objects)
    monkeypatch.setattr(db, "delete_runs", lambda ids: [fake_db.pop(i) for i in ids])
    fake_db["mine"] = {"id": "mine", "user_id": USER, "status": "done", "steps": [], "tier": "free"}
    fake_db["theirs"] = {"id": "theirs", "user_id": "someone-else", "status": "done", "steps": [], "tier": "free"}
    c = TestClient(app)
    assert c.delete("/runs/theirs").status_code == 404 and "theirs" in fake_db
    assert c.delete("/runs/mine").json() == {"deleted": "mine"}
    assert "mine" not in fake_db and objects["mine"] == []


def test_export_returns_only_my_runs(monkeypatch):
    monkeypatch.setattr(db, "runs_for_user", lambda uid: [{"id": "a", "user_id": uid}])
    body = TestClient(app).get("/account/export").json()
    assert body["user"]["id"] == USER and body["runs"] == [{"id": "a", "user_id": USER}]
    assert body["evidence_retention_days"] == retention.RETENTION_DAYS


def test_delete_account_needs_exact_email_then_deletes_user(monkeypatch):
    calls = fake_supabase(monkeypatch, {"a": ["a/1.jpg"]})
    monkeypatch.setattr(db, "run_ids_for_user", lambda uid: ["a"])
    monkeypatch.setattr(db, "delete_runs", lambda ids: calls.append(("rows", ",".join(ids))))
    c = TestClient(app)
    assert c.post("/account/delete", json={"confirm": "wrong@example.com"}).status_code == 422
    assert calls == []
    assert c.post("/account/delete", json={"confirm": " Tester@Example.com "}).json() == {"deleted": True}
    assert calls == [("storage-delete", "a/1.jpg"), ("rows", "a"), ("auth-delete", USER)]  # files, rows, then user
