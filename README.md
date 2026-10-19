# AI Tech Consultant

One system for a software/service business: it **knows the product** (Task 1), **handles the inbox** (Task 2), and **turns meetings into scopes** (Task 3). Tasks 2 and 3 never copy Task 1 — they call its API, so any business can plug in its own help centre later.

| Task | Folder | Language | Runs on |
|---|---|---|---|
| 1 · Knowledge Brain (RAG + screenshots + daily sync + API) | `task1-knowledge-brain/` | Python (FastAPI) | http://localhost:8000 (UI `/`, docs `/docs`) |
| 2 · Inbox Agent (classify → grounded draft → human review → learns) | `task2-inbox-agent/` | TypeScript strict (Node) | http://localhost:3001 |
| 3 · Meeting to Scope (5 agents → scope, estimates, proposal, diff) | `task3-meeting-to-scope/` | Python (FastAPI) | http://localhost:8001 |

## Run it (one command)

```bash
./setup.sh   # first time only: installs Python + Node deps, builds Task 2
./run.sh     # starts all three services; Ctrl-C stops everything
```

Then open the three URLs above. No API key is needed: the system runs in an honest offline mode (TF-IDF retrieval + extractive answers for Task 1, deterministic classifier/heuristic agents for Tasks 2–3). Add a key to switch on Claude generation/vision without code changes:

```bash
cp .env.example .env   # set ANTHROPIC_API_KEY, ANTHROPIC_MODEL (e.g. claude-sonnet-4-5)
```

## Try the three demos in 3 minutes

1. **:8000** — ask “How do I refund a member payment?” (cited answer), then “Book me a flight to Tokyo?” (honest “don't know” + human escalation created).
2. **:3001** — pick email EM-03 → *Draft reply* (grounded via Task 1) → edit → *Approve*. Watch autonomy streaks at the bottom (20 unedited of a kind = eligible; refunds/complaints never).
3. **:8001** — paste `task3-meeting-to-scope/transcripts/meeting_a_website_search.txt` → scope + estimates + proposal. Approve it, then paste `meeting_c_followup.txt` with that project ID → added/removed/out-of-scope diff.

Offline Task 3 demo (no servers): `cd task3-meeting-to-scope && python run_cli.py --demo`

## Test & evaluate

```bash
cd task1-knowledge-brain  && python -m pytest tests/ -q && python evaluation/run_evals.py
cd task2-inbox-agent      && npm test && KNOWLEDGE_BRAIN_URL=http://127.0.0.1:8000 npm run eval
cd task3-meeting-to-scope && python -m pytest tests/ -q && python evaluation/run_evals.py
```

Live crawl (start small — polite, resumable): `POST :8000/ingestion/run {"limit":20,"Delay_seconds":1}` or `python task1-knowledge-brain/ingestion/crawler.py 20`. Daily freshness: `task1-knowledge-brain/daily_sync.py` (cron example inside).

## Docs

- **DESIGN.md** — why it is built this way, what was dropped, model choices, limits.
- **EVALS.md** — 22+ cases per task, measured quality/latency/cost, failures found & fixed.
- **AI_LOG.md** — template for your 5 real AI-coding prompts + one rejection (**you must fill this in yourself**).
- **shared-docs/PREP_CHECKLIST.md** — 4-day plan, 10-minute demo script, live-review questions.
- **shared-docs/API.md** — the Task 1 contract Tasks 2 & 3 use.
