"""The founder's admin panel: plan requests, users and their plans, your own access, and what happened.

Runs on the founder's machine only (127.0.0.1, `python -m admin`), never on the public API. It talks to Supabase with
the secret key from apps/api/.env, the same way scripts/billing.py and scripts/grant_plan.py do.

Every page needs a session from password + authenticator code; every change needs a fresh authenticator code too.
Server-rendered HTML with no JavaScript, a CSP that allows none, and every value escaped.
"""

import html
import os
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response

from admin.auth import Guard, totp_counter
from app import billing, db, plans

PORT = int(os.environ.get("ADMIN_PORT", "8020"))
ALLOWED_HOSTS = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}  # also refuses DNS-rebinding hosts
COOKIE = "wt_admin"
PAID = [p for p in plans.PLANS if p != "free"]
PLAN_NAME = {"free": "Free", "launch": "Launch Pack", "pro": "Pro", "plus": "Plus"}

guard = Guard()
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


def _admin_email() -> str:
    return (os.environ.get("ADMIN_EMAIL") or os.environ.get("FOUNDER_EMAIL") or "").strip().lower()


def e(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


# ---------- the walls: host, origin, CSRF, headers ----------

HEADERS = {
    "Content-Security-Policy": "default-src 'none'; style-src 'self'; img-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",  # "no-referrer" makes browsers send Origin: null on form posts
    "Cache-Control": "no-store",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}


@app.middleware("http")
async def walls(request: Request, call_next) -> Response:
    if request.headers.get("host", "") not in ALLOWED_HOSTS:
        return PlainTextResponse("Not found", status_code=404)
    if request.method == "POST" and request.headers.get("origin") not in {f"http://{h}" for h in ALLOWED_HOSTS}:
        return PlainTextResponse("Forbidden", status_code=403)
    response = await call_next(request)
    response.headers.update(HEADERS)
    return response


def _session(request: Request):
    return guard.session(request.cookies.get(COOKIE))


def _home(message: str) -> RedirectResponse:
    return RedirectResponse(f"/?m={message}", status_code=303)


def _refused(request: Request, csrf: str, code: str) -> Response | None:
    """Why a change is refused, or None. Changes need a live session, the form's CSRF token and a current code."""
    s = _session(request)
    if s is None:
        return RedirectResponse("/login", status_code=303)
    if not csrf or csrf != s.csrf:
        return PlainTextResponse("Forbidden", status_code=403)
    if totp_counter(os.environ["ADMIN_TOTP_SECRET"], code) is None:
        return _home("bad-code")
    return None


# ---------- data (secret key, server side) ----------


def _users() -> list[dict]:
    """Every account: only what the panel shows. ponytail: pages through Auth each load; cache past a few thousand users."""
    out: list[dict] = []
    for page in range(1, 51):
        batch = (db._request("GET", "/auth/v1/admin/users", params={"page": str(page), "per_page": "200"}) or {}).get("users", [])
        out += [{"id": u["id"], "email": (u.get("email") or "").lower(), "created_at": u.get("created_at") or "",
                 "last_sign_in_at": u.get("last_sign_in_at") or "", "provider": (u.get("app_metadata") or {}).get("provider", "")} for u in batch]
        if len(batch) < 200:
            break
    return out


def _passes() -> dict[str, dict]:
    now = datetime.now(UTC).isoformat()
    rows = db._select("entitlements", {"starts_at": f"lte.{now}", "expires_at": f"gt.{now}", "revoked_at": "is.null",
                                       "select": "user_id,plan,expires_at,runs_granted,source", "order": "expires_at.asc"})
    return {r["user_id"]: r for r in rows}  # the latest-ending pass wins


def _recent(table: str, select: str, limit: int = 30) -> list[dict]:
    return db._select(table, {"select": select, "order": "created_at.desc", "limit": str(limit)})


def _uuid(value: str) -> bool:
    try:
        return str(uuid.UUID(value)) == value.lower()
    except ValueError:
        return False


def _grant(email: str, plan: str, days: int, request_id: str | None, actor: str) -> str:
    if plan not in PAID or not 1 <= days <= 366:
        return "bad-input"
    user = next((u for u in _users() if u["email"] == email.strip().lower()), None)
    if user is None:
        return "no-user"
    db.grant_entitlement(user["id"], plan, days, plans.PLANS[plan].runs, "founder")
    if request_id:
        db.decide_access_request(request_id, "approved")
    db.audit(actor, "pass.grant", user["id"], {"email": user["email"], "plan": plan, "days": days, "request_id": request_id})
    return "granted"


# ---------- pages ----------


def _page(title: str, body: str, *, signed_in: bool = False, csrf: str = "") -> HTMLResponse:
    out = (f'<form method="post" action="/logout"><input type="hidden" name="csrf" value="{e(csrf)}">'
           '<button class="link">Sign out</button></form>') if signed_in else ""
    return HTMLResponse(
        f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<meta name="robots" content="noindex, nofollow"><title>{e(title)}</title><link rel="stylesheet" href="/admin.css"></head>'
        f'<body><header><strong>Walkthru admin</strong>{out}</header><main>{body}</main></body></html>'
    )


MESSAGES = {
    "granted": "Pass granted.", "ended": "Pass ended.", "rejected": "Request declined.", "offered": "Payment offer sent. It shows on their Plan & billing page for 24 hours.",
    "bad-code": "That authenticator code did not work. Nothing changed.", "no-user": "No account with that email. They need to sign in once first.",
    "bad-input": "Check the plan and the number of days.", "no-request": "That request was already decided.", "offer-failed": "Could not create the payment offer. Check the Dodo settings.",
}


@app.get("/admin.css")
def css() -> Response:
    return Response(CSS, media_type="text/css")


@app.get("/login", response_class=HTMLResponse)
def login_page(m: str = "") -> HTMLResponse:
    note = {"wrong": "Wrong password or code.", "locked": "Too many attempts. The panel is locked for 15 minutes."}.get(m, "")
    return _page("Sign in", f"""
      <section class="narrow"><h1>Sign in</h1>{f'<p class="note" role="alert">{e(note)}</p>' if note else ''}
      <form method="post" action="/login" class="stack">
        <label>Password <input type="password" name="password" autocomplete="current-password" required></label>
        <label>Authenticator code <input name="code" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9 ]{{6,7}}" required></label>
        <button>Sign in</button>
      </form></section>""")


@app.post("/login")
def login(password: str = Form(max_length=200), code: str = Form(max_length=10)) -> Response:
    if guard.locked():
        return RedirectResponse("/login?m=locked", status_code=303)
    token = guard.login(password, code, os.environ["ADMIN_PASSWORD_HASH"], os.environ["ADMIN_TOTP_SECRET"])
    actor = _admin_email() or "admin"
    if token is None:
        db.audit(actor, "admin.login_failed", "panel", {"locked": guard.locked()})
        return RedirectResponse("/login?m=locked" if guard.locked() else "/login?m=wrong", status_code=303)
    previous = db._select("admin_audit_log", {"action": "eq.admin.login", "select": "created_at", "order": "created_at.desc", "limit": "1"})
    guard.session(token).since = previous[0]["created_at"] if previous else ""
    db.audit(actor, "admin.login", "panel", {})
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(COOKIE, token, httponly=True, samesite="strict", path="/", max_age=8 * 3600)
    return response


@app.post("/logout")
def logout(request: Request, csrf: str = Form("")) -> Response:
    s = _session(request)
    if s is not None and csrf == s.csrf:
        guard.logout(request.cookies.get(COOKIE))
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(COOKIE, path="/")
    return response


def _code_field() -> str:
    return '<input name="code" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9 ]{6,7}" placeholder="Code" aria-label="Authenticator code" required class="code">'


def _plan_select(selected: str = "pro") -> str:
    return '<select name="plan" aria-label="Plan">' + "".join(
        f'<option value="{p}"{" selected" if p == selected else ""}>{PLAN_NAME[p]}</option>' for p in PAID) + "</select>"


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, m: str = "", q: str = "") -> Response:
    s = _session(request)
    if s is None:
        return RedirectResponse("/login", status_code=303)
    hidden = f'<input type="hidden" name="csrf" value="{e(s.csrf)}">'
    users, passes = _users(), _passes()
    email_of = {u["id"]: u["email"] for u in users}
    requests = db.pending_access_requests()
    events = _recent("app_events", "kind,user_id,detail,created_at", 50)
    payments = db._select("billing_events", {"select": "event_type,received_at,result", "order": "received_at.desc", "limit": "20"})
    audit = _recent("admin_audit_log", "actor,action,detail,created_at", 30)
    since = s.since

    new = lambda rows, key="created_at": sum(1 for r in rows if since and (r.get(key) or "") > since)
    by_plan = {p: sum(1 for x in passes.values() if x["plan"] == p) for p in PAID}
    strip = "".join(f'<div><span>{e(label)}</span><strong>{value}</strong></div>' for label, value in [
        ("Users", len(users)), *((PLAN_NAME[p], by_plan[p]) for p in PAID), ("Waiting requests", len(requests))])
    fresh = [(label, n) for label, n in [
        ("new users", new(users)), ("requests", new(requests)), ("feedback", new([x for x in events if x["kind"] == "feedback"])),
        ("server errors", new([x for x in events if x["kind"] == "server_error"])), ("payment events", new(payments, "received_at"))] if n]
    since_line = ("Since your last sign-in: " + ", ".join(f"{n} {label}" for label, n in fresh)) if fresh else (
        "Nothing new since your last sign-in." if since else "First sign-in.")

    offer_on = billing.configured()
    rows = "".join(f"""<tr><td>{e(email_of.get(r['user_id'], r['user_id']))}</td><td>{e(PLAN_NAME.get(r['plan'], r['plan']))}</td>
      <td class="muted">{e(r['note']) or '-'}</td><td class="muted">{e(r['created_at'][:16].replace('T', ' '))}</td><td>
      <form method="post" action="/grant" class="row">{hidden}<input type="hidden" name="email" value="{e(email_of.get(r['user_id'], ''))}">
        <input type="hidden" name="request_id" value="{e(r['id'])}">{_plan_select(r['plan'])}
        <input name="days" type="number" min="1" max="366" value="30" aria-label="Days">{_code_field()}<button>Grant free</button></form>
      {f'''<form method="post" action="/offer" class="row">{hidden}<input type="hidden" name="request_id" value="{e(r['id'])}">
        <label class="check"><input type="checkbox" name="founding" value="1"> Founding price</label>{_code_field()}<button>Send payment offer</button></form>''' if offer_on else ''}
      <form method="post" action="/reject" class="row">{hidden}<input type="hidden" name="request_id" value="{e(r['id'])}">{_code_field()}<button class="quiet">Decline</button></form>
      </td></tr>""" for r in requests) or '<tr><td colspan="5" class="muted">No requests waiting.</td></tr>'

    me = _admin_email()
    my_id = next((u["id"] for u in users if u["email"] == me), None)
    mine = passes.get(my_id) if my_id else None
    my_plan = f"{PLAN_NAME[mine['plan']]} until {mine['expires_at'][:10]}" if mine else "Free"

    wanted = q.strip().lower()
    listed = [u for u in users if wanted in u["email"]] if wanted else users
    user_rows = "".join(f"""<tr><td>{e(u['email'])}</td><td>{e(PLAN_NAME[passes[u['id']]['plan']]) if u['id'] in passes else 'Free'}</td>
      <td class="muted">{e(passes[u['id']]['expires_at'][:10]) if u['id'] in passes else '-'}</td><td class="muted">{e(u['provider'])}</td>
      <td class="muted">{e(u['created_at'][:10])}</td><td class="muted">{e(u['last_sign_in_at'][:10]) or '-'}</td></tr>"""
                        for u in sorted(listed, key=lambda u: u["created_at"], reverse=True)[:200])

    feed = sorted(
        [(x["created_at"], "Feedback" if x["kind"] == "feedback" else "Server error",
          (f"{email_of.get(x['user_id'], 'someone')}: {x['detail'].get('message', '')}" + (f" (on {x['detail']['page']})" if x["detail"].get("page") else ""))
          if x["kind"] == "feedback" else f"{x['detail'].get('method', '')} {x['detail'].get('route', '')}: {x['detail'].get('error', '')} {x['detail'].get('message', '')}")
         for x in events]
        + [(u["created_at"], "New user", f"{u['email']} ({u['provider'] or 'email'})") for u in sorted(users, key=lambda u: u["created_at"], reverse=True)[:20]]
        + [(p["received_at"], "Payment", f"{p['event_type']}: {p.get('result') or 'received'}") for p in payments]
        + [(a["created_at"], "Admin", f"{a['action']} {a['detail'].get('email', '')} {a['detail'].get('plan', '')}".strip()) for a in audit],
        key=lambda item: item[0], reverse=True)[:60]
    feed_rows = "".join(f'<li><time>{e(t[:16].replace("T", " "))}</time><span class="tag">{e(kind)}</span><span>{e(text)}</span></li>' for t, kind, text in feed)

    body = f"""
      {f'<p class="note" role="status">{e(MESSAGES.get(m, ""))}</p>' if m in MESSAGES else ''}
      <p class="muted">{e(since_line)}</p>
      <section class="strip">{strip}</section>

      <section><h2>Plan requests</h2>
        <table><thead><tr><th>Account</th><th>Plan</th><th>What they will test</th><th>Asked</th><th>Decide</th></tr></thead><tbody>{rows}</tbody></table>
        <p class="muted small">Grant free gives the pass now with no payment. {'Send payment offer lets them pay from Plan &amp; billing; the pass starts when Dodo confirms.' if offer_on else 'Payment offers appear here once Dodo is set up (docs/billing.md).'}</p>
      </section>

      <section><h2>Your access</h2>
        <p>{e(me or 'Set ADMIN_EMAIL in apps/api/.env')}: <strong>{e(my_plan)}</strong></p>
        {f'<form method="post" action="/grant-self" class="row">{hidden}{_plan_select("plus")}<input name="days" type="number" min="1" max="366" value="30" aria-label="Days">{_code_field()}<button>Give me this plan</button></form>' if me else ''}
      </section>

      <section><h2>Grant or end a pass</h2>
        <form method="post" action="/grant" class="row">{hidden}<input name="email" type="email" placeholder="Email" aria-label="Email" required>{_plan_select()}
          <input name="days" type="number" min="1" max="366" value="30" aria-label="Days">{_code_field()}<button>Grant</button></form>
        <form method="post" action="/end" class="row">{hidden}<input name="email" type="email" placeholder="Email" aria-label="Email to end the pass of" required>{_code_field()}<button class="quiet">End pass now</button></form>
      </section>

      <section><h2>Users <span class="muted">{len(listed)}</span></h2>
        <form method="get" action="/" class="row"><input name="q" value="{e(q)}" placeholder="Search by email" aria-label="Search by email"><button class="quiet">Search</button></form>
        <table><thead><tr><th>Email</th><th>Plan</th><th>Pass ends</th><th>Sign-in</th><th>Joined</th><th>Last seen</th></tr></thead><tbody>{user_rows or '<tr><td colspan="6" class="muted">No users.</td></tr>'}</tbody></table>
      </section>

      <section><h2>Activity</h2><ul class="feed">{feed_rows or '<li class="muted">Nothing yet.</li>'}</ul></section>"""
    return _page("Walkthru admin", body, signed_in=True, csrf=s.csrf)


# ---------- changes: each needs the session, the CSRF token and a fresh authenticator code ----------


@app.post("/grant")
def grant(request: Request, csrf: str = Form(""), code: str = Form(""), email: str = Form(max_length=320), plan: str = Form(max_length=20),
          days: int = Form(30), request_id: str = Form("", max_length=64)) -> Response:
    if refused := _refused(request, csrf, code):
        return refused
    if request_id and not (_uuid(request_id) and (db.get_access_request(request_id) or {}).get("status") == "pending"):
        return _home("no-request")
    return _home(_grant(email, plan, days, request_id or None, _admin_email() or "admin"))


@app.post("/grant-self")
def grant_self(request: Request, csrf: str = Form(""), code: str = Form(""), plan: str = Form(max_length=20), days: int = Form(30)) -> Response:
    if refused := _refused(request, csrf, code):
        return refused
    return _home(_grant(_admin_email(), plan, days, None, _admin_email() or "admin"))  # always the admin's own email, never the form's


@app.post("/end")
def end(request: Request, csrf: str = Form(""), code: str = Form(""), email: str = Form(max_length=320)) -> Response:
    if refused := _refused(request, csrf, code):
        return refused
    user = next((u for u in _users() if u["email"] == email.strip().lower()), None)
    if user is None:
        return _home("no-user")
    db.expire_entitlements(user["id"])
    db.audit(_admin_email() or "admin", "pass.end", user["id"], {"email": user["email"]})
    return _home("ended")


@app.post("/reject")
def reject(request: Request, csrf: str = Form(""), code: str = Form(""), request_id: str = Form(max_length=64)) -> Response:
    if refused := _refused(request, csrf, code):
        return refused
    if not _uuid(request_id) or not db.decide_access_request(request_id, "rejected"):
        return _home("no-request")
    db.audit(_admin_email() or "admin", "request.reject", request_id, {})
    return _home("rejected")


@app.post("/offer")
def offer(request: Request, csrf: str = Form(""), code: str = Form(""), request_id: str = Form(max_length=64), founding: str = Form("")) -> Response:
    """The same approval as `scripts/billing.py approve`: an exact-price offer the user pays within 24 hours."""
    if refused := _refused(request, csrf, code):
        return refused
    req = db.get_access_request(request_id) if _uuid(request_id) else None
    if not req or req["status"] != "pending":
        return _home("no-request")
    try:
        is_founding = founding == "1" and db.paid_founding_offers() < billing.FOUNDING_SEATS
        terms = billing.offer_terms(req["plan"], is_founding)
        billing.check_product(terms)  # refuse a checkout whose Dodo product charges something else
        expires = datetime.now(UTC) + timedelta(hours=billing.CHECKOUT_HOURS)
        made = db.create_offer(terms | {"user_id": req["user_id"], "request_id": req["id"], "checkout_expires_at": expires.isoformat(), "approved_by": _admin_email() or "admin"})
    except (billing.NotConfigured, ValueError):
        return _home("offer-failed")
    if not db.decide_access_request(req["id"], "approved"):
        db.mark_offer(made["id"], "approved", {"status": "cancelled"})
        return _home("no-request")
    db.audit(_admin_email() or "admin", "offer.create", made["id"], {"request_id": req["id"], "plan": req["plan"], "founding": is_founding})
    return _home("offered")


CSS = """
:root{--bg:#f4f4f5;--surface:#e9e9eb;--ink:#1b1b1f;--muted:#63636b;--line:#dedee2;--accent:#4d7274;--danger:#a33b3b;color-scheme:light}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
header{display:flex;justify-content:space-between;align-items:center;padding:14px 24px;border-bottom:1px solid var(--line)}
main{max-width:1100px;margin:0 auto;padding:24px}section{margin:0 0 36px}h1{font-weight:300;font-size:28px}h2{font-weight:400;font-size:18px;margin:0 0 12px}
.narrow{max-width:360px;margin:12vh auto}.stack{display:grid;gap:14px}label{display:grid;gap:6px;color:var(--muted)}
input,select,button{font:inherit;color:var(--ink);background:#fff;border:1px solid var(--line);border-radius:10px;padding:8px 10px}
input:focus,select:focus,button:focus{outline:2px solid var(--accent);outline-offset:1px}
button{background:var(--ink);color:var(--bg);border-color:var(--ink);cursor:pointer}button.quiet{background:#fff;color:var(--ink);border-color:var(--line)}
button.link{background:none;border:0;color:var(--muted);padding:0;text-decoration:underline}
.row{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 8px}.row input[type=number]{width:80px}.code{width:96px}.check{display:flex;flex-direction:row;gap:6px;align-items:center}
.strip{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:1px;background:var(--line);border:1px solid var(--line);border-radius:16px;overflow:hidden}
.strip div{background:var(--bg);padding:14px 16px;display:grid}.strip span{color:var(--muted);font-size:12px}.strip strong{font-weight:300;font-size:26px}
table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:10px 8px;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--muted);font-weight:400;font-size:12px}
.muted{color:var(--muted)}.small{font-size:12px}.note{border:1px solid var(--line);background:var(--surface);border-radius:12px;padding:10px 14px}
.feed{list-style:none;padding:0;margin:0;border-top:1px solid var(--line)}.feed li{display:grid;grid-template-columns:130px 110px 1fr;gap:12px;padding:10px 0;border-bottom:1px solid var(--line)}
.feed time{color:var(--muted);font-variant-numeric:tabular-nums}.tag{font-size:12px;color:var(--accent)}
@media (max-width:700px){.feed li{grid-template-columns:1fr}table{display:block;overflow-x:auto}}
"""
