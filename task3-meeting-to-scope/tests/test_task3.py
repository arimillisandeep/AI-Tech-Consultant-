import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fastapi.testclient import TestClient
from app.main import app

SAMPLE = "Sarah: We need search filters by category and location.\nSarah: We also want radius search by postcode."

def test_process_creates_draft_not_sendable():
    with TestClient(app) as c:
        r = c.post("/process", json={"project": "T", "transcript": SAMPLE}).json()
        assert r["status"] == "draft_pending_approval" and r["sendable"] is False and r["requirements"]

def test_cannot_send_unapproved():
    with TestClient(app) as c:
        pid = c.post("/process", json={"project": "T2", "transcript": SAMPLE}).json()["id"]
        assert c.post(f"/projects/{pid}/mark-sent").status_code == 409
        assert c.post(f"/projects/{pid}/approve", json={"reviewer": "qa"}).status_code == 200
        assert c.post(f"/projects/{pid}/mark-sent").status_code == 200

def test_diff_requires_approved_baseline():
    with TestClient(app) as c:
        pid = c.post("/process", json={"project": "T3", "transcript": SAMPLE}).json()["id"]
        r = c.post("/process", json={"project": "T3 follow", "transcript": SAMPLE, "baseline_project_id": pid})
        assert r.status_code == 409  # baseline is still a draft
