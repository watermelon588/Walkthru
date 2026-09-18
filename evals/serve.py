"""Serve the fixture sites with per-site response headers.

    python evals/serve.py        # easy on :8101, hard on :8102

`easy` gets sane security headers; `hard` gets none plus a leaky Server header and
an insecure cookie. Static http.server cannot set headers, hence this file.
"""

import io
import os
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")

HEADERS = {
    "easy": {
        "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Set-Cookie": "session=abc; Path=/; Secure; HttpOnly; SameSite=Lax",
    },
    "hard": {
        "Server": "Apache/2.2.3 (CentOS)",  # X6 version leak
        "Set-Cookie": "session=abc; Path=/",  # X2 no Secure / HttpOnly
    },
}
# X3: exposed files. Stored under exposed/ because git ignores .env and cannot track a nested .git.
EXPOSED = {"/.env": "/exposed/env", "/.git/config": "/exposed/git-config"}


class Handler(SimpleHTTPRequestHandler):
    site = "easy"

    def version_string(self):  # the stdlib emits its own Server header; replace it rather than duplicate it
        return HEADERS[self.site].get("Server") or "fixture"

    def end_headers(self):
        for k, v in HEADERS[self.site].items():
            if k != "Server":
                self.send_header(k, v)
        super().end_headers()

    def send_head(self):
        if self.path in EXPOSED:
            if self.site == "easy":
                self.send_error(404)
                return None
            self.path = EXPOSED[self.path]
        if self.site == "hard" and self.path == "/app.js":
            return self._send_bundle()
        return super().send_head()

    def _send_bundle(self):
        # X4: fake secrets assembled here so the literal patterns never sit in git.
        with open(os.path.join(ROOT, "hard", "app.js"), encoding="utf-8") as f:
            body = f.read()
        body = body.replace("__STRIPE_LIVE_KEY__", "sk_" + "live_" + "51FAKE" + "FAKE" * 8 + "00")
        body = body.replace("__AWS_ACCESS_KEY__", "AKIA" + "FAKE" * 4)
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/javascript")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        return io.BytesIO(data)

    def log_message(self, *a):  # quiet
        pass


def make_server(site: str, port: int) -> ThreadingHTTPServer:
    handler = type(f"{site.title()}Handler", (Handler,), {"site": site})
    return ThreadingHTTPServer(("127.0.0.1", port), partial(handler, directory=os.path.join(ROOT, site)))


def start(site: str, port: int) -> ThreadingHTTPServer:
    srv = make_server(site, port)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


if __name__ == "__main__":
    start("easy", 8101)
    start("hard", 8102)
    print("easy http://127.0.0.1:8101  hard http://127.0.0.1:8102  (Ctrl+C to stop)")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        sys.exit(0)
