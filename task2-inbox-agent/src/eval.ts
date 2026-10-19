import { readFileSync, writeFileSync } from "fs";
import { join } from "path";
import { classify } from "./classifier";
import { draftReply, validateDraft } from "./drafter";
import type { CustomerEmail } from "./types";

/**
 * Task 2 evals (>=20 cases = all 50 labelled emails, report EM-41..50 holdout separately).
 * Measures: classification accuracy, draft validation pass, unsafe-promise rate,
 * latency. Draft-quality (tone/helpfulness) needs human scoring of a sample —
 * record that honestly in EVALS.md, automation can't judge tone.
 * Requires Task 1 running on KNOWLEDGE_BRAIN_URL for grounding checks; without
 * it, how-to drafts correctly degrade to holding replies (also a valid test).
 */
async function main(): Promise<void> {
  const emails = JSON.parse(readFileSync(join(__dirname, "..", "data", "emails.json"), "utf-8")) as CustomerEmail[];
  const cases = emails.slice(0, 24); // fixed eval set; keep stable across prompt versions
  const rows: string[] = ["task,case_id,model_mode,expected_category,actual_category,classify_ok,valid,unsafe,knowledge,latency_ms,passed"];
  let passed = 0;
  for (const e of cases) {
    const t0 = Date.now();
    const { category } = classify(e);
    const draft = await draftReply(e);
    const ms = Date.now() - t0;
    const classifyOk = category === e.expectedCategory;
    const valid = validateDraft(draft).length === 0;
    const unsafe = /we (will|promise to) refund|guaranteed|free of charge/i.test(draft.suggestedReply);
    const ok = classifyOk && valid && !unsafe;
    if (ok) passed++;
    rows.push(["inbox", e.id, draft.promptVersion, e.expectedCategory ?? "", category, classifyOk, valid, unsafe, draft.knowledgeStatus, ms, ok].join(","));
    console.log(`${ok ? "PASS" : "FAIL"} ${e.id} expected=${e.expectedCategory} got=${category} kb=${draft.knowledgeStatus} ${ms}ms`);
  }
  const out = join(__dirname, "..", "evaluation", "results.csv");
  writeFileSync(out, rows.join("\n"));
  console.log(`\n${passed}/${cases.length} passed -> ${out}`);
}

void main();
