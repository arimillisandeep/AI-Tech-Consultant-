"""Offline CLI demo — no servers needed.
Usage:
  python run_cli.py transcripts/meeting_a_website_search.txt "Meridian Sports"
  python run_cli.py --demo     # A -> approve -> C follow-up diff, writes examples/
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.agents import run_pipeline
from app.diff import diff_requirements

ROOT = Path(__file__).resolve().parent

def write_outputs(result: dict, name: str) -> None:
    out = ROOT / "examples"; out.mkdir(parents=True, exist_ok=True)
    (out / f"{name}_scope.md").write_text(result["scope_md"])
    (out / f"{name}_proposal.md").write_text(result["proposal_md"])
    (out / f"{name}_full.json").write_text(json.dumps(result, indent=2))
    t = result["totals"]
    print(f"{name}: {len(result['requirements'])} requirements · likely {t['likely_h']:.0f}h "
          f"(range {t['low_h']:.0f}–{t['high_h']:.0f}h) -> examples/{name}_scope.md")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        a = run_pipeline("Meridian Sports — Search & Mobile (Meeting A)",
                         (ROOT / "transcripts/meeting_a_website_search.txt").read_text(), use_api=False)
        write_outputs(a, "meeting_a")
        b = run_pipeline("BloomBox — E-commerce (Meeting B)",
                         (ROOT / "transcripts/meeting_b_ecommerce.txt").read_text(), use_api=False)
        write_outputs(b, "meeting_b")
        c_text = (ROOT / "transcripts/meeting_c_followup.txt").read_text()
        c = run_pipeline("Meridian Sports — Follow-up (Meeting C)", c_text, use_api=False)
        c["diff"] = diff_requirements(a["requirements"], c["requirements"], c_text)
        write_outputs(c, "meeting_c_followup")
        print("\nDIFF (C vs approved A baseline):", c["diff"]["summary"])
        for k in ("added", "removed", "modified"):
            print(f" {k}:", [x["description"][:80] for x in c["diff"][k]])
    else:
        path = Path(sys.argv[1]); name = sys.argv[2] if len(sys.argv) > 2 else "Client Project"
        write_outputs(run_pipeline(name, path.read_text()), path.stem)
