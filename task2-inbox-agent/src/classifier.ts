import type { Category, CustomerEmail, Risk } from "./types";

/**
 * Classifier v1.1: deterministic keyword scoring. Deliberately boring and
 * auditable for the live review. The interface is the seam where a Claude
 * classifier plugs in; EVALS compares the two on identical cases before
 * any swap (routing decision = measured, not assumed).
 *
 * v1 -> v1.1 changes, each from a measured eval failure (see EVALS.md):
 * - Word-boundary matching: v1 used substring includes(), so "customers"
 *   matched the project keyword "custom" (EM-14 spam email misrouted).
 * - Phrases weigh 2, single words 1: "can't find the Refund button" is
 *   troubleshooting, not a refund request, despite containing "refund".
 * - Added failing/expires/can't-find patterns from EM-13/EM-19/EM-22.
 * Rule order still breaks remaining ties conservatively (money/safety first).
 */
const RULES: Array<{ cat: Category; risk: Risk; words: string[] }> = [
  { cat: "refund_cancellation", risk: "high", words: ["refund", "cancel", "money back", "chargeback", "unsubscribe my plan", "close my account"] },
  { cat: "complaint", risk: "high", words: ["complaint", "unacceptable", "angry", "frustrated", "broke our", "broken since", "terrible", "disappointed", "lawyer", "legal"] },
  { cat: "quote_request", risk: "moderate", words: ["how much", "quote", "price for", "cost to", "pricing for", "estimate for"] },
  { cat: "project_request", risk: "moderate", words: ["can you build", "add a feature", "new feature", "develop", "custom", "we want a", "we need a"] },
  { cat: "follow_up", risk: "low", words: ["follow up", "following up", "any update", "did you receive", "still waiting", "previous email", "last week i wrote"] },
  { cat: "troubleshooting", risk: "moderate", words: ["not working", "error", "fails", "failed", "failing", "can't log in", "cannot log in", "can't find", "cannot find", "stopped", "spam", "locked", "expires", "expired"] },
  { cat: "how_to", risk: "low", words: ["how do i", "how to", "where do i", "can i change", "steps to", "how can i"] },
];

function matches(text: string, phrase: string): boolean {
  const escaped = phrase.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`\\b${escaped}\\b`).test(text);
}

export function classify(email: CustomerEmail): { category: Category; risk: Risk } {
  const text = `${email.subject}\n${email.body}`.toLowerCase();
  let best: { category: Category; risk: Risk; score: number } = { category: "unknown", risk: "moderate", score: 0 };
  for (const rule of RULES) {
    const score = rule.words.reduce((acc, w) => acc + (matches(text, w) ? (w.includes(" ") ? 2 : 1) : 0), 0);
    if (score > best.score) best = { category: rule.cat, risk: rule.risk, score };
  }
  return { category: best.category, risk: best.risk };
}

export const CLASSIFIER_VERSION = "classifier-v1.1";

/** High-risk categories NEVER become autonomous, regardless of streak length. */
export const NEVER_AUTONOMOUS: ReadonlySet<Category> = new Set(["refund_cancellation", "complaint"]);
