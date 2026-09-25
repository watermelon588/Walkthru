"""Dangling DNS and subdomain takeover, for subdomains the crawl found (verified domains only, P1.2).

Fingerprints come from can-i-take-over-xyz (CC-BY-4.0, attribution in apps/api/THIRD_PARTY.md), kept to services it
marks vulnerable. Per subdomain: one CNAME lookup over DNS-over-HTTPS, then either an NXDOMAIN lookup of the target or
one GET of the subdomain's homepage to look for the service's "no such site" page. Nothing is claimed or registered.
"""

import json
import os
import re
from functools import lru_cache
from urllib.parse import urljoin, urlsplit

import httpx
from selectolax.parser import HTMLParser

from app.agent.schema import Finding
from app.scans import fetch
from app.scans.tls import dns

DATA = os.path.join(os.path.dirname(__file__), "data", "takeover.json")
MAX_HOSTS = 10


@lru_cache(maxsize=1)
def _services() -> list[dict]:
    with open(DATA, encoding="utf-8") as f:
        return json.load(f)


def subdomains(pages: list[tuple[str, str]], root_url: str) -> list[str]:
    """Hosts under the verified host that the audited pages link to or load from (www. counts as the same site)."""
    root = (urlsplit(root_url).hostname or "").lower()
    apex = root.removeprefix("www.")
    found: dict[str, None] = {}
    for page_url, html in pages:
        for node in HTMLParser(html).css("a[href], script[src], img[src], link[href], iframe[src], form[action]"):
            raw = node.attributes.get("href") or node.attributes.get("src") or node.attributes.get("action") or ""
            host = (urlsplit(urljoin(page_url, raw)).hostname or "").lower()
            if host.endswith("." + apex) and host not in (root, "www." + apex):
                found.setdefault(host)
    return list(found)[:MAX_HOSTS]


def _service(target: str) -> dict | None:
    target = target.rstrip(".").lower()
    return next((s for s in _services() if any(target == c.lower() or target.endswith("." + c.lower().lstrip(".")) for c in s["cname"])), None)


def check(pages: list[tuple[str, str]], root_url: str, c: httpx.Client) -> list[Finding]:
    out = []
    for host in subdomains(pages, root_url):
        try:
            _, cnames = dns(c, host, "CNAME")
            if not cnames:
                continue
            target = cnames[-1].rstrip(".")
            service = _service(target)
            gone = dns(c, target, "A")[0] == 3  # NXDOMAIN: the name the subdomain points at does not exist
        except (httpx.HTTPError, ValueError, KeyError):
            continue
        if service and service["nxdomain"] and gone:
            out.append(_takeover(host, target, service))
        elif service and not service["nxdomain"]:
            page = fetch.get(c, f"https://{host}/", timeout=5) or fetch.get(c, f"http://{host}/", timeout=5)
            if page is not None and re.search(service["fingerprint"], page.text[:50_000]):
                out.append(_takeover(host, target, service))
        elif gone:
            out.append(Finding(kind="security", severity="medium", title=f"Subdomain {host} points at a name that does not exist",
                               detail=f"{host} is a CNAME to {target}, which no longer exists. If someone can register that name, they control what {host} serves.",
                               fix=f"Delete the CNAME record for {host}, or point it at a live resource you own.", evidence=f"{host} CNAME {target} (NXDOMAIN)"))
    return out


def _takeover(host: str, target: str, service: dict) -> Finding:
    return Finding(kind="security", severity="high", title=f"Subdomain {host} can be taken over",
                   detail=f"{host} points at {service['service']} ({target}), but the resource there is gone. Anyone who creates it again on {service['service']} can serve their own pages, and steal cookies scoped to your domain, on {host}.",
                   fix=f"Delete the DNS record for {host} now, or recreate the resource on {service['service']} under your account.", evidence=f"{host} CNAME {target}")
