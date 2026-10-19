# Task 3 — Meeting to Scope of Work (Python)

5 agents (analyse → feasibility via Task 1 API → scope → estimate → proposal) + approved-baseline diffing + human-approval state machine. Nothing is sendable unapproved (API returns 409).

- `app/agents.py` pipeline · `app/diff.py` follow-up comparison · `app/main.py` API+UI · `transcripts/` 3 sample meetings (**replace with your own role-plays**) · `examples/` generated scopes/proposals
- Run: `python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8001`
- Offline demo: `python3 run_cli.py --demo` · Test: `python3 -m pytest tests/ -q` · Eval: `python3 evaluation/run_evals.py`
- Optional pricing: pass `hourly_rate` to `/process`; otherwise proposals show hours only.
