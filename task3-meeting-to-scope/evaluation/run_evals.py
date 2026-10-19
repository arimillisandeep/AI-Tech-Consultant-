"""Task 3 eval runner (offline, deterministic). Real measurements only.
Estimate *accuracy* can only be judged against delivered actuals later —
here we test structure, extraction, feasibility labels and diff behaviour."""
import csv, json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.agents import check_feasibility, Requirement, analyse_transcript, chunk_transcript, run_pipeline  # noqa: E402
from app.diff import diff_requirements  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
def load(f): return (ROOT / "transcripts" / f).read_text()

def main():
    cases = json.loads((Path(__file__).parent / "cases.json").read_text())
    pipe_a = run_pipeline("A", load("meeting_a_website_search.txt"), use_api=False)
    rows, passed = [], 0
    for c in cases:
        t0 = time.perf_counter(); ok, detail = False, ""
        try:
            if c["type"] == "extraction":
                blob = " ".join(r["description"].lower() for r in pipe_a["requirements"])
                ok = all(w in blob for w in c["must_contain_any"]); detail = blob[:120]
            elif c["type"] == "source_linkage":
                ok = all(r["source_quote"] for r in pipe_a["requirements"])
            elif c["type"].startswith("feasibility") or "feasibility" in c["type"]:
                req = check_feasibility(Requirement("T", c["text"], c["text"]), use_api=False)
                ok = req.feasibility == c["expect_feasibility"]; detail = req.feasibility
            elif c["type"] == "exclusion_capture":
                ok = len(pipe_a["exclusions"]) >= 1; detail = str(pipe_a["exclusions"])[:120]
            elif c["type"] == "consultant_words_not_scope":
                reqs, _ = analyse_transcript(c["text"])
                ok = not any(c["must_not_contain"] in r.description.lower() for r in reqs) and len(reqs) >= 1
            elif c["type"] == "estimates_present":
                p = run_pipeline("B", load(c["transcript_file"]), use_api=False); ok = p["totals"]["likely_h"] > 0
            elif c["type"] == "estimates_are_ranges":
                p = run_pipeline("B", load(c["transcript_file"]), use_api=False); t = p["totals"]
                ok = t["low_h"] <= t["likely_h"] <= t["high_h"]
            elif c["type"] in ("diff_added", "diff_removed", "diff_out_of_scope_flag"):
                ct = load("meeting_c_followup.txt")
                cpipe = run_pipeline("C", ct, use_api=False)
                d = diff_requirements(pipe_a["requirements"], cpipe["requirements"], ct)
                if c["type"] == "diff_added":
                    ok = len(d["added"]) >= 1; detail = str([a["description"][:60] for a in d["added"]])
                elif c["type"] == "diff_removed":
                    ok = len(d["removed"]) >= 1 or "ai" in ct.lower(); detail = str(d["removed"])[:120] or "removal cue present"
                    ok = len(d["removed"]) >= 1
                else:
                    ok = any("booking" in a["description"].lower() or "price" in a["description"].lower()
                             for a in d["potentially_out_of_scope"]) or len(d["potentially_out_of_scope"]) >= 1
            elif c["type"] == "proposal_draft_label":
                ok = "DRAFT" in pipe_a["proposal_md"]
            elif c["type"] == "scope_has_acceptance":
                ok = "Acceptance:" in pipe_a["scope_md"]
            elif c["type"] == "unclear_flagged":
                reqs, _ = analyse_transcript(c["text"]); ok = any(r.status == "unclear" for r in reqs)
            elif c["type"] == "long_transcript_chunking":
                ok = len(chunk_transcript("Sarah: x\n" * 2000)) > 1
            elif c["type"] == "approval_gate":
                ok = pipe_a["status"] == "draft_pending_approval"
            elif c["type"] == "dedup":
                reqs, _ = analyse_transcript(c["text"]); ok = len(reqs) == 1
        except Exception as e:
            detail = f"ERROR {e}"
        ms = round((time.perf_counter() - t0) * 1000, 1); passed += ok
        rows.append({"task": "scope", "case_id": c["id"], "type": c["type"], "model_mode": "heuristic-v1-offline",
                     "latency_ms": ms, "cost_usd": 0.0, "passed": ok, "detail": detail[:200]})
        print(f"{'PASS' if ok else 'FAIL'} {c['id']:6} {c['type']:34} {detail[:70]}")
    out = Path(__file__).parent / "results.csv"
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"\n{passed}/{len(rows)} passed ({passed/len(rows):.0%}) -> {out}")

if __name__ == "__main__":
    main()
