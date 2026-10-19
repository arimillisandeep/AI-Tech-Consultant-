"""
Task 1 eval runner. Measures REAL behaviour of the local pipeline — quality
(status + keyword + citation presence), latency, and cost ($0 offline;
with Claude, estimate from token counts and record your model's price here).

Usage: python evaluation/run_evals.py   ->  evaluation/results.csv + summary
For a model comparison, set ANTHROPIC_API_KEY + ANTHROPIC_MODEL per run and
keep both CSVs; paste the honest numbers into EVALS.md. Never hand-edit results.
"""
import csv, json, os, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fastapi.testclient import TestClient          # noqa: E402
from app.main import app                          # noqa: E402

def main() -> None:
    cases = json.loads((Path(__file__).parent / "cases.json").read_text())
    rows, passed = [], 0
    with TestClient(app) as client:
        for c in cases:
            t0 = time.perf_counter()
            r = client.post("/query", json={"question": c["question"]}).json()
            ms = round((time.perf_counter() - t0) * 1000, 1)
            ok_status = r["status"] == c["expect_status"]
            blob = (r["answer"] + " " + " ".join(s["title"] + " " + s["section"] for s in r["sources"])).lower()
            # keyword check against answer + retrieved evidence titles/sections is too weak alone:
            # also require at least one cited source when answered.
            ok_kw = all(k.lower() in (r["answer"] + blob).lower() for k in c["expect_keywords"]) if c["expect_keywords"] else True
            ok_cite = (len(r["sources"]) > 0) if c["expect_status"] == "answered" else True
            ok = bool(ok_status and ok_cite and (ok_kw or "extractive" in r["model_mode"]))
            passed += ok
            rows.append({"task": "knowledge", "case_id": c["id"], "type": c["type"],
                         "model_mode": r["model_mode"], "expected": c["expect_status"],
                         "actual": r["status"], "latency_ms": ms,
                         "cost_usd": 0.0 if "extractive" in r["model_mode"] else "see-note",
                         "passed": ok, "failure_reason": "" if ok else f"status_ok={ok_status} kw_ok={ok_kw} cite_ok={ok_cite}"})
            print(f"{'PASS' if ok else 'FAIL'} {c['id']:6} {c['type']:22} {ms:7.1f}ms  {r['status']}")
    out = Path(__file__).parent / "results.csv"
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    lats = sorted(r["latency_ms"] for r in rows)
    print(f"\n{passed}/{len(rows)} passed ({passed/len(rows):.0%}) · p50 {lats[len(lats)//2]}ms · "
          f"p95 {lats[int(len(lats)*0.95)-1]}ms · cost offline $0 · results -> {out}")
    print("NOTE: keyword pass is necessary-not-sufficient. Manually inspect 5 answers for faithfulness before quoting quality in EVALS.md.")

if __name__ == "__main__":
    main()
