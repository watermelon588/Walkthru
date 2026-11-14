import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'apps/api'))
from app.runner.cdp import browser

HTML = b'''<!doctype html><html><head><title>H4b local fixture</title></head><body>
<a href="#projects">Explore projects</a><div style="height:1800px"></div>
<section id="projects" style="height:350px;background:#eee"><h2>Selected projects</h2><button>Open project</button></section>
</body></html>'''
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.send_header('Content-Type', 'text/html'); self.end_headers(); self.wfile.write(HTML)
    def log_message(self, *args):
        pass

server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
checks = []
try:
    with browser() as tab:
        tab.send('Page.navigate', url=f'http://127.0.0.1:{server.server_port}/')
        tab.wait_loaded()
        before = tab.message({'type': 'snapshot'})
        again = tab.message({'type': 'snapshot'})
        assert before['document_id'] == again['document_id'] and before['revision'] != again['revision']
        checks.append('snapshot identity stable')
        assert before['elements'][0]['section_target'] == 'projects'
        assert before['sections'][0]['in_view'] is False and before['sections'][0]['reveal_direction'] == 'down'
        checks.append('offscreen section linked with bounded down hint')
        tab.js("document.querySelector('a').click()")
        tab.wait_loaded()
        after = tab.message({'type': 'snapshot'})
        assert after['document_id'] == before['document_id']
        assert after['sections'][0]['in_view'] is True and after['sections'][0]['occluded'] is False
        checks.append('anchor scroll exposes same-document section')
        tab.js("const c=document.createElement('div'); c.style='position:fixed;inset:0;z-index:99999;background:white'; document.body.append(c)")
        covered = tab.message({'type': 'snapshot'})
        assert covered['sections'][0]['occluded'] is True
        checks.append('overlay prevents uncovered section proof')
        tab.send('Page.reload'); tab.wait_loaded()
        reloaded = tab.message({'type': 'snapshot'})
        assert reloaded['document_id'] != before['document_id']
        checks.append('reload produces a new document identity')
        output = {'evidence_type': 'local headless Chromium with built extension injection; no live account', 'checks': checks,
                  'before': before, 'after': after, 'covered': covered, 'reload_document_id': reloaded['document_id']}
        (ROOT / 'tmp/h4b-browser-check.json').write_text(json.dumps(output, indent=2), encoding='utf-8')
        print(json.dumps({'passed': len(checks), 'checks': checks}))
finally:
    server.shutdown()
