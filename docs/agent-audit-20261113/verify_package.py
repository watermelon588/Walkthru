from pathlib import Path
import json,re,hashlib
import pypdfium2 as pdfium
from pypdf import PdfReader,PdfWriter
from PIL import Image,ImageDraw
OUT=Path(__file__).parent;ROOT=OUT.parents[1];render=ROOT/'tmp/pdfs/agent-audit';render.mkdir(parents=True,exist_ok=True)
pdf=OUT/'walkthru-live-agent-audit.pdf'
reader=PdfReader(pdf);writer=PdfWriter();writer.clone_document_from_reader(reader)
for i,page in enumerate(reader.pages):
 text=page.extract_text() or ''
 lines=text.splitlines()
 for line in lines:
  if re.match(r'^(?:\d+(?:a)?\. |[A-Za-z ]+ / run breakdown|[A-Za-z ]+ / observed graph)',line):
   writer.add_outline_item(line,i);break
tmp=OUT/'bookmarked.tmp.pdf'
with tmp.open('wb') as f:writer.write(f)
tmp.replace(pdf)
doc=pdfium.PdfDocument(pdf)
for i,page in enumerate(doc):
 im=page.render(scale=1).to_pil();im.save(render/f'page-{i+1:02d}.png')
for start in range(0,len(doc),12):
 sheet=Image.new('RGB',(900,1260),'#dfe5e9');d=ImageDraw.Draw(sheet)
 for offset in range(min(12,len(doc)-start)):
  i=start+offset;im=Image.open(render/f'page-{i+1:02d}.png');im.thumbnail((290,290));x=offset%3*300;y=offset//3*315
  sheet.paste(im,(x+(300-im.width)//2,y+20));d.text((x+10,y+2),str(i+1),fill='black')
 sheet.save(render/f'contact-{start//12+1}.png')
manifest=json.loads((OUT/'evidence/manifest.json').read_text())
hashes=json.loads((OUT/'evidence-hashes.json').read_text());assert all(hashlib.sha256((OUT/p).read_bytes()).hexdigest()==h for p,h in hashes.items())
steps=0;frames=0;events=0
for r in manifest:
 p=OUT/'evidence'/r['slug'];saved=json.loads((p/'saved-run.json').read_text());assert saved['report']
 for i,s in enumerate(saved['steps']):assert (p/'frames'/f'step-{i+1:02d}.jpg').exists()
 steps+=len(saved['steps']);frames+=len(list((p/'frames').glob('*.jpg')));events+=len((p/'events.jsonl').read_text(encoding='utf8').splitlines())
html=(OUT/'trace-appendix.html').read_text(encoding='utf8')
for target in re.findall(r'(?:href|src)="([^"]+)"',html):
 if not target.startswith(('http:','https:','#')):assert (OUT/target).exists(),target
validation={'pdf_pages':len(doc),'saved_runs':len(manifest),'saved_steps':steps,'screenshot_files':frames,'recorded_events':events,'evidence_hashes_verified':len(hashes),'local_html_links':'pass','all_saved_steps_have_frames':True}
(OUT/'validation.json').write_text(json.dumps(validation,indent=2),encoding='utf8');print(validation)
readme=['# Walkthru live agent audit','', 'Read [the illustrated paper](walkthru-live-agent-audit.pdf) or open [the complete trace appendix](trace-appendix.html).','',f"{len(manifest)} saved runs · {steps} saved steps · {frames} screenshots · {events} recorded events.",'','## Main finding','', 'The portfolio reached its project detail on baseline step 2, but an unprovable checkpoint kept progress at zero. The matched-route diagnostic completed in 2 steps. Reusing a stale route on a different theme failed, so the fix must ground predicates in each run. Scribb reproduced outcome misclassification even for an available Demo Journal flow.','', 'Product fixes are specified, not shipped. Internal handlers and the local headless runner were exercised; deployed HTTP authentication and queue leasing were not.','', '## Saved account reports','']
for r in manifest:readme.append(f"- [{r['slug']}](http://localhost:5173/app/runs/{r['run_id']}): {r['status']}, {r['steps']} steps. ID `{r['run_id']}`.")
readme+=['','Open those links in the local Walkthru app while signed into the requested account. Reports and uploaded frames remain private. Longer temporary development passes created by the audit were revoked; the prior Pro pass is active.','', '## Diagram source and exports','', '- [Complete graph source](walkthru-agent-flowchart.excalidraw) · [SVG](walkthru-agent-flowchart.svg)','- [Detailed state/context source](walkthru-agent.excalidraw) · [SVG](walkthru-agent.svg)','- [Observed traces source](live-traces.excalidraw) · [SVG](live-traces.svg) · [PNG](live-traces.png)','', '## Reproduction','', 'Run `build_paper.py` using the existing bundled Python with reportlab/Pillow, then `verify_package.py` to add PDF navigation and validate/render outputs. Raw capture, controlled interventions and replay checks are in `evals/results/publishable-agent-audit-20261113/`. No new project dependency was installed.','', 'Publication copy redacts the requested account email and provider organization identifiers. Original frame bytes are preserved. The package has not been published externally.']
(OUT/'README.md').write_text('\n'.join(readme),encoding='utf8')
