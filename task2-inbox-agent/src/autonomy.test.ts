import { test } from "node:test";
import assert from "node:assert";
import { streakFor, outcomeFor } from "./feedback";
import { classify, NEVER_AUTONOMOUS } from "./classifier";
import type { FeedbackRecord } from "./types";

/** Compiled by the normal TS build; run with `node --test dist/autonomy.test.js`
 *  via `npm test`. (Was a plain-JS file — converted on audit so Task 2 is
 *  TypeScript end to end, as the brief requires.) */

const rec = (outcome: FeedbackRecord["outcome"]): FeedbackRecord => ({
  emailId: "T", category: "how_to", generatedDraft: "x", finalSent: "x",
  outcome, reason: "", promptVersion: "t", at: "2026-10-19",
});

test("20 consecutive unedited sends reach the threshold", () => {
  const recs = Array.from({ length: 20 }, () => rec("approved_unedited"));
  assert.equal(streakFor("how_to", recs), 20);
});

test("one edit resets the streak to zero", () => {
  const recs = [...Array.from({ length: 20 }, () => rec("approved_unedited")), rec("edited_then_sent")];
  assert.equal(streakFor("how_to", recs), 0);
});

test("unedited = normalised text equality, not the approve click", () => {
  assert.equal(outcomeFor("Hello  world", "hello world", false), "approved_unedited");
  assert.equal(outcomeFor("Hello world", "Hello there world", false), "edited_then_sent");
  assert.equal(outcomeFor("x", "x", true), "rejected");
});

test("refunds and complaints are never autonomous", () => {
  assert.ok(NEVER_AUTONOMOUS.has("refund_cancellation") && NEVER_AUTONOMOUS.has("complaint"));
});

test("word-boundary matching: 'customers' is not a custom project (EM-14 regression)", () => {
  const c = classify({
    id: "T", from: "a@b.c", subject: "Emails going to spam",
    body: "Order emails land in spam for most customers",
  });
  assert.equal(c.category, "troubleshooting");
});
