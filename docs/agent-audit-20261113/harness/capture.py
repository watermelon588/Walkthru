import os, sys, json, time, uuid, threading, functools, hashlib
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path.cwd()
sys.path.insert(0,str(ROOT/"apps/api"))
from dotenv import load_dotenv
load_dotenv(ROOT/"apps/api/.env")
os.environ["RETENTION_JOB"]="0"
os.environ["JOB_WORKERS"]="0"
os.environ["WARMUP"]="0"
# Evaluation is explicitly restricted to the existing free model chain.
for key in ("CLAUDE_VERTEX_PROJECT","ANTHROPIC_API_KEY","CONTROLLER_CANDIDATE","RESEND_API_KEY"):
    os.environ[key]=""
os.environ["PERSONA_DECISION_MODEL"]="llm"
from app import db, main, jobs, plans, reservations
from app.agent import runtime, goal, report
from app.runner import journey, cdp
from scripts.grant_plan import user_id_for
from langchain_core.callbacks import BaseCallbackHandler

OUT=ROOT/"evals/results/publishable-agent-audit-20261113"
lock=threading.Lock()
active=None
pending=[]
def safe(obj):
    if hasattr(obj,"model_dump"): return safe(obj.model_dump(mode="json"))
    if isinstance(obj,dict): return {str(k):safe(v) for k,v in obj.items() if k not in {"user_id","email","access_token","refresh_token"}}
    if isinstance(obj,(list,tuple)): return [safe(v) for v in obj]
    if isinstance(obj,(str,int,float,bool)) or obj is None:return obj
    return str(obj)
def event(kind,**data):
    item={"time":datetime.now(timezone.utc).isoformat(),"kind":kind,**safe(data)}
    if active:
        with lock:
            with (active/"events.jsonl").open("a",encoding="utf8") as f:f.write(json.dumps(item,ensure_ascii=False)+"\n")
    return item
class Nodes(BaseCallbackHandler):
    def __init__(self):self.names={}
    def on_chain_start(self,serialized,inputs,*,run_id,**kw):
        name=kw.get("name") or (serialized or {}).get("name")
        if name in {"LangGraph","decide","act","check","first_impression","site_scan","accessibility_scan","performance_scan","stack_scan","synthesize"}:
            self.names[str(run_id)]=name;event("node_start",node=name,invocation=str(run_id),inputs=inputs)
    def on_chain_end(self,outputs,*,run_id,**kw):
        name=self.names.pop(str(run_id),None)
        if name:event("node_end",node=name,invocation=str(run_id),outputs=outputs)
    def on_chain_error(self,error,*,run_id,**kw):
        name=self.names.pop(str(run_id),None)
        if name:event("node_error",node=name,error=str(error)[:700])
nodes=Nodes()
old_invoke=runtime.invoke
def invoke(tier,value,config):
    return old_invoke(tier,value,{**config,"callbacks":[nodes]})
runtime.invoke=invoke
old_call=runtime.call
def call(schema,messages,*a,**kw):
    event("model_input",stage=schema.__name__,messages=messages)
    start=time.monotonic()
    try:
        value,tokens=old_call(schema,messages,*a,**kw)
        event("model_output",stage=schema.__name__,value=value,tokens=tokens,seconds=time.monotonic()-start)
        return value,tokens
    except Exception as e:
        event("model_error",stage=schema.__name__,error=str(e)[:500]);raise
runtime.call=call
old_make=runtime.make_model
class Controller:
    def __init__(self,inner):self.inner=inner
    def invoke(self,messages):
        event("model_input",stage="PersonaStep",messages=messages)
        started=time.monotonic()
        result=self.inner.invoke(messages)
        answer,tokens=runtime.unwrap(result)
        event("model_output",stage="PersonaStep",value=answer,tokens=tokens,seconds=time.monotonic()-started)
        return result
runtime.make_model=lambda tier:Controller(old_make(tier))
old_guard=runtime.guarded
def guarded(provider,model,*,model_name="unknown"):
    from langchain_core.runnables import RunnableLambda
    inner=old_guard(provider,model,model_name=model_name)
    def attempt(messages,config):
        started=time.monotonic()
        event("provider_start",provider=provider,model=model_name)
        try:
            result=inner.invoke(messages,config=config)
            event("provider_end",provider=provider,model=model_name,seconds=time.monotonic()-started)
            return result
        except Exception as e:
            event("provider_error",provider=provider,model=model_name,seconds=time.monotonic()-started,error=str(e)[:400]);raise
    return RunnableLambda(attempt)
runtime.guarded=guarded
old_evidence=goal.evidence
def evidence(checkpoint,before,after,action,start_url):
    result=old_evidence(checkpoint,before,after,action,start_url)
    event("proof_check",checkpoint=checkpoint,before=before,after=after,action=action,proof=result)
    return result
goal.evidence=evidence
old_message=cdp.Tab.message
def message(tab,msg):
    started=time.monotonic()
    try:
        result=old_message(tab,msg)
    except Exception as exc:
        event("browser_error",request=msg,error=str(exc))
        print("BROWSER_ERROR",str(exc)[:1500],flush=True)
        raise
    if msg.get("type") in {"snapshot","act","act_cancel","evidence_capture"}:
        event("browser_tool",request=msg,result=result,seconds=time.monotonic()-started)
    return result
cdp.Tab.message=message
old_upload=db.upload_evidence
def upload(path,jpeg):
    folder=active/"frames";folder.mkdir(exist_ok=True)
    (folder/Path(path).name).write_bytes(jpeg)
    old_upload(path,jpeg)
    event("screenshot",path=path,sha256=hashlib.sha256(jpeg).hexdigest(),bytes=len(jpeg))
db.upload_evidence=upload
old_enqueue=jobs.enqueue
def enqueue(kind,payload=None,**kw):
    if kind=="finish_run":
        pending.append((kind,payload));event("report_handoff",payload=payload);return
    return old_enqueue(kind,payload,**kw)
jobs.enqueue=enqueue
old_build=report.build_graph
class ReportGraph:
    def __init__(self):self.graph=old_build()
    def invoke(self,state):return self.graph.invoke(state,{"callbacks":[nodes]})
report._graph=ReportGraph()
uid=user_id_for(os.environ["WALKTHRU_AUDIT_EMAIL"])
before_ids={r["id"] for r in db.entitlements_for_user(uid)}
db.grant_entitlement(uid,"plus",31,10,"dev")
temporary_ids=[r["id"] for r in db.entitlements_for_user(uid) if r["id"] not in before_ids]
(OUT/"temporary-pass.json").write_text(json.dumps({"ids":temporary_ids}),encoding="utf8")
print("TEMPORARY_PLAN",plans.summary(plans.current(uid)),flush=True)
targets=[
("portfolio","https://portfolio2-mu-inky.vercel.app/","Find the projects section and open one project detail on this website."),
("scribb","https://www.scribb.xyz/","Find what Scribb offers and open its pricing or plans page."),
("tripverse","https://tripverse-0.vercel.app/","Find the destinations or trips listing and open one destination or trip detail.")]
manifest=json.loads((OUT/"manifest.json").read_text()) if (OUT/"manifest.json").exists() else []
for slug,site,objective in targets:
    if any(r["slug"]==slug and r.get("report_ready") for r in manifest):continue
    active=OUT/slug;active.mkdir(exist_ok=True)
    print("START",slug,flush=True)
    event("experiment",site=site,goal=objective,persona="first_timer",scope="direct runner with normal admission; report handler in same instrumented process; free models")
    row={"id":str(uuid.uuid4()),"group_id":str(uuid.uuid4()),"user_id":uid,"site":site,"goal":objective,"persona":"first_timer","max_steps":20}
    held={}
    def hold(values):
        if values:held.update(values)
        return True
    t=time.monotonic()
    status,error=journey.run(row,hold)
    run_id=held.get("run_id")
    entry={"site":site,"slug":slug,"goal":objective,"run_id":run_id,"runner_status":status,"error":error,"journey_seconds":round(time.monotonic()-t,2)}
    if run_id:
        state=runtime.get_state(db.get_run(run_id)["tier"],main._cfg(run_id)).values
        (active/"final-state.json").write_text(json.dumps(safe(state),indent=2),encoding="utf8")
        for kind,payload in pending:
            if payload["run_id"]!=run_id:continue
            for attempt in range(3):
                try:jobs.handle(kind,payload);break
                except Exception as exc:
                    event("report_retry",attempt=attempt+1,error=str(exc)[:500])
                    if attempt<2:time.sleep(10)
        saved=db.get_run(run_id)
        entry.update(status=saved["status"],steps=len(saved.get("steps",[])),report_ready=bool(saved.get("report")))
        (active/"saved-run.json").write_text(json.dumps(safe(saved),indent=2),encoding="utf8")
    manifest=[r for r in manifest if r["slug"]!=slug]+[entry]
    (OUT/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf8")
    print("FINISH",json.dumps(entry),flush=True)
for entitlement_id in temporary_ids:
    db._request("PATCH","/rest/v1/entitlements",params={"id":f"eq.{entitlement_id}","user_id":f"eq.{uid}"},json_body={"revoked_at":datetime.now(timezone.utc).isoformat()},prefer="return=minimal")
print("RESTORED_PLAN",plans.summary(plans.current(uid)),flush=True)
runtime.close_checkpointer()
print("ALL_DONE",flush=True)
os._exit(0)
