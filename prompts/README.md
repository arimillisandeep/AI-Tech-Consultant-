# Versioned prompts

Rule: **any prompt change = version bump in code + file here + re-run that task's eval set + note result in EVALS.md.** If quality regresses, roll back — the old file stays.

| Version string (in API responses / feedback records) | File | Used by |
|---|---|---|
| `kb-answer-v1` | `task1/kb-answer-v1.md` | Task 1 Claude answer generation (`app/llm.py`) |
| `inbox-draft-v1` (+ `classifier-v1.1`) | `task2/inbox-draft-v1.md` | Task 2 drafting policy (`src/drafter.ts`) |
| `scope-pipeline-v1` | `task3/scope-pipeline-v1.md` | Task 3 agent contracts (`app/agents.py`) |

Offline mode implements the same policies deterministically, so evals measure the *policy* even without an API key.
