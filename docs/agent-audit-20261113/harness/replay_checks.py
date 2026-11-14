import sys,json,hashlib,ast,re,subprocess
from pathlib import Path
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'apps/api'))
from app.agent import goal,persona
from app.agent.schema import PersonaStep
OUT=Path(__file__).parent
def events(slug):return [json.loads(l) for l in (OUT/slug/'events.jsonl').read_text(encoding='utf8').splitlines()]
checks=[]
ps=[e for e in events('portfolio') if e['kind']=='proof_check']
for i,e in enumerate(ps[:2]):
 fixed=dict(e['checkpoint'],kind='navigation',url_contains=['/dial/projects.html','/dial/work.html'][i],text_contains=None)
 actual=goal.evidence(e['checkpoint'],e['before'],e['after'],e['action'],e['before']['url'])
 repaired=goal.evidence(fixed,e['before'],e['after'],e['action'],e['before']['url'])
 checks.append({'test':'portfolio recorded transition '+str(i+1),'baseline_checkpoint':e['checkpoint'],'baseline_proof':actual,'hypothetical_checkpoint':fixed,'replay_proof':repaired})
 assert actual is None and repaired
ss=[e for e in events('scribb') if e['kind']=='node_start' and e['node']=='decide'][-1]['inputs']
raw=[e for e in events('scribb') if e['kind']=='model_output' and e['stage']=='PersonaStep'][-1]['value']
step,code=persona._enforce(PersonaStep.model_validate(raw),ss)
el=next(e for e in ss['observation']['elements'] if e['id']==raw['target_id'])
checks.append({'test':'scribb offscreen selection','selected_element':el,'model_choice':raw,'enforced_action':step.model_dump(),'stop_code':code})
assert code=='agent_lost' and el['in_view'] is False
if (OUT/'tripverse/final-state.json').exists():
 s=json.loads((OUT/'tripverse/final-state.json').read_text()); rows=s['steps']
 checks.append({'test':'tripverse loop signature','steps':[{'step':i+1,**{k:x.get(k) for k in ('action','target_id','target_label','url','scroll_pct','scroll_container_id','scroll_direction','scroll_position','wait_condition')}} for i,x in enumerate(rows)]})
(OUT/'replay-checks.json').write_text(json.dumps(checks,indent=2),encoding='utf8')
print('PASS: recorded portfolio proof mismatches and Scribb viewport refusal reproduced without model calls.')
inventory=[]; hashes={}
files=list((ROOT/'apps/api/app/agent').glob('*.py'))+list((ROOT/'apps/api/app/scans').glob('*.py'))+list((ROOT/'apps/api/app/runner').glob('*.py'))
files += [ROOT/'apps/api/app'/f for f in ['main.py','db.py','jobs.py','plans.py','provider_usage.py','providers.py','quotes.py','reservations.py','cloud.py']]
for p in files:
 text=p.read_text(encoding='utf8');rel=str(p.relative_to(ROOT)).replace('\\','/');hashes[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
 tree=ast.parse(text)
 def visit(node,prefix=''):
  for n in ast.iter_child_nodes(node):
   if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
    name=prefix+n.name
    calls=sorted(set(ast.unparse(c.func) for c in ast.walk(n) if isinstance(c,ast.Call))) if not isinstance(n,ast.ClassDef) else []
    inventory.append({'file':rel,'line':n.lineno,'name':name,'kind':type(n).__name__,'doc':ast.get_docstring(n) or '', 'calls':calls})
    visit(n,name+'.')
   else:visit(n,prefix)
 visit(tree)
for p in list((ROOT/'apps/extension/lib').glob('*.ts'))+list((ROOT/'apps/extension/entrypoints').rglob('*.ts')):
 rel=str(p.relative_to(ROOT)).replace('\\','/');hashes[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
 for m in re.finditer(r'(?m)^(?:export )?(?:async )?function (\w+)',p.read_text(encoding='utf8')):
  inventory.append({'file':rel,'line':p.read_text(encoding='utf8')[:m.start()].count('\n')+1,'name':m.group(1),'kind':'TS declared function','doc':'','calls':[]})
p=ROOT/'apps/extension/.output/chrome-mv3/inject.js';hashes[str(p.relative_to(ROOT)).replace('\\','/')]=hashlib.sha256(p.read_bytes()).hexdigest()
(OUT/'function-inventory.json').write_text(json.dumps(inventory,indent=2),encoding='utf8')
(OUT/'source-manifest.json').write_text(json.dumps({'git_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'working_tree':'dirty; hashes identify inspected content, not a clean release','files':hashes},indent=2),encoding='utf8')
print(len(inventory),'function/class entries indexed;',len(hashes),'source hashes recorded')
