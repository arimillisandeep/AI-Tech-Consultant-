"""
Knowledge Brain API — the single service Tasks 2 & 3 consume.
Run: uvicorn app.main:app --host 0.0.0.0 --port 8000   (docs at /docs, chat UI at /)

Abstention rule: if the best retrieval score < ABSTAIN_THRESHOLD we return
status=insufficient_evidence, create a human escalation, and DO NOT generate
a fluent-but-ungrounded answer. Threshold is tuned on evaluation/cases.json.
"""
from __future__ import annotations
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import store                      # noqa: E402
from app.llm import generate_answer        # noqa: E402
from app.models import (EscalationCreate, EscalationResolve, IngestionRunRequest,  # noqa: E402
                        QueryRequest, QueryResponse, Source)

ABSTAIN_THRESHOLD = 0.08  # TF-IDF cosine scale; justify with evals, don't cargo-cult

app = FastAPI(title="Knowledge Brain API", version="1.0.0",
              description="Shared product-knowledge service. Tasks 2 & 3 must use this API, never internal code.")


@app.on_event("startup")
def startup() -> None:
    store.seed_if_empty()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", **store.stats()}


_STOP = {"what", "does", "with", "from", "that", "this", "your", "have", "will",
         "when", "where", "which", "into", "about", "there", "their", "them", "should", "would", "could"}


def term_coverage(question: str, chunk_text: str) -> float:
    """Share of distinctive question terms (4-char prefix match, so
    'failing'~'failed') present in the best chunk. A raw TF-IDF threshold
    alone is fooled by generic words like 'setting' — a nonsense question
    about a 'purple zebra setting' scored 0.097 in testing. Coverage fixes
    that class of false-answers. Found by test_task1, kept as a regression."""
    import re
    terms = [w for w in re.findall(r"[a-z]{4,}", question.lower()) if w not in _STOP]
    if not terms:
        return 1.0
    text = chunk_text.lower()
    return sum(1 for t in terms if t[:4] in text) / len(terms)


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest) -> QueryResponse:
    results = store.search(req.question, top_k=req.top_k)
    top = results[0]["score"] if results else 0.0
    coverage = term_coverage(req.question, results[0]["text"]) if results else 0.0
    sources = [Source(title=r["title"], url=r["url"], section=r["section"],
                      relevance=round(r["score"], 3), image_refs=r["image_refs"]) for r in results]
    # Two-tier abstention: coverage only gates MARGINAL retrievals. A strong
    # match (e.g. favicon email -> logo article at 0.21) answers even when the
    # customer's extra words ("ours looks blurry") dilute term coverage,
    # while nonsense with a generic-word match (0.097) still abstains.
    if not results or top < ABSTAIN_THRESHOLD or (top < 0.15 and coverage < 0.34):
        eid = store.create_escalation(
            req.question, context=f"top_score={top:.3f} threshold={ABSTAIN_THRESHOLD} coverage={coverage:.2f}")
        return QueryResponse(
            answer="I don't have enough information in the knowledge base to answer that reliably. "
                   "I've created a task for a human expert; their answer will be added to the knowledge base.",
            status="insufficient_evidence", sources=sources, confidence=round(top, 3),
            needs_human=True, escalation_id=eid)
    answer, mode = generate_answer(req.question, results)
    return QueryResponse(answer=answer, status="answered", sources=sources,
                         confidence=round(min(1.0, top), 3), model_mode=mode)


@app.post("/ingestion/run")
async def ingestion_run(req: IngestionRunRequest) -> dict:
    from ingestion.crawler import run_ingestion
    return await run_ingestion(req.sitemap_url, limit=req.limit, delay_seconds=req.delay_seconds)


@app.get("/ingestion/status")
def ingestion_status() -> dict:
    return store.stats()


@app.post("/escalations")
def create_escalation(req: EscalationCreate) -> dict:
    return {"id": store.create_escalation(req.question, req.reason, req.context), "status": "open"}


@app.get("/escalations")
def list_escalations() -> list[dict]:
    with store.get_db() as c:
        return [dict(r) for r in c.execute("SELECT * FROM escalations ORDER BY created_at DESC LIMIT 100")]


@app.post("/escalations/{eid}/resolve")
def resolve(eid: str, req: EscalationResolve) -> dict:
    if not store.resolve_escalation(eid, req.expert_answer, req.reviewer):
        raise HTTPException(404, "escalation not found")
    return {"id": eid, "status": "resolved", "indexed_as": f"expert-answer://{eid}"}


@app.get("/", response_class=HTMLResponse)
def chat_ui() -> str:
    return """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Knowledge Brain</title>
<style>body{font-family:system-ui,sans-serif;max-width:760px;margin:2rem auto;padding:0 1rem;color:#17202a}
textarea{width:100%;padding:.7rem}button{background:#14532d;color:#fff;border:0;padding:.7rem 1.2rem;border-radius:6px;cursor:pointer}
.card{background:#f4f6f5;border-radius:8px;padding:1rem;margin-top:1rem;white-space:pre-wrap}.esc{background:#fdf3e3}
a{color:#14532d}small{color:#666}</style></head><body>
<h1>🧠 Knowledge Brain</h1><p>Ask about the product. Answers cite their articles.
If the knowledge base doesn't know, it says so and escalates to a human — try asking something off-topic.</p>
<textarea id="q" rows="3" placeholder="e.g. How do I refund a member payment?"></textarea>
<p><button onclick="ask()">Ask</button> <small id="st"></small></p><div id="out"></div>
<p><small>API docs: <a href="/docs">/docs</a> · Health: <a href="/health">/health</a> ·
Escalations: <a href="/escalations">/escalations</a></small></p>
<script>
async function ask(){const q=document.getElementById('q').value.trim();if(!q)return;
document.getElementById('st').textContent='Searching knowledge base…';
try{const r=await fetch('/query',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q})});
const d=await r.json();document.getElementById('st').textContent='';
const src=d.sources.map(s=>`<li><a href="${s.url}" target="_blank" rel="noopener">${s.title}</a> — ${s.section} (relevance ${s.relevance})${s.image_refs.length?' · 🖼️ screenshot':''}</li>`).join('');
document.getElementById('out').innerHTML=`<div class="card ${d.needs_human?'esc':''}">${d.answer}
${src?'<h4>Sources</h4><ul>'+src+'</ul>':''}<small>Status: ${d.status} · confidence (retrieval): ${d.confidence} · mode: ${d.model_mode}${d.escalation_id?' · escalation: '+d.escalation_id:''}</small></div>`;
}catch(e){document.getElementById('st').textContent='Knowledge service unavailable — please retry. ('+e+')';}}
</script></body></html>"""
