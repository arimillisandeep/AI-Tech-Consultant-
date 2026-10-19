# Knowledge Brain API — the contract Tasks 2 & 3 build against

Base URL: `KNOWLEDGE_BRAIN_URL` (default `http://127.0.0.1:8000`) · Interactive docs: `/docs` (OpenAPI) · Types: `task1-knowledge-brain/app/models.py`

## `POST /query`
```json
→ { "question": "How do I refund a member payment?", "top_k": 4 }
← { "answer": "…", "status": "answered" | "insufficient_evidence",
    "sources": [{ "title": "…", "url": "…", "section": "…", "relevance": 0.31, "image_refs": ["…"] }],
    "confidence": 0.31,          // retrieval strength, NOT a probability of correctness
    "needs_human": false, "escalation_id": null, "model_mode": "extractive-fallback:kb-answer-v1" }
```
Rules for callers:
- `insufficient_evidence` ⇒ **do not** present `answer` as product facts; use a holding/escalation path. An escalation has already been created (`escalation_id`).
- Cite `sources` whenever you use the answer (Task 2 shows them to the reviewer; Task 3 stores them as evidence).
- `422` on questions shorter than 3 chars; treat network timeout like `insufficient_evidence`, never like an answer.

## Ingestion
- `POST /ingestion/run` `{ "sitemap_url": "…/sitemap.xml", "limit": 20, "delay_seconds": 1.0 }` → `{new, updated, unchanged, failed, removed, total_sitemap, article_urls}`. Limited runs never deactivate removals; full runs (daily sync) do.
- `GET /ingestion/status` → article/chunk/escalation counts.

## Human escalations (the self-improving loop)
- `POST /escalations` `{question, reason, context}` → `{id}` (also auto-created by `/query` abstentions).
- `GET /escalations` → recent tasks for the expert queue.
- `POST /escalations/{id}/resolve` `{expert_answer, reviewer}` → answer is indexed under `expert-answer://{id}` so future queries can find it, labelled as expert-contributed.

## `GET /health` → `{status:"ok", active_articles, active_chunks, open_escalations, …}`

**Versioning:** response shape is the contract. Add fields freely; never rename/remove existing ones without bumping clients (Tasks 2/3) in the same commit.
