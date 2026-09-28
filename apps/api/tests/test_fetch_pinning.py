"""SD-4.5: a scan connects only to the address it checked. DNS rebinding (public on the check, private on the connect)
and IPv6 forms that hide a private IPv4 address must never reach this machine or the cloud metadata service."""

import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app.scans import fetch, tls


@pytest.mark.parametrize("address", ["127.0.0.1", "10.0.0.5", "192.168.1.1", "169.254.169.254", "169.254.170.2", "100.100.100.200",
                                     "0.0.0.0", "::1", "fd00:ec2::254", "fe80::1%eth0", "::ffff:127.0.0.1", "::ffff:169.254.169.254",
                                     "64:ff9b::7f00:1", "2002:7f00:1::1", "224.0.0.1", "ff02::1", "203.0.113.9"])
def test_private_and_disguised_addresses_are_refused(address):
    assert not fetch.is_public_ip(address)


@pytest.mark.parametrize("address", ["8.8.8.8", "93.184.216.34", "2606:4700:4700::1111", "::ffff:8.8.8.8", "64:ff9b::808:808"])
def test_public_addresses_pass(address):
    assert fetch.is_public_ip(address)


@pytest.fixture
def local_server(monkeypatch):
    """A server on this machine that records every request, standing in for an internal service."""
    monkeypatch.delenv("ALLOW_LOCAL_SCANS", raising=False)
    seen: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            seen.append(self.headers.get("Host", ""))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"internal")

        def log_message(self, *a):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server.server_address[1], seen
    server.shutdown()


def resolver(monkeypatch, answers: list[str]):
    """A DNS server that gives each answer in turn (the last one repeats), counting lookups."""
    calls: list[str] = []

    def getaddrinfo(host, port, *a, **k):
        calls.append(host)
        address = answers[min(len(calls), len(answers)) - 1]
        family = socket.AF_INET6 if ":" in address else socket.AF_INET
        return [(family, socket.SOCK_STREAM, 6, "", (address, port))]

    monkeypatch.setattr(fetch.socket, "getaddrinfo", getaddrinfo)
    return calls


def test_dns_rebinding_to_this_machine_is_refused(monkeypatch, local_server):
    port, seen = local_server
    resolver(monkeypatch, ["93.184.216.34", "127.0.0.1"])  # public for the check, then this machine for the connection
    with fetch.client(timeout=3) as c:
        assert fetch.get(c, f"http://rebind.test:{port}/") is None
    assert seen == []  # the internal service never saw a request


def test_the_connection_goes_to_the_checked_address_with_the_real_host_name(monkeypatch, local_server):
    port, seen = local_server
    calls = resolver(monkeypatch, ["127.0.0.1"])
    monkeypatch.setattr(fetch, "is_public_ip", lambda address: address == "127.0.0.1")  # pretend it is public
    with fetch.client(timeout=3) as c:
        response = c.get(f"http://pinned.test:{port}/")
    assert response.text == "internal" and seen == [f"pinned.test:{port}"]
    # The name is resolved once, by the guard. The socket then only parses the checked address it was given (no DNS).
    assert calls == ["pinned.test", "127.0.0.1"]


def test_an_unreachable_first_address_falls_back_to_the_next(monkeypatch, local_server):
    port, _ = local_server
    monkeypatch.setattr(fetch, "is_public_ip", lambda address: True)

    def getaddrinfo(host, p, *a, **k):  # an IPv6 answer first, as on a machine without IPv6, then IPv4
        return [(socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("::1", p, 0, 0)), (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", p))]

    monkeypatch.setattr(fetch.socket, "getaddrinfo", getaddrinfo)
    with fetch.client(timeout=3) as c:
        assert c.get(f"http://dual.test:{port}/").status_code == 200


def test_every_request_of_a_scan_client_is_guarded_even_without_fetch_get(monkeypatch, local_server):
    port, seen = local_server
    resolver(monkeypatch, ["169.254.169.254"])
    with fetch.client(timeout=3) as c, pytest.raises(fetch.httpx.ConnectError, match="private address"):
        c.get(f"http://metadata.test:{port}/latest/meta-data")  # a scanner calling c.get directly is covered too
    assert seen == []


def test_tls_handshake_uses_the_same_rule(monkeypatch):
    monkeypatch.delenv("ALLOW_LOCAL_SCANS", raising=False)
    resolver(monkeypatch, ["::ffff:10.0.0.1"])
    assert tls.check("https://sneaky.test/") == []  # refused before any handshake
    with pytest.raises(ValueError):
        tls._address("sneaky.test", 443)
