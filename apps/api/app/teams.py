"""Plus team workspaces (docs/team-collaboration.md): one shared place per team for reports, finding triage, chat
and activity.

Rules every route follows:
- Membership and role are read from the database on every request, never cached and never taken from the client.
  A caller who is not a member gets 404, so a workspace id reveals nothing.
- A workspace is active while its owner is on Plus (the server decides the plan). An inactive workspace stays
  readable; adding things (chat, shares, triage, invitations) answers 402 until the owner renews or hands it over.
  Leaving, removing people, revoking invitations, deleting your own messages and deleting the workspace always work.
- Invitation codes carry 120 random bits, are shown once and stored as SHA-256. An email invitation works only for
  the verified address it was sent to; an invite link can be limited to one email domain. Seats are counted inside
  one locked database transaction (public.team_join), so two people can never take the last seat at once.
"""

import base64
import hashlib
import logging
import os
import re
import secrets
import time
import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, EmailStr, Field

from app import db, deliver
from app.agent import compare
from app.auth import require_user

log = logging.getLogger("walkthru.teams")
router = APIRouter(tags=["teams"])

WEB_URL = os.environ.get("WEB_URL", "http://localhost:5173").rstrip("/")
SEATS = int(os.environ.get("TEAM_SEATS", "3"))  # founder/pricing-strategy.md: Plus includes 3 seats sharing reports
MAX_OWNED = 3  # workspaces one Plus account can own
MAX_MEMBERSHIPS = 20  # workspaces one account can be in
MAX_LINKS = 5  # open invite links per workspace
INVITE_DAYS = 7
ONLINE_SECONDS = 120
BOARD_RUNS = 200  # latest shared reports the findings board reads
RANK = {"viewer": 0, "member": 1, "admin": 2, "owner": 3}
STATUSES = ("open", "in_progress", "fixed", "wont_fix")
KINDS = {"ux", "accessibility", "performance", "seo", "security", "geo"}
RUN_ID = r"^[0-9a-f]{32}$"
THREAD = re.compile(r"general|run:[0-9a-f]{32}|finding:[0-9a-f]{32}")
# Control characters and bidirectional overrides: they can disguise names and messages.
_HIDDEN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\u200b-\u200f\u202a-\u202e\u2060-\u2069\ufeff]")
_DOMAIN = re.compile(r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}")
_NEEDS = {
    "member": "Viewers can read and chat. Ask an admin to make you a member for this.",
    "admin": "Only the workspace owner and admins can do this.",
    "owner": "Only the workspace owner can do this.",
}
READ_ONLY = ("This workspace is read-only because its owner's Plus plan has ended. "
             "The owner can renew, or hand the workspace to a member who is on Plus.")


# ---------- small helpers ----------


def _now() -> datetime:
    return datetime.now(UTC)


def _ts(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


_hits: dict[str, list[float]] = {}  # ponytail: per-process, like the scan and billing limits


def _limit(key: str, count: int, window: int, message: str) -> None:
    now = time.time()
    hits = [t for t in _hits.get(key, []) if now - t < window]
    if len(hits) >= count:
        raise HTTPException(429, message)
    _hits[key] = [*hits, now]
    if len(_hits) > 20_000:
        for k in [k for k, v in _hits.items() if now - v[-1] > 86_400]:
            del _hits[k]


def _name(user: dict) -> str:
    """How a person shows in the workspace: their profile name, else the part of their email before the @."""
    return (user.get("name") or (user.get("email") or "").split("@")[0] or "Member")[:80]


def _line(value: str) -> str:
    return " ".join(_HIDDEN.sub("", value).split())


def clean_name(value: str) -> str:
    name = _line(value)
    if not 1 <= len(name) <= 60:
        raise HTTPException(422, "Name the workspace in 1 to 60 characters.")
    if re.search(r"://|www\.|https?:", name, re.IGNORECASE):  # the name appears in invitation emails
        raise HTTPException(422, "Leave links out of the workspace name.")
    return name


def clean_body(value: str) -> str:
    text = _HIDDEN.sub("", value).replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        raise HTTPException(422, "Write a message first.")
    if len(text) > 4000:
        raise HTTPException(422, "Keep a message to 4,000 characters.")
    return text


def clean_domain(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    domain = value.strip().lower().removeprefix("@")
    if not _DOMAIN.fullmatch(domain):
        raise HTTPException(422, "Enter an email domain like acme.com.")
    return domain


def mask(email: str) -> str:
    local, _, domain = email.partition("@")
    return f"{local[:1]}{'*' * max(1, min(len(local) - 1, 6))}@{domain}"


def new_code() -> str:
    """24 characters of base32 (A to Z and 2 to 7): 120 random bits that still read and type easily."""
    return base64.b32encode(secrets.token_bytes(15)).decode()


def show_code(raw: str) -> str:
    return "-".join(raw[i:i + 4] for i in range(0, len(raw), 4))


def read_code(text: str) -> str | None:
    """A pasted invite link or code, with or without dashes or spaces, in any case."""
    raw = re.sub(r"[\s-]", "", text.strip().rsplit("#", 1)[-1]).upper()
    return raw if re.fullmatch(r"[A-Z2-7]{24}", raw) else None


def code_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def join_link(raw: str) -> str:
    # The code rides in the fragment: browsers never send it to a server or in a Referer header.
    return f"{WEB_URL}/join#{show_code(raw)}"


def finding_thread(origin: str, fingerprint: str) -> str:
    return "finding:" + hashlib.sha256(f"{origin}\n{fingerprint}".encode()).hexdigest()[:32]


def _plus(user_id: str) -> bool:
    grant = db.active_entitlement(user_id, _now().isoformat())
    return bool(grant and grant.get("plan") == "plus")


def _member(team_id: uuid.UUID | str, user: dict, need: str = "viewer", *, write: bool = False) -> dict:
    """The caller's member row (team embedded). 404 for non-members, 403 below `need`, 402 on writes when inactive."""
    me = db.membership(str(team_id), user["id"])
    if not me or not me.get("team"):
        raise HTTPException(404, "No workspace with that id, or you are not a member of it.")
    if RANK[me["role"]] < RANK[need]:
        raise HTTPException(403, _NEEDS[need])
    if write and not _active(me):
        raise HTTPException(402, READ_ONLY)
    return me


def _active(me: dict) -> bool:
    if "active" not in me:
        me["active"] = _plus(me["team"]["owner_id"])
    return me["active"]


def _can(role: str, active: bool) -> dict[str, bool]:
    """What the caller may do here, so the web app shows only working controls. The routes enforce the same rules."""
    r = RANK[role]
    return {"chat": active, "share": active and r >= 1, "triage": active and r >= 1, "invite": active and r >= 2,
            "manage_members": r >= 2, "rename": active and r >= 2, "manage_admins": r == 3, "transfer": r == 3, "delete": r == 3}


def _event(team_id: str, user: dict, event_type: str, /, **detail) -> None:
    """Activity feed and audit trail. The action already happened, so a failed write is logged, not raised."""
    try:
        db.insert_event({"team_id": team_id, "actor_id": user["id"], "actor_name": _name(user), "type": event_type, "detail": detail})
    except Exception:
        log.warning("team event %s not recorded", event_type, exc_info=True)


def _member_out(m: dict) -> dict:
    seen = _ts(m.get("last_seen_at"))
    return {"user_id": m["user_id"], "name": m["name"] or "Member", "email": m["email"], "role": m["role"], "joined_at": m["joined_at"],
            "last_seen_at": m.get("last_seen_at"), "online": bool(seen and (_now() - seen).total_seconds() < ONLINE_SECONDS)}


def _invite_out(inv: dict) -> dict:
    return {k: inv.get(k) for k in ("id", "kind", "email", "email_domain", "role", "max_uses", "uses", "invited_by_name", "created_at", "expires_at")}


def _message_out(m: dict) -> dict:
    gone = bool(m.get("deleted_at"))
    return {"id": m["id"], "thread": m["thread"], "author_id": m.get("author_id"), "author_name": m.get("author_name") or "Former member",
            "body": "" if gone else m["body"], "mentions": [] if gone else (m.get("mentions") or []),
            "created_at": m["created_at"], "edited_at": m.get("edited_at"), "deleted": gone}


def _event_out(e: dict) -> dict:
    return {k: e.get(k) for k in ("id", "type", "actor_id", "actor_name", "detail", "created_at")}


def _findings(run: dict) -> list[dict]:
    """A run's findings that have the fields the board needs (old or partial reports are skipped, not trusted)."""
    return [f for f in run.get("findings") or [] if isinstance(f, dict) and f.get("kind") in KINDS
            and f.get("severity") in ("high", "medium", "low") and isinstance(f.get("title"), str)]


def _counts(run: dict) -> dict[str, int]:
    found = Counter(f["severity"] for f in _findings(run))
    return {s: found.get(s, 0) for s in ("high", "medium", "low")}


def _score(run: dict) -> int | None:
    ready = run.get("launch_ready")
    return ready.get("score") if isinstance(ready, dict) else None


def _touch(me: dict, user: dict) -> None:
    """Presence and a fresh display copy of the member's name and email, written at most once a minute."""
    values: dict = {}
    seen = _ts(me.get("last_seen_at"))
    if not seen or (_now() - seen).total_seconds() > 60:
        values["last_seen_at"] = _now().isoformat()
    name, email = _name(user), user.get("email") or ""
    if (name, email) != (me["name"], me["email"]):
        values |= {"name": name, "email": email}
    if values:
        db.update_member(me["team_id"], user["id"], values)


# ---------- the board: every finding across the workspace's shared reports, with its triage ----------


def _board(team_id: str, shares: list[dict] | None = None, runs: list[dict] | None = None, names: dict[str, str] | None = None) -> list[dict]:
    if shares is None:
        shares = db.team_runs(team_id, limit=BOARD_RUNS)
    if runs is None:
        runs = db.runs_brief([s["run_id"] for s in shares])
    if names is None:
        names = {m["user_id"]: m["name"] for m in db.team_members(team_id)}
    items: dict[tuple[str, str], dict] = {}
    for run in sorted(runs, key=lambda r: _ts(r["created_at"]) or _now()):  # oldest first: the latest sighting wins
        origin = compare.origin(run["site"])
        for f in _findings(run):
            fp = compare.fingerprint(f)
            item = items.setdefault((origin, fp), {"origin": origin, "fingerprint": fp, "thread": finding_thread(origin, fp),
                                                   "first_seen": run["created_at"], "run_ids": set()})
            item.update(kind=f["kind"], severity=f["severity"], title=f["title"], detail=str(f.get("detail") or ""), fix=str(f.get("fix") or ""),
                        evidence=f.get("evidence") if isinstance(f.get("evidence"), str) else None, site=run["site"], run_id=run["id"], last_seen=run["created_at"])
            item["run_ids"].add(run["id"])
    states = {(s["origin"], s["fingerprint"]): s for s in db.team_finding_states(team_id)} if items else {}
    comments = db.thread_counts(team_id) if items else {}
    board = []
    for key, item in items.items():
        state = states.get(key) or {}
        status = state.get("status") or "open"
        updated = _ts(state.get("updated_at"))
        assignee = state.get("assignee_id")
        board.append({**{k: v for k, v in item.items() if k != "run_ids"}, "reports": len(item["run_ids"]), "status": status,
                      "assignee_id": assignee, "assignee_name": names.get(assignee, "Former member") if assignee else None,
                      "updated_at": state.get("updated_at"), "updated_by_name": names.get(state.get("updated_by") or "", None),
                      # Marked fixed, then found again in a report that ran later: worth a second look.
                      "seen_again": status == "fixed" and bool(updated and (_ts(item["last_seen"]) or updated) > updated),
                      "comments": comments.get(item["thread"], 0)})
    order = {"open": 0, "in_progress": 1, "wont_fix": 2, "fixed": 3}
    rank = {"high": 0, "medium": 1, "low": 2}
    board.sort(key=lambda i: (0 if i["seen_again"] else order[i["status"]], rank[i["severity"]], -(_ts(i["last_seen"]) or _now()).timestamp()))
    return board[:1000]


def _sites(runs: list[dict]) -> list[dict]:
    """The latest shared report per site, for the overview."""
    latest: dict[str, dict] = {}
    reports: Counter[str] = Counter()
    for run in runs:
        if run.get("kind") in ("compare", "compare_part"):
            continue
        origin = compare.origin(run["site"])
        reports[origin] += 1
        if origin not in latest or (_ts(run["created_at"]) or _now()) > (_ts(latest[origin]["created_at"]) or _now()):
            latest[origin] = run
    out = [{"origin": o, "site": r["site"], "run_id": r["id"], "kind": r["kind"], "status": r["status"], "created_at": r["created_at"],
            "score": _score(r), "findings": _counts(r), "reports": reports[o]} for o, r in latest.items()]
    return sorted(out, key=lambda s: s["created_at"], reverse=True)


# ---------- workspaces ----------


class NewTeam(BaseModel):
    model_config = {"extra": "forbid"}
    name: str = Field(min_length=1, max_length=200)


@router.get("/teams")
def list_teams(user: dict = Depends(require_user)) -> dict:
    """The caller's workspaces with unread counts, plus open invitations sent to their verified email."""
    rows = [m for m in db.memberships(user["id"]) if m.get("team")]
    plus = _plus(user["id"])
    owners = {user["id"]: plus}
    teams = []
    for m in rows:
        team = m["team"]
        if team["owner_id"] not in owners:
            owners[team["owner_id"]] = _plus(team["owner_id"])
        channel, mentions = db.unread(team["id"], user["id"], m["last_read_message_id"])
        teams.append({"id": team["id"], "name": team["name"], "role": m["role"], "active": owners[team["owner_id"]],
                      "unread": channel, "mentions": mentions, "created_at": team["created_at"]})
    mine = {t["id"] for t in teams}
    invitations = []
    if user.get("email_verified") and user.get("email"):
        invitations = [{"id": i["id"], "team": {"id": i["team"]["id"], "name": i["team"]["name"]}, "role": i["role"],
                        "invited_by_name": i["invited_by_name"], "expires_at": i["expires_at"]}
                       for i in db.invites_for_email(user["email"].lower()) if i.get("team") and i["team"]["id"] not in mine]
    owned = sum(1 for m in rows if m["role"] == "owner")
    return {"teams": teams, "invitations": invitations, "plus": plus, "can_create": plus and owned < MAX_OWNED and len(rows) < MAX_MEMBERSHIPS,
            "owned": owned, "max_owned": MAX_OWNED, "seats": SEATS}


@router.post("/teams")
def create_team(body: NewTeam, user: dict = Depends(require_user)) -> dict:
    name = clean_name(body.name)
    if not _plus(user["id"]):
        raise HTTPException(402, "Team workspaces are part of the Plus plan.")
    _limit(f"create:{user['id']}", 10, 86_400, "You created many workspaces today. Try again tomorrow.")
    rows = db.memberships(user["id"])
    if sum(1 for m in rows if m["role"] == "owner") >= MAX_OWNED:
        raise HTTPException(409, f"You can own up to {MAX_OWNED} workspaces. Delete one or hand it over first.")
    if len(rows) >= MAX_MEMBERSHIPS:
        raise HTTPException(409, "You are in the most workspaces one account can join. Leave one first.")
    team = db.create_team(name, user["id"])
    try:
        db.add_member({"team_id": team["id"], "user_id": user["id"], "role": "owner", "name": _name(user), "email": user.get("email") or "",
                       "last_seen_at": _now().isoformat()})
    except Exception:
        db.delete_team(team["id"])  # never leave a workspace without its owner
        raise
    _event(team["id"], user, "team.created", name=name)
    return {"id": team["id"], "name": name}


@router.get("/teams/{team_id}")
def overview(team_id: uuid.UUID, user: dict = Depends(require_user)) -> dict:
    """Everything the workspace home shows in one call: members and presence, sites, triage totals, activity, unread."""
    me = _member(team_id, user)
    tid, team, active = str(team_id), me["team"], _active(me)
    _touch(me, user)
    members = db.team_members(tid)
    names = {m["user_id"]: m["name"] for m in members}
    shares = db.team_runs(tid, limit=BOARD_RUNS)
    runs = db.runs_brief([s["run_id"] for s in shares])
    board = _board(tid, shares, runs, names)
    channel, mentions = db.unread(tid, user["id"], me["last_read_message_id"])
    status = Counter(i["status"] for i in board)
    return {
        "team": {"id": tid, "name": team["name"], "owner_id": team["owner_id"], "created_at": team["created_at"], "active": active, "seats": SEATS},
        "me": {"user_id": user["id"], "role": me["role"], "auto_share": me["auto_share"], "last_read_message_id": me["last_read_message_id"],
               "can": _can(me["role"], active)},
        "members": [_member_out(m) for m in members],
        "sites": _sites(runs),
        "findings": {**{s: status.get(s, 0) for s in STATUSES},
                     "high_open": sum(1 for i in board if i["severity"] == "high" and i["status"] in ("open", "in_progress")),
                     "seen_again": sum(1 for i in board if i["seen_again"]),
                     "mine": sum(1 for i in board if i["assignee_id"] == user["id"] and i["status"] in ("open", "in_progress"))},
        "reports": len(shares),
        "activity": [_event_out(e) for e in db.team_events(tid, limit=15)],
        "unread": channel,
        "mentions": mentions,
    }


class Rename(BaseModel):
    model_config = {"extra": "forbid"}
    name: str = Field(min_length=1, max_length=200)


@router.post("/teams/{team_id}")
def rename_team(team_id: uuid.UUID, body: Rename, user: dict = Depends(require_user)) -> dict:
    me = _member(team_id, user, "admin", write=True)
    name = clean_name(body.name)
    if name != me["team"]["name"]:
        db.update_team(str(team_id), {"name": name})
        _event(str(team_id), user, "team.renamed", old=me["team"]["name"], new=name)
    return {"id": str(team_id), "name": name}


class DeleteTeam(BaseModel):
    model_config = {"extra": "forbid"}
    confirm: str = Field(max_length=200)


@router.post("/teams/{team_id}/delete")
def delete_team(team_id: uuid.UUID, body: DeleteTeam, user: dict = Depends(require_user)) -> dict:
    """Owner only; they type the name to confirm. Chat, triage and invitations go; the reports stay in their owners' accounts."""
    me = _member(team_id, user, "owner")
    if _line(body.confirm) != me["team"]["name"]:
        raise HTTPException(422, "Type the workspace name exactly to confirm.")
    db.delete_team(str(team_id))
    log.info("workspace %s deleted by its owner", team_id)
    return {"deleted": str(team_id)}


class Transfer(BaseModel):
    model_config = {"extra": "forbid"}
    user_id: uuid.UUID


@router.post("/teams/{team_id}/transfer")
def transfer_team(team_id: uuid.UUID, body: Transfer, user: dict = Depends(require_user)) -> dict:
    """Hand the workspace to another member. The old owner stays as an admin. Works while inactive, which is how a
    workspace whose owner left Plus comes back."""
    _member(team_id, user, "owner")
    tid, to = str(team_id), str(body.user_id)
    target = db.membership(tid, to)
    if not target or to == user["id"]:
        raise HTTPException(404, "Pick a member of this workspace.")
    if target["role"] == "viewer":
        raise HTTPException(409, "Make them a member or admin first. Viewers cannot own a workspace.")
    if len(db.teams_owned(to)) >= MAX_OWNED:
        raise HTTPException(409, f"They already own {MAX_OWNED} workspaces, the most one account can own.")
    if not db.rpc("team_transfer", {"p_team": tid, "p_from": user["id"], "p_to": to}):
        raise HTTPException(409, "The workspace changed hands already. Reload the page.")
    active = _plus(to)
    _event(tid, user, "team.transferred", to_id=to, to_name=target["name"], active=active)
    return {"owner_id": to, "active": active}


class MySettings(BaseModel):
    model_config = {"extra": "forbid"}
    auto_share: bool


@router.post("/teams/{team_id}/me")
def my_settings(team_id: uuid.UUID, body: MySettings, user: dict = Depends(require_user)) -> dict:
    """Auto-share: every new report of mine (test runs, scans, watch checks) lands in this workspace."""
    me = _member(team_id, user)
    if body.auto_share and me["role"] == "viewer":
        raise HTTPException(403, "Viewers cannot share reports.")
    db.update_member(str(team_id), user["id"], {"auto_share": body.auto_share})
    return {"auto_share": body.auto_share}


# ---------- members and invitations ----------


@router.get("/teams/{team_id}/members")
def list_members(team_id: uuid.UUID, user: dict = Depends(require_user)) -> dict:
    me = _member(team_id, user)
    tid = str(team_id)
    members = db.team_members(tid)
    admin = RANK[me["role"]] >= RANK["admin"]
    invites = [i for i in db.team_invites(tid) if i["uses"] < i["max_uses"]] if admin else []
    return {"members": [_member_out(m) for m in members], "invites": [_invite_out(i) for i in invites], "seats": SEATS,
            "seats_used": len(members) + sum(1 for i in invites if i["kind"] == "email"), "me": {"role": me["role"], "can": _can(me["role"], _active(me))}}


class RoleChange(BaseModel):
    model_config = {"extra": "forbid"}
    role: Literal["admin", "member", "viewer"]


@router.post("/teams/{team_id}/members/{member_id}/role")
def change_role(team_id: uuid.UUID, member_id: uuid.UUID, body: RoleChange, user: dict = Depends(require_user)) -> dict:
    me = _member(team_id, user, "admin")
    tid, uid = str(team_id), str(member_id)
    if uid == user["id"]:
        raise HTTPException(409, "You cannot change your own role. The owner hands the workspace over instead.")
    target = db.membership(tid, uid)
    if not target:
        raise HTTPException(404, "That person is not in this workspace.")
    if target["role"] == "owner":
        raise HTTPException(403, "The owner's role changes only when they hand the workspace over.")
    if me["role"] != "owner" and "admin" in (target["role"], body.role):
        raise HTTPException(403, "Only the owner can add or remove admins.")
    if target["role"] != body.role:
        values: dict = {"role": body.role} | ({"auto_share": False} if body.role == "viewer" else {})
        if not db.update_member(tid, uid, values, role=f"eq.{target['role']}"):
            raise HTTPException(409, "Their role changed a moment ago. Reload the page.")
        _event(tid, user, "member.role", member_id=uid, member_name=target["name"], old=target["role"], new=body.role)
    return {"user_id": uid, "role": body.role}


@router.delete("/teams/{team_id}/members/{member_id}")
def remove_member(team_id: uuid.UUID, member_id: uuid.UUID, user: dict = Depends(require_user)) -> dict:
    """Remove someone, or leave (your own id). Reports they shared stay; they can delete their runs to take them back."""
    me = _member(team_id, user)
    tid, uid = str(team_id), str(member_id)
    if uid == user["id"]:
        if me["role"] == "owner":
            raise HTTPException(409, "Hand the workspace to another member, or delete it, before you leave.")
        db.remove_member(tid, uid)
        _event(tid, user, "member.left")
        return {"left": tid}
    if RANK[me["role"]] < RANK["admin"]:
        raise HTTPException(403, _NEEDS["admin"])
    target = db.membership(tid, uid)
    if not target:
        raise HTTPException(404, "That person is not in this workspace.")
    if target["role"] == "owner":
        raise HTTPException(403, "The owner cannot be removed.")
    if target["role"] == "admin" and me["role"] != "owner":
        raise HTTPException(403, "Only the owner can remove an admin.")
    db.remove_member(tid, uid)
    _event(tid, user, "member.removed", member_id=uid, member_name=target["name"])
    return {"removed": uid}


class EmailInvite(BaseModel):
    model_config = {"extra": "forbid"}
    email: EmailStr
    role: Literal["admin", "member", "viewer"] = "member"


@router.post("/teams/{team_id}/invites")
def invite_by_email(team_id: uuid.UUID, body: EmailInvite, user: dict = Depends(require_user)) -> dict:
    """Invite one address. The code works only for that verified address, once, for 7 days. An open invitation holds a
    seat; inviting the same address again replaces it."""
    me = _member(team_id, user, "admin", write=True)
    if body.role == "admin" and me["role"] != "owner":
        raise HTTPException(403, "Only the owner can invite admins.")
    tid, email = str(team_id), str(body.email).strip().lower()
    members = db.team_members(tid)
    if any(m["email"].lower() == email for m in members):
        raise HTTPException(409, "That person is already in this workspace.")
    open_invites = [i for i in db.team_invites(tid) if i["uses"] < i["max_uses"]]
    replaced = [i for i in open_invites if i["kind"] == "email" and i["email"] == email]
    if len(members) + sum(1 for i in open_invites if i["kind"] == "email") - len(replaced) >= SEATS:
        raise HTTPException(409, f"All {SEATS} seats are taken, counting open invitations. Remove someone or revoke an invitation first.")
    _limit(f"invite:{tid}", 30, 86_400, "This workspace sent many invitations today. Try again tomorrow.")
    raw, expires = new_code(), _now() + timedelta(days=INVITE_DAYS)
    invite = db.insert_invite({"team_id": tid, "kind": "email", "token_hash": code_hash(raw), "email": email, "role": body.role,
                               "invited_by": user["id"], "invited_by_name": _name(user), "expires_at": expires.isoformat()})
    for old in replaced:
        db.revoke_invite(tid, old["id"])
    link = join_link(raw)
    try:
        emailed = deliver.send_team_invite(email, me["team"]["name"], _name(user), body.role, link, expires)
    except Exception:  # the invitation exists either way; the admin can copy the link
        log.warning("team invite email failed", exc_info=True)
        emailed = False
    _event(tid, user, "invite.sent", email=email, role=body.role)
    return {"invite": _invite_out(invite), "link": link, "code": show_code(raw), "emailed": emailed}


class NewLink(BaseModel):
    model_config = {"extra": "forbid"}
    role: Literal["member", "viewer"] = "member"
    days: int = Field(default=7, ge=1, le=30)
    max_uses: int = Field(default=10, ge=1, le=100)
    email_domain: str | None = Field(default=None, max_length=253)


@router.post("/teams/{team_id}/links")
def create_link(team_id: uuid.UUID, body: NewLink, user: dict = Depends(require_user)) -> dict:
    """An invite link (a join code people can also type). Never grants admin; seats still limit who gets in."""
    _member(team_id, user, "admin", write=True)
    tid, domain = str(team_id), clean_domain(body.email_domain)
    if sum(1 for i in db.team_invites(tid) if i["kind"] == "link" and i["uses"] < i["max_uses"]) >= MAX_LINKS:
        raise HTTPException(409, f"This workspace has {MAX_LINKS} open invite links. Revoke one first.")
    _limit(f"invite:{tid}", 30, 86_400, "This workspace made many invitations today. Try again tomorrow.")
    raw = new_code()
    invite = db.insert_invite({"team_id": tid, "kind": "link", "token_hash": code_hash(raw), "email_domain": domain, "role": body.role,
                               "max_uses": body.max_uses, "invited_by": user["id"], "invited_by_name": _name(user),
                               "expires_at": (_now() + timedelta(days=body.days)).isoformat()})
    _event(tid, user, "link.created", role=body.role, email_domain=domain, max_uses=body.max_uses, days=body.days)
    return {"invite": _invite_out(invite), "link": join_link(raw), "code": show_code(raw)}


@router.delete("/teams/{team_id}/invites/{invite_id}")
def revoke_invite(team_id: uuid.UUID, invite_id: uuid.UUID, user: dict = Depends(require_user)) -> dict:
    _member(team_id, user, "admin")
    if not db.revoke_invite(str(team_id), str(invite_id)):
        raise HTTPException(404, "No open invitation with that id.")
    _event(str(team_id), user, "invite.revoked", invite_id=str(invite_id))
    return {"revoked": str(invite_id)}


class Code(BaseModel):
    model_config = {"extra": "forbid"}
    code: str = Field(min_length=1, max_length=500)


def _invite_for(text: str) -> dict:
    raw = read_code(text)
    invite = db.invite_by_hash(code_hash(raw)) if raw else None
    if not invite or not invite.get("team"):
        raise HTTPException(404, "That invitation code is not valid. Check it, or ask for a new invitation.")
    return invite


def _problem(invite: dict, user: dict) -> tuple[int, str] | None:
    """Why this person cannot use this invitation now, as (status, plain message), or None."""
    if invite["revoked_at"]:
        return 410, "This invitation was withdrawn. Ask for a new one."
    if (_ts(invite["expires_at"]) or _now()) <= _now():
        return 410, "This invitation has expired. Ask for a new one."
    if invite["uses"] >= invite["max_uses"]:
        return 410, "This invitation has already been used. Ask for a new one."
    email = (user.get("email") or "").lower()
    if not user.get("email_verified"):
        return 403, "Confirm your email address first, then open the invitation again."
    if invite["kind"] == "email" and email != invite["email"]:
        return 403, f"This invitation was sent to {mask(invite['email'])}. Sign in with that address to accept it."
    if invite.get("email_domain") and email.rsplit("@", 1)[-1] != invite["email_domain"]:
        return 403, f"This link is for @{invite['email_domain']} email addresses."
    return None


def _join(invite: dict, user: dict) -> dict:
    tid = invite["team_id"]
    if db.membership(tid, user["id"]):
        return {"team_id": tid, "joined": False}
    problem = _problem(invite, user)
    if problem:
        raise HTTPException(*problem)
    if not _plus(invite["team"]["owner_id"]):
        raise HTTPException(402, "This workspace is read-only right now, so it cannot take new members.")
    result = db.rpc("team_join", {"p_invite": invite["id"], "p_user": user["id"], "p_name": _name(user), "p_email": (user.get("email") or "").lower(),
                                  "p_seats": SEATS, "p_max_teams": MAX_MEMBERSHIPS})
    if result == "full":
        raise HTTPException(409, "This workspace has no free seat. Ask its owner to make room.")
    if result == "limit":
        raise HTTPException(409, "You are in the most workspaces one account can join. Leave one first.")
    if result not in ("joined", "member"):
        raise HTTPException(410, "This invitation is no longer valid. Ask for a new one.")
    if result == "joined":
        _event(tid, user, "member.joined", role=invite["role"], via=invite["kind"])
    return {"team_id": tid, "joined": result == "joined"}


@router.post("/invites/preview")
def preview_invite(body: Code, user: dict = Depends(require_user)) -> dict:
    """What a code leads to, before joining: the workspace name, who invited, the role, and anything in the way."""
    _limit(f"code:{user['id']}", 30, 600, "Too many invitation attempts. Wait ten minutes and try again.")
    invite = _invite_for(body.code)
    member = db.membership(invite["team_id"], user["id"]) is not None
    problem = None if member else _problem(invite, user)
    return {"team": {"id": invite["team"]["id"], "name": invite["team"]["name"]}, "role": invite["role"], "kind": invite["kind"],
            "invited_by_name": invite["invited_by_name"], "expires_at": invite["expires_at"], "member": member, "problem": problem[1] if problem else None}


@router.post("/invites/accept")
def accept_invite(body: Code, user: dict = Depends(require_user)) -> dict:
    _limit(f"code:{user['id']}", 30, 600, "Too many invitation attempts. Wait ten minutes and try again.")
    return _join(_invite_for(body.code), user)


def _addressed(invite_id: uuid.UUID, user: dict) -> dict:
    """An email invitation, only for its verified addressee (everyone else gets 404)."""
    invite = db.get_invite(str(invite_id))
    email = (user.get("email") or "").lower()
    if not invite or invite["kind"] != "email" or not invite.get("team") or not user.get("email_verified") or invite["email"] != email:
        raise HTTPException(404, "No invitation with that id for your email address.")
    return invite


@router.post("/invites/{invite_id}/accept")
def accept_listed_invite(invite_id: uuid.UUID, user: dict = Depends(require_user)) -> dict:
    """Accept from the Team page, without the code: the invitation was sent to this verified address."""
    return _join(_addressed(invite_id, user), user)


@router.post("/invites/{invite_id}/decline")
def decline_invite(invite_id: uuid.UUID, user: dict = Depends(require_user)) -> dict:
    invite = _addressed(invite_id, user)
    if db.revoke_invite(invite["team_id"], invite["id"]):
        _event(invite["team_id"], user, "invite.declined", email=invite["email"])
    return {"declined": str(invite_id)}


# ---------- shared reports ----------


class ShareRun(BaseModel):
    model_config = {"extra": "forbid"}
    run_id: str = Field(pattern=RUN_ID)


@router.get("/teams/{team_id}/runs")
def shared_runs(team_id: uuid.UUID, before: str | None = Query(None, max_length=40), user: dict = Depends(require_user)) -> dict:
    """Reports shared into the workspace, newest first, 50 per page (`before` = the last `shared_at` seen)."""
    _member(team_id, user)
    tid = str(team_id)
    if before:
        try:
            before = datetime.fromisoformat(before.replace(" ", "+")).isoformat()
        except ValueError as e:
            raise HTTPException(422, "before must be a timestamp") from e
    shares = db.team_runs(tid, 50, before)
    runs = {r["id"]: r for r in db.runs_brief([s["run_id"] for s in shares])}
    names = {m["user_id"]: m["name"] for m in db.team_members(tid)}
    comments = db.thread_counts(tid) if shares else {}
    out = []
    for s in shares:
        run = runs.get(s["run_id"])
        if not run:
            continue
        out.append({"run_id": run["id"], "site": run["site"], "goal": run["goal"], "persona": run["persona"], "kind": run["kind"], "status": run["status"],
                    "created_at": run["created_at"], "score": _score(run), "findings": _counts(run), "owner_id": run.get("user_id"),
                    "shared_by": s["shared_by"], "shared_by_name": names.get(s["shared_by"] or "", "Former member"), "shared_at": s["shared_at"],
                    "comments": comments.get(f"run:{run['id']}", 0)})
    return {"runs": out, "has_more": len(shares) == 50}


@router.post("/teams/{team_id}/runs")
def share_run(team_id: uuid.UUID, body: ShareRun, user: dict = Depends(require_user)) -> dict:
    """Share one of your own runs. Members read it (and its screenshots) through row-level security from then on."""
    _member(team_id, user, "member", write=True)
    run = db.get_run(body.run_id)
    if not run or str(run.get("user_id")) != user["id"]:
        raise HTTPException(404, "unknown run")
    if run.get("kind") in ("compare", "compare_part"):
        raise HTTPException(422, "Competitor comparisons cannot be shared to a workspace yet. Share the report of your own site.")
    if db.share_run(str(team_id), body.run_id, user["id"]):
        _event(str(team_id), user, "run.shared", run_id=body.run_id, site=run["site"], kind=run.get("kind"))
    return {"shared": body.run_id}


@router.delete("/teams/{team_id}/runs/{run_id}")
def unshare_run(team_id: uuid.UUID, run_id: str = Path(pattern=RUN_ID), user: dict = Depends(require_user)) -> dict:
    """The person who shared it, the run's owner, or an admin can take a report out of the workspace."""
    me = _member(team_id, user)
    tid = str(team_id)
    share = db.team_run(tid, run_id)
    if not share:
        raise HTTPException(404, "That report is not shared in this workspace.")
    run = db.get_run(run_id)
    if share["shared_by"] != user["id"] and RANK[me["role"]] < RANK["admin"] and (not run or str(run.get("user_id")) != user["id"]):
        raise HTTPException(403, "Only the person who shared this report, its owner or an admin can remove it.")
    db.unshare_run(tid, run_id)
    _event(tid, user, "run.unshared", run_id=run_id, site=run["site"] if run else None)
    return {"unshared": run_id}


@router.get("/runs/{run_id}/teams")
def run_teams(run_id: str = Path(pattern=RUN_ID), user: dict = Depends(require_user)) -> dict:
    """For the owner's report page: the workspaces this run can go to, and where it already is."""
    run = db.get_run(run_id)
    if not run or str(run.get("user_id")) != user["id"]:
        raise HTTPException(404, "unknown run")
    shared = set(db.teams_for_run(run_id))
    rows = [m for m in db.memberships(user["id"]) if m.get("team") and m["role"] != "viewer"]
    return {"teams": [{"id": m["team"]["id"], "name": m["team"]["name"], "shared": m["team"]["id"] in shared} for m in rows]}


def auto_share(user_id: str, run_id: str, site: str, kind: str) -> None:
    """Put a new run into every active workspace where its owner turned on auto-share. Never raises: a run must not
    fail because of a workspace."""
    try:
        for tid in db.auto_share_teams(user_id):
            me = db.membership(tid, user_id)
            if not me or me["role"] == "viewer" or not me.get("team") or not _plus(me["team"]["owner_id"]):
                continue
            if db.share_run(tid, run_id, user_id):
                db.insert_event({"team_id": tid, "actor_id": user_id, "actor_name": me["name"] or "Member", "type": "run.shared",
                                 "detail": {"run_id": run_id, "site": site, "kind": kind, "auto": True}})
    except Exception:
        log.warning("auto-share of run %s failed", run_id, exc_info=True)


# ---------- findings board ----------


class Triage(BaseModel):
    model_config = {"extra": "forbid"}
    origin: str = Field(min_length=1, max_length=300)
    fingerprint: str = Field(min_length=3, max_length=300)
    status: Literal["open", "in_progress", "fixed", "wont_fix"] | None = None
    assignee_id: uuid.UUID | None = None


@router.get("/teams/{team_id}/findings")
def findings(team_id: uuid.UUID, user: dict = Depends(require_user)) -> dict:
    me = _member(team_id, user)
    tid = str(team_id)
    members = db.team_members(tid)
    return {"findings": _board(tid, names={m["user_id"]: m["name"] for m in members}),
            "assignees": [{"user_id": m["user_id"], "name": m["name"]} for m in members if m["role"] != "viewer"],
            "can_triage": _can(me["role"], _active(me))["triage"]}


@router.post("/teams/{team_id}/findings")
def triage(team_id: uuid.UUID, body: Triage, user: dict = Depends(require_user)) -> dict:
    """Set a finding's status and/or assignee. Only findings that appear in this workspace's reports can be triaged."""
    _member(team_id, user, "member", write=True)
    tid = str(team_id)
    if body.status is None and "assignee_id" not in body.model_fields_set:
        raise HTTPException(422, "Change the status or the assignee.")
    members = {m["user_id"]: m for m in db.team_members(tid)}
    item = next((i for i in _board(tid, names={k: m["name"] for k, m in members.items()})
                 if i["origin"] == body.origin and i["fingerprint"] == body.fingerprint), None)
    if not item:
        raise HTTPException(404, "That finding is not in this workspace's reports.")
    status, assignee = body.status or item["status"], item["assignee_id"]
    if "assignee_id" in body.model_fields_set:
        assignee = str(body.assignee_id) if body.assignee_id else None
        if assignee and (assignee not in members or members[assignee]["role"] == "viewer"):
            raise HTTPException(422, "Assign findings to a member of this workspace (not a viewer).")
    saved = db.save_finding_state({"team_id": tid, "origin": body.origin, "fingerprint": body.fingerprint, "status": status,
                                   "assignee_id": assignee, "updated_by": user["id"]}) or {}
    if status != item["status"]:
        _event(tid, user, "finding.status", title=item["title"], site=item["site"], thread=item["thread"], old=item["status"], new=status)
    if assignee != item["assignee_id"]:
        _event(tid, user, "finding.assigned", title=item["title"], site=item["site"], thread=item["thread"],
               assignee_id=assignee, assignee_name=members[assignee]["name"] if assignee else None)
    return {**item, "status": status, "assignee_id": assignee, "assignee_name": members[assignee]["name"] if assignee else None,
            "updated_at": saved.get("updated_at"), "updated_by_name": _name(user), "seen_again": False}


# ---------- chat and comments ----------


class NewMessage(BaseModel):
    model_config = {"extra": "forbid"}
    body: str = Field(min_length=1, max_length=8000)
    thread: str = Field(default="general", max_length=48)
    mentions: list[uuid.UUID] = Field(default_factory=list, max_length=20)
    client_id: uuid.UUID | None = None  # the browser's id for this send, so a retry lands once


class EditMessage(BaseModel):
    model_config = {"extra": "forbid"}
    body: str = Field(min_length=1, max_length=8000)


class Read(BaseModel):
    model_config = {"extra": "forbid"}
    message_id: int = Field(ge=0, le=2**62)


def _thread(thread: str) -> str:
    if not THREAD.fullmatch(thread):
        raise HTTPException(422, "thread is general, run:<run id> or finding:<key>")
    return thread


@router.get("/teams/{team_id}/messages")
def list_messages(team_id: uuid.UUID, thread: str = Query("general", max_length=48), after: int | None = Query(None, ge=0, le=2**62),
                  before: int | None = Query(None, ge=1, le=2**62), limit: int = Query(50, ge=1, le=100), user: dict = Depends(require_user)) -> dict:
    """Oldest first. `after` fetches what arrived since a message id (live updates); `before` pages back in history."""
    _member(team_id, user)
    rows = db.team_messages(str(team_id), _thread(thread), after=after, before=before, limit=limit)
    return {"messages": [_message_out(m) for m in rows], "has_more": len(rows) == limit}


@router.post("/teams/{team_id}/messages")
def post_message(team_id: uuid.UUID, body: NewMessage, user: dict = Depends(require_user)) -> dict:
    me = _member(team_id, user, write=True)
    tid, thread = str(team_id), _thread(body.thread)
    if thread.startswith("run:") and not db.team_run(tid, thread[4:]):
        raise HTTPException(404, "That report is not shared in this workspace.")
    text = clean_body(body.body)
    _limit(f"message:{user['id']}", 30, 60, "You are sending messages very fast. Wait a moment and try again.")
    member_ids = {m["user_id"] for m in db.team_members(tid)} if body.mentions else set()
    mentions = [u for u in dict.fromkeys(str(m) for m in body.mentions) if u in member_ids and u != user["id"]]
    stored = db.insert_message({"team_id": tid, "thread": thread, "author_id": user["id"], "author_name": _name(user), "body": text,
                                "mentions": mentions, "client_id": str(body.client_id or uuid.uuid4())})
    if not stored or stored.get("author_id") != user["id"]:
        raise HTTPException(409, "That message id is already taken. Send it again.")
    if thread == "general" and stored["id"] > me["last_read_message_id"]:  # your own message counts as read
        db.update_member(tid, user["id"], {"last_read_message_id": stored["id"], "last_seen_at": _now().isoformat()}, last_read_message_id=f"lt.{stored['id']}")
    return _message_out(stored)


@router.post("/teams/{team_id}/messages/{message_id}")
def edit_message(team_id: uuid.UUID, body: EditMessage, message_id: int = Path(ge=1, le=2**62), user: dict = Depends(require_user)) -> dict:
    _member(team_id, user, write=True)
    tid = str(team_id)
    message = db.get_message(tid, message_id)
    if not message or message.get("deleted_at"):
        raise HTTPException(404, "No message with that id.")
    if message.get("author_id") != user["id"]:
        raise HTTPException(403, "You can only edit your own messages.")
    updated = db.update_message(tid, message_id, {"body": clean_body(body.body), "edited_at": _now().isoformat()})
    if not updated:
        raise HTTPException(404, "No message with that id.")
    return _message_out(updated)


@router.delete("/teams/{team_id}/messages/{message_id}")
def delete_message(team_id: uuid.UUID, message_id: int = Path(ge=1, le=2**62), user: dict = Depends(require_user)) -> dict:
    """The author can always delete their message; admins can remove anyone's (recorded in the activity log)."""
    me = _member(team_id, user)
    tid = str(team_id)
    message = db.get_message(tid, message_id)
    if not message or message.get("deleted_at"):
        raise HTTPException(404, "No message with that id.")
    own = message.get("author_id") == user["id"]
    if not own and RANK[me["role"]] < RANK["admin"]:
        raise HTTPException(403, "Only the author or an admin can delete this message.")
    db.update_message(tid, message_id, {"body": "", "mentions": [], "deleted_at": _now().isoformat()})
    if not own:
        _event(tid, user, "message.removed", author_name=message.get("author_name"), thread=message["thread"])
    return {"deleted": message_id}


@router.post("/teams/{team_id}/read")
def mark_read(team_id: uuid.UUID, body: Read, user: dict = Depends(require_user)) -> dict:
    """Mark the workspace channel read up to a message, and say you are here (presence)."""
    me = _member(team_id, user)
    tid, now = str(team_id), _now().isoformat()
    if body.message_id > me["last_read_message_id"] and db.update_member(tid, user["id"], {"last_read_message_id": body.message_id, "last_seen_at": now},
                                                                          last_read_message_id=f"lt.{body.message_id}"):
        return {"last_read_message_id": body.message_id}
    db.update_member(tid, user["id"], {"last_seen_at": now})
    return {"last_read_message_id": me["last_read_message_id"]}


@router.get("/teams/{team_id}/activity")
def activity(team_id: uuid.UUID, before: int | None = Query(None, ge=1, le=2**62), user: dict = Depends(require_user)) -> dict:
    _member(team_id, user)
    rows = db.team_events(str(team_id), before, 50)
    return {"events": [_event_out(e) for e in rows], "has_more": len(rows) == 50}


# ---------- account export and deletion ----------


def before_account_delete(user_id: str) -> None:
    """Refuse to delete an account that owns a workspace with other people in it: they would lose it. Workspaces the
    user owns alone go with the account (database cascade)."""
    blocked = [m["team"]["name"] for m in db.memberships(user_id)
               if m["role"] == "owner" and m.get("team") and len(db.team_members(m["team_id"])) > 1]
    if blocked:
        raise HTTPException(409, f"Hand over or delete your workspaces with other members first: {', '.join(blocked)}.")


def export(user_id: str) -> dict:
    return {"memberships": [{"team_id": m["team_id"], "team": m["team"]["name"] if m.get("team") else None, "role": m["role"], "joined_at": m["joined_at"],
                             "auto_share": m["auto_share"]} for m in db.memberships(user_id)],
            "messages": db.messages_by(user_id)}
