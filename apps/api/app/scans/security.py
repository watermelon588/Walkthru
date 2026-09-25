"""Passive security hygiene. Headers, cookies, transport and mixed content for everyone; exposed files and
secrets in JS bundles only on verified domains (SPEC safety rule). Never sends payloads, never fuzzes."""

import hashlib
import hmac
import ipaddress
import os
import re
from urllib.parse import urljoin, urlsplit

import httpx
from selectolax.parser import HTMLParser

from app.agent.schema import Finding
from app.scans.fetch import get, origin

EXPOSED = {
    "/.env": re.compile(r"^\s*[A-Z_][A-Z0-9_]*\s*=", re.MULTILINE),
    "/.git/config": re.compile(r"\[core\]"),
    "/.git/HEAD": re.compile(r"^ref: refs/", re.MULTILINE),
    "/.DS_Store": re.compile(r"Bud1"),
    "/wp-config.php.bak": re.compile(r"DB_PASSWORD"),
}
SECRETS = [
    ("Stripe live key", re.compile(r"\bsk_live_[A-Za-z0-9]{20,}")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}")),
    ("Slack token", re.compile(r"\bxox[abp]-[0-9A-Za-z-]{20,}")),
    ("Private key block", re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----")),
]


def _f(severity: str, title: str, detail: str, fix: str, evidence: str | None = None) -> Finding:
    return Finding(kind="security", severity=severity, title=title, detail=detail, fix=fix, evidence=evidence)


def _local_address(url: str) -> bool:
    host = (urlsplit(url).hostname or "").lower()
    if host == "localhost" or host.endswith(".localhost"):
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return address.is_private or address.is_loopback or address.is_link_local


def verification_token(user_id: str) -> str:
    """Per-account token the site owner publishes to prove control of the domain."""
    key = os.environ.get("SUPABASE_SECRET_KEY", "dev").encode()
    return "wt-" + hmac.new(key, user_id.encode(), hashlib.sha256).hexdigest()[:24]


def verify_domain(url: str, token: str, c: httpx.Client, html: str | None = None) -> bool:
    """True when the homepage carries <meta name="walkthru-verification"> or /.well-known/walkthru.txt holds the token."""
    if html is None:
        r = get(c, url)
        html = r.text if r is not None else ""
    meta = HTMLParser(html).css_first('meta[name="walkthru-verification"]')
    if meta is not None and (meta.attributes.get("content") or "").strip() == token:
        return True
    r = get(c, f"{origin(url)}/.well-known/walkthru.txt")
    return r is not None and r.status_code == 200 and r.text.strip() == token


def check_headers(resp: httpx.Response) -> list[Finding]:
    h = {k.lower(): v for k, v in resp.headers.items()}
    https = resp.url.scheme == "https"
    out: list[Finding] = []
    if https and not _local_address(str(resp.url)) and "strict-transport-security" not in h:
        out.append(_f("high", "No HSTS header", "Browsers may still try plain http first, which allows downgrade attacks on public Wi-Fi.", "Send Strict-Transport-Security: max-age=63072000; includeSubDomains.", str(resp.url)))
    if "content-security-policy" not in h:
        out.append(_f("medium", "No Content-Security-Policy", "Without a CSP, any injected script runs with full access to the page.", "Start with default-src 'self' and add sources as needed; use report-only first.", str(resp.url)))
    if "x-content-type-options" not in h:
        out.append(_f("low", "No X-Content-Type-Options", "Browsers may sniff file types and run a text file as script.", "Send X-Content-Type-Options: nosniff.", str(resp.url)))
    if "x-frame-options" not in h and "frame-ancestors" not in h.get("content-security-policy", ""):
        out.append(_f("medium", "Page can be framed", "Another site can embed this page and trick users into clicking (clickjacking).", "Send X-Frame-Options: DENY or a CSP frame-ancestors directive.", str(resp.url)))
    if "referrer-policy" not in h:
        out.append(_f("low", "No Referrer-Policy", "Full URLs, including query strings, leak to every site you link to.", "Send Referrer-Policy: strict-origin-when-cross-origin.", str(resp.url)))
    server = h.get("server", "")
    if re.search(r"\d+\.\d+", server):
        out.append(_f("low", "Server header reveals a version", f'The Server header is "{server}". Version numbers make known exploits easy to target.', "Remove the version from the Server header.", server))
    for raw in resp.headers.get_list("set-cookie"):
        name = raw.split("=", 1)[0].strip()
        flags = raw.lower()
        missing = [f for f, present in (("Secure", "secure" in flags or not https), ("HttpOnly", "httponly" in flags), ("SameSite", "samesite" in flags)) if not present]
        if missing:
            out.append(_f("medium", f'Cookie "{name}" is missing {", ".join(missing)}', "Cookies without these flags can be read by scripts or sent over plain http.", "Set Secure, HttpOnly and SameSite=Lax (or Strict) on session cookies.", raw[:80]))
    return out


def check_transport(url: str, resp: httpx.Response, c: httpx.Client) -> list[Finding]:
    if resp.url.scheme != "https":
        if _local_address(str(resp.url)):
            return [_f("low", "Local development uses plain http", "This address is local or private, so HTTPS is not required for this development check.",
                       "Check HTTPS and redirects again on the deployed public domain.", str(resp.url))]
        return [_f("high", "Site is served over plain http", "Everything visitors type, including passwords, crosses the network unencrypted.", "Get a certificate (Let's Encrypt is free) and redirect http to https.", str(resp.url))]
    host = urlsplit(url).netloc
    if _local_address(url):
        return []
    plain = get(c, f"http://{host}/")
    if plain is not None and plain.url.scheme != "https":
        return [_f("medium", "http does not redirect to https", "Visitors who type the bare domain stay on the unencrypted version.", "Redirect all http requests to https with a 301.", f"http://{host}/")]
    return []


def check_content(html: str, page_url: str) -> list[Finding]:
    tree = HTMLParser(html)
    out: list[Finding] = []
    for form in tree.css("form"):
        action = form.attributes.get("action") or ""
        if action.startswith("http://"):
            if _local_address(action):
                out.append(_f("low", "Local form submits over plain http", "This form posts to a local or private address during development.",
                              "Use HTTPS when the form is deployed on a public domain.", action[:80]))
            else:
                out.append(_f("high", "Form submits over plain http", "Whatever the visitor types in this form is sent unencrypted.", "Point the form action at an https URL.", action[:80]))
    if page_url.startswith("https://"):
        mixed = [n.attributes.get("src") for n in tree.css("script[src], img[src], iframe[src], link[href]") if (n.attributes.get("src") or n.attributes.get("href") or "").startswith("http://")]
        if mixed:
            out.append(_f("medium", f"{len(mixed)} resources load over plain http", "Browsers block or warn about mixed content, and scripts over http can be tampered with.", "Load every asset over https.", ", ".join(m[:50] for m in mixed[:3] if m)))
    return out


def check_exposed(base: str, c: httpx.Client) -> list[Finding]:
    out = []
    for path, pattern in EXPOSED.items():
        r = get(c, base + path)
        if r is not None and r.status_code == 200 and pattern.search(r.text[:5000]):
            out.append(_f("high", f"{path} is publicly readable", "This file usually holds credentials or repository internals and should never be served.", "Block the path at the web server and rotate any secrets it contains.", base + path))
    return out


def check_bundles(html: str, page_url: str, c: httpx.Client) -> list[Finding]:
    tree = HTMLParser(html)
    base = origin(page_url)
    srcs = [urljoin(page_url, s.attributes.get("src") or "") for s in tree.css("script[src]")]
    out = []
    for src in [s for s in srcs if s.startswith(base)][:10]:
        r = get(c, src)
        if r is None or r.status_code != 200:
            continue
        for label, pattern in SECRETS:
            m = pattern.search(r.text)
            if m:
                out.append(_f("high", f"{label} in a JavaScript bundle", "Anyone can read this key from the page source and use it as you.", "Move the key server-side and rotate it now.", f"{src.split('/')[-1]}: {m.group(0)[:8]}…"))
                break
    return out


def scan(url: str, c: httpx.Client, verified: bool, resp: httpx.Response | None = None) -> list[Finding]:
    if resp is None:
        resp = get(c, url)
    if resp is None:
        return [_f("high", "Site did not respond", "The homepage could not be fetched.", "Check that the site is up and reachable.", url)]
    html, final = resp.text, str(resp.url)
    out = check_transport(url, resp, c) + check_headers(resp) + check_content(html, final)
    if verified:
        out += check_exposed(origin(final), c) + check_bundles(html, final, c)
    return out
