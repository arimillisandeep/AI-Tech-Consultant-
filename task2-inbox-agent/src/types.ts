// Typed end to end (brief requirement). Task 1 shapes mirror task1/app/models.py.
export type Category =
  | "how_to" | "troubleshooting" | "project_request" | "refund_cancellation"
  | "complaint" | "quote_request" | "follow_up" | "unknown";

export type Risk = "low" | "moderate" | "high";

export interface CustomerEmail {
  id: string;
  from: string;
  subject: string;
  body: string;
  expectedCategory?: Category;   // dataset labels only; never used by the pipeline
  risk?: Risk;
}

export interface KbSource { title: string; url: string; section: string; relevance: number; image_refs: string[] }

export interface KbResponse {
  answer: string;
  status: "answered" | "insufficient_evidence";
  sources: KbSource[];
  confidence: number;
  needs_human: boolean;
  escalation_id: string | null;
  model_mode: string;
}

/** Structured output contract for every draft (schema-validated in drafter.ts). */
export interface DraftResult {
  emailId: string;
  category: Category;
  summary: string;
  suggestedReply: string;
  evidence: KbSource[];
  knowledgeStatus: "answered" | "insufficient_evidence" | "not_needed" | "kb_unavailable";
  risk: Risk;
  requiresHumanApproval: boolean;
  nextAction: string;
  promptVersion: string;
}

export interface FeedbackRecord {
  emailId: string;
  category: Category;
  generatedDraft: string;
  finalSent: string;
  outcome: "approved_unedited" | "edited_then_sent" | "rejected" | "escalated";
  reason: string;
  promptVersion: string;
  at: string;
}
