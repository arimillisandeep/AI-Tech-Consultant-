import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fastapi.testclient import TestClient
from app.main import app
from ingestion.crawler import parse_sitemap, extract_article

def test_sitemap_parse_dedupes():
    xml = """<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url><loc>https://x/a</loc><lastmod>2026-01-01</lastmod></url>
    <url><loc>https://x/a</loc></url></urlset>"""
    assert len(parse_sitemap(xml)) == 1

def test_extract_strips_nav_keeps_images():
    html = "<html><head><title>T</title></head><body><nav>NAVJUNK</nav><article><p>Hello body</p><img src='https://x/i.png' alt='A pic'></article></body></html>"
    a = extract_article(html, "https://x/a")
    assert "Hello body" in a["body"] and "NAVJUNK" not in a["body"] and len(a["images"]) == 1

def test_query_answers_with_citation():
    with TestClient(app) as c:
        r = c.post("/query", json={"question": "How do I refund a member payment?"}).json()
        assert r["status"] == "answered" and r["sources"] and r["sources"][0]["url"]

def test_query_abstains_and_escalates():
    with TestClient(app) as c:
        r = c.post("/query", json={"question": "How do I book a flight to Tokyo?"}).json()
        assert r["status"] == "insufficient_evidence" and r["needs_human"] and r["escalation_id"]

def test_escalation_resolution_becomes_searchable(tmp_path, monkeypatch):
    # Isolated DB + unique term: expert answers persist by design, and short
    # expert chunks otherwise match new nonsense queries on generic words
    # ('secret', 'setting') — the test must not depend on run history.
    import uuid
    from app import store
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "test-kb.db")
    store.seed_if_empty()
    term = f"zebrafish{uuid.uuid4().hex[:6]}"
    with TestClient(app) as c:
        r = c.post("/query", json={"question": f"What is the secret {term} setting?"}).json()
        eid = r["escalation_id"]
        assert eid, f"expected escalation, got {r['status']}"
        assert c.post(f"/escalations/{eid}/resolve", json={"expert_answer": f"The {term} setting lives under Settings > Advanced > {term}.", "reviewer": "test"}).status_code == 200
        r2 = c.post("/query", json={"question": f"{term} setting advanced"}).json()
        assert r2["status"] == "answered"

def test_validation_rejects_short_question():
    with TestClient(app) as c:
        assert c.post("/query", json={"question": "hi"}).status_code == 422

def test_ingestion_idempotent_update_and_removal(tmp_path, monkeypatch):
    """Audit-added: re-ingesting must not duplicate chunks, a changed article
    must replace its chunks, and a removed article must stop answering."""
    from app import store
    from app.seed_data import SEED_ARTICLES
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "ingest.db")
    store.init_db()
    a = dict(SEED_ARTICLES[0])
    assert store.upsert_article(a) == "new"
    n = store.stats()["active_chunks"]
    assert store.upsert_article(a) == "unchanged" and store.stats()["active_chunks"] == n
    a2 = dict(a); a2["body"] = a["body"] + "\n## New\nManager approval marker ZEBRAMARKER."
    assert store.upsert_article(a2) == "updated"
    assert any("ZEBRAMARKER" in h["text"] for h in store.search("manager approval ZEBRAMARKER", 3))
    assert store.deactivate_missing(set()) == 1
    assert store.search("How do I refund a member payment?", 3) == []
