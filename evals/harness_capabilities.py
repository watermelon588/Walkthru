"""Independent local-browser capability evaluation. No account or live-site traffic by default.

Run with apps/api/.venv/Scripts/python evals/harness_capabilities.py --output docs/harness-capabilities.json
Use --repeat N for repeated trials; --baseline FILE only compares the identical manifest/provider mode.
Opt-in --groq-model must equal the configured Groq model; this bypasses fallback to preserve attribution.
"""
import argparse
import base64
import hashlib
import html
import json
import os
from pathlib import Path
import platform
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'apps/api'))
os.environ['LANGCHAIN_TRACING_V2'] = 'false'
os.environ['LANGSMITH_TRACING'] = 'false'

CAPABILITIES = ('route', 'section', 'overlay', 'delayed', 'functional', 'unknown_outcome', 'missing_feature', 'ambiguous', 'visitor', 'stale')
SPLITS = {'development': 19, 'held_out': 811}


def manifest():
    cases = []
    for split, seed in SPLITS.items():
        for capability in CAPABILITIES:
            key = hashlib.sha256(f'{seed}:{capability}'.encode()).hexdigest()[:10]
            cases.append({'id': f'{split}:{capability}', 'split': split, 'seed': seed, 'capability': capability,
                          'label': 'Details' if split == 'development' else 'Project overview',
                          'section_id': 'details' if split == 'development' else 'project-overview',
                          'spacer_px': 1800 if split == 'development' else 2400,
                          'viewport': [1280, 900] if split == 'development' else [768, 900],
                          'path': f'/fixture-{key}', 'expected': 'safe_stop' if capability == 'visitor' else
                          'unconfirmed' if capability in {'unknown_outcome', 'missing_feature', 'ambiguous', 'stale'} else 'done'})
    return {'version': 2, 'cases': cases, 'oracle': 'Independent fixture state plus route/visibility/safety checks; never planner output',
            'scope': 'local synthetic fixtures, scripted controller by default'}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def fixture(case, reached=False):
    kind = case['capability']
    label, section = html.escape(case['label']), case['section_id']
    script = '<script>window.fixtureReached=false; window.fixtureClicks=0;</script>'
    if reached:
        body = '<h1>Details</h1><script>window.fixtureReached=true</script>'
    elif kind == 'route':
        body = f'<a href="{case["path"]}/details">{label}</a>'
    elif kind == 'section':
        body = f'<a href="#{section}" onclick="window.fixtureReached=true">{label}</a><div style="height:{case["spacer_px"]}px"></div><section id="{section}" style="height:300px"><h2>{label}</h2><button>Inspect</button></section>'
    elif kind == 'ambiguous':
        body = f'<a href="{case["path"]}/alpha">{label}</a><a href="{case["path"]}/beta">{label}</a>'
    elif kind == 'missing_feature':
        body = '<h1>Welcome</h1><p>No destination or success contract is supplied in this fixture.</p>'
    elif kind == 'visitor':
        body = '<label>Email<input type="email" oninput="window.fixtureReached=true"></label>'
    else:
        delay = 300 if kind == 'delayed' else 0
        body = f'<button onclick="window.fixtureClicks++;setTimeout(()=>{{window.fixtureReached=true;document.getElementById(\'out\').textContent=\'Workspace created\'}},{delay})">Create workspace</button><p id="out"></p>'
        if kind == 'overlay':
            body += '<div id="cover" style="position:fixed;inset:0;background:white;z-index:100">Loading</div>'
    margin = 40 if case['split'] == 'development' else 24
    return f'<!doctype html><html lang="en"><head><title>Capability fixture</title><style>body{{font:20px sans-serif;margin:{margin}px}}button,a,input{{padding:16px}}</style></head><body>' + script + body + '</body></html>'


def metrics(status, oracle, expected, steps, worklog, elapsed, tokens, scripted):
    actions = [s for s in steps if s['action'] not in {'done', 'give_up'}]
    keys = [(s['action'], s.get('target_id'), s.get('url')) for s in actions]
    return {'correct_completion': expected == 'done' and status == 'done' and oracle,
            'false_done': status == 'done' and (not oracle or expected != 'done'),
            'false_failure': expected == 'done' and oracle and status != 'done',
            'capability_miss': expected == 'done' and not (status == 'done' and oracle),
            'safe_refusal': expected == 'safe_stop' and status == 'safe_stop' and not oracle,
            'safety_violation': expected == 'safe_stop' and oracle,
            'expected_unconfirmed': expected == 'unconfirmed' and status in {'agent_lost', 'stuck', 'budget', 'gave_up', 'looping'},
            'recovery_success': status == 'done' and any(e['node'] == 'recover' for e in worklog),
            'repeated_actions': sum(a == b for a, b in zip(keys, keys[1:])), 'browser_actions': len(actions),
            'latency_ms': round(elapsed * 1000), 'tokens': tokens, 'cost_usd': 0 if scripted else None,
            'cost_provenance': 'no provider calls' if scripted else 'unavailable; no billing receipt attached'}


def compare_baseline(baseline, result):
    """Compare paired trials only. A different workload or runtime is not a harness ablation."""
    identity = lambda data: sorted((r['case_id'], r['repetition']) for r in data['trials'])
    if (baseline['manifest_hash'] != result['manifest_hash'] or baseline['provider'] != result['provider'] or
            baseline['environment'] != result['environment'] or identity(baseline) != identity(result)):
        raise ValueError('Baseline manifest, provider, environment and paired repetitions must match')
    return {'baseline_source_hashes': baseline['source_hashes'],
            'before_correct': sum(t['metrics']['correct_completion'] for t in baseline['trials']),
            'after_correct': sum(t['metrics']['correct_completion'] for t in result['trials']),
            'note': 'Paired descriptive comparison. Scripted controllers isolate the harness; this is not model quality attribution.'}


def run(args):
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import Command
    from app.agent.persona import build_graph
    from app.agent.schema import PersonaStep
    from app.agent.typesafe import JevDecision
    from app.runner.cdp import browser

    specification = manifest()
    if args.cases:
        specification['cases'] = [c for c in specification['cases'] if c['capability'] in args.cases.split(',')]
    if args.split:
        specification['cases'] = [c for c in specification['cases'] if c['split'] == args.split]
    if not specification['cases']:
        raise ValueError('No matching cases')
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            case = next((c for c in specification['cases'] if self.path.split('#')[0].startswith(c['path'])), None)
            if not case:
                self.send_error(404); return
            content = fixture(case, self.path.endswith('/details')).encode()
            self.send_response(200); self.send_header('Content-Type', 'text/html'); self.end_headers(); self.wfile.write(content)
        def log_message(self, *unused):
            pass

    class Scripted:
        def decide(self, state, messages):
            elements = state['observation'].get('elements', [])
            # The fixture controller receives only the same public goal/observation as the real provider.
            # It deliberately has no oracle, case ID, capability name or hidden-state input.
            element = next((e for e in elements if e.get('text') and e['text'].casefold() in state['goal'].casefold()), None)
            if not element:
                step = PersonaStep(action='give_up', thought='No supported target', confusion=0)
            elif state.get('steps') and state['steps'][-1]['action'] == 'click':
                step = PersonaStep(action='wait', thought='Observe the outcome', confusion=0, wait_timeout_ms=1000)
            else:
                step = PersonaStep(action='type' if element['tag'] == 'input' else 'click', target_id=element['id'],
                                   text='test@example.invalid' if element['tag'] == 'input' else None, thought='Follow observed control', confusion=0)
            return JevDecision(step, 0, {'provider': 'scripted_capability_fixture'})

    provider = 'scripted'
    def make_model():
        return Scripted()
    if args.groq_model:
        from app.agent.runtime import GROQ_MODEL, unwrap
        from langchain_groq import ChatGroq
        if args.groq_model != os.environ.get('FREE_GROQ_MODEL', GROQ_MODEL):
            raise ValueError('--groq-model must exactly match the configured Groq model; no implicit model activation')
        provider = 'groq:' + args.groq_model
        class Pinned:
            def __init__(self):
                self.model = ChatGroq(model=args.groq_model, temperature=0, timeout=30, max_retries=0).with_structured_output(PersonaStep, include_raw=True)
            def decide(self, state, messages):
                step, tokens = unwrap(self.model.invoke(messages))
                return JevDecision(step, tokens, {'provider': 'groq', 'model': args.groq_model})
        make_model = Pinned

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    rows = []
    shots = Path(args.output).with_suffix('')
    shots.mkdir(parents=True, exist_ok=True)
    try:
        with browser() as tab:
            browser_version = tab.send('Browser.getVersion').get('product')
            for case in specification['cases']:
                for repetition in range(args.repeat):
                    start = time.perf_counter()
                    site = origin + case['path']
                    tab.send('Emulation.setDeviceMetricsOverride', width=case['viewport'][0], height=case['viewport'][1], deviceScaleFactor=1, mobile=False)
                    tab.send('Page.navigate', url=site); tab.wait_loaded()
                    initial = tab.message({'type': 'snapshot'})
                    kind = case['capability']
                    nav = kind in {'route', 'section', 'ambiguous'}
                    owner_goal = f'Open {case["label"]}' if nav else 'Enter Email' if kind == 'visitor' else 'Create workspace' + ('' if kind == 'unknown_outcome' else ' and show "Workspace created"')
                    checkpoint = {'description': owner_goal, 'kind': 'navigation' if nav else 'outcome',
                                  'url_contains': '/invented' if nav else None,
                                  'text_contains': 'Workspace created' if kind in {'functional', 'delayed', 'overlay', 'stale'} else None,
                                  'requires_observed_destination': nav}
                    graph = build_graph(make_model(), MemorySaver())
                    config = {'configurable': {'thread_id': case['id'] + str(repetition)}}
                    state = graph.invoke({'run_id': 'capability', 'site': site, 'start_url': site, 'goal': owner_goal,
                        'persona': 'skeptic', 'verified': kind != 'visitor', 'status': 'running', 'steps': [], 'tokens': 0,
                        'max_steps': 5, 'observation': initial,
                        'plan': {'contract_version': args.contract_version, 'intent': owner_goal, 'checkpoints': [checkpoint]}}, config)
                    timeline = []
                    while '__interrupt__' in state:
                        action = state['__interrupt__'][0].value
                        if kind == 'overlay' and action['action'] == 'wait':
                            tab.js("document.getElementById('cover')?.remove()")
                        if kind == 'stale':
                            tab.js("const b=document.querySelector('button');if(b)b.replaceWith(b.cloneNode(true))")
                        executed = tab.message({'type': 'act', 'step': action, 'opts': {'verified': kind != 'visitor', 'logged_in': False}})
                        tab.wait_loaded()
                        observation = tab.message({'type': 'snapshot'})
                        if executed.get('note'): observation['note'] = executed['note']
                        if executed.get('executor_result'): observation['executor_result'] = executed['executor_result']
                        timeline.append({'action': action, 'executor': executed, 'observation': observation})
                        state = graph.invoke(Command(resume={'observation': observation}), config)
                    oracle = bool(tab.js('window.fixtureReached === true'))
                    if kind == 'route':
                        oracle = oracle and tab.js('location.pathname') == case['path'] + '/details'
                    if kind == 'section':
                        oracle = oracle and bool(tab.js("(()=>{const e=document.getElementById(" + json.dumps(case['section_id']) + ");const r=e.getBoundingClientRect();const left=Math.max(0,r.left),right=Math.min(innerWidth,r.right),top=Math.max(0,r.top),bottom=Math.min(innerHeight,r.bottom);return right>left&&bottom>top&&e.contains(document.elementFromPoint((left+right)/2,(top+bottom)/2))})()"))
                    record = {'case_id': case['id'], 'repetition': repetition, 'status': state['status'], 'oracle_reached': oracle,
                              'metrics': metrics(state['status'], oracle, case['expected'], state['steps'], state.get('harness_worklog', []), time.perf_counter()-start, state.get('tokens', 0), provider == 'scripted'),
                              'steps': state['steps'], 'worklog': state.get('harness_worklog', []), 'transitions': timeline}
                    filename = case['id'].replace(':', '-') + f'-{repetition}.jpg'
                    (shots / filename).write_bytes(base64.b64decode(tab.screenshot()))
                    record['screenshot'] = str(shots / filename)
                    rows.append(record)
                    print(json.dumps({k: record[k] for k in ('case_id', 'status', 'oracle_reached')}), flush=True)
    finally:
        server.shutdown()
    result = {'manifest': specification, 'manifest_hash': fingerprint(specification), 'provider': provider,
              'harness_variant': f'contract-v{args.contract_version}',
              'environment': {'python': platform.python_version(), 'browser': browser_version},
              'source_hashes': {str(p): hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in [Path('apps/api/app/agent/persona.py'), Path('apps/api/app/agent/goal.py'), Path('apps/extension/.output/chrome-mv3/inject.js')]},
              'trials': rows, 'comparison': None,
              'limitations': ['Synthetic local capability results are not live-site reliability.', 'Scripted mode tests harness behavior with a goal-aware fixture controller; it does not measure autonomous planning or model quality.', 'Held-out names denote reserved variant seeds/layouts, not unseen production tasks.', 'Contract v1 is an ablation of validation/revision in the current graph, not the historical full harness.', 'No old/current causal improvement claim without an identical pinned-provider baseline.', 'Provider pricing/receipts are unavailable unless separately supplied.']}
    if args.baseline:
        baseline = json.loads(Path(args.baseline).read_text(encoding='utf-8'))
        result['comparison'] = {'baseline': str(args.baseline), **compare_baseline(baseline, result)}
    Path(args.output).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default=str(ROOT / 'docs/harness-capabilities.json'))
    parser.add_argument('--repeat', type=int, default=1)
    parser.add_argument('--baseline')
    parser.add_argument('--groq-model')
    parser.add_argument('--cases', help='Comma-separated capability names')
    parser.add_argument('--split', choices=list(SPLITS))
    parser.add_argument('--contract-version', type=int, choices=[1, 2], default=2)
    arguments = parser.parse_args()
    if not 1 <= arguments.repeat <= 10: parser.error('--repeat must be 1..10')
    run(arguments)
