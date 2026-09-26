"""Passive security hygiene. Header quality, cookies, transport, mixed content, CORS, TLS and vulnerable libraries for
everyone; exposed files, secrets and source maps in JS bundles and subdomain takeover only on verified domains (SPEC
safety rule). Never sends payloads, never fuzzes. Rule sources for P1.2 are listed in apps/api/THIRD_PARTY.md."""

import hashlib
import hmac
import ipaddress
import os
import re
from urllib.parse import urljoin, urlsplit

import httpx
from selectolax.parser import HTMLParser

from app.agent.schema import Finding
from app.scans import csp, libraries, secrets
from app.scans.fetch import assert_public, get, is_local_site, origin

ENV = re.compile(r"^\s*[A-Z_][A-Z0-9_]*\s*=", re.MULTILINE)
SQL_DUMP = re.compile(rb"(CREATE TABLE|INSERT INTO|-- MySQL dump|PostgreSQL database dump|-- Dump of)", re.IGNORECASE)
# path -> (what proves the file is really there, what it usually holds). Bytes patterns look at raw bytes (archives),
# text patterns at the decoded start. A single-page app answers every path with its index.html, so a 200 alone
# proves nothing.
EXPOSED: dict[str, tuple[re.Pattern, str]] = {
    "/.env": (ENV, "credentials"),
    "/.env.local": (ENV, "credentials"),
    "/.env.production": (ENV, "production credentials"),
    "/.env.development": (ENV, "credentials"),
    "/.git/config": (re.compile(r"\[core\]"), "repository internals"),
    "/.git/HEAD": (re.compile(r"^ref: refs/", re.MULTILINE), "repository internals"),
    "/.git/index": (re.compile(rb"^DIRC"), "the list of every file in the repository"),
    "/.DS_Store": (re.compile(r"Bud1"), "a listing of the folder"),
    "/wp-config.php.bak": (re.compile(r"DB_PASSWORD"), "database credentials"),
    "/backup.zip": (re.compile(rb"^PK\x03\x04"), "a full backup"),
    "/backup.tar.gz": (re.compile(rb"^\x1f\x8b"), "a full backup"),
    "/backup.sql": (SQL_DUMP, "a database dump"),
    "/dump.sql": (SQL_DUMP, "a database dump"),
    "/database.sql": (SQL_DUMP, "a database dump"),
    "/db.sql": (SQL_DUMP, "a database dump"),
    "/server-status": (re.compile(r"Apache Server Status"), "live requests, client addresses and internal URLs"),
    "/phpinfo.php": (re.compile(r"phpinfo\(\)|PHP Version \d"), "server configuration and environment variables"),
    "/info.php": (re.compile(r"phpinfo\(\)|PHP Version \d"), "server configuration and environment variables"),
}
PEEK_BYTES = 8192
# Public CDNs serve versioned, unchanging files, so Subresource Integrity works there. Loader scripts from analytics,
# payments or chat vendors change without a new URL, so SRI cannot be used on them and they are not flagged.
SRI_HOSTS = ("cdn.jsdelivr.net", "unpkg.com", "cdnjs.cloudflare.com", "code.jquery.com", "ajax.googleapis.com",
             "stackpath.bootstrapcdn.com", "maxcdn.bootstrapcdn.com", "cdn.skypack.dev", "esm.sh", "ga.jspm.io")
CORS_ORIGIN = "https://cors-check.walkthru.invalid"  # never a real site: a reflected value proves the server echoes any origin
HSTS_MIN, PRELOAD_MIN = 15_552_000, 31_536_000  # 180 days (MDN Observatory's bar) and one year (the preload list's)


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


TXT_PREFIX = "walkthru-verification="


def txt_name(url: str) -> str:
    """Where the DNS proof lives: a TXT record on _walkthru.<host>, so it never collides with SPF or other TXT records."""
    return f"_walkthru.{(urlsplit(url).hostname or '').rstrip('.').lower()}"


def verify_domain(url: str, token: str, c: httpx.Client, html: str | None = None) -> bool:
    """True when the owner published the token one of three ways, the same proofs Search Console accepts:
    <meta name="walkthru-verification"> on the homepage, /.well-known/walkthru.txt, or a DNS TXT record
    `_walkthru.<host>` holding `walkthru-verification=<token>`. Checked again at every run start, never cached."""
    if html is None:
        r = get(c, url)
        html = r.text if r is not None else ""
    meta = HTMLParser(html).css_first('meta[name="walkthru-verification"]')
    if meta is not None and (meta.attributes.get("content") or "").strip() == token:
        return True
    r = get(c, f"{origin(url)}/.well-known/walkthru.txt")
    if r is not None and r.status_code == 200 and r.text.strip() == token:
        return True
    return txt_verified(url, token, c)


def txt_verified(url: str, token: str, c: httpx.Client) -> bool:
    from app.scans.tls import dns

    name = txt_name(url)
    if is_local_site(url) or name == "_walkthru.":
        return False  # IP addresses and local servers have no DNS to publish in
    try:
        _, records = dns(c, name, "TXT")
    except (httpx.HTTPError, ValueError, KeyError):
        return False
    # DNS-over-HTTPS returns TXT data quoted, and long records split into several quoted strings.
    return any("".join(part for part in r.split('"') if part.strip()).strip() == TXT_PREFIX + token for r in records)


def check_headers(resp: httpx.Response) -> list[Finding]:
    h = {k.lower(): v for k, v in resp.headers.items()}
    https = resp.url.scheme == "https"
    url = str(resp.url)
    meta_csp = [n.attributes.get("content") or "" for n in HTMLParser(resp.text).css('meta[http-equiv]')
                if (n.attributes.get("http-equiv") or "").lower() == "content-security-policy"] if "html" in h.get("content-type", "text/html") else []
    out: list[Finding] = []
    if https and not _local_address(url):
        out += _hsts(h.get("strict-transport-security"), url)
    if "content-security-policy" not in h and not meta_csp:
        if "content-security-policy-report-only" in h:
            out.append(_f("low", "Content-Security-Policy is report-only", "The policy only reports violations; injected scripts still run.", "Once the reports are clean, send the same policy as Content-Security-Policy.", url))
        else:
            out.append(_f("medium", "No Content-Security-Policy", "Without a CSP, any injected script runs with full access to the page.", "Start with default-src 'self' and add sources as needed; use report-only first.", url))
    else:
        out += csp.check(h, meta_csp, url)
    if "x-content-type-options" not in h:
        out.append(_f("low", "No X-Content-Type-Options", "Browsers may sniff file types and run a text file as script.", "Send X-Content-Type-Options: nosniff.", url))
    if "x-frame-options" not in h and "frame-ancestors" not in h.get("content-security-policy", ""):
        out.append(_f("medium", "Page can be framed", "Another site can embed this page and trick users into clicking (clickjacking).", "Send X-Frame-Options: DENY or a CSP frame-ancestors directive.", url))
    if "referrer-policy" not in h:
        out.append(_f("low", "No Referrer-Policy", "Full URLs, including query strings, leak to every site you link to.", "Send Referrer-Policy: strict-origin-when-cross-origin.", url))
    server = h.get("server", "")
    if re.search(r"\d+\.\d+", server):
        out.append(_f("low", "Server header reveals a version", f'The Server header is "{server}". Version numbers make known exploits easy to target.', "Remove the version from the Server header.", server))
    for raw in resp.headers.get_list("set-cookie"):
        out += _cookie(raw, https)
    return out


def _hsts(value: str | None, url: str) -> list[Finding]:
    if value is None:
        return [_f("high", "No HSTS header", "Browsers may still try plain http first, which allows downgrade attacks on public Wi-Fi.", "Send Strict-Transport-Security: max-age=63072000; includeSubDomains.", url)]
    parts = {p.strip().split("=", 1)[0].lower(): (p.split("=", 1)[1].strip().strip('"') if "=" in p else "") for p in value.split(";") if p.strip()}
    age = parts.get("max-age", "")
    if not age.isdigit():
        return [_f("medium", "HSTS header is invalid", f'Strict-Transport-Security "{value[:80]}" has no valid max-age, so browsers ignore it.', "Send Strict-Transport-Security: max-age=63072000; includeSubDomains.", url)]
    if int(age) == 0:
        return [_f("high", "HSTS is switched off", "max-age=0 tells browsers to forget the https-only rule for this site.", "Send Strict-Transport-Security: max-age=63072000; includeSubDomains.", url)]
    out = []
    if int(age) < HSTS_MIN:
        out.append(_f("medium", "HSTS max-age is too short", f"max-age is {int(age) // 86400} days. Visitors who return after it runs out can be downgraded to plain http again.", "Raise max-age to at least 15552000 (180 days); 63072000 (two years) is common.", f"{url}: {value[:80]}"))
    if "preload" in parts and (int(age) < PRELOAD_MIN or "includesubdomains" not in parts):
        out.append(_f("low", "HSTS preload requirements not met", "The header asks for preloading, but the preload list needs max-age of at least one year and includeSubDomains, so the request is refused.", "Send max-age=63072000; includeSubDomains; preload, or drop preload.", f"{url}: {value[:80]}"))
    return out


def _cookie(raw: str, https: bool) -> list[Finding]:
    name = raw.split("=", 1)[0].strip()
    attrs = {a.strip().split("=", 1)[0].lower(): (a.split("=", 1)[1].strip() if "=" in a else "") for a in raw.split(";")[1:]}
    out = []
    missing = [f for f, present in (("Secure", "secure" in attrs or not https), ("HttpOnly", "httponly" in attrs), ("SameSite", "samesite" in attrs)) if not present]
    if missing:
        out.append(_f("medium", f'Cookie "{name}" is missing {", ".join(missing)}', "Cookies without these flags can be read by scripts or sent over plain http.", "Set Secure, HttpOnly and SameSite=Lax (or Strict) on session cookies.", raw[:80]))
    # Cookie prefixes are enforced by browsers: a __Host- or __Secure- cookie that breaks the rules is silently dropped.
    broken = []
    if name.startswith(("__Host-", "__Secure-")) and "secure" not in attrs:
        broken.append("Secure")
    if name.startswith("__Host-") and ("domain" in attrs or attrs.get("path", "") != "/"):
        broken.append("Path=/ and no Domain")
    if broken:
        prefix = "__Host-" if name.startswith("__Host-") else "__Secure-"
        out.append(_f("medium", f'Cookie "{name}" breaks its {prefix} prefix rules', f"Browsers refuse to store a {prefix} cookie without {' and '.join(broken)}, so this cookie never reaches visitors and whatever depends on it fails.",
                      f"Set it with {'Secure; Path=/ and no Domain' if prefix == '__Host-' else 'Secure'}.", raw[:80]))
    return out


def check_cors(url: str, c: httpx.Client) -> list[Finding]:
    """One ordinary GET with an Origin header, as MDN Observatory does. Only the answer's headers are read."""
    r = get(c, url, headers={"Origin": CORS_ORIGIN})
    if r is None:
        return []
    allow = r.headers.get("access-control-allow-origin", "").strip()
    credentials = r.headers.get("access-control-allow-credentials", "").strip().lower() == "true"
    if allow == CORS_ORIGIN:
        if credentials:
            return [_f("high", "CORS trusts any website with visitors' cookies", "The server copies any Origin into Access-Control-Allow-Origin and allows credentials, so any website a signed-in visitor opens can read their data from this site.",
                       "Answer only origins on an allowlist, and never reflect the request's Origin with Access-Control-Allow-Credentials: true.", f"{url}: Origin {CORS_ORIGIN} allowed with credentials")]
        return [_f("low", "CORS allows any origin", "The server copies any Origin into Access-Control-Allow-Origin, so any website can read these responses (without cookies).",
                   "Answer only the origins that need access; use * only for truly public data.", f"{url}: Origin {CORS_ORIGIN} allowed")]
    if allow == "*" and credentials:
        return [_f("medium", "CORS combines * with credentials", "Access-Control-Allow-Origin: * with Access-Control-Allow-Credentials: true is refused by browsers, and usually means someone tried to open the API to every site.",
                   "Pick explicit allowed origins, or drop credentials for public data.", f"{url}: Access-Control-Allow-Origin: *")]
    return []


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
    scripts = [(urljoin(page_url, n.attributes.get("src") or ""), n) for n in tree.css("script[src]")]
    unchecked = [src for src, n in scripts if (urlsplit(src).hostname or "").lower() in SRI_HOSTS and not n.attributes.get("integrity")]
    if unchecked:
        out.append(_f("low", "Library from a public CDN loads without an integrity check", "If the CDN or the package is compromised, the changed file runs on your pages unnoticed. An integrity hash makes the browser refuse a changed file.",
                      'Add integrity="sha384-..." and crossorigin="anonymous" to the script tag (srihash.org computes the hash), or host the file yourself.', ", ".join(u[:80] for u in unchecked[:3])))
    out += libraries.check_scripts([src for src, _ in scripts])
    return out


def _peek(c: httpx.Client, url: str) -> tuple[int, bytes] | None:
    """Status and the first bytes of one URL, without following redirects or downloading a large file."""
    try:
        assert_public(url)
        with c.stream("GET", url) as r:
            data = b""
            for chunk in r.iter_bytes():
                data += chunk
                if len(data) >= PEEK_BYTES:
                    break
            return r.status_code, data[:PEEK_BYTES]
    except (httpx.HTTPError, ValueError):
        return None


def check_exposed(base: str, c: httpx.Client) -> list[Finding]:
    out = []
    for path, (pattern, holds) in EXPOSED.items():
        got = _peek(c, base + path)
        if got is None or got[0] != 200:
            continue
        body = got[1] if isinstance(pattern.pattern, bytes) else got[1].decode("utf-8", "replace")
        if pattern.search(body):
            out.append(_f("high", f"{path} is publicly readable", f"This file usually holds {holds} and should never be served.", "Block the path at the web server, delete the file from the web root, and rotate any secrets it contains.", base + path))
    return out


def check_bundles(html: str, page_url: str, c: httpx.Client) -> list[Finding]:
    """Same-origin scripts of the page (verified domains only): secrets, library banners and public source maps."""
    tree = HTMLParser(html)
    base = origin(page_url)
    srcs = [urljoin(page_url, s.attributes.get("src") or "") for s in tree.css("script[src]")]
    out: list[Finding] = []
    maps: list[str] = []
    for src in list(dict.fromkeys(s for s in srcs if s.startswith(base)))[:10]:
        r = get(c, src)
        if r is None or r.status_code != 200:
            continue
        name = src.split("/")[-1] or src
        for rule_id, secret in secrets.find(r.text):
            label = secrets.label(rule_id, secret)
            if rule_id in secrets.PUBLIC_BY_DESIGN:
                out.append(_f("low", f"{label} in a JavaScript bundle", "Browser keys like this are public by design, so anyone can copy it. That is fine only if the key is restricted.",
                              "Restrict the key to your domains (HTTP referrers) and to the APIs the page needs, in the provider's console.", f"{name}: {secrets.mask(secret)}"))
            else:
                out.append(_f("high", f"{label} in a JavaScript bundle", "Anyone can read this key from the page source and use it as you.", "Move the key server-side and rotate it now.", f"{name}: {secrets.mask(secret)}"))
        out += libraries.check_content(r.text, src)
        if (found := _source_map(src, r, c)):
            maps.append(found)
    if maps:
        out.append(_f("medium", "Source maps are publicly readable", f"{len(maps)} script{'s' if len(maps) > 1 else ''} point to a source map anyone can download. It rebuilds your original source code, comments and file layout, which makes finding bugs to attack much easier.",
                      "Stop uploading .map files to production (for Vite: build.sourcemap false or 'hidden'), or upload them only to your error tracker.", ", ".join(maps[:3])))
    return out


def _source_map(src: str, r: httpx.Response, c: httpx.Client) -> str | None:
    """The source map URL when the bundle names one and it really serves a map (or embeds one inline)."""
    named = r.headers.get("sourcemap") or r.headers.get("x-sourcemap")
    if not named:
        m = re.search(r"[#@]\s*sourceMappingURL=(\S+)", r.text[-2000:])
        named = m.group(1) if m else None
    if not named:
        return None
    if named.startswith("data:"):
        return f"{src} (inline)"
    map_url = urljoin(src, named)
    if origin(map_url) != origin(src):
        return None
    got = _peek(c, map_url)
    if got and got[0] == 200 and got[1].lstrip()[:1] == b"{" and (b'"mappings"' in got[1] or b'"sources"' in got[1]):
        return map_url
    return None


def scan(url: str, c: httpx.Client, verified: bool, resp: httpx.Response | None = None) -> list[Finding]:
    if resp is None:
        resp = get(c, url)
    if resp is None:
        return [_f("high", "Site did not respond", "The homepage could not be fetched.", "Check that the site is up and reachable.", url)]
    html, final = resp.text, str(resp.url)
    out = check_transport(url, resp, c) + check_headers(resp) + check_content(html, final) + check_cors(final, c)
    if verified:
        out += check_exposed(origin(final), c) + check_bundles(html, final, c)
    return out
