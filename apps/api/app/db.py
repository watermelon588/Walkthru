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


def audit_run(row: dict) -> None:
    _insert("run_audit", row)


def end_run_audit(run_id: str, status: str, code: str | None, actions: list[dict]) -> None:
    _update("run_audit", {"run_id": f"eq.{run_id}"}, {"status": status, "code": code, "actions": actions})


def run_audit_since(since: str, *, host: str | None = None, user_id: str | None = None, refused: bool = False) -> list[dict]:
    params = {"created_at": f"gte.{since}", "select": "user_id,host,code", "limit": "500", "code": "not.is.null" if refused else "is.null"}
    if host:
        params["host"] = f"eq.{host}"
    if user_id:
        params["user_id"] = f"eq.{user_id}"
    return _select("run_audit", params)


def active_run_blocks(now: str) -> list[dict]:
    return _select("run_blocks", {"lifted_at": "is.null", "or": f"(until.is.null,until.gt.{now})", "select": "id,scope,value,reason,until,created_at"})


def add_run_block(scope: str, value: str, reason: str, created_by: str, until: str | None = None) -> None:
    _insert("run_blocks", {"scope": scope, "value": value, "reason": reason[:300], "created_by": created_by, "until": until})


def lift_run_block(block_id: int) -> None:
    _update("run_blocks", {"id": f"eq.{block_id}"}, {"lifted_at": _now()})


def purge_run_audit(before: str) -> None:
    _request("DELETE", "/rest/v1/run_audit", params={"created_at": f"lt.{before}"}, prefer="return=minimal")


def app_event(kind: str, user_id: str | None, detail: dict) -> None:
    """Feedback or a server error for the founder's admin panel (apps/api/admin)."""
    _insert("app_events", {"kind": kind, "user_id": user_id, "detail": detail})


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
        for stmt in statements(f.read()):
            conn.execute(stmt)


def statements(sql: str) -> list[str]:
    """schema.sql as single statements: `--` comment lines dropped, split on semicolons outside $$ bodies, so a
    function or DO block keeps its inner semicolons."""
    sql = "\n".join(line for line in sql.splitlines() if not line.lstrip().startswith("--"))
    found, current = [], ""
    for i, part in enumerate(sql.split("$$")):
        if i % 2:  # inside a $$ body
            current += f"$${part}$$"
            continue
        first, *rest = part.split(";")
        current += first
        for piece in rest:
            found.append(current)
            current = piece
    found.append(current)
    return [s.strip() for s in found if s.strip()]


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


# ---------- Plus team workspaces (app/teams.py, docs/team-collaboration.md) ----------
# Membership and role are read on every request; nothing here trusts a team id the caller sent without that check.

_MEMBER = "team_id,user_id,role,name,email,auto_share,last_read_message_id,last_seen_at,joined_at"
_TEAM = "id,name,owner_id,created_at,updated_at"
_MESSAGE = "id,team_id,thread,author_id,author_name,bot,body,mentions,created_at,edited_at,deleted_at"
_INVITE = "id,team_id,kind,email,email_domain,role,max_uses,uses,invited_by,invited_by_name,created_at,expires_at,revoked_at"


def _one(rows: list[dict]) -> dict | None:
    return rows[0] if rows else None


def rpc(name: str, args: dict) -> Any:
    return _request("POST", f"/rest/v1/rpc/{name}", json_body=args)


def membership(team_id: str, user_id: str) -> dict | None:
    """The caller's member row with its team embedded, or None when they are not a member."""
    return _one(_select("team_members", {"team_id": f"eq.{team_id}", "user_id": f"eq.{user_id}", "select": f"{_MEMBER},team:teams({_TEAM})", "limit": "1"}))


def memberships(user_id: str) -> list[dict]:
    return _select("team_members", {"user_id": f"eq.{user_id}", "select": f"{_MEMBER},team:teams({_TEAM})", "order": "joined_at.asc", "limit": "100"})


def teams_owned(user_id: str) -> list[dict]:
    return _select("teams", {"owner_id": f"eq.{user_id}", "select": _TEAM})


def create_team(name: str, owner_id: str) -> dict:
    return _insert("teams", {"name": name, "owner_id": owner_id}) or {}


def update_team(team_id: str, values: dict) -> None:
    _update("teams", {"id": f"eq.{team_id}"}, {**values, "updated_at": _now()})


def delete_team(team_id: str) -> None:
    _request("DELETE", "/rest/v1/teams", params={"id": f"eq.{team_id}"})


def add_member(row: dict) -> dict | None:
    return _insert("team_members", row, on_conflict="team_id,user_id")


def team_members(team_id: str) -> list[dict]:
    return _select("team_members", {"team_id": f"eq.{team_id}", "select": _MEMBER, "order": "joined_at.asc"})


def update_member(team_id: str, user_id: str, values: dict, **filters: str) -> list[dict]:
    """Compare-and-set on one member row; extra `filters` are PostgREST conditions like role="eq.member"."""
    return _update("team_members", {"team_id": f"eq.{team_id}", "user_id": f"eq.{user_id}", **filters}, values)


def remove_member(team_id: str, user_id: str) -> bool:
    return bool(_request("DELETE", "/rest/v1/team_members", params={"team_id": f"eq.{team_id}", "user_id": f"eq.{user_id}", "role": "neq.owner", "select": "user_id"},
                         prefer="return=representation"))


def team_invites(team_id: str) -> list[dict]:
    """Invitations not revoked and not expired. Used-up ones are filtered by the caller (uses < max_uses)."""
    return _select("team_invites", {"team_id": f"eq.{team_id}", "revoked_at": "is.null", "expires_at": f"gt.{_now()}", "select": _INVITE, "order": "created_at.desc", "limit": "200"})


def insert_invite(row: dict) -> dict:
    return _insert("team_invites", row) or {}


def invite_by_hash(token_hash: str) -> dict | None:
    return _one(_select("team_invites", {"token_hash": f"eq.{token_hash}", "select": f"{_INVITE},team:teams({_TEAM})", "limit": "1"}))


def get_invite(invite_id: str) -> dict | None:
    return _one(_select("team_invites", {"id": f"eq.{invite_id}", "select": f"{_INVITE},team:teams({_TEAM})", "limit": "1"}))


def revoke_invite(team_id: str, invite_id: str) -> bool:
    return bool(_update("team_invites", {"id": f"eq.{invite_id}", "team_id": f"eq.{team_id}", "revoked_at": "is.null"}, {"revoked_at": _now()}))


def invites_for_email(email: str) -> list[dict]:
    """Open email invitations addressed to this (verified) address, across workspaces."""
    rows = _select("team_invites", {"email": f"eq.{email}", "kind": "eq.email", "revoked_at": "is.null", "expires_at": f"gt.{_now()}",
                                    "select": f"{_INVITE},team:teams({_TEAM})", "order": "created_at.desc", "limit": "20"})
    return [r for r in rows if r["uses"] < r["max_uses"]]


def share_run(team_id: str, run_id: str, user_id: str) -> bool:
    """False when the run was already shared into this workspace."""
    return _insert("team_runs", {"team_id": team_id, "run_id": run_id, "shared_by": user_id}, on_conflict="team_id,run_id") is not None


def unshare_run(team_id: str, run_id: str) -> bool:
    return bool(_request("DELETE", "/rest/v1/team_runs", params={"team_id": f"eq.{team_id}", "run_id": f"eq.{run_id}", "select": "run_id"}, prefer="return=representation"))


def team_run(team_id: str, run_id: str) -> dict | None:
    return _one(_select("team_runs", {"team_id": f"eq.{team_id}", "run_id": f"eq.{run_id}", "limit": "1"}))


def team_runs(team_id: str, limit: int = 50, before: str | None = None) -> list[dict]:
    params = {"team_id": f"eq.{team_id}", "order": "shared_at.desc", "limit": str(limit)}
    if before:
        params["shared_at"] = f"lt.{before}"
    return _select("team_runs", params)


def teams_for_run(run_id: str) -> list[str]:
    return [r["team_id"] for r in _select("team_runs", {"run_id": f"eq.{run_id}", "select": "team_id"})]


def runs_brief(run_ids: list[str]) -> list[dict]:
    """What workspace pages show of shared runs: no steps or evidence, only the report's findings and score."""
    found: list[dict] = []
    for i in range(0, len(run_ids), 100):  # keeps the query string short
        found += _rows({"id": f"in.({','.join(run_ids[i:i + 100])})",
                        "select": "id,user_id,site,goal,persona,kind,status,created_at,findings:report->findings,launch_ready:report->launch_ready,summary:report->>summary"})
    return found


def team_finding_states(team_id: str) -> list[dict]:
    return _select("team_findings", {"team_id": f"eq.{team_id}", "limit": "5000"})


def save_finding_state(row: dict) -> dict | None:
    rows = _request("POST", "/rest/v1/team_findings", params={"on_conflict": "team_id,origin,fingerprint"}, json_body={**row, "updated_at": _now()},
                    prefer="resolution=merge-duplicates,return=representation") or []
    return _one(rows)


def insert_message(row: dict) -> dict | None:
    """Once per (team, client_id): a retried send returns the message already stored, with `new` False."""
    stored = _insert("team_messages", row, on_conflict="team_id,client_id")
    if stored:
        return {**{k: stored.get(k) for k in _MESSAGE.split(",")}, "new": True}
    earlier = _one(_select("team_messages", {"team_id": f"eq.{row['team_id']}", "client_id": f"eq.{row['client_id']}", "select": _MESSAGE, "limit": "1"}))
    return {**earlier, "new": False} if earlier else None


def team_messages(team_id: str, thread: str, *, after: int | None = None, before: int | None = None, limit: int = 50) -> list[dict]:
    """Oldest first. `after` pages forward (live updates); otherwise the latest `limit` messages before `before`."""
    params = {"team_id": f"eq.{team_id}", "thread": f"eq.{thread}", "select": _MESSAGE, "limit": str(limit)}
    if after is not None:
        return _select("team_messages", params | {"id": f"gt.{after}", "order": "id.asc"})
    if before is not None:
        params["id"] = f"lt.{before}"
    return list(reversed(_select("team_messages", params | {"order": "id.desc"})))


def get_message(team_id: str, message_id: int) -> dict | None:
    return _one(_select("team_messages", {"team_id": f"eq.{team_id}", "id": f"eq.{message_id}", "select": _MESSAGE, "limit": "1"}))


def update_message(team_id: str, message_id: int, values: dict) -> dict | None:
    rows = _update("team_messages", {"team_id": f"eq.{team_id}", "id": f"eq.{message_id}", "deleted_at": "is.null", "select": _MESSAGE}, values)
    return _one(rows)


def unread(team_id: str, user_id: str, last_read: int) -> tuple[int, int]:
    """(unread messages in the workspace channel, unread mentions anywhere) by others, each capped at 100."""
    base = {"team_id": f"eq.{team_id}", "id": f"gt.{last_read}", "deleted_at": "is.null", "or": f"(author_id.is.null,author_id.neq.{user_id})", "select": "id", "limit": "100"}
    channel = _select("team_messages", base | {"thread": "eq.general"})
    mentions = _select("team_messages", base | {"mentions": f"cs.{{{user_id}}}"})
    return len(channel), len(mentions)


def thread_counts(team_id: str) -> dict[str, int]:
    """Comments per run and finding thread. ponytail: reads thread names; a grouped count view past ~5,000 comments."""
    rows = _select("team_messages", {"team_id": f"eq.{team_id}", "thread": "neq.general", "deleted_at": "is.null", "select": "thread", "limit": "5000"})
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["thread"]] = counts.get(r["thread"], 0) + 1
    return counts


def insert_event(row: dict) -> None:
    _request("POST", "/rest/v1/team_events", json_body=row, prefer="return=minimal")


def team_events(team_id: str, before: int | None = None, limit: int = 50) -> list[dict]:
    params = {"team_id": f"eq.{team_id}", "order": "id.desc", "limit": str(limit)}
    if before is not None:
        params["id"] = f"lt.{before}"
    return _select("team_events", params)


def auto_share_teams(user_id: str) -> list[str]:
    return [r["team_id"] for r in _select("team_members", {"user_id": f"eq.{user_id}", "auto_share": "is.true", "role": "neq.viewer", "select": "team_id"})]


def anonymize_team_user(user_id: str) -> None:
    for table, id_column, name_column in (("team_messages", "author_id", "author_name"), ("team_events", "actor_id", "actor_name"), ("team_invites", "invited_by", "invited_by_name")):
        _request("PATCH", f"/rest/v1/{table}", params={id_column: f"eq.{user_id}"}, json_body={name_column: "Former member"}, prefer="return=minimal")


def messages_by(user_id: str) -> list[dict]:
    """Every chat message and comment this user wrote, for the account export."""
    return _select("team_messages", {"author_id": f"eq.{user_id}", "select": "id,team_id,thread,body,created_at,edited_at,deleted_at", "order": "id.asc", "limit": "10000"})


# ---------- GitHub App installations (Plus fix pull requests, app/github.py) ----------


def github_installations(user_id: str) -> list[dict]:
    return _select("github_installations", {"user_id": f"eq.{user_id}", "order": "created_at.asc"})


def add_github_installation(user_id: str, installation_id: int, account: str) -> None:
    _request("POST", "/rest/v1/github_installations", params={"on_conflict": "user_id,installation_id"},
             json_body={"user_id": user_id, "installation_id": installation_id, "account_login": account[:100]}, prefer="resolution=merge-duplicates,return=minimal")


def remove_github_installation(user_id: str, installation_id: int) -> bool:
    return bool(_request("DELETE", "/rest/v1/github_installations", params={"user_id": f"eq.{user_id}", "installation_id": f"eq.{installation_id}",
                                                                             "select": "installation_id"}, prefer="return=representation"))
