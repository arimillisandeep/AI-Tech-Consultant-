# Task 2 — Inbox Agent (TypeScript, strict)

Classify → query Task 1 API → structured draft → human approve/edit/reject → feedback → 20-consecutive-unedited autonomy eligibility (refunds/complaints never). Sending is **simulated** (idempotency-guarded) — documented in DESIGN.md.

- `src/classifier.ts` (v1.1, word-boundary + phrase weights) · `src/knowledgeClient.ts` (timeout+retry, the only KB path) · `src/drafter.ts` (draft policy + schema validation) · `src/feedback.ts` (learning loop + streaks) · `src/server.ts` (UI + API, Node builtins only)
- Build/run: `npm install && npm run build && KNOWLEDGE_BRAIN_URL=http://127.0.0.1:8000 npm start` (:3001)
- Data: `data/emails.json` — 50 labelled emails — extend by editing the JSON (keep IDs/categories stable) or add a TS generator under `src/`. Hold out EM-41…50.
- Test: `npm test` · Eval (Task 1 running): `npm run eval`
