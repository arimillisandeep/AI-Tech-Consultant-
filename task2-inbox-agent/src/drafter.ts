import { classify, NEVER_AUTONOMOUS } from "./classifier";
import { queryKnowledge } from "./knowledgeClient";
import type { CustomerEmail, DraftResult } from "./types";

export const PROMPT_VERSION = "inbox-draft-v1"; // bump + re-run evals on change (prompts/task2/)

/**
 * Drafting policy (the safety core of Task 2):
 * - Factual product claims come ONLY from a Task 1 'answered' response.
 * - Refunds/quotes/projects: KB facts may inform, but the draft never
 *   promises money, dates or scope. A human owns commercial commitments.
 * - KB unavailable / insufficient evidence  ->  honest holding reply + escalation flag.
 * - Email text is untrusted input: it is data for classification/drafting,
 *   never instructions that can change these rules.
 * With ANTHROPIC_API_KEY, replace the template bodies with a Claude call that
 * returns the same DraftResult JSON schema; validate with validateDraft().
 */
export function validateDraft(d: DraftResult): string[] {
  const errs: string[] = [];
  if (!d.suggestedReply || d.suggestedReply.length < 20) errs.push("reply too short");
  if (!d.category) errs.push("missing category");
  if (d.knowledgeStatus === "answered" && d.evidence.length === 0) errs.push("answered without evidence");
  if (/we (will|promise to) refund/i.test(d.suggestedReply)) errs.push("unauthorised refund promise");
  if (/\$\s?\d/.test(d.suggestedReply) && d.category === "quote_request") errs.push("unapproved price in quote draft");
  return errs;
}

const NEEDS_KB = new Set(["how_to", "troubleshooting", "refund_cancellation"]);

export async function draftReply(email: CustomerEmail): Promise<DraftResult> {
  const { category, risk } = classify(email);
  const name = (email.from.split("@")[0] ?? "there").replace(/[._-]+/g, " ");
  let reply = "";
  let knowledgeStatus: DraftResult["knowledgeStatus"] = "not_needed";
  let evidence: DraftResult["evidence"] = [];
  let nextAction = "Human review, then send.";

  if (NEEDS_KB.has(category)) {
    const kb = await queryKnowledge(`${email.subject}. ${email.body.slice(0, 500)}`);
    if (kb === null) {
      knowledgeStatus = "kb_unavailable";
      reply = `Hi ${name},\n\nThanks for writing in. I've received your message about "${email.subject}" and a member of our support team will reply with the details shortly. I didn't want to guess at an answer without checking our product documentation first.\n\nBest regards,\nSupport Team`;
      nextAction = "Knowledge service unavailable: retry later or answer manually. Do not send factual claims.";
    } else if (kb.status !== "answered") {
      knowledgeStatus = "insufficient_evidence";
      reply = `Hi ${name},\n\nThanks for writing in about "${email.subject}". I don't have a verified answer for this in our help centre yet, so I've passed it to a specialist who will reply directly. Case reference: ${kb.escalation_id ?? "pending"}.\n\nBest regards,\nSupport Team`;
      nextAction = `Escalated to human expert (${kb.escalation_id ?? "see Task 1"}).`;
    } else {
      knowledgeStatus = "answered";
      evidence = kb.sources;
      const top = kb.sources[0];
      const facts = kb.answer.replace(/^Based on the knowledge base:\n?/, "").trim();
      if (category === "refund_cancellation") {
        reply = `Hi ${name},\n\nI'm sorry to hear you'd like to cancel. Here's how refunds and cancellations work according to our help centre:\n\n${facts}\n\nI've flagged your account for our billing team, who will confirm the exact next step for your specific payment before anything is processed.\n\nBest regards,\nSupport Team`;
        nextAction = "Billing team must confirm eligibility before any refund is processed. Never auto-send.";
      } else {
        reply = `Hi ${name},\n\nThanks for writing in. Here's what our help centre says:\n\n${facts}\n\nFull guide: ${top ? `${top.title} — ${top.url}` : "see help centre"}\n\nIf anything looks different on your screen, reply with a screenshot and we'll walk through it step by step.\n\nBest regards,\nSupport Team`;
      }
    }
  } else if (category === "complaint") {
    reply = `Hi ${name},\n\nI'm really sorry about this — I understand the frustration. I've escalated your message to a senior support specialist as a priority, and they'll reply personally. To help them move fast, could you share when this started and any error message you saw?\n\nBest regards,\nSupport Team`;
    nextAction = "Senior specialist responds personally. Never auto-send complaint replies.";
  } else if (category === "quote_request" || category === "project_request") {
    reply = `Hi ${name},\n\nThanks for describing what you'd like to build. So we can scope it properly (and check whether existing product settings already cover part of it, which usually costs far less than custom work), a consultant will review and reply with next steps and any clarifying questions.\n\nBest regards,\nSupport Team`;
    nextAction = "Route to Meeting-to-Scope (Task 3) for scope + estimate. Do not quote a price from the inbox.";
  } else if (category === "follow_up") {
    reply = `Hi ${name},\n\nThanks for following up — I can see your earlier message and I've bumped it for the team member handling it. You should hear from us directly. Sorry for the wait.\n\nBest regards,\nSupport Team`;
    nextAction = "Attach to original thread; owner replies with status.";
  } else {
    reply = `Hi ${name},\n\nThanks for writing in about "${email.subject}". I've passed your message to the right team member, who will reply shortly.\n\nBest regards,\nSupport Team`;
    nextAction = "Unclassified: human triage required.";
  }

  const draft: DraftResult = {
    emailId: email.id, category,
    summary: `${category.replace(/_/g, " ")} — ${email.subject}`.slice(0, 140),
    suggestedReply: reply, evidence, knowledgeStatus, risk,
    requiresHumanApproval: true, // autonomy is decided by feedback.ts streak, never here
    nextAction, promptVersion: PROMPT_VERSION,
  };
  const errs = validateDraft(draft);
  if (errs.length > 0) draft.nextAction = `BLOCKED by validation: ${errs.join("; ")}`;
  if (NEVER_AUTONOMOUS.has(category)) draft.nextAction += " [Category is never eligible for auto-send.]";
  return draft;
}
