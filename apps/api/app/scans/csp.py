"""Content-Security-Policy quality: which directive is weak, not only whether the header exists (P1.2).

The checks follow Google's csp-evaluator (Apache-2.0; notice in apps/api/THIRD_PARTY.md): unsafe-inline without a
nonce or hash, unsafe-eval, wildcard and plain-scheme sources for scripts and objects, no object-src, no base-uri on
nonce-based policies, and no script restriction at all. Severities are capped at medium because no CSP at all is
reported as medium: a weak policy is never worse than none.
"""

import re

from app.agent.schema import Finding

SCRIPT, OBJECT, DEFAULT, BASE = "script-src", "object-src", "default-src", "base-uri"
NONCE_OR_HASH = re.compile(r"^'(nonce-|sha(256|384|512)-)", re.IGNORECASE)
PLAIN_SCHEMES = {"http:", "https:", "data:", "blob:", "filesystem:"}


def parse(policy: str) -> dict[str, list[str]]:
    """One policy: directive name -> source list. The first occurrence of a directive wins, as in browsers."""
    directives: dict[str, list[str]] = {}
    for part in policy.split(";"):
        tokens = part.strip().split()
        if tokens:
            directives.setdefault(tokens[0].lower(), [t.lower() if t.startswith("'") else t for t in tokens[1:]])
    return directives


def policies(headers: dict[str, str], meta: list[str]) -> list[dict[str, list[str]]]:
    """Every enforced policy: the header may hold several (comma-separated) and <meta> tags add more."""
    raw = [p for p in headers.get("content-security-policy", "").split(",") if p.strip()] + [m for m in meta if m.strip()]
    return [parse(p) for p in raw]


def _effective(d: dict[str, list[str]], name: str) -> list[str] | None:
    return d.get(name, d.get(DEFAULT))


def _weaknesses(d: dict[str, list[str]]) -> dict[str, tuple[str, str, str, str]]:
    """title -> (severity, detail, fix, evidence) for one policy."""
    out: dict[str, tuple[str, str, str, str]] = {}
    scripts = _effective(d, SCRIPT)
    if scripts is None:
        out["CSP does not restrict scripts"] = (
            "medium", "The policy has neither script-src nor default-src, so an injected script runs as if there were no CSP.",
            "Add script-src 'self' (plus the hosts you load scripts from), or default-src 'self'.", "no script-src or default-src")
        scripts = []
    trusted = any(NONCE_OR_HASH.match(s) for s in scripts) or "'strict-dynamic'" in scripts
    if "'unsafe-inline'" in scripts and not trusted:
        out["CSP allows inline scripts"] = (
            "medium", "script-src includes 'unsafe-inline', so an injected <script> tag or onclick handler still runs. This removes most of the protection a CSP gives.",
            "Move inline scripts into files, or give each one a nonce or hash, then drop 'unsafe-inline'. Roll it out with Content-Security-Policy-Report-Only first.",
            "script-src 'unsafe-inline'")
    if "'unsafe-eval'" in scripts:
        out["CSP allows eval"] = (
            "low", "script-src includes 'unsafe-eval', so strings can be run as code (eval, new Function), which turns some injection bugs into script execution.",
            "Remove 'unsafe-eval'. If a library needs it, look for a CSP-compatible build of that library.", "script-src 'unsafe-eval'")
    for name, label in ((SCRIPT, "scripts"), (OBJECT, "plugins")):
        sources = _effective(d, name) or []
        broad = [s for s in sources if s == "*" or s.lower() in PLAIN_SCHEMES]
        if broad and not (name == SCRIPT and trusted and "'strict-dynamic'" in sources):
            out[f"CSP allows {label} from any site"] = (
                "medium", f"{name} allows {', '.join(broad)}, so {label} can be loaded from any website, including one an attacker controls.",
                f"List the exact hosts you load {label} from instead of {' or '.join(broad)}." + (" For plugins, object-src 'none' is best." if name == OBJECT else ""),
                f"{name} {' '.join(broad)}")
    if _effective(d, OBJECT) is None:
        out["CSP has no object-src"] = (
            "low", "Without object-src (or default-src), plugin content such as <object> and <embed> is not restricted.",
            "Add object-src 'none'.", "no object-src or default-src")
    if trusted and BASE not in d:
        out["CSP has no base-uri"] = (
            "low", "The policy trusts scripts by nonce or hash, but an injected <base> tag could redirect relative script URLs to another site.",
            "Add base-uri 'none' (or 'self').", "no base-uri")
    return out


def check(headers: dict[str, str], meta: list[str], page_url: str) -> list[Finding]:
    """Weaknesses shared by every enforced policy. Several policies all apply, so the strictest one decides."""
    found = [_weaknesses(p) for p in policies(headers, meta)]
    if not found:
        return []
    common = set(found[0]).intersection(*found[1:])
    return [Finding(kind="security", severity=found[0][t][0], title=t, detail=found[0][t][1], fix=found[0][t][2], evidence=f"{page_url}: {found[0][t][3]}")
            for t in found[0] if t in common]
