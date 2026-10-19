"""
Task 3 API + minimal UI. Run: uvicorn app.main:app --host 0.0.0.0 --port 8001
Human approval is a state machine, not a checkbox in spirit:
  draft_pending_approval --approve--> approved_baseline --follow-up--> revised_draft
A proposal is only 'sendable' from approved_baseline. The API refuses to mark
anything sent from a draft state (409). Versions are kept in data/projects.json.
"""
from __future__ import annotations
import json, sys, uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.agents import run_pipeline   # noqa: E402
from app.diff import diff_requirements  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data" / "projects.json"
app = FastAPI(title="Meeting to Scope", version="1.0.0")


class ProcessRequest(BaseModel):
    project: str
    transcript: str
    hourly_rate: float | None = None
    baseline_project_id: str | None = None  # set for follow-up meetings


class ApproveRequest(BaseModel):
    reviewer: str = "consultant"
    note: str = ""


def load() -> dict:
    if DATA.exists():
        try:
            return json.loads(DATA.read_text())
        except Exception:
            return {}
    return {}


def save(store: dict) -> None:
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(store, indent=2))


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "projects": len(load())}


@app.post("/process")
def process(req: ProcessRequest) -> dict:
    result = run_pipeline(req.project, req.transcript, hourly_rate=req.hourly_rate)
    pid = "proj-" + uuid.uuid4().hex[:10]
    entry = {**result, "id": pid, "created_at": datetime.now(timezone.utc).isoformat(),
             "approval": None, "sendable": False, "version": 1}
    store = load()
    if req.baseline_project_id:
        base = store.get(req.baseline_project_id)
        if not base:
            raise HTTPException(404, "baseline project not found")
        if base.get("status") != "approved_baseline":
            raise HTTPException(409, "Diffs must compare against an APPROVED baseline, not a draft.")
        entry["diff"] = diff_requirements(base["requirements"], result["requirements"], req.transcript)
        entry["baseline_project_id"] = req.baseline_project_id
    store[pid] = entry
    save(store)
    return entry


@app.post("/projects/{pid}/approve")
def approve(pid: str, req: ApproveRequest) -> dict:
    store = load()
    entry = store.get(pid)
    if not entry:
        raise HTTPException(404, "project not found")
    entry["status"] = "approved_baseline"
    entry["sendable"] = True
    entry["approval"] = {"reviewer": req.reviewer, "note": req.note,
                         "at": datetime.now(timezone.utc).isoformat()}
    save(store)
    return {"id": pid, "status": entry["status"], "sendable": True, "approval": entry["approval"]}


@app.post("/projects/{pid}/mark-sent")
def mark_sent(pid: str) -> dict:
    store = load()
    entry = store.get(pid)
    if not entry:
        raise HTTPException(404, "project not found")
    if not entry.get("sendable"):
        raise HTTPException(409, "Refused: proposal is not approved. Human approval is required before sending.")
    entry["status"] = "sent"
    save(store)
    return {"id": pid, "status": "sent"}


@app.get("/projects")
def projects() -> list[dict]:
    return [{"id": k, "project": v["project"], "status": v["status"], "sendable": v.get("sendable", False),
             "requirements": len(v["requirements"]), "totals": v["totals"]} for k, v in load().items()]


@app.get("/projects/{pid}")
def project(pid: str) -> dict:
    entry = load().get(pid)
    if not entry:
        raise HTTPException(404, "project not found")
    return entry


@app.get("/", response_class=HTMLResponse)
def ui() -> str:
    return """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Meeting to Scope</title>
<style>body{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;color:#17202a}
textarea,input{width:100%;padding:.6rem}button{background:#14532d;color:#fff;border:0;padding:.6rem 1rem;border-radius:6px;cursor:pointer}
.card{background:#f4f6f5;border-radius:8px;padding:1rem;margin-top:1rem;white-space:pre-wrap;max-height:520px;overflow:auto}small{color:#666}</style></head>
<body><h1>📐 Meeting to Scope of Work</h1>
<p>Paste a transcript → requirements (checked against Task 1 knowledge) → scope, estimates, proposal.
Nothing is sendable until a human approves. For a follow-up, paste the new transcript and enter the approved baseline project ID to get a change diff.</p>
<input id="proj" placeholder="Project name, e.g. Northgate Sports" value="Client Project">
<input id="base" placeholder="Baseline project ID (follow-ups only, must be approved)">
<textarea id="tr" rows="12" placeholder="Paste transcript here — 'Sarah: We want…' format works best"></textarea>
<p><button onclick="run()">Build scope</button> <small id="st"></small></p>
<div class="card" id="out">Scope, estimates, proposal and (for follow-ups) the diff will appear here.</div>
<p><button onclick="approve()">✅ Approve as baseline</button> <small>Approving makes the proposal sendable and locks this version as the diff baseline.</small></p>
<script>let pid=null;
async function run(){document.getElementById('st').textContent='Analysing… agents are checking the Knowledge Brain.';
const body={project:proj.value,transcript:tr.value,baseline_project_id:base.value||null};
const r=await fetch('/process',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
const d=await r.json();document.getElementById('st').textContent='';
if(!r.ok){out.textContent='Error: '+(d.detail||JSON.stringify(d));return;} pid=d.id;
let txt='Project ID (save for follow-ups): '+pid+'\\nStatus: '+d.status+'\\nTotals: '+JSON.stringify(d.totals);
if(d.diff)txt+='\\n\\n=== CHANGE DIFF ===\\n'+d.diff.summary+'\\nAdded/out-of-scope: '+JSON.stringify(d.diff.added.map(a=>a.description))+'\\nRemoved: '+JSON.stringify(d.diff.removed.map(a=>a.description))+'\\nModified: '+JSON.stringify(d.diff.modified.map(a=>a.description));
out.textContent=txt+'\\n\\n=== SCOPE ===\\n'+d.scope_md+'\\n\\n=== PROPOSAL ===\\n'+d.proposal_md;}
async function approve(){if(!pid){alert('Build a scope first');return;}
const r=await fetch('/projects/'+pid+'/approve',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({reviewer:'ui-user'})});
document.getElementById('st').textContent=JSON.stringify(await r.json());}
</script></body></html>"""
