"""GitHub App connect and fix pull requests (Plus; P2.1 minimal, P4.4).

The Walkthru GitHub App is installed by the owner on the repositories they choose. We keep only the installation id.
Tokens are minted per action, scoped to one repository, and never stored.

Connecting proves ownership: GitHub's install redirect carries an installation id anyone could copy, so the connect
call also needs the user-to-server OAuth code from that same redirect. We exchange it once, check that the
installation is in the signed-in GitHub user's installations, and revoke the token straight away.

A fix pull request only makes deterministic config changes from recipes.json: security headers in vercel.json,
netlify.toml or public/_headers, and new llms.txt or ai.txt files. Files are created or appended to, never
rewritten. Secrets and application code are never touched. The PR explains every change and the checks. Walkthru
never merges; the owner reviews and merges.
"""

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time

import httpx

from app.agent import fix_prompt

API = os.environ.get("GITHUB_API_URL", "https://api.github.com")
WEB = os.environ.get("GITHUB_WEB_URL", "https://github.com")
TIMEOUT = httpx.Timeout(20.0, connect=5.0)
REPO_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9-]{0,38}/(?!\.\.?$)[A-Za-z0-9_.-]{1,100}$"  # GitHub owner rules; never "." or ".."
REPO = re.compile(REPO_PATTERN)


class GitHubError(Exception):
    """GitHub refused or failed; the message is safe to show."""


def configured() -> bool:
    return all(os.environ.get(k) for k in ("GITHUB_APP_ID", "GITHUB_APP_SLUG", "GITHUB_APP_PRIVATE_KEY", "GITHUB_APP_CLIENT_ID", "GITHUB_APP_CLIENT_SECRET"))


def _http() -> httpx.Client:
    return httpx.Client(timeout=TIMEOUT, headers={"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "Walkthru"})


def _private_key() -> str:
    key = os.environ["GITHUB_APP_PRIVATE_KEY"]
    return key.replace("\\n", "\n") if "\\n" in key else key  # .env files often hold the PEM on one line


def app_jwt() -> str:
    """The App's own 9-minute token (RS256), used only to mint installation tokens."""
    import jwt

    now = int(time.time())
    return jwt.encode({"iat": now - 60, "exp": now + 540, "iss": os.environ["GITHUB_APP_ID"]}, _private_key(), algorithm="RS256")


def _check(r: httpx.Response, what: str) -> dict | list:
    if r.status_code >= 400:
        detail = ""
        try:
            detail = str(r.json().get("message", ""))[:160]
        except ValueError:
            pass
        raise GitHubError(f"GitHub refused to {what} ({r.status_code}{': ' + detail if detail else ''}).")
    return r.json() if r.content else {}


def installation_token(installation_id: int, repo: str | None = None) -> str:
    """A one-hour token for one installation, narrowed to one repository and the permissions a fix PR needs."""
    body: dict = {}
    if repo:
        body = {"repositories": [repo.split("/", 1)[1]], "permissions": {"contents": "write", "pull_requests": "write", "metadata": "read"}}
    with _http() as c:
        data = _check(c.post(f"{API}/app/installations/{int(installation_id)}/access_tokens", json=body, headers={"Authorization": f"Bearer {app_jwt()}"}),
                      "open that repository")
    return data["token"]


# ---------- connecting: signed state and the OAuth ownership check ----------


def _state_key() -> bytes:
    return hashlib.sha256(b"walkthru-github-state:" + os.environ["GITHUB_APP_CLIENT_SECRET"].encode()).digest()


def state_for(user_id: str) -> str:
    """Ties the install redirect to the signed-in Walkthru user for an hour (stops a forged connect link)."""
    stamp = str(int(time.time()))
    sig = hmac.new(_state_key(), f"{user_id}.{stamp}".encode(), hashlib.sha256).hexdigest()[:32]
    return f"{stamp}.{sig}"


def state_ok(user_id: str, state: str) -> bool:
    stamp, _, sig = state.partition(".")
    if not stamp.isdigit() or time.time() - int(stamp) > 3600:
        return False
    good = hmac.new(_state_key(), f"{user_id}.{stamp}".encode(), hashlib.sha256).hexdigest()[:32]
    return hmac.compare_digest(good, sig)


def install_url(user_id: str) -> str:
    return f"{WEB}/apps/{os.environ['GITHUB_APP_SLUG']}/installations/new?state={state_for(user_id)}"


def owned_installation(code: str, installation_id: int) -> str:
    """Exchange the OAuth code from the install redirect, confirm the GitHub user can see this installation, and revoke
    the user token. Returns the account (user or organization) the installation belongs to."""
    client_id, client_secret = os.environ["GITHUB_APP_CLIENT_ID"], os.environ["GITHUB_APP_CLIENT_SECRET"]
    with _http() as c:
        tok = c.post(f"{WEB}/login/oauth/access_token", data={"client_id": client_id, "client_secret": client_secret, "code": code},
                     headers={"Accept": "application/json"})
        token = (tok.json() if tok.status_code == 200 else {}).get("access_token")
        if not token:
            raise GitHubError("GitHub did not confirm the sign-in. Start the connection again from Settings.")
        try:
            data = _check(c.get(f"{API}/user/installations", headers={"Authorization": f"Bearer {token}"}), "list your installations")
            match = next((i for i in data.get("installations", []) if int(i.get("id", 0)) == int(installation_id)), None)
        finally:
            c.request("DELETE", f"{API}/applications/{client_id}/token", json={"access_token": token}, auth=(client_id, client_secret))
    if not match:
        raise GitHubError("That installation does not belong to the GitHub account you signed in with.")
    return str((match.get("account") or {}).get("login") or "")


def repositories(installation_id: int) -> list[dict]:
    """Repositories the owner gave the App, first 100."""
    token = installation_token(installation_id)
    with _http() as c:
        data = _check(c.get(f"{API}/installation/repositories", params={"per_page": 100}, headers={"Authorization": f"Bearer {token}"}), "list repositories")
    return [{"full_name": r["full_name"], "private": bool(r.get("private")), "default_branch": r.get("default_branch") or "main",
             "installation_id": int(installation_id)} for r in data.get("repositories", [])]


# ---------- the fix: deterministic changes from recipes ----------


def _headers_for(report: dict) -> dict[str, dict]:
    """Header name -> {value, titles} from findings whose recipe sets a header with a real value."""
    out: dict[str, dict] = {}
    for f in report.get("findings", []):
        r = fix_prompt.recipe(f) or {}
        h = r.get("header")
        if not h or "<" in h["value"]:
            continue
        entry = out.setdefault(h["name"], {"value": h["value"], "titles": []})
        entry["titles"].append(f["title"])
    return out


def changes(report: dict, read) -> tuple[list[dict], list[str]]:
    """The file changes a fix PR would make, and what it leaves for the owner. `read(path)` returns the file's text or
    None. Every change: {path, content, action (create or update), summary, titles}."""
    stack = report.get("stack") or {}
    done: list[dict] = []
    left: list[str] = []
    headers = _headers_for(report)
    host, framework = stack.get("hosting"), stack.get("framework")

    if headers:
        if host == "vercel":  # also right for Next.js on Vercel: Vercel applies vercel.json headers to every framework
            _vercel(headers, read, done, left)
        elif host == "netlify":
            _netlify(headers, read, done)
        elif host == "cloudflare":
            _underscore_headers(headers, read, done)
        else:
            where = "next.config.js" if framework == "nextjs" else "your hosting's header settings"
            left.append(f"Security headers ({', '.join(headers)}): Walkthru only edits vercel.json, netlify.toml or _headers; add them in {where} (the fix plan has the snippet).")

    public = "public/" if read("public/") is not None or framework in ("nextjs", "vite", "lovable", "bolt", "astro") else ""
    llms = next((x for x in (report.get("geo") or {}).get("fixes", []) if x.get("id") == "llms"), None)
    rules = {fix_prompt.rule_of(f) for f in report.get("findings", [])}
    if "geo.no_llms_txt" in rules and llms and read(f"{public}llms.txt") is None:
        done.append({"path": f"{public}llms.txt", "content": llms["code"].rstrip() + "\n", "action": "create",
                     "summary": "Add llms.txt, a map of your site for AI assistants", "titles": ["No llms.txt"]})
    if "geo.no_well_known_ai_txt" in rules and read(f"{public}.well-known/ai.txt") is None:
        done.append({"path": f"{public}.well-known/ai.txt", "content": "User-Agent: *\nAllow: /\n", "action": "create",
                     "summary": "Add /.well-known/ai.txt", "titles": ["No /.well-known/ai.txt"]})
    covered = {t for c in done for t in c["titles"]}
    for f in report.get("findings", []):
        if f["title"] not in covered and f["kind"] != "ux":
            left.append(f["title"])
    return done, left


def _vercel(headers: dict, read, done: list, left: list) -> None:
    text = read("vercel.json")
    try:
        config = json.loads(text) if text else {}
    except ValueError:
        left.append("vercel.json is not plain JSON, so Walkthru did not edit it; add the headers by hand (the fix plan has the snippet).")
        return
    if not isinstance(config, dict):
        return
    present = {h.get("key", "").lower() for rule in config.get("headers", []) if isinstance(rule, dict) for h in rule.get("headers", []) if isinstance(h, dict)}
    new = {k: v for k, v in headers.items() if k.lower() not in present}
    if not new:
        return
    config.setdefault("headers", []).append({"source": "/(.*)", "headers": [{"key": k, "value": v["value"]} for k, v in new.items()]})
    done.append({"path": "vercel.json", "content": json.dumps(config, indent=2) + "\n", "action": "update" if text else "create",
                 "summary": f"Send {', '.join(new)} on every page", "titles": [t for v in new.values() for t in v["titles"]]})


def _netlify(headers: dict, read, done: list) -> None:
    text = read("netlify.toml") or ""
    new = {k: v for k, v in headers.items() if k.lower() not in text.lower()}
    if not new:
        return
    block = '\n[[headers]]\n  for = "/*"\n  [headers.values]\n' + "".join(f'    {k} = "{v["value"]}"\n' for k, v in new.items())
    done.append({"path": "netlify.toml", "content": (text.rstrip() + "\n" if text else "") + block.lstrip("\n" if not text else ""),
                 "action": "update" if text else "create", "summary": f"Send {', '.join(new)} on every page",
                 "titles": [t for v in new.values() for t in v["titles"]]})


def _underscore_headers(headers: dict, read, done: list) -> None:
    path = "public/_headers"
    text = read(path) or ""
    new = {k: v for k, v in headers.items() if k.lower() not in text.lower()}
    if not new:
        return
    block = "/*\n" + "".join(f"  {k}: {v['value']}\n" for k, v in new.items())
    done.append({"path": path, "content": (text.rstrip() + "\n\n" if text else "") + block, "action": "update" if text else "create",
                 "summary": f"Send {', '.join(new)} on every page", "titles": [t for v in new.values() for t in v["titles"]]})


def _body(run: dict, done: list[dict], left: list[str], report: dict) -> str:
    places = fix_prompt._places(run, report)
    checks = []
    for f in report.get("findings", []):
        r = fix_prompt.recipe(f) or {}
        if r.get("check") and any(f["title"] in c["titles"] for c in done):
            checks.append(fix_prompt._fill(r["check"], places))
    risk = ["Content-Security-Policy is added in report-only mode: it logs problems and blocks nothing until you switch it on."] \
        if any("Content-Security-Policy-Report-Only" in c["content"] for c in done) else []
    lines = [
        f"Walkthru found these on {run['site']} (report `{run['id']}`) and made the config-only fixes below. Nothing else in the repository changed.",
        "",
        "## Changes",
        *[f"- `{c['path']}` ({c['action']}): {c['summary']}. Fixes: {'; '.join(c['titles'])}." for c in done],
        "",
        *(["## Risk", *[f"- {x}" for x in risk], ""] if risk else []),
        "## Check after deploying a preview",
        *([f"- `{c}`" for c in dict.fromkeys(checks)] or ["- Open the preview and click through the main pages."]),
        "",
        *(["## Not in this pull request", "Code, content and settings changes stay with you (the Walkthru fix plan covers them):",
           *[f"- {fix_prompt._mask(x)}" for x in left[:40]], ""] if left else []),
        "Walkthru never merges. Review the diff, deploy a preview, then merge when the checks pass, and rerun Walkthru to confirm.",
    ]
    return "\n".join(lines)


def _reader(c: httpx.Client, repo: str, token: str, ref: str):
    cache: dict[str, dict | None] = {}

    def fetch(path: str) -> dict | None:
        if path not in cache:
            r = c.get(f"{API}/repos/{repo}/contents/{path.rstrip('/')}", params={"ref": ref}, headers={"Authorization": f"Bearer {token}"})
            cache[path] = None if r.status_code == 404 else _check(r, f"read {path}")
        return cache[path]

    def read(path: str) -> str | None:
        data = fetch(path)
        if data is None:
            return None
        if isinstance(data, list):  # a folder
            return ""
        if data.get("type") != "file" or data.get("size", 0) > 200_000:
            return None
        return base64.b64decode(data.get("content") or "").decode("utf-8", errors="replace")

    return read, fetch


def open_fix_pr(installation_id: int, repo: str, run: dict, report: dict, *, confirm: bool) -> dict:
    """Preview (confirm False) or open (confirm True) the fix pull request on the repository's default branch."""
    if not REPO.fullmatch(repo):
        raise GitHubError("Pick a repository from the list.")
    token = installation_token(installation_id, repo)
    auth = {"Authorization": f"Bearer {token}"}
    with _http() as c:
        info = _check(c.get(f"{API}/repos/{repo}", headers=auth), "open that repository")
        base = info.get("default_branch") or "main"
        read, fetch = _reader(c, repo, token, base)
        done, left = changes(report, read)
        preview = {"repo": repo, "base": base, "changes": [{k: v for k, v in x.items() if k != "content"} | {"lines": x["content"].count("\n")} for x in done],
                   "left": left[:40]}
        if not confirm or not done:
            return preview
        head = _check(c.get(f"{API}/repos/{repo}/git/ref/heads/{base}", headers=auth), "read the default branch")["object"]["sha"]
        branch = f"walkthru/fixes-{run['id'][:8]}-{secrets.token_hex(2)}"
        _check(c.post(f"{API}/repos/{repo}/git/refs", json={"ref": f"refs/heads/{branch}", "sha": head}, headers=auth), "create a branch")
        for x in done:
            existing = fetch(x["path"])
            body = {"message": f"Walkthru: {x['summary']}", "branch": branch, "content": base64.b64encode(x["content"].encode()).decode()}
            if isinstance(existing, dict) and existing.get("sha"):
                body["sha"] = existing["sha"]
            _check(c.put(f"{API}/repos/{repo}/contents/{x['path']}", json=body, headers=auth), f"write {x['path']}")
        fixed = sum(len(x["titles"]) for x in done)
        pr = _check(c.post(f"{API}/repos/{repo}/pulls", headers=auth, json={
            "title": f"Walkthru: fix {fixed} finding{'s' if fixed != 1 else ''} on {fix_prompt._places(run, report)['host']}",
            "head": branch, "base": base, "body": _body(run, done, left, report), "maintainer_can_modify": True}), "open the pull request")
        return preview | {"url": pr.get("html_url"), "number": pr.get("number"), "branch": branch}
