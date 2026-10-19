# DESIGN — AI Tech Consultant

## 1. The problem in one paragraph

Code got cheap; everything around code did not. A small software company still pays people to (a) find answers buried in hundreds of help articles — often inside screenshots, (b) read, research and reply to every customer email, and (c) turn a vague client meeting (“make search better”) into a scope, an estimate and a proposal. Those three jobs cap growth at whatever a few good consultants can do by hand. The AI Tech Consultant attacks all three with **one shared knowledge service**: product knowledge is expensive to build and keep fresh, so it is built once (Task 1) and reused by the inbox (Task 2) and the scoping team (Task 3) over an API. Any software/service business should be able to swap in its own help centre, inbox and transcripts.

## 2. Architecture

```
                ┌─────────────────────────────────────────────────┐
                │  TASK 1 · Knowledge Brain (Python/FastAPI :8000)│
                │  sitemap crawl → parse+vision → chunk → index  │
                │  POST /query (answer+citations|abstain)         │
                │  POST /ingestion/run · GET /ingestion/status    │
                │  POST /escalations → expert answer re-indexed   │
                │  daily_sync: add/update/deactivate-removed      │
                └──────────────▲──────────────────▲───────────────┘
                        HTTP API │                  │ HTTP API
              ┌──────────────────┴───────┐ ┌────────┴──────────────────┐
              │ TASK 2 · Inbox (TS:3001) │ │ TASK 3 · Scope (Py :8001) │
              │ classify → KB → draft →  │ │ 5 agents: analyse →       │
              │ human review → feedback →│ │ feasibility(KB) → scope → │
              │ 20-unedited autonomy rule│ │ estimate → proposal →     │
              │                          │ │ approve → follow-up diff  │
              └──────────────────────────┘ └───────────────────────────┘
   Shared: versioned prompts (prompts/) · structured outputs · retries/timeouts ·
   human approval gates · eval sets per task · offline fallbacks (no key needed)
```

**Why one API, not shared code:** the brief's reusability test. Tasks 2/3 import nothing from Task 1; `task2/src/knowledgeClient.ts` and Task 3's feasibility agent speak only HTTP. A knowledge update (or an expert escalation answer) improves both downstream apps with zero redeploys. The cost — network failure modes — is handled explicitly: Task 2 drafts an honest holding reply when the KB is down; it never fabricates facts.

## 3. Key design decisions (and why)

**Task 1.** SQLite over Postgres+pgvector for a 4-day build: zero-ops, one file, and the retrieval seam (`store.search`) is where a real embedding model plugs in. Retrieval is hybrid TF-IDF + keyword boost offline; the `EmbeddingProvider` seam is where Voyage (Anthropic's recommended pairing) or similar drops in. We say plainly: TF-IDF is a fallback with known vocabulary limits, not a quality claim. Chunking is heading-aware so procedures stay intact; screenshot descriptions are indexed as text tied to their article/section (Claude vision when a key exists, labelled alt-text+context offline). **Abstention is a retrieval decision, not a model mood:** two-tier gate — score threshold plus, for marginal matches, distinctive-term coverage. This was tuned against real failures (EVALS.md). The crawler is rate-limited, checkpointed in a manifest table, idempotent by content hash, and filters the live sitemap's 1,699 URLs down to its 1,540 article URLs (index pages pollute retrieval — found by actually crawling). Removals deactivate chunks so deleted articles stop being cited. Expert answers are indexed under `expert-answer://` URLs: usable, but never disguised as official docs.

**Task 2.** Classifier v1 is deterministic keyword scoring — boring on purpose: every routing decision is explainable in a live review, and it gives a free baseline a Claude classifier must *beat on the same cases* before replacing it. Drafting policy is the safety core: factual claims only from Task-1 `answered` responses; refund/quote drafts never promise money, dates or prices (`validateDraft` blocks them); email bodies are untrusted data, never instructions. **“Same kind” = classifier category; “without changing” = normalised text equality between draft and sent** (clicking Approve after editing does not count). Streaks reset on any edit/reject/escalate; 20 makes a category *eligible for a monitored trial*, a human flips the switch, and refunds/complaints are never eligible at any streak. Learning is a weekly human loop over recorded draft→sent pairs → prompt/template revision → re-run fixed eval set → keep or roll back. The system never silently rewrites itself.

**Task 3.** Five agents because there are five jobs a senior consultant separates: extract (client words only — consultant lines never create scope), check feasibility against the KB *before* quoting custom work (existing configuration / existing-with-limitation / potential custom / needs clarification — a KB miss is *never* proof a feature doesn't exist), write scope (acceptance criteria + exclusions + open questions), estimate (low/likely/high from an explicit, challengeable table; unclear “maybe” items get only a discovery spike, never firm hours), and draft the proposal. Prices need a human-set hourly rate; without one the proposal shows hours only. Approval is a state machine (`draft → approved_baseline → sent`); the API returns 409 on any attempt to send a draft, and follow-up diffs compare only against *approved* baselines — an unapproved AI suggestion can never sneak into commitments. Diff matching puts explicit client signals first (“one more…”, “drop the AI search”) and flags everything new as potentially out-of-scope for a separate quote.

## 4. Model choices — decided by evals, not adjectives

Claude is the centre when a key is present (`ANTHROPIC_MODEL`, default `claude-sonnet-4-5`): answer generation + vision (Task 1), and the documented seams in Tasks 2/3. **Honest status: this build was developed and measured without an API key**, so the shipped numbers in EVALS.md are for the offline deterministic mode. The model-comparison protocol is ready and must be run before submission: same frozen cases, `ANTHROPIC_MODEL=claude-haiku-4-5` vs `claude-sonnet-4-5`, record quality + p50/p95 latency + cost/call, then route cheap/fast where quality ties (hypothesis: Haiku for email classification, Sonnet for transcript analysis — a hypothesis, not a result). Routing code changes only after numbers exist. Every prompt is versioned in `prompts/`; a version bump requires re-running that task's eval set.

## 5. What I dropped (and why)

- **Real email sending / Gmail integration** — simulated send with an idempotency guard; SMTP plumbing eats a day and demonstrates nothing about judgement. Documented in UI + API response.
- **Knowledge graphs, rerankers, fine-tuning, multi-tenant auth** — unmeasurable within 4 days; each has a named seam instead of a half-build.
- **Calendar/timeline auto-scheduling from estimates** — hours→dates invents commitments. Humans own dates.
- **Auto-retraining / self-editing prompts** — unsafe and unauditable; weekly reviewed revisions instead.
- **Full 1,540-article crawl in the default demo DB** — ships with 10 seed articles modelled on the help centre so evals are reproducible offline; the live crawler is proven on real articles and one command away. *(Before final submission, run the full polite crawl and re-run Task 1 evals against it.)*

## 6. What breaks / known limits

1. TF-IDF misses paraphrases (“size” vs “32×32”); some genuine questions abstain and escalate. Safe, but it caps recall until embeddings land.
2. Keyword classification/extraction will misread novel phrasing in hidden emails/transcripts — e.g. it extracts the fragment “Customers keep asking for it” as a requirement. The approval UI exists partly for this.
3. Estimates are heuristic v1 ranges, uncalibrated against delivered actuals. They are decision support, not quotes.
4. Vision in offline mode is alt-text + context, clearly labelled — a screenshot whose answer exists only in pixels needs the Claude key.
5. Single-file/SQLite stores suit one team instance, not concurrent multi-tenant production.

## 7. What I would build next

(1) Full live crawl + embeddings + reranking, re-measured on a held-out question set written from *real* articles; (2) run the Haiku-vs-Sonnet comparison and set routing by data; (3) calibrate estimation against completed projects and report error %; (4) real inbox integration (IMAP/Gmail) behind the same review UI; (5) per-business onboarding: point Tasks 1–3 at a different help centre and prove the “any business” claim on a second product.
