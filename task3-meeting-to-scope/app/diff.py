"""
Scope diff: follow-up meeting vs APPROVED baseline (never vs an unapproved
AI draft — otherwise AI suggestions silently become commitments).

Matching rules (in order):
1. Explicit client signals win: "one more / new idea / additionally" => added;
   "drop / no longer / remove X" => the baseline item matching X is removed
   (matched on the removed phrase's terms, not broad topics — dropping
   'AI search' must not delete radius search).
2. Otherwise same-topic text similarity (difflib). Different-topic matches
   need a much higher bar, so a booking request can't 'match' an old
   sentence just because both mention members.
3. Unmatched follow-up items are 'added' AND 'potentially_out_of_scope':
   quoted separately, never absorbed silently.
4. Unmatched baseline items with no removal signal are
   'not_mentioned_confirm': assume still in scope, confirm with client.
"""
from __future__ import annotations
import difflib, re

_ADD_CUES = ("one more", "new idea", "additionally", "on top of", "also add")
_REMOVAL_CUES = ("drop", "no longer", "remove", "cancel the", "not needed", "scrap")
_STOP = {"drop", "remove", "cancel", "scrap", "the", "idea", "for", "now", "no", "longer",
         "needed", "not", "second", "first", "phase", "one", "in", "a", "an"}


def _sim(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _removed_terms(followup_text: str) -> set[str]:
    """Terms of the thing being dropped: the few content words right after a
    removal verb ('drop the AI search idea' -> {ai, search}). Whole-sentence
    matching wrongly removed radius search via common words like 'we'."""
    terms: set[str] = set()
    for sent in re.split(r"(?<=[.!?])\s+", followup_text.replace("\n", " ")):
        words = re.findall(r"[a-z]{2,}", sent.lower())
        for verb in ("drop", "remove", "cancel", "scrap"):
            if verb in words:
                after = words[words.index(verb) + 1:]
                terms |= {w for w in after if w not in _STOP}
                terms = set(list(terms)[:8])
                break
    return terms


def diff_requirements(baseline: list[dict], followup: list[dict], followup_text: str = "") -> dict:
    removed_terms = _removed_terms(followup_text)
    matched_base: set[str] = set()
    added, modified, unchanged = [], [], []
    for new in followup:
        if any(c in new["description"].lower() for c in _ADD_CUES):
            added.append({"description": new["description"], "topic": new.get("topic", "general"),
                          "signal": "client explicitly signalled an addition",
                          "action": "needs estimate + acceptance criteria; quote separately if out of scope"})
            continue
        best, best_score = None, 0.0
        for base in baseline:
            if base["id"] in matched_base:
                continue
            score = _sim(new["description"], base["description"])
            same_topic = new.get("topic") == base.get("topic")
            if same_topic:
                score += 0.08
            elif score < 0.65:  # cross-topic matches need near-identical wording
                continue
            if score > best_score:
                best, best_score = base, score
        if best and best_score >= 0.42:
            matched_base.add(best["id"])
            (unchanged if best_score >= 0.82 else modified).append(
                {"baseline_id": best["id"], "description": new["description"],
                 "was": best["description"], "match": round(best_score, 2),
                 "action": "keep" if best_score >= 0.82 else "re-estimate affected tasks"})
        else:
            added.append({"description": new["description"], "topic": new.get("topic", "general"),
                          "signal": "no matching baseline requirement",
                          "action": "needs estimate + acceptance criteria; quote separately if out of scope"})
    removed, not_mentioned = [], []
    for b in baseline:
        if b["id"] in matched_base:
            continue
        overlap = {w for w in re.findall(r"[a-z]{2,}", b["description"].lower()) if w in removed_terms}
        # 'AI search' -> {ai, search}: both terms hits the right item only.
        if len(overlap) >= 2:
            removed.append({"baseline_id": b["id"], "description": b["description"],
                            "matched_removed_terms": sorted(overlap),
                            "action": "remove from scope; deduct estimate"})
        else:
            not_mentioned.append({"baseline_id": b["id"], "description": b["description"],
                                  "action": "not mentioned in follow-up — assume still in scope, confirm with client"})
    return {"added": added, "modified": modified, "removed": removed,
            "not_mentioned_confirm": not_mentioned, "unchanged": unchanged,
            "potentially_out_of_scope": added,  # by definition vs approved baseline
            "summary": f"{len(added)} added, {len(modified)} modified, {len(removed)} removed, "
                       f"{len(unchanged)} unchanged, {len(not_mentioned)} to confirm."}
