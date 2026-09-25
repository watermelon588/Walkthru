"""Runs table access over Supabase's HTTPS Data API (PostgREST) with the server secret key.

Why HTTPS and not a Postgres socket: the direct database host is IPv6-only and raw Postgres to the
project region drops connections on some networks, while the HTTPS API sits behind Cloudflare and
reuses one keep-alive connection. Every call fails fast (4 s connect) and retries once.
`setup()` alone still speaks SQL, because schema changes need it; run it with `python -m app.db`.
"""

import json
import os
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any

import httpx

SCHEMA = os.path.join(os.path.dirname(__file__), "..", "schema.sql")
BUCKET = "run-evidence"


class DatabaseUnavailable(Exception):
    """Supabase could not be reached or answered with a server error. Mapped to a fast 503."""


@lru_cache(maxsize=1)
def client() -> httpx.Client:
    key = os.environ["SUPABASE_SECRET_KEY"]
    return httpx.Client(
        base_url=os.environ["SUPABASE_URL"],
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
        timeout=httpx.Timeout(10.0, connect=4.0),
        limits=httpx.Limits(max_keepalive_connections=8, keepalive_expiry=60),
    )


def _request(method: str, path: str, *, params: dict | None = None, json_body: Any = None, prefer: str | None = None) -> Any:
    headers = {"Prefer": prefer} if prefer else {}
    for attempt in range(2):  # every call here is idempotent, so one retry is safe
        try:
            r = client().request(method, path, params=params, json=json_body, headers=headers)
        except httpx.TransportError as e:
            if attempt:
                raise DatabaseUnavailable(str(e) or type(e).__name__) from e
            continue
        if r.status_code >= 500:
            if attempt:
                raise DatabaseUnavailable(f"{r.status_code} {r.text[:200]}")
            continue
        r.raise_for_status()
        return r.json() if r.content else None
    return None


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _rows(params: dict) -> list[dict]:
    return _request("GET", "/rest/v1/runs", params=params) or []


def _patch(filters: dict, values: dict, *, returning: bool = False) -> list[dict]:
    prefer = "return=representation" if returning else "return=minimal"
    return _request("PATCH", "/rest/v1/runs", params=filters | ({"select": "id"} if returning else {}), json_body=values, prefer=prefer) or []


def insert_run(run_id: str, user_id: str | None, site: str, goal: str, persona: str, tier: str, logged_in: bool, *, kind: str = "test", public: bool = False,
               group_id: str | None = None) -> None:
    # No email here: public reports are readable with the public key, so contact details never live in this table.
    row = {"id": run_id, "user_id": user_id, "site": site, "goal": goal, "persona": persona, "tier": tier, "logged_in": logged_in, "kind": kind, "public": public}
    if group_id:
        row["group_id"] = group_id
    _request("POST", "/rest/v1/runs", json_body=row, prefer="resolution=ignore-duplicates,return=minimal")


def get_run(run_id: str) -> dict | None:
    rows = _rows({"id": f"eq.{run_id}", "select": "*", "limit": "1"})
    return rows[0] if rows else None


def update_run(run_id: str, status: str, steps: list[dict], tokens: int = 0) -> None:
    _patch({"id": f"eq.{run_id}"}, {"status": status, "steps": steps, "tokens": tokens, "updated_at": _now()})


def mark_run_stopped(run_id: str, steps: list[dict], tokens: int = 0) -> bool:
    """Atomically close a running row. False means another request already closed it."""
    changed = _patch({"id": f"eq.{run_id}", "status": "eq.running"}, {"status": "stopped", "steps": steps, "tokens": tokens, "updated_at": _now()}, returning=True)
    return bool(changed)


def set_report(run_id: str, report: dict, status: str | None = None) -> None:
    values = {"report": report, "tokens": report.get("tokens", 0), "updated_at": _now()}
    if status:
        values["status"] = status
    _patch({"id": f"eq.{run_id}"}, values)


def set_public(run_id: str, public: bool = True) -> None:
    _patch({"id": f"eq.{run_id}"}, {"public": public, "updated_at": _now()})


def runs_for_user(user_id: str) -> list[dict]:
    return _rows({"user_id": f"eq.{user_id}", "select": "*", "order": "created_at.asc"})


def test_runs_since(user_id: str, since: str) -> list[dict]:
    return _rows({"user_id": f"eq.{user_id}", "kind": "eq.test", "created_at": f"gte.{since}", "select": "site"})


def free_runs_today(kind: str = "test") -> int:
    """Free test runs (or Instant Scans, kind="scan") started today, UTC. Counted in the database, so every API process sees the same number."""
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    # ponytail: fetches ids to count them; switch to a Prefer: count=exact HEAD past a few thousand runs a day
    return len(_rows({"kind": f"eq.{kind}", "tier": "eq.free", "created_at": f"gte.{today}", "select": "id"}))


# ---------- entitlements (paid passes; SPEC.md "Plans", payment.md) ----------


def active_entitlement(user_id: str, now: str) -> dict | None:
    rows = _request("GET", "/rest/v1/entitlements", params={
        "user_id": f"eq.{user_id}", "starts_at": f"lte.{now}", "expires_at": f"gt.{now}", "revoked_at": "is.null",
        "select": "plan,starts_at,expires_at,runs_granted", "order": "expires_at.desc", "limit": "1"}) or []
    return rows[0] if rows else None


def entitlements_for_user(user_id: str) -> list[dict]:
    return _request("GET", "/rest/v1/entitlements", params={"user_id": f"eq.{user_id}", "select": "*", "order": "created_at.asc"}) or []


def grant_entitlement(user_id: str, plan: str, days: int, runs: int, source: str) -> None:
    now = datetime.now(UTC)
    row = {"user_id": user_id, "plan": plan, "starts_at": now.isoformat(), "expires_at": (now + timedelta(days=days)).isoformat(), "runs_granted": runs, "source": source}
    _request("POST", "/rest/v1/entitlements", json_body=row, prefer="return=minimal")


def expire_entitlements(user_id: str) -> None:
    now = _now()
    _request("PATCH", "/rest/v1/entitlements", params={"user_id": f"eq.{user_id}", "expires_at": f"gt.{now}"}, json_body={"expires_at": now}, prefer="return=minimal")


# ---------- billing (V10, payment.md): requests, offers, webhook events, audit ----------


class Conflict(Exception):
    """A unique constraint refused the write (for example a second pending access request)."""


def _insert(table: str, row: dict, *, on_conflict: str | None = None) -> dict | None:
    """Insert and return the stored row. With `on_conflict`, a duplicate is skipped and None comes back."""
    params = {"on_conflict": on_conflict} if on_conflict else None
    prefer = "return=representation" + (",resolution=ignore-duplicates" if on_conflict else "")
    try:
        rows = _request("POST", f"/rest/v1/{table}", params=params, json_body=row, prefer=prefer) or []
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 409:
            raise Conflict(table) from e
        raise
    return rows[0] if rows else None


def _select(table: str, params: dict) -> list[dict]:
    return _request("GET", f"/rest/v1/{table}", params={"select": "*"} | params) or []


def _update(table: str, filters: dict, values: dict) -> list[dict]:
    """Conditional update; the returned rows say whether anything matched (compare-and-set)."""
    return _request("PATCH", f"/rest/v1/{table}", params=filters, json_body=values, prefer="return=representation") or []


def create_access_request(user_id: str, plan: str, note: str) -> dict:
    return _insert("access_requests", {"user_id": user_id, "plan": plan, "note": note}) or {}


def access_requests_for_user(user_id: str, limit: int = 20) -> list[dict]:
    return _select("access_requests", {"user_id": f"eq.{user_id}", "order": "created_at.desc", "limit": str(limit)})


def get_access_request(request_id: str) -> dict | None:
    rows = _select("access_requests", {"id": f"eq.{request_id}", "limit": "1"})
    return rows[0] if rows else None


def pending_access_requests() -> list[dict]:
    return _select("access_requests", {"status": "eq.pending", "order": "created_at.asc", "limit": "200"})


def decide_access_request(request_id: str, status: str) -> bool:
    """pending -> approved or rejected, once."""
    return bool(_update("access_requests", {"id": f"eq.{request_id}", "status": "eq.pending"}, {"status": status, "decided_at": _now()}))


def create_offer(row: dict) -> dict:
    return _insert("billing_offers", row) or {}


def get_offer(offer_id: str) -> dict | None:
    rows = _select("billing_offers", {"id": f"eq.{offer_id}", "limit": "1"})
    return rows[0] if rows else None


def offers_for_user(user_id: str, limit: int = 20) -> list[dict]:
    return _select("billing_offers", {"user_id": f"eq.{user_id}", "order": "created_at.desc", "limit": str(limit)})


def open_offers() -> list[dict]:
    return _select("billing_offers", {"status": "eq.approved", "checkout_expires_at": f"gt.{_now()}", "order": "created_at.asc", "limit": "200"})


def paid_founding_offers() -> int:
    return len(_select("billing_offers", {"founding": "eq.true", "status": "eq.paid", "select": "id"}))


def mark_offer(offer_id: str, from_status: str, values: dict) -> bool:
    """Move an offer out of `from_status`. False when another request moved it first."""
    return bool(_update("billing_offers", {"id": f"eq.{offer_id}", "status": f"eq.{from_status}"}, values))


def record_billing_event(webhook_id: str, event_type: str, object_id: str | None, body_sha256: str) -> dict:
    """Store a verified webhook once. Returns the stored row, which is the earlier one on redelivery."""
    row = {"webhook_id": webhook_id, "event_type": event_type, "object_id": object_id, "body_sha256": body_sha256}
    stored = _insert("billing_events", row, on_conflict="webhook_id")
    if stored:
        return stored
    return _select("billing_events", {"webhook_id": f"eq.{webhook_id}", "limit": "1"})[0]


def finish_billing_event(webhook_id: str, result: str) -> None:
    _update("billing_events", {"webhook_id": f"eq.{webhook_id}"}, {"processed_at": _now(), "result": result[:200]})


def grant_paid_entitlement(row: dict) -> bool:
    """Insert the pass for an offer. False when that offer already granted one (a retry or a race)."""
    return _insert("entitlements", row, on_conflict="offer_id") is not None


def revoke_entitlement(payment_id: str, reason: str) -> list[dict]:
    return _update("entitlements", {"payment_id": f"eq.{payment_id}", "revoked_at": "is.null"}, {"revoked_at": _now(), "revoked_reason": reason[:200]})


def offer_for_payment(payment_id: str) -> dict | None:
    rows = _select("billing_offers", {"payment_id": f"eq.{payment_id}", "limit": "1"})
    return rows[0] if rows else None


def audit(actor: str, action: str, target: str, detail: dict) -> None:
    _insert("admin_audit_log", {"actor": actor[:200], "action": action, "target": target, "detail": detail})


def public_reports(user_id: str) -> list[dict]:
    """The owner's shared reports, newest first: the badge follows the latest one for its site."""
    return _rows({"user_id": f"eq.{user_id}", "public": "eq.true", "report": "not.is.null",
                  "select": "id,site,status,kind,created_at,report", "order": "created_at.desc", "limit": "50"})


def recent_reports(user_id: str, exclude_id: str, limit: int = 20) -> list[dict]:
    """The user's latest finished test runs with a report, newest first: candidates for rerun comparison."""
    return _rows({"user_id": f"eq.{user_id}", "kind": "eq.test", "id": f"neq.{exclude_id}", "report": "not.is.null",
                  "select": "id,site,goal,created_at,report", "order": "created_at.desc", "limit": str(limit)})


# ---------- ignored findings (paid plans; SPEC.md "Ignore a finding") ----------


def ignored_fingerprints(user_id: str, origin: str) -> dict[str, str]:
    rows = _request("GET", "/rest/v1/finding_states", params={"user_id": f"eq.{user_id}", "origin": f"eq.{origin}", "select": "fingerprint,reason"}) or []
    return {r["fingerprint"]: r["reason"] for r in rows}


def set_ignored(user_id: str, origin: str, fingerprint: str, reason: str) -> None:
    row = {"user_id": user_id, "origin": origin, "fingerprint": fingerprint, "reason": reason, "created_at": _now()}
    _request("POST", "/rest/v1/finding_states", json_body=row, prefer="resolution=merge-duplicates,return=minimal")


def clear_ignored(user_id: str, origin: str, fingerprint: str) -> None:
    _request("DELETE", "/rest/v1/finding_states", params={"user_id": f"eq.{user_id}", "origin": f"eq.{origin}", "fingerprint": f"eq.{fingerprint}"})


def ignored_for_user(user_id: str) -> list[dict]:
    return _request("GET", "/rest/v1/finding_states", params={"user_id": f"eq.{user_id}", "select": "*"}) or []


def run_ids_for_user(user_id: str) -> list[str]:
    return [r["id"] for r in _rows({"user_id": f"eq.{user_id}", "select": "id"})]


def evidence_objects(run_ids: list[str]) -> list[str]:
    """Storage paths under each run's folder, through the Storage API."""
    names: list[str] = []
    for run_id in run_ids:
        listed = _request("POST", f"/storage/v1/object/list/{BUCKET}", json_body={"prefix": run_id, "limit": 1000}) or []
        names += [f"{run_id}/{o['name']}" for o in listed if o.get("name") and not o["name"].startswith(".")]
    return names


def _cutoff(days: int) -> str:
    return (datetime.now(UTC) - timedelta(days=days)).isoformat()


def expired_evidence_runs(days: int, limit: int = 100) -> list[dict]:
    return _rows({"kind": "eq.test", "evidence_purged_at": "is.null", "created_at": f"lt.{_cutoff(days)}", "select": "id,steps", "order": "created_at.asc", "limit": str(limit)})


def mark_evidence_purged(run_id: str, steps: list[dict]) -> None:
    _patch({"id": f"eq.{run_id}"}, {"steps": steps, "evidence_purged_at": _now()})


def user_email(user_id: str) -> str | None:
    """The account's email from Supabase Auth, read only when a report email is sent."""
    try:
        return (_request("GET", f"/auth/v1/admin/users/{user_id}") or {}).get("email")
    except httpx.HTTPStatusError:
        return None


def delete_runs(run_ids: list[str]) -> None:
    if run_ids:
        _request("DELETE", "/rest/v1/runs", params={"id": f"in.({','.join(run_ids)})"}, prefer="return=minimal")


def setup() -> None:
    """Apply schema.sql over a direct SQL connection (admin task, retried by hand if the network drops)."""
    import psycopg

    with open(SCHEMA, encoding="utf-8") as f, psycopg.connect(os.environ["DATABASE_URL"], autocommit=True, connect_timeout=15) as conn:
        sql = "\n".join(line for line in f if not line.lstrip().startswith("--"))
        for stmt in sql.split(";"):
            if stmt.strip():
                conn.execute(stmt)


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    setup()
    print(json.dumps({"ok": True, "runs": get_run("__none__") is None}))


# ---------- personal API keys for the MCP server (Plus; ARCHITECTURE.md `mcp`) ----------
# Only the SHA-256 of a key is stored. The table has no anon or authenticated grants: the API reads it as the service role.


def insert_api_key(user_id: str, name: str, key_hash: str) -> dict:
    rows = _request("POST", "/rest/v1/api_keys", json_body={"user_id": user_id, "name": name, "key_hash": key_hash},
                    params={"select": "id,name,created_at"}, prefer="return=representation") or []
    return rows[0]


def api_keys_for_user(user_id: str) -> list[dict]:
    return _request("GET", "/rest/v1/api_keys", params={"user_id": f"eq.{user_id}", "revoked_at": "is.null",
                                                         "select": "id,name,created_at,last_used_at", "order": "created_at.desc"}) or []


def revoke_api_key(user_id: str, key_id: str) -> bool:
    rows = _request("PATCH", "/rest/v1/api_keys", params={"id": f"eq.{key_id}", "user_id": f"eq.{user_id}", "revoked_at": "is.null", "select": "id"},
                    json_body={"revoked_at": _now()}, prefer="return=representation") or []
    return bool(rows)


def api_key_owner(key_hash: str) -> dict | None:
    rows = _request("GET", "/rest/v1/api_keys", params={"key_hash": f"eq.{key_hash}", "revoked_at": "is.null", "select": "id,user_id", "limit": "1"}) or []
    return rows[0] if rows else None


def touch_api_key(key_id: str) -> None:
    _request("PATCH", "/rest/v1/api_keys", params={"id": f"eq.{key_id}"}, json_body={"last_used_at": _now()}, prefer="return=minimal")


def user_scans_today(user_id: str) -> int:
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    # Owner scans from MCP and each site of a competitor comparison share one daily cap.
    return len(_rows({"user_id": f"eq.{user_id}", "kind": "in.(scan,compare_part)", "created_at": f"gte.{today}", "select": "id"}))


# ---------- watched sites (Plus weekly watch; ARCHITECTURE.md `watch`) ----------

_SITE_COLUMNS = "id,user_id,site,watch,last_run_id,last_changes,next_check_at,last_hook_at,created_at"


def sites_for_user(user_id: str) -> list[dict]:
    return _request("GET", "/rest/v1/sites", params={"user_id": f"eq.{user_id}", "select": _SITE_COLUMNS, "order": "created_at.asc"}) or []


def add_site(user_id: str, site: str) -> dict:
    rows = _request("POST", "/rest/v1/sites", json_body={"user_id": user_id, "site": site}, params={"select": _SITE_COLUMNS}, prefer="return=representation") or []
    return rows[0]


def remove_site(user_id: str, site_id: str) -> bool:
    return bool(_request("DELETE", "/rest/v1/sites", params={"id": f"eq.{site_id}", "user_id": f"eq.{user_id}", "select": "id"}, prefer="return=representation"))


def due_sites(now: str, limit: int = 20) -> list[dict]:
    return _request("GET", "/rest/v1/sites", params={"watch": "is.true", "next_check_at": f"lte.{now}", "select": _SITE_COLUMNS, "order": "next_check_at.asc", "limit": str(limit)}) or []


def site_by_hook(hook_hash: str) -> dict | None:
    rows = _request("GET", "/rest/v1/sites", params={"hook_hash": f"eq.{hook_hash}", "select": _SITE_COLUMNS, "limit": "1"}) or []
    return rows[0] if rows else None


def update_site(site_id: str, values: dict) -> None:
    _request("PATCH", "/rest/v1/sites", params={"id": f"eq.{site_id}"}, json_body=values, prefer="return=minimal")


def claim_hook(site_id: str, not_before: str) -> bool:
    """Atomically record a deploy-hook run unless one ran after `not_before` (the 10-minute rate limit)."""
    rows = _request("PATCH", "/rest/v1/sites", params={"id": f"eq.{site_id}", "or": f"(last_hook_at.is.null,last_hook_at.lt.{not_before})", "select": "id"},
                    json_body={"last_hook_at": _now()}, prefer="return=representation") or []
    return bool(rows)


# ---------- Plus: custom test users, run groups (P4.2) and report branding (P4.3) ----------


def test_users_for(user_id: str) -> list[dict]:
    return _select("test_users", {"user_id": f"eq.{user_id}", "select": "id,name,description,created_at", "order": "created_at.asc"})


def get_test_user(user_id: str, test_user_id: str) -> dict | None:
    rows = _select("test_users", {"id": f"eq.{test_user_id}", "user_id": f"eq.{user_id}", "select": "id,name,description", "limit": "1"})
    return rows[0] if rows else None


def create_test_user(user_id: str, name: str, description: str) -> dict:
    return _insert("test_users", {"user_id": user_id, "name": name, "description": description}) or {}


def delete_test_user(user_id: str, test_user_id: str) -> bool:
    return bool(_request("DELETE", "/rest/v1/test_users", params={"id": f"eq.{test_user_id}", "user_id": f"eq.{user_id}"}, prefer="return=representation"))


def runs_in_group(group_id: str) -> list[dict]:
    return _rows({"group_id": f"eq.{group_id}", "select": "id,user_id,site,goal"})


def get_brand(user_id: str) -> dict | None:
    rows = _select("report_brands", {"user_id": f"eq.{user_id}", "select": "name,color,footer,logo,updated_at", "limit": "1"})
    return rows[0] if rows else None


def save_brand(user_id: str, values: dict) -> None:
    row = {"user_id": user_id, **values, "updated_at": _now()}
    _request("POST", "/rest/v1/report_brands", params={"on_conflict": "user_id"}, json_body=row, prefer="resolution=merge-duplicates,return=minimal")


def delete_brand(user_id: str) -> None:
    _request("DELETE", "/rest/v1/report_brands", params={"user_id": f"eq.{user_id}"})
