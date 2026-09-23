"""DEV/EVAL: replay saved runs through candidate report-writer models with the exact production prompt.

    apps/api/.venv/Scripts/python evals/model_bakeoff.py [run_id ...]

Per model and run it records: valid output, latency, raw UX findings, invented ones (cite no step that
went wrong, or restate a scan finding; the production filter would drop them), whether a real problem
was caught, and summary wording that describes problems when none happened. Summaries go to a file
for reading. Costs one model call per model per run.
"""

import json
import os
import re
import sys
import time

import httpx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "apps", "api"))
os.chdir(os.path.join(ROOT, "apps", "api"))

from dotenv import load_dotenv

load_dotenv(".env")

from app import db
from app.agent.report import grounded_ux, problem_steps, synthesis_inputs
from app.agent.schema import Synthesis

DEFAULT_RUNS = [
    "c6f323e2ac9e431693bfc4b0d2bf1970",  # portfolio contact, everything worked
    "10627ec001374267a35ce3a1be7bcc42",  # portfolio contact, everything worked
    "48ab78fd71f34f989de295bc66028a54",  # fixture contact, verified send, everything worked
    "f3611d6d92064012a6dd7c4d78ddc19f",  # Tripverse signup, real error at submit
    "fcacc124ca00451cb32667729d38df97",  # Tripverse signup, real error at submit
]
OPENROUTER = [
    ("nvidia/nemotron-3-super-120b-a12b:free", "json"),
    ("nex-agi/nex-n2.5-pro:free", "json"),
    ("google/gemma-4-31b-it:free", "json"),
    ("nvidia/nemotron-3-ultra-550b-a55b:free", "tool"),
]
PROBLEM_WORDS = re.compile(r"\b(struggl|confus|could ?n[o']t|cannot|can't|fail|difficult|repeated|frustrat|stuck|unclear|hard to)\w*", re.IGNORECASE)


def state_from_run(row: dict) -> dict:
    rep = row["report"] or {}
    steps = [{k: v for k, v in s.items() if k != "diagnostics"} for s in row["steps"] or []]
    state = {
        "site": row["site"], "goal": row["goal"], "persona": row["persona"], "status": row["status"], "steps": steps,
        "first_impression": rep.get("first_impression") or {}, "site_audit": rep.get("site_audit"),
        "production_like": row["site"].startswith(("http://127.0.0.1:8101", "http://127.0.0.1:8102")),
        "accessibility": [], "performance": [], "seo": [], "security": [],
    }
    for f in rep.get("findings", []):
        if f["kind"] in state and f["kind"] != "ux":
            state[f["kind"]].append(f)
    return state


def openrouter(model: str, mode: str, messages: list) -> tuple[dict, int]:
    body = {"model": model, "messages": [{"role": r if r != "human" else "user", "content": c} for r, c in messages], "temperature": 0}
    schema = Synthesis.model_json_schema()
    if mode == "json":
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": "Synthesis", "schema": schema}}
    else:
        body["tools"] = [{"type": "function", "function": {"name": "write_report", "description": "Return the report.", "parameters": schema}}]
        body["tool_choice"] = {"type": "function", "function": {"name": "write_report"}}
    r = httpx.post("https://openrouter.ai/api/v1/chat/completions", headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}, json=body, timeout=httpx.Timeout(90.0, connect=10.0))
    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code} {r.text[:200]}")
    data = r.json()
    msg = data["choices"][0]["message"]
    raw = msg["tool_calls"][0]["function"]["arguments"] if mode == "tool" else msg.get("content") or ""
    raw = re.sub(r"^```(?:json)?|```$", "", raw.strip()).strip()
    return json.loads(raw), int((data.get("usage") or {}).get("total_tokens") or 0)


def langchain_model(name: str):
    if name.startswith("groq:"):
        from langchain_groq import ChatGroq

        return ChatGroq(model=name[5:], temperature=0, max_tokens=4096, reasoning_effort="low", timeout=60, max_retries=0).with_structured_output(Synthesis, method="json_schema", strict=True, include_raw=True)
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(model=name[7:], temperature=0, timeout=60, max_retries=0).with_structured_output(Synthesis, include_raw=True)


def call(model: str, mode: str, messages: list) -> tuple[Synthesis, int]:
    if mode == "lc":
        from app.agent.runtime import unwrap

        return unwrap(langchain_model(model).invoke(messages))
    data, tokens = openrouter(model, mode, messages)
    return Synthesis.model_validate(data), tokens


def main() -> None:
    runs = sys.argv[1:] or DEFAULT_RUNS
    models = [("groq:openai/gpt-oss-120b", "lc"), ("gemini:gemini-3.5-flash", "lc")] + OPENROUTER
    if os.environ.get("MODELS"):  # e.g. MODELS=groq:openai/gpt-oss-20b,google/gemma-4-31b-it:free
        known = dict([*models, ("groq:openai/gpt-oss-20b", "lc")])
        models = [(m, known.get(m, "json")) for m in os.environ["MODELS"].split(",")]
    out = os.path.join(ROOT, "evals", "results")
    os.makedirs(out, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M")
    inputs = {}
    for run_id in runs:
        row = db.get_run(run_id)
        st = state_from_run(row)
        inputs[run_id] = (st, synthesis_inputs(st))
    results, lines = [], []
    for model, mode in models:
        for run_id, (st, inp) in inputs.items():
            problems = problem_steps(st["steps"], st["status"])
            t = time.time()
            try:
                syn, tokens = call(model, mode, inp["messages"])
            except Exception as e:  # noqa: BLE001 - record and continue
                results.append({"model": model, "run": run_id[:8], "ok": False, "error": str(e)[:160], "secs": round(time.time() - t, 1)})
                print(f"{model:45} {run_id[:8]} FAILED {str(e)[:120]}", flush=True)
                continue
            secs = round(time.time() - t, 1)
            kept = grounded_ux(syn.ux_findings, inp["code_findings"], st["steps"], st["status"])
            invented = len(syn.ux_findings) - len(kept)
            caught = bool(kept) if problems else None
            summary_flag = bool(PROBLEM_WORDS.search(syn.summary)) if not problems else None
            results.append({"model": model, "run": run_id[:8], "ok": True, "secs": secs, "raw_ux": len(syn.ux_findings), "invented": invented,
                            "caught_real_problem": caught, "summary_invents_problem": summary_flag, "tokens": tokens})
            print(f"{model:45} {run_id[:8]} {secs:5.1f}s raw_ux={len(syn.ux_findings)} invented={invented} caught={caught} summary_flag={summary_flag}", flush=True)
            lines.append(f"## {model} / {run_id[:8]} ({'problems at ' + str(sorted(problems)) if problems else 'no problems'})\n"
                         f"SUMMARY: {syn.summary}\nUX: {[(f.title, f.evidence) for f in syn.ux_findings]}\nFIXES: {syn.top_fixes}\n")
            with open(os.path.join(out, f"bakeoff-{stamp}.json"), "w", encoding="utf-8") as f:  # save as we go
                json.dump(results, f, indent=1)
            with open(os.path.join(out, f"bakeoff-{stamp}-summaries.md"), "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            time.sleep(25 if model.startswith("groq:") else 3)  # free-tier limits (Groq: 8k tokens/min per model)
    print("\nper model:")
    for model, _ in models:
        rows = [r for r in results if r["model"] == model]
        ok = [r for r in rows if r["ok"]]
        if not ok:
            print(f"  {model:45} all failed: {rows[0]['error'] if rows else ''}")
            continue
        inv = sum(r["invented"] for r in ok)
        caught = [r["caught_real_problem"] for r in ok if r["caught_real_problem"] is not None]
        flags = [r["summary_invents_problem"] for r in ok if r["summary_invents_problem"] is not None]
        med = sorted(r["secs"] for r in ok)[len(ok) // 2]
        print(f"  {model:45} ok {len(ok)}/{len(rows)}  invented {inv}  caught {sum(caught)}/{len(caught)}  summary-invents {sum(flags)}/{len(flags)}  median {med}s")
    print(f"\nsummaries: evals/results/bakeoff-{stamp}-summaries.md")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
