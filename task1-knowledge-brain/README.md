# Task 1 — Knowledge Brain (Python)

Shared knowledge service. Tasks 2 & 3 use **only** its HTTP API (`shared-docs/API.md`).

- `app/main.py` FastAPI + chat UI · `app/store.py` SQLite + chunking + hybrid retrieval · `app/llm.py` Claude/extractive + vision · `ingestion/crawler.py` polite resumable sitemap ingestion · `daily_sync.py` daily freshness · `retrieval/` `multimodal/` readmes map to the code above.
- Run: `python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Ingest (start small): `python3 ingestion/crawler.py 20` · Test: `python3 -m pytest tests/ -q` · Eval: `python3 evaluation/run_evals.py`
- Ships with 10 seed articles for offline reproducibility; live-crawl Brilliant Directories to replace them (see EVALS.md §1).
