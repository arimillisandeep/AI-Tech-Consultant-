import { existsSync, mkdirSync, readFileSync, writeFileSync } from "fs";
import { join } from "path";
import { NEVER_AUTONOMOUS } from "./classifier";
import type { Category, FeedbackRecord } from "./types";

/**
 * Learning loop + the 20-consecutive-unedited rule.
 *
 * Definitions (decided explicitly, as the brief demands):
 * - "Same kind"     = same Category from classifier.ts.
 * - "Without changing" = final sent text equals generated draft after
 *   normalising whitespace. Clicking Approve is NOT enough; we diff text.
 * - Streak resets on any edit, rejection, escalation or validation failure.
 * - 20 = ELIGIBLE for a controlled trial, not proof of safety.
 * - refund_cancellation + complaint are NEVER autonomous at any streak.
 * - Autonomy is a per-category flag a human flips; any edited draft while
 *   autonomous immediately revokes it (kill-switch by construction).
 * Learning = weekly review of edited pairs -> prompt/template revision ->
 * re-run fixed eval set -> keep or roll back. No silent self-modification.
 */
const DIR = join(__dirname, "..", "data");
const FILE = join(DIR, "feedback.json");
const THRESHOLD = 20;

export function normalise(s: string): string {
  return s.replace(/\s+/g, " ").trim().toLowerCase();
}

export function loadFeedback(): FeedbackRecord[] {
  if (!existsSync(FILE)) return [];
  try { return JSON.parse(readFileSync(FILE, "utf-8")) as FeedbackRecord[]; } catch { return []; }
}

export function recordFeedback(rec: FeedbackRecord): void {
  mkdirSync(DIR, { recursive: true });
  const all = loadFeedback();
  all.push(rec);
  writeFileSync(FILE, JSON.stringify(all, null, 2));
}

export function outcomeFor(generated: string, finalSent: string, rejected: boolean): FeedbackRecord["outcome"] {
  if (rejected) return "rejected";
  return normalise(generated) === normalise(finalSent) ? "approved_unedited" : "edited_then_sent";
}

export function streakFor(category: Category, records = loadFeedback()): number {
  let streak = 0;
  for (const r of records.filter((x) => x.category === category)) {
    streak = r.outcome === "approved_unedited" ? streak + 1 : 0;
  }
  return streak;
}

export function autonomyStatus(): Record<string, { streak: number; eligible: boolean; reason: string }> {
  const out: Record<string, { streak: number; eligible: boolean; reason: string }> = {};
  const cats: Category[] = ["how_to", "troubleshooting", "project_request", "refund_cancellation", "complaint", "quote_request", "follow_up", "unknown"];
  for (const c of cats) {
    const streak = streakFor(c);
    if (NEVER_AUTONOMOUS.has(c)) out[c] = { streak, eligible: false, reason: "high-risk category: human always reviews" };
    else if (streak >= THRESHOLD) out[c] = { streak, eligible: true, reason: `${THRESHOLD}+ consecutive unedited sends; human may enable a monitored trial` };
    else out[c] = { streak, eligible: false, reason: `${streak}/${THRESHOLD} consecutive unedited sends` };
  }
  return out;
}
