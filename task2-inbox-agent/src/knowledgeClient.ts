import type { KbResponse } from "./types";

const KB_URL = process.env.KNOWLEDGE_BRAIN_URL ?? "http://127.0.0.1:8000";
const TIMEOUT_MS = 8000;

/**
 * The ONLY way Task 2 touches product knowledge: over Task 1's HTTP API.
 * Retries once on transient failure. On total failure returns null and the
 * caller must draft a holding reply — never a fabricated factual answer.
 */
export async function queryKnowledge(question: string): Promise<KbResponse | null> {
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
      const res = await fetch(`${KB_URL}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, top_k: 4 }),
        signal: ctrl.signal,
      });
      clearTimeout(timer);
      if (!res.ok) throw new Error(`KB HTTP ${res.status}`);
      return (await res.json()) as KbResponse;
    } catch {
      if (attempt === 1) return null;
      await new Promise((r) => setTimeout(r, 500));
    }
  }
  return null;
}
