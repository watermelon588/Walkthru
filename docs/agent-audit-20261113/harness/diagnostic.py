"""Controlled follow-ups. Does not edit product source or claim a shipped fix."""
from pathlib import Path
source=Path(__file__).with_name('capture.py').read_text(encoding='utf8')
source=source.replace('targets=[\n', '''targets=[
("portfolio-grounded","https://portfolio2-mu-inky.vercel.app/","Find the projects section and open one project detail on this website."),
("scribb-supported","https://www.scribb.xyz/","Open Explore and open the Demo Journal."),
]\nignored_targets=[\n''')
source=source.replace('old_evidence=goal.evidence', '''old_plan=goal.plan
def diagnostic_plan(site,objective,observation,paid=False):
    proposed=old_plan(site,objective,observation,paid)
    if active.name=="portfolio-grounded":
        grounded={"intent":objective,"feasible":True,"refusal":None,"checkpoints":[
          {"description":"Open the Projects page.","kind":"navigation","url_contains":"/dial/projects.html","text_contains":None},
          {"description":"Open a project detail page.","kind":"navigation","url_contains":"/dial/work.html","text_contains":None}]}
        event("experimental_intervention",original=proposed,replacement=grounded,basis="Routes observed in the prior baseline run. This is an evaluation-only planner substitution, not a deployed fix.")
        return grounded
    return proposed
goal.plan=diagnostic_plan
import httpx
from urllib.parse import urlsplit
old_http_send=httpx.Client.send
def http_send(client,request,*args,**kwargs):
    start=time.monotonic(); parsed=urlsplit(str(request.url))
    location=parsed.scheme+"://"+parsed.netloc+parsed.path
    try:
        response=old_http_send(client,request,*args,**kwargs)
        event("http_tool",method=request.method,url=location,status=response.status_code,seconds=time.monotonic()-start)
        return response
    except Exception as exc:
        event("http_tool",method=request.method,url=location,error=type(exc).__name__,seconds=time.monotonic()-start)
        raise
httpx.Client.send=http_send
old_evidence=goal.evidence''')
exec(compile(source,str(Path(__file__).with_name('capture.py')),'exec'))
