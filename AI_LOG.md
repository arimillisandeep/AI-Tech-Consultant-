# AI_LOG

**Tool used:** Claude Code  
**Threads retained:** Stored in the original coding session (kept for live review).

## 5 Most Useful Prompts

### 1. "Force abstention design before any implementation"
> "Before writing retrieval/answer code for Task 1, define an explicit abstention policy: distinguish 'insufficient evidence' from 'unknown' and require both a score threshold and a non-generic term coverage check. Do not generate fluent answers when coverage is weak; return cited-only when supported, else abstain+escalate. Give me the decision table and a concrete failure case (e.g. 'secret purple zebra setting')."

**Why it helped / Kept vs changed:** This pushed the two-tier gate (score + distinctive-term coverage) early. I kept the coverage check as a hard gate for marginal scores and rewrote the failure path to create an escalation record instead of guessing. It prevented the exact hallucination later caught in KB-21.

### 2. "Make the crawler resumable, polite, and idempotent"
> "Design ingestion for the Brilliant Directories sitemap: rate-limiting/delay, checkpointing per URL, content-hash idempotency, resume after interruption, and deactivating removed pages so they stop appearing in answers. Treat index/section pages as noise to filter. Show the manifest schema and a kill-and-resume test plan."

**Why it helped / Kept vs changed:** Led to the manifest/checkpoint model, hash-based reprocess, and filtering 1,699 URLs to 1,540 article URLs (index pages polluted retrieval). I kept polite delays and resumability; only tweaked filtering rules after seeing actual sitemap structure.

### 3. "Define 'same kind' and 'without changing' precisely for the 20-email rule"
> "For Task 2 autonomy: define 'same kind' and 'without changing' with zero ambiguity. Require normalized text equality (not click-based), reset on edit/reject/escalate, never allow refunds/complaints, and treat emails as untrusted (no instruction injection). Provide the exact state transitions and unit tests."

**Why it helped / Kept vs changed:** Produced concrete policy (category = same kind; normalized draft vs sent = unedited). I kept hard bans and reset semantics exactly; added 'eligible for monitored trial' phrasing. This drove EM-14's boundary fix and the 5 autonomy tests.

### 4. "Diff follow-ups against the approved baseline only"
> "For Meeting C vs A, enforce: follow-up diffs must compare against the approved baseline (not last draft/AI output). Define explicit addition/removal/modification cues, flag new items as potentially out-of-scope, and estimate unclear 'maybe' items as discovery spikes only. Also block sending unapproved proposals with a 409. Give test cases that would catch scope creep."

**Why it helped / Kept vs changed:** Enforced baseline gate and out-of-scope flagging. I kept baseline-only comparison; adjusted removal matching after a false broad deletion. Discovery spikes only for unclear items prevented inflating firm hours from 'maybe' statements.

### 5. "Turn every real failure into an eval case"
> "Whenever a failure is found (abstention leak, false keyword match like customers/custom, over-broad diff removal), convert it to a minimal eval case before fixing, record both versions (before/after), and ensure the fix is guarded by that case. Include failure reason + expected behavior."

**Why it helped / Kept vs changed:** Disciplined v1->v1+fixes progression (KB 21/22, Inbox 19/24->24/24, Scope 17/22->22/22). Never deleted failing cases; recorded fixes with case IDs to prevent regressions.

## One Time I Rejected the AI's Answer

**What the AI suggested:** A single global TF-IDF similarity threshold for abstention without checking for distinctive terms. Also suggested click-based 'approved' could count as unedited for autonomy.

**Why I rejected it:** Off-topic questions like 'secret purple zebra setting' could score high enough to produce fluent unsupported answers. Click-based approval would falsely count edited drafts as unedited, enabling unsafe autonomous sends.

**What I did instead, and how I verified it:** Added two-tier gate (threshold + distinctive-term coverage), enforced normalized draft-vs-sent equality with hard resets and bans (refunds/complaints never eligible). Verified via KB-21, EM-14, and the 5 autonomy unit tests — all pass and guard regressions.
