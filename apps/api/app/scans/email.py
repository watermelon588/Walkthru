"""Signup email check: can this domain's signup, verification and reset emails reach an inbox?

Reads DNS over HTTPS from one fixed resolver with the existing httpx client (no new dependency). Passive:
three DNS lookups, nothing is sent. DKIM is not checked because selectors cannot be listed.
"""

import ipaddress
from urllib.parse import urlsplit

import httpx

from app.agent.schema import Finding

RESOLVER = "https://cloudflare-dns.com/dns-query"
# Sites on these hosts do not own the domain's email records, so judging them would only blame the host.
SHARED_HOSTS = ("vercel.app", "netlify.app", "github.io", "pages.dev", "onrender.com", "herokuapp.com", "fly.dev",
                "web.app", "firebaseapp.com", "lovable.app", "bolt.new", "replit.app", "surge.sh", "glitch.me", "azurewebsites.net")


def _f(severity: str, title: str, detail: str, fix: str, evidence: str) -> Finding:
    return Finding(kind="security", severity=severity, title=title, detail=detail, fix=fix, evidence=evidence)


def _records(c: httpx.Client, name: str, kind: str) -> list[str]:
    r = c.get(RESOLVER, params={"name": name, "type": kind}, headers={"accept": "application/dns-json"}, timeout=5)
    r.raise_for_status()
    wanted = {"TXT": 16, "MX": 15}[kind]
    return [a["data"].strip('"').replace('" "', "") for a in r.json().get("Answer", []) if a.get("type") == wanted]


def domain_of(url: str) -> str | None:
    """The domain to check, or None when the site does not own its email DNS (local, IP, shared hosting)."""
    host = (urlsplit(url).hostname or "").lower().removeprefix("www.")
    if not host or host == "localhost" or host.endswith((".localhost", *(f".{h}" for h in SHARED_HOSTS))):
        return None
    try:
        ipaddress.ip_address(host)
        return None
    except ValueError:
        return host


def check(url: str, c: httpx.Client, *, full: bool) -> tuple[list[Finding], str | None]:
    """(findings, note). `full` (paid plans) adds the MX check. The note says why nothing was checked, if so."""
    domain = domain_of(url)
    if not domain:
        return [], "Signup email records not checked: the site runs on a local address or a shared hosting domain it does not own."
    try:
        txt = _records(c, domain, "TXT")
        dmarc = [r for r in _records(c, f"_dmarc.{domain}", "TXT") if r.lower().startswith("v=dmarc1")]
        mx = _records(c, domain, "MX") if full else None
    except (httpx.HTTPError, ValueError, KeyError):
        return [], "Signup email records could not be read (DNS lookup failed)."

    findings = []
    if not any(r.lower().startswith("v=spf1") for r in txt):
        findings.append(_f("medium", "No SPF record",
                           f"{domain} does not say which servers may send its email, so signup, verification and password-reset emails are more likely to land in spam or be rejected.",
                           "Add one TXT record to the domain listing your email provider, for example v=spf1 include:_spf.google.com ~all (use your provider's value).",
                           f"TXT {domain}"))
    if not dmarc:
        findings.append(_f("medium", "No DMARC policy",
                           f"{domain} has no DMARC record. Mailbox providers trust its email less, and anyone can send email pretending to be {domain}.",
                           "Add a TXT record at _dmarc with v=DMARC1; p=none; rua=mailto:you@yourdomain, then move to p=quarantine once reports look clean.",
                           f"TXT _dmarc.{domain}"))
    elif "p=none" in dmarc[0].lower().replace(" ", ""):
        findings.append(_f("low", "DMARC policy only monitors (p=none)",
                           f"{domain} publishes DMARC but tells mailbox providers to take no action on email that fails it.",
                           "Once DMARC reports show only your own senders, change the policy to p=quarantine.",
                           f"TXT _dmarc.{domain}: {dmarc[0][:120]}"))
    if mx is not None and not mx:
        findings.append(_f("low", "Domain has no MX record",
                           f"{domain} cannot receive email, so replies to your signup and support emails bounce.",
                           "Add MX records for your email provider, or send from an address on a domain that receives mail.",
                           f"MX {domain}"))
    return findings, None
