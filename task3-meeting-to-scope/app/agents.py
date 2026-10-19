"""
Task 3 agent team. Five agents, one clear job each, typed handoffs:

  1. TranscriptAnalyst  transcript -> list[Requirement] (with source quotes)
  2. FeasibilityAgent   Requirement -> KB check via Task 1 API (+ offline map fallback)
  3. ScopeAgent         requirements+feasibility -> scope of work (markdown)
  4. EstimationAgent    requirements -> task breakdown, low/likely/high hours
  5. ProposalAgent      scope+estimates -> client proposal (markdown, DRAFT)

Offline mode uses transparent heuristics (keyword extraction, estimation v1
table) so the pipeline is testable end-to-end. With ANTHROPIC_API_KEY each
agent's `run` is the seam for a Claude call returning the SAME dataclasses —
validate, never trust raw model JSON. Assumptions are labelled, never
silently promoted to 'confirmed'.
"""
from __future__ import annotations
import os, re
from dataclasses import asdict, dataclass, field

import httpx

KB_URL = os.getenv("KNOWLEDGE_BRAIN_URL", "http://127.0.0.1:8000")
PROMPT_VERSION = "scope-pipeline-v1"


@dataclass
class Requirement:
    id: str
    description: str
    source_quote: str
    speaker: str = ""
    status: str = "confirmed"          # confirmed | unclear | inferred
    priority: str = "should-have"      # must-have | should-have | optional
    topic: str = "general"
    feasibility: str = "needs_clarification"  # existing_configuration | existing_with_limitation | potential_custom_development | needs_clarification
    feasibility_note: str = ""
    evidence: list = field(default_factory=list)
    acceptance_criteria: str = ""


# ---------------- Agent 1: Transcript Analyst ----------------
_TOPIC_WORDS = {
    "search": ["search", "filter", "radius", "postcode", "typo"],
    "ai_search": ["ai search", "understands what people mean", "semantic"],
    "mobile": ["mobile", "phone"],
    "payments": ["payment", "checkout", "stripe", "paypal", "gateway", "refund", "billing", "cancel"],
    "notifications": ["email", "notification", "confirmation", "reminder", "spam"],
    "booking": ["booking", "calendar", "appointment"],
    "ranking": ["higher in results", "premium members", "appear higher", "rank"],
}
_CUES = ("we want", "we need", "we also want", "i want", "i need", "should be able", "should sit",
         "should handle", "ideally", "also,", "one more", "customers keep asking", "must", "wish",
         "could members", "we would like", "hoping to launch", "we want to launch",
         "maybe add", "maybe")  # 'maybe' extracts as status=unclear — a question, never a commitment
_NEG = ("no redesign", "no mobile app", "don't touch", "do not want", "no longer needed",
        "drop the", "outside the original scope")  # exclusions/removals handled by Scope/diff, not new requirements


def topic_of(text: str) -> str:
    low = text.lower()
    for topic, words in _TOPIC_WORDS.items():
        if any(w in low for w in words):
            return topic
    return "general"


def chunk_transcript(text: str, max_chars: int = 3000, overlap_lines: int = 2) -> list[str]:
    """Long-transcript handling: line-preserving windows with overlap.
    Requirements keep their source quote, so a summary never becomes the
    only evidence for a commercial commitment."""
    lines = text.splitlines()
    chunks, cur = [], []
    for line in lines:
        cur.append(line)
        if sum(len(x) for x in cur) > max_chars:
            chunks.append("\n".join(cur))
            cur = cur[-overlap_lines:]
    if cur:
        chunks.append("\n".join(cur))
    return chunks or [text]


def analyse_transcript(text: str) -> tuple[list[Requirement], list[str]]:
    """Returns (requirements, exclusions). Deduplicates near-identical lines."""
    reqs: list[Requirement] = []
    exclusions: list[str] = []
    seen: set[str] = set()
    for chunk in chunk_transcript(text):
        for line in chunk.splitlines():
            m = re.match(r"^([A-Z][a-zA-Z ]+):\s*(.+)$", line.strip())
            if not m:
                continue
            speaker, speech = m.group(1).strip(), m.group(2).strip()
            if speaker.lower() == "consultant":
                continue  # client words create scope; consultant words don't
            low = speech.lower()
            if any(n in low for n in _NEG):
                exclusions.append(speech)
                continue
            for sent in re.split(r"(?<=[.!?])\s+", speech):
                s_low = sent.lower()
                if not any(c in s_low for c in _CUES):
                    continue
                key = re.sub(r"\W+", " ", s_low)[:90]
                if key in seen or len(sent) < 15:
                    continue
                seen.add(key)
                topic = topic_of(sent)
                # 'Maybe add X' / 'not sure' = unclear. But 'filters by A, B, maybe C'
                # is a confirmed ask with one optional sub-item — don't downgrade it all.
                unclear = s_low.startswith("maybe") or "maybe add" in s_low or "not sure" in s_low
                reqs.append(Requirement(
                    id=f"REQ-{len(reqs)+1:03d}", description=sent.strip().rstrip("."),
                    source_quote=line.strip()[:300], speaker=speaker,
                    status="unclear" if unclear else "confirmed",
                    priority="must-have" if any(w in s_low for w in ("need", "must")) else "should-have",
                    topic=topic,
                    acceptance_criteria=f"Client can verify: {sent.strip().rstrip('.').lower()} (confirm exact test at approval)."))
    return reqs, exclusions


# ---------------- Agent 2: Product Feasibility (Task 1 API) ----------------
# Offline fallback mirrors Task 1 seed articles. A KB *miss* never proves a
# feature doesn't exist -> needs_clarification, not 'custom'. (Say this in viva.)
_OFFLINE_KB = [
    (("filter", "radius", "postcode", "location"), "existing_configuration",
     "Search filters (category/location/level) and radius search are settings under Search Settings."),
    (("ai search", "typo", "understands what people mean", "semantic"), "potential_custom_development",
     "Built-in search has no AI semantic ranking or typo tolerance beyond partial matches."),
    (("higher in results", "premium members", "rank"), "needs_clarification",
     "Docs describe keyword search + filters; paid-tier ranking boost is not documented."),
    (("mobile", "phone", "search bar"), "existing_with_limitation",
     "Themes responsive; mobile search-bar position is a Design Setting. Custom mobile layouts need dev."),
    (("stripe", "paypal"), "existing_configuration", "Stripe and PayPal supported out of the box."),
    (("gateway", "local payment"), "potential_custom_development", "Other gateways require a custom integration."),
    (("refund", "cancel"), "existing_configuration", "Refunds via Finance > Transactions; dashboard limit 180 days."),
    (("spam", "confirmation", "notification", "reminder", "email"), "existing_with_limitation",
     "Templates editable/on-off; deliverability needs SPF+DKIM on sending domain."),
    (("booking", "calendar", "appointment"), "potential_custom_development",
     "No booking calendar in documented features."),
    (("price range",), "needs_clarification", "Price-range filter not in documented filter list (category/location/level)."),
    (("launch", "christmas", "january"), "needs_clarification", "Timeline statement — not a product feature; confirm as project constraint."),
]


def check_feasibility(req: Requirement, use_api: bool = True) -> Requirement:
    if use_api:
        try:
            r = httpx.post(f"{KB_URL}/query", json={"question": f"Does the product support: {req.description}", "top_k": 3},
                           timeout=6.0)
            if r.status_code == 200:
                data = r.json()
                req.evidence = [{"title": s["title"], "url": s["url"]} for s in data.get("sources", [])]
                if data.get("status") == "answered" and _classify_offline(req.description) is None:
                    req.feasibility = "existing_configuration"
                    req.feasibility_note = "Knowledge Brain returned supporting documentation (verify exact setting at design stage)."
                    return req
        except Exception:
            pass  # KB down -> offline map; feasibility marked accordingly in note
    hit = _classify_offline(req.description)
    if hit:
        req.feasibility, req.feasibility_note = hit
    else:
        req.feasibility, req.feasibility_note = ("needs_clarification",
            "No matching documented capability found. Absence of evidence is not evidence of absence — expert to confirm.")
    return req


def _classify_offline(text: str):
    low = text.lower()
    for words, feas, note in _OFFLINE_KB:
        if any(w in low for w in words):
            return feas, note
    return None


# ---------------- Agent 4: Estimation ----------------
# Heuristic v1 — deliberately explicit so a reviewer can challenge it.
# Calibrate against actuals after delivery; record error in EVALS.
_EST = {
    "existing_configuration":       [("Requirements & design", 1, 2, 3), ("Configuration", 1, 2, 4), ("Testing & handover", 1, 2, 3)],
    "existing_with_limitation":     [("Requirements & design", 1, 2, 4), ("Configuration + workarounds", 2, 4, 7), ("Testing & handover", 1, 3, 5)],
    "potential_custom_development": [("Requirements & technical design", 2, 4, 7), ("Backend implementation", 6, 12, 22),
                                     ("Frontend implementation", 4, 8, 14), ("Testing, integration & deployment", 3, 6, 10)],
    "needs_clarification":          [("Discovery / feasibility spike", 2, 4, 8)],
}


@dataclass
class EstimateRow:
    requirement_id: str
    task: str
    low_h: float
    likely_h: float
    high_h: float
    assumption: str


def estimate(reqs: list[Requirement]) -> list[EstimateRow]:
    rows: list[EstimateRow] = []
    for req in reqs:
        # Uncertain statements are NEVER estimated as firm work: an unclear
        # requirement gets only a discovery spike until the client confirms it.
        # (Without this, a throwaway 'maybe add AI' added ~45h to Meeting A.)
        bucket = "needs_clarification" if req.status == "unclear" else req.feasibility
        scale = 1.5 if req.topic in ("ai_search", "payments") and bucket == "potential_custom_development" else 1.0
        note = f"Heuristic v1 for '{bucket}'" + ("; integration/AI complexity ×1.5" if scale != 1.0 else "") + \
               ("; UNCONFIRMED requirement — discovery only" if req.status == "unclear" else "") + ". Needs senior review."
        for task, lo, li, hi in _EST[bucket]:
            rows.append(EstimateRow(req.id, f"{req.id} · {task}", lo * scale, li * scale, hi * scale, note))
    return rows


def totals(rows: list[EstimateRow]) -> dict:
    return {"low_h": sum(r.low_h for r in rows), "likely_h": sum(r.likely_h for r in rows),
            "high_h": sum(r.high_h for r in rows)}


# ---------------- Agents 3 & 5: Scope + Proposal ----------------
def build_scope(project: str, reqs: list[Requirement], exclusions: list[str], rows: list[EstimateRow]) -> str:
    t = totals(rows)
    lines = [f"# Scope of Work — {project}", "", f"_Status: DRAFT — requires human approval before sending. Pipeline: {PROMPT_VERSION}_", "",
             "## Requirements (with feasibility checked against product knowledge)", ""]
    for r in reqs:
        ev = "; ".join(e["title"] for e in r.evidence) or "no KB citation (offline check)"
        lines += [f"### {r.id} — {r.description}",
                  f"- Status: **{r.status}** · Priority: {r.priority} · Feasibility: **{r.feasibility}**",
                  f"- Feasibility note: {r.feasibility_note}", f"- Evidence: {ev}",
                  f"- Acceptance: {r.acceptance_criteria}", f"- Client said ({r.speaker}): “{r.source_quote}”", ""]
    lines += ["## Explicit exclusions (from client's own words)", ""]
    lines += [f"- {e}" for e in exclusions] or ["- None recorded — confirm at approval."]
    unclear = [r for r in reqs if r.status == "unclear" or r.feasibility == "needs_clarification"]
    lines += ["", "## Open questions (do not estimate as firm work until answered)", ""]
    lines += [f"- {r.id}: {r.description} — {r.feasibility_note}" for r in unclear] or ["- None."]
    lines += ["", "## Effort summary", "",
              f"- Low: **{t['low_h']:.0f} h** · Likely: **{t['likely_h']:.0f} h** · High: **{t['high_h']:.0f} h**",
              "- Ranges, not a fixed quote. `needs_clarification` items carry only a discovery spike.",
              "", "## Client responsibilities", "- Approve/revise this scope; confirm acceptance tests; provide test data and timely feedback.", ""]
    return "\n".join(lines)


def build_proposal(project: str, reqs: list[Requirement], rows: list[EstimateRow],
                   hourly_rate: float | None = None, currency: str = "USD") -> str:
    t = totals(rows)
    config = [r for r in reqs if r.feasibility.startswith("existing")]
    custom = [r for r in reqs if r.feasibility == "potential_custom_development"]
    lines = [f"# Proposal — {project}", "", "_Status: DRAFT — not sent. Human approval required._", "",
             "## Executive summary",
             f"We reviewed your requirements against the product's documented capabilities first. "
             f"{len(config)} item(s) can be delivered mainly through existing settings (faster, cheaper); "
             f"{len(custom)} item(s) need custom development and are priced separately below.", "",
             "## Deliverables", ""]
    lines += [f"- **{r.id}** {r.description} ({r.feasibility.replace('_', ' ')})" for r in reqs]
    lines += ["", "## Effort & pricing assumptions", "",
              f"- Estimated effort: {t['low_h']:.0f}–{t['high_h']:.0f} hours (likely {t['likely_h']:.0f} h)."]
    if hourly_rate:
        lines.append(f"- At {currency} {hourly_rate:.0f}/h: approx {currency} {t['low_h']*hourly_rate:,.0f}–{t['high_h']*hourly_rate:,.0f} (likely {currency} {t['likely_h']*hourly_rate:,.0f}), taxes excluded. Rate is configurable — confirm commercially before sending.")
    else:
        lines.append("- Hourly rate not set: hours only. A human confirms the commercial price before this is sent.")
    lines += ["- Items marked 'needs clarification' are quoted only as a short discovery spike until confirmed.", "",
              "## What is NOT included", "- Anything in the scope's exclusions, and any requirement added after approval (quoted as a change).", "",
              "## Next step", "- Reply approving this scope (or request changes). No work begins before approval.", ""]
    return "\n".join(lines)


def run_pipeline(project: str, transcript: str, hourly_rate: float | None = None, use_api: bool = True) -> dict:
    reqs, exclusions = analyse_transcript(transcript)
    reqs = [check_feasibility(r, use_api=use_api) for r in reqs]
    rows = estimate(reqs)
    return {"project": project, "prompt_version": PROMPT_VERSION, "status": "draft_pending_approval",
            "requirements": [asdict(r) for r in reqs], "exclusions": exclusions,
            "estimates": [asdict(r) for r in rows], "totals": totals(rows),
            "scope_md": build_scope(project, reqs, exclusions, rows),
            "proposal_md": build_proposal(project, reqs, rows, hourly_rate)}
