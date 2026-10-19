# Completion audit — checked 2026-10-19 (re-run, not assumed)

Legend: ✅ done & verified today · 🟡 partial (works, with a stated gap) · ❌ not done.
Re-run results today: **T1 tests 7/7, evals 22/22 · T2 typecheck clean, tests 5/5, evals 24/24 · T3 tests 3/3, evals 22/22 · `./run.sh` cold-start 3/3 services + live T2→T1 and T3→T1 grounding.**

## Fixes made during this re-check
1. ❌→✅ Removed `task2/data/generate_emails.py` — a Python file inside the TypeScript task violated "do not mix languages in a task". `emails.json` is the dataset artefact.
2. ❌→✅ Converted `task2/tests/autonomy.test.js` → `src/autonomy.test.ts` so Task 2 is TypeScript end to end.
3. 🟡→✅ Added a permanent Task-1 test for ingestion **idempotency + update + removal** (previously only manually verified).
4. 🟡→✅ `./run.sh` one-command run tested from cold (previously services were started individually).

> **Re-verified 2026-10-19 (follow-up check):** Step 1 — file absent, zero `.py` under `task2-inbox-agent/` (excl. `node_modules`), `emails.json` = 50 unique labelled emails, no stale references. Step 2 — old `.js` test absent, `src/autonomy.test.ts` present, `tsc --noEmit` strict-clean, `npm test` 5/5 via compiled `dist/`. Step 3 — `test_ingestion_idempotent_update_and_removal` present and passing. All 3 services healthy after the changes.

## Task 1 — Knowledge Brain
| Instruction (brief) | Status | Evidence / gap |
|---|---|---|
| Read everything once, politely; batching, speed, stops-halfway | 🟡 | Rate Delay, retries+backoff, manifest checkpoint, hash idempotency (tested). **Full 1,540-article crawl NOT run** — proved on 5 real articles; sitemap 1,699→1,540 article URLs. Demo DB = 10 seed articles. |
| Understand images; know which article each belongs to | 🟡 | Pipeline + chunk linkage done; Claude-vision code present. **Real vision untested (no API key)**; offline = labelled alt-text+context. |
| Stay fresh daily; added/updated/removed; removed stops appearing | 🟡 | `daily_sync.py` + hash diff + deactivation (now unit-tested). **No cron actually installed**; full-run removal sweep on live site not yet exercised. |
| Chatbot: correct answer, show sources, honest "don't know" | ✅ (offline) | UI + 22/22 evals incl. abstention & injection cases. Claude-generated answers untested. |
| Clean API usable from documentation alone | ✅ | OpenAPI `/docs` + `shared-docs/API.md`; both downstream tasks consume only HTTP. |
| Can't answer → human task → expert answer flows back into memory | ✅ | Endpoint + re-indexing tested (`expert-answer://` URLs). |
| RAG with vector DB / embeddings (skills matrix) | 🟡 | RAG ✅; **no embedding model/vector DB** — TF-IDF hybrid with a documented seam. |

## Task 2 — Inbox Agent
| Instruction | Status | Evidence / gap |
|---|---|---|
| Understand each email kind; get facts via Task 1 API | ✅ | 7 categories; live draft shows KB evidence. |
| Draft in company voice; human sends/edits/writes own | 🟡 | UI approve/edit/reject works; **sending is simulated** (no real email integration); tone not yet human-scored. |
| Learns from edits; stored; prove better not worse | 🟡 | Feedback records + versioned prompts + rollback rule; classifier v1→v1.1 measured 19/24→24/24. **No feedback-driven prompt revision cycle run yet** (needs real review data — process is manual by design). |
| 20 same-kind unedited → may go out on its own; lose freedom on quality drop | 🟡 | Streak/eligibility/reset/never-autonomous implemented + tested. **Actual autonomous sending is NOT wired** — human must enable; drafts always carry `requiresHumanApproval`. Deliberate safety call, but there is no auto-send path to demo. |
| Write ≥50 realistic emails covering every kind | ✅ | 50 labelled (12/10/6/6/6/5/5). Personalise before submission; hidden emails will differ. |
| TypeScript strict, no language mixing | ✅ | `tsc --noEmit` clean after audit fixes 1–2. |

## Task 3 — Meeting to Scope
| Instruction | Status | Evidence / gap |
|---|---|---|
| Agent team with chosen roles & handoffs | ✅ | 5 agents, typed dataclasses, versioned contracts. |
| Produce scope + task/hour estimates + client proposal | ✅ | Generated examples in `examples/` (A: 9 reqs, 76 h likely; B: 23 h). |
| Check existing settings via Task 1 before custom work | ✅/🟡 | Live run: 9/9 requirements carry KB evidence; labels fall back to a documented offline map when KB evidence is ambiguous. |
| Follow-up meeting: show changed/new/out-of-scope | ✅ | C-vs-A: 2 added (price filter, booking, flagged out-of-scope), 1 removed (AI search), modified mobile/timeline. |
| Handle long transcripts well | 🟡 | Overlapping chunker + 61k-char stress test passes. **No real ~1-hour transcript tested**; samples are only 224–338 words. |
| Nothing reaches client until human approves | ✅ | 409 on unapproved send + 409 on diff-vs-draft (tests). |
| Role-play ≥3 meetings with a friend, record, use transcripts (1 = follow-up) | ❌ | 3 **written sample** transcripts exist as scaffolding. **You must role-play/record your own.** |
| Estimates a senior would trust | 🟡 | Explicit heuristic ranges; **no comparison vs a human estimator's numbers yet**. |

## Cross-cutting skills (brief matrix)
| Skill | Status | Note |
|---|---|---|
| Scraping/batching/scheduled jobs | 🟡 | Scheduler = script + cron instruction, not installed. |
| Images (multimodal) | 🟡 | See Task 1 images row. |
| Clean API design · Structured JSON · Human-in-loop & retries · Simple UIs | ✅ | All demonstrated live. |
| Tool calling & MCP | 🟡/❌ | KB-over-HTTP acts as the tool boundary; **no MCP server and no LLM tool-calling**. |
| Multi-agent | ✅ | Task 3 (core). |
| Routing across models | ❌ | Single `ANTHROPIC_MODEL` env; no routing until comparison numbers exist. |
| Evals quality/cost/speed (≥20/task) | 🟡 | Offline: complete with latency. **Claude quality/cost/speed: not measured.** |
| Self-improving prompts (measurable, undoable) | 🟡 | Versioning + measured classifier fix; feedback-loop revision not yet run on real feedback. |
| Long-context handling | 🟡 | Chunking yes; LLM long-context untested. |

## Rules & submission
| Requirement | Status | Evidence / gap |
|---|---|---|
| Claude at the centre | ❌ | Hooks + prompts ready (`app/llm.py`), but **running system is offline-deterministic until you add a key**. Biggest gap. |
| Every model choice justified with 20–30 evals; ≥2 models compared on quality/cost/speed | ❌ | Protocol + empty table in `EVALS.md §5` — **pending your API key**. |
| One AI coding tool only; full chat history shown | ❌ (yours) | This scaffold was built with an AI agent session, **not** Claude Code/Cursor. Do your continued development in one required tool and retain those threads. |
| GitHub repo, folder per task, one-command run, commits over 4 days | 🟡 | Structure ✅, `./run.sh` ✅ (verified today, after `./setup.sh`). **Zero commits so far; not pushed to GitHub.** |
| README ≤1 page | ✅ | 447 words. |
| DESIGN 3–5 pages, diagram, dropped features, model choices, what's next | 🟡 | Draft complete, 1,287 words (≈2.5–3 pp — expand slightly with *your* experience to sit safely in range). |
| EVALS 2–3 pages, ≥20 cases/task, model comparison with cost/speed | 🟡 | 1,163 words; offline numbers real; **model-comparison section pending**. |
| AI_LOG ≤1 page: 5 real prompts + 1 rejection | ❌ | **Template only — must come from your own sessions.** |
| Demo video ≤10 min, face first 30 s, all 3 tasks + one failure | ❌ | Not recorded. Script ready in `PREP_CHECKLIST.md`. |
| Live review (explain + live change) & hidden tests | 🟡 | Q&A + practice changes listed in `PREP_CHECKLIST.md`; safe-degradation behaviours (abstain/holding reply/409) verified. Unseen-data quality unknown until you run holdouts + full crawl. |

## Bottom line
- **Engineering skeleton: complete and re-verified** — all tests/evals green, one-command run works, three tasks genuinely integrated through the Task 1 API.
- **Not yet submittable as-is.** Blocking items, in order: ① Claude key → run model comparison + switch on generation/vision, ② full polite live crawl + fresh eval questions, ③ your own 3 recorded role-play transcripts, ④ AI_LOG from your real tool history + daily git commits + GitHub push, ⑤ demo video, ⑥ small calls: wire (or explicitly justify not wiring) an auto-send path behind the 20-streak, human tone-scoring of drafts, human reference estimate for Meeting A.
