"""
Storage + retrieval for the Knowledge Brain.

Design choices (see DESIGN.md):
- SQLite (stdlib) for articles/chunks/manifest/escalations: zero-ops for a 4-day build,
  one file to back up, trivially swappable for Postgres+pgvector later.
- Hybrid retrieval: TF-IDF cosine (semantic-ish overlap) + keyword boost.
  The EmbeddingProvider interface below is where a real embedding model
  (e.g. Voyage, which Anthropic recommends alongside Claude) plugs in without
  touching callers. TF-IDF is the honest offline fallback, not a claim of SOTA.
- Idempotency: chunks are keyed by (article_url_hash, chunk_index, content_hash);
  re-ingesting an unchanged article replaces nothing and creates no duplicates.
- Removed pages are marked inactive and excluded from retrieval.
"""
from __future__ import annotations
import hashlib, json, re, sqlite3, threading, uuid
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "knowledge.db"
_lock = threading.Lock()


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()[:32]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS articles(
          url TEXT PRIMARY KEY, title TEXT, category TEXT, folder TEXT,
          content_hash TEXT, active INTEGER DEFAULT 1, lastmod TEXT, ingested_at TEXT);
        CREATE TABLE IF NOT EXISTS chunks(
          chunk_id TEXT PRIMARY KEY, url TEXT, title TEXT, section TEXT,
          text TEXT, image_refs TEXT DEFAULT '[]', active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS manifest(
          url TEXT PRIMARY KEY, status TEXT, attempts INTEGER DEFAULT 0,
          content_hash TEXT, last_checked TEXT, error TEXT);
        CREATE TABLE IF NOT EXISTS escalations(
          id TEXT PRIMARY KEY, question TEXT, reason TEXT, context TEXT,
          status TEXT DEFAULT 'open', expert_answer TEXT, reviewer TEXT,
          created_at TEXT, resolved_at TEXT);
        """)


def chunk_article(title: str, body: str, images: list[dict]) -> list[dict]:
    """Heading-aware chunking: split at '## ' first, keep procedures intact,
    fall back to paragraph windows. Image descriptions become their own
    searchable text attached to the chunk containing their nearby text."""
    sections: list[tuple[str, str]] = []
    parts = re.split(r"^##\s+", body, flags=re.M)
    if len(parts) == 1:
        sections = [("Overview", body.strip())]
    else:
        for p in parts:
            if not p.strip():
                continue
            lines = p.strip().split("\n", 1)
            heading = lines[0].strip()[:120]
            rest = lines[1].strip() if len(lines) > 1 else ""
            sections.append((heading, rest or heading))
    chunks = []
    for i, (section, text) in enumerate(sections):
        img_refs, img_text = [], ""
        for img in images or []:
            nearby = (img.get("nearby_text") or "")[:40]
            if nearby and nearby.split(".")[0][:25].lower() in text.lower():
                img_refs.append(img.get("url", ""))
                img_text += f"\n[Image: {img.get('vision_description') or img.get('alt','')}]"
        full = f"{title} — {section}. {text}{img_text}".strip()
        chunks.append({"section": section, "text": full, "image_refs": img_refs, "index": i})
    # images not matched to any section still become searchable
    matched = {r for ch in chunks for r in ch["image_refs"]}
    for img in images or []:
        if img.get("url") not in matched and (img.get("vision_description") or img.get("alt")):
            chunks.append({"section": "Screenshot", "index": len(chunks),
                           "text": f"{title} — Screenshot. {img.get('vision_description') or img.get('alt','')}",
                           "image_refs": [img.get("url", "")]})
    return chunks


def upsert_article(article: dict) -> str:
    """Returns 'new' | 'updated' | 'unchanged'."""
    url, body = article["url"], article.get("body", "")
    chash = sha(body + json.dumps(article.get("images", []), sort_keys=True))
    with _lock, get_db() as c:
        row = c.execute("SELECT content_hash FROM articles WHERE url=?", (url,)).fetchone()
        if row and row["content_hash"] == chash:
            c.execute("UPDATE manifest SET status='unchanged',last_checked=? WHERE url=?", (now(), url))
            return "unchanged"
        status = "updated" if row else "new"
        c.execute("""INSERT INTO articles(url,title,category,folder,content_hash,active,lastmod,ingested_at)
                     VALUES(?,?,?,?,?,1,?,?) ON CONFLICT(url) DO UPDATE SET
                     title=excluded.title,category=excluded.category,folder=excluded.folder,
                     content_hash=excluded.content_hash,active=1,ingested_at=excluded.ingested_at""",
                  (url, article.get("title", ""), article.get("category", ""), article.get("folder", ""),
                   chash, article.get("lastmod", ""), now()))
        c.execute("DELETE FROM chunks WHERE url=?", (url,))
        for ch in chunk_article(article.get("title", ""), body, article.get("images", [])):
            cid = sha(url) + f"-{ch['index']}-" + sha(ch["text"])[:10]
            c.execute("INSERT OR REPLACE INTO chunks VALUES(?,?,?,?,?,?,1)",
                      (cid, url, article.get("title", ""), ch["section"], ch["text"],
                       json.dumps(ch["image_refs"])))
        c.execute("""INSERT INTO manifest(url,status,attempts,content_hash,last_checked) VALUES(?,?,1,?,?)
                     ON CONFLICT(url) DO UPDATE SET status=excluded.status,content_hash=excluded.content_hash,
                     last_checked=excluded.last_checked, attempts=manifest.attempts+1""",
                  (url, status, chash, now()))
    return status


def deactivate_missing(seen_urls: set[str]) -> int:
    with _lock, get_db() as c:
        rows = c.execute("SELECT url FROM articles WHERE active=1").fetchall()
        gone = [r["url"] for r in rows if r["url"] not in seen_urls]
        for u in gone:
            c.execute("UPDATE articles SET active=0 WHERE url=?", (u,))
            c.execute("UPDATE chunks SET active=0 WHERE url=?", (u,))
            c.execute("INSERT OR REPLACE INTO manifest(url,status,last_checked) VALUES(?,?,?)",
                      (u, "removed", now()))
    return len(gone)


def search(question: str, top_k: int = 4) -> list[dict]:
    """Hybrid: TF-IDF cosine + exact-keyword boost. Returns [] on empty KB."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    with get_db() as c:
        rows = [dict(r) for r in c.execute("SELECT * FROM chunks WHERE active=1").fetchall()]
    if not rows:
        return []
    corpus = [r["text"] for r in rows]
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2)).fit(corpus + [question])
    sims = cosine_similarity(vec.transform([question]), vec.transform(corpus))[0]
    qwords = {w for w in re.findall(r"[a-z]{3,}", question.lower())}
    scored = []
    for r, s in zip(rows, sims):
        hits = sum(1 for w in qwords if w in r["text"].lower())
        boost = min(0.15, 0.03 * hits)
        scored.append({**r, "image_refs": json.loads(r["image_refs"] or "[]"),
                       "score": float(s) + boost})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def create_escalation(question: str, reason: str = "insufficient_evidence", context: str = "") -> str:
    eid = "esc-" + uuid.uuid4().hex[:10]
    with _lock, get_db() as c:
        c.execute("INSERT INTO escalations(id,question,reason,context,created_at) VALUES(?,?,?,?,?)",
                  (eid, question, reason, context, now()))
    return eid


def resolve_escalation(eid: str, answer: str, reviewer: str) -> bool:
    """Expert answer becomes a versioned, clearly-labelled knowledge article
    so future queries can cite it — but its URL marks it as expert-contributed,
    never as official product documentation."""
    with _lock, get_db() as c:
        row = c.execute("SELECT * FROM escalations WHERE id=?", (eid,)).fetchone()
        if not row:
            return False
        c.execute("UPDATE escalations SET status='resolved',expert_answer=?,reviewer=?,resolved_at=? WHERE id=?",
                  (answer, reviewer, now(), eid))
    upsert_article({"url": f"expert-answer://{eid}", "title": f"Expert answer: {row['question'][:80]}",
                    "category": "Expert Answers", "folder": "Escalations",
                    "body": f"## Question\n{row['question']}\n## Expert answer (reviewed by {reviewer})\n{answer}",
                    "images": []})
    return True


def stats() -> dict:
    with get_db() as c:
        one = lambda q: c.execute(q).fetchone()[0]  # noqa: E731
        return {"active_articles": one("SELECT COUNT(*) FROM articles WHERE active=1"),
                "inactive_articles": one("SELECT COUNT(*) FROM articles WHERE active=0"),
                "active_chunks": one("SELECT COUNT(*) FROM chunks WHERE active=1"),
                "open_escalations": one("SELECT COUNT(*) FROM escalations WHERE status='open'"),
                "manifest_rows": one("SELECT COUNT(*) FROM manifest")}


def seed_if_empty() -> int:
    init_db()
    if stats()["active_articles"] > 0:
        return 0
    from .seed_data import SEED_ARTICLES
    for a in SEED_ARTICLES:
        upsert_article(a)
    return len(SEED_ARTICLES)
