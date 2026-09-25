"""TLS certificate and protocol, and CAA records (P1.2). Python's `ssl` module only: sslyze is AGPL-3.0.

One normal handshake reads the certificate and the negotiated version, like any browser. A second handshake offering
only TLS 1.0 and 1.1 tells whether the server still accepts them. CAA is read over DNS-over-HTTPS with the scan's
httpx client. Local and IP-only sites are skipped: they have no public certificate or DNS to judge.
"""

import ipaddress
import os
import socket
import ssl
import time
import warnings
from urllib.parse import urlsplit

import httpx

from app.agent.schema import Finding
from app.scans.email import RESOLVER, domain_of
from app.scans.fetch import is_local_site

EXPIRY_DAYS = 21
TIMEOUT = 4.0


def _f(severity: str, title: str, detail: str, fix: str, evidence: str) -> Finding:
    return Finding(kind="security", severity=severity, title=title, detail=detail, fix=fix, evidence=evidence)


def _address(host: str, port: int) -> str:
    """Resolve once and connect to that address, so a public name cannot point the handshake at a private one."""
    address = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)[0][4][0]
    if host == "localhost" and os.environ.get("ALLOW_LOCAL_SCANS") == "1":
        # Windows resolves localhost to ::1 first; the local fixture listens on IPv4.
        address = "127.0.0.1"
    if os.environ.get("ALLOW_LOCAL_SCANS") != "1" and not ipaddress.ip_address(address).is_global:
        raise ValueError("site resolves to a private address")
    return address


def _handshake(host: str, address: str, port: int, context: ssl.SSLContext) -> tuple[dict, str | None]:
    with socket.create_connection((address, port), timeout=TIMEOUT) as sock, context.wrap_socket(sock, server_hostname=host) as tls:
        return tls.getpeercert() or {}, tls.version()


def check(url: str, *, context: ssl.SSLContext | None = None, now: float | None = None) -> list[Finding]:
    parts = urlsplit(url)
    host, port = parts.hostname or "", parts.port or 443
    if parts.scheme != "https" or not host or (is_local_site(url) and os.environ.get("ALLOW_LOCAL_SCANS") != "1"):
        return []
    try:
        address = _address(host, port)
    except (OSError, ValueError):
        return []
    try:
        cert, version = _handshake(host, address, port, context or ssl.create_default_context())
    except ssl.SSLCertVerificationError as e:
        reason = e.verify_message or "the certificate could not be verified"
        title = "TLS certificate has expired" if "expired" in reason else "TLS certificate is not trusted"
        return [_f("high", title, f"Browsers show a full-page security warning instead of the site ({reason}). Most visitors leave.",
                   "Renew or reissue the certificate for this exact host name (Let's Encrypt is free), and install the full chain.", f"{host}: {reason}")]
    except (OSError, ssl.SSLError):
        return []
    out = []
    if cert.get("notAfter"):
        days = int((ssl.cert_time_to_seconds(cert["notAfter"]) - (now or time.time())) // 86400)
        if days < EXPIRY_DAYS:
            out.append(_f("high" if days < 7 else "medium", f"TLS certificate expires in {days} day{'s' if days != 1 else ''}",
                          "When it expires, browsers block the site with a security warning.",
                          "Renew it now and turn on automatic renewal (certbot, your host's managed certificates).", f"{host}: valid until {cert['notAfter']}"))
    if version in ("SSLv3", "TLSv1", "TLSv1.1"):
        out.append(_f("high", "Server negotiates TLS older than 1.2", f"The best this server offers is {version}, which browsers no longer accept.",
                      "Enable TLS 1.2 and 1.3 on the server or load balancer.", f"{host}: {version}"))
    elif _accepts_legacy(host, address, port):
        out.append(_f("medium", "Server still accepts TLS 1.0 or 1.1", "Old protocol versions have known weaknesses and are rejected by current browsers and PCI DSS.",
                      "Allow only TLS 1.2 and 1.3 (for nginx: ssl_protocols TLSv1.2 TLSv1.3).", f"{host}: accepted a TLS 1.1 handshake"))
    return out


def _accepts_legacy(host: str, address: str, port: int) -> bool:
    """A handshake that offers only TLS 1.0 and 1.1. False when this machine's OpenSSL cannot offer them at all."""
    try:
        legacy = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        legacy.check_hostname = False
        legacy.verify_mode = ssl.CERT_NONE
        with warnings.catch_warnings():  # the old versions are deprecated for use; offering them is the point here
            warnings.simplefilter("ignore", DeprecationWarning)
            legacy.minimum_version = ssl.TLSVersion.TLSv1
            legacy.maximum_version = ssl.TLSVersion.TLSv1_1
        legacy.set_ciphers("DEFAULT:@SECLEVEL=0")
        _, version = _handshake(host, address, port, legacy)
        return version in ("TLSv1", "TLSv1.1")
    except (OSError, ssl.SSLError, ValueError):
        return False


def dns(c: httpx.Client, name: str, rtype: str) -> tuple[int, list[str]]:
    """(DNS status, answer data) over DNS-over-HTTPS. Status 3 is NXDOMAIN."""
    code = {"CAA": 257, "CNAME": 5, "A": 1}[rtype]
    r = c.get(RESOLVER, params={"name": name, "type": rtype}, headers={"accept": "application/dns-json"}, timeout=3)
    r.raise_for_status()
    body = r.json()
    return int(body.get("Status", 2)), [a["data"] for a in body.get("Answer", []) if a.get("type") == code]


def check_caa(url: str, c: httpx.Client) -> list[Finding]:
    """No CAA record on the host or any parent: any certificate authority may issue certificates for the domain."""
    domain = domain_of(url)
    if not domain:
        return []
    labels = domain.split(".")
    try:
        for i in range(len(labels) - 1):  # the host, then each parent, as CAs do (RFC 8659); never the bare TLD
            if dns(c, ".".join(labels[i:]), "CAA")[1]:
                return []
    except (httpx.HTTPError, ValueError, KeyError):
        return []
    return [_f("low", "No CAA record", f"{domain} does not name which certificate authorities may issue certificates for it, so a mistake or attack at any authority can produce a valid certificate.",
               'Add a CAA record for the authority you use, for example: 0 issue "letsencrypt.org".', f"CAA {domain}")]
