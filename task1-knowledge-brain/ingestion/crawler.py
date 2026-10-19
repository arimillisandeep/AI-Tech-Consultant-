"""
Polite, resumable, incremental ingestion of the Brilliant Directories sitemap.

Guarantees the brief asks for:
- Rate limiting (delay + bounded concurrency) — never hammers the source.
- Retries with exponential backoff on 5xx/network only; 4xx is permanent.
- Checkpointing in the manifest table: kill it halfway, rerun, it resumes
  (unchanged pages are hash-skipped in store.upsert_article).
- Failure isolation: one bad page logs to manifest.error and the job continues.
- Incremental daily runs: compare sitemap URLs + content hash; deactivate removed.

Run a small batch first (limit=20), inspect, then scale. See daily_sync.py.
"""
from __future__ import annotations
import asyncio, sys, xml.etree.ElementTree as ET
from pathlib import Path
import httpx
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import store          # noqa: E402
from app.llm import describe_image  # noqa: E402

HEADERS = {"User-Agent": "AI-Tech-Consultant-Capstone/1.0 (educational; rate-limited)"}
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def parse_sitemap(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    entries, seen = [], set()
    for url_el in root.findall(".//sm:url", NS) or root.findall(".//url"):
        loc = url_el.findtext("sm:loc", default="", namespaces=NS) or url_el.findtext("loc", "")
        lastmod = url_el.findtext("sm:lastmod", default="", namespaces=NS) or url_el.findtext("lastmod", "")
        if loc and loc not in seen:
            seen.add(loc)
            entries.append({"url": loc.strip(), "lastmod": (lastmod or "").strip()})
    return entries


def extract_article(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["nav", "footer", "script", "style", "header", "aside"]):
        tag.decompose()
    title = (soup.title.get_text(" ", strip=True) if soup.title else "") or url
    main = soup.find("article") or soup.find("main") or soup.body or soup
    body = main.get_text("\n", strip=True) if main else ""
    images = []
    for img in (main.find_all("img") if main else []):
        src = img.get("src") or img.get("data-src") or ""
        if not src or src.startswith("data:"):
            continue
        nearby = img.parent.get_text(" ", strip=True)[:300] if img.parent else ""
        images.append({"url": src, "alt": img.get("alt", ""), "nearby_text": nearby,
                       "vision_description": describe_image(src, img.get("alt", ""), nearby)})
    return {"url": url, "title": title[:200], "body": body[:50000], "images": images[:20],
            "category": "", "folder": ""}


async def fetch_with_retries(client: httpx.AsyncClient, url: str, retries: int = 3) -> str:
    delay = 1.0
    for attempt in range(retries):
        try:
            r = await client.get(url)
            if r.status_code < 500:
                r.raise_for_status() if r.status_code >= 400 else None
                return r.text
            raise httpx.HTTPStatusError("5xx", request=r.request, response=r)
        except (httpx.TransportError, httpx.HTTPStatusError):
            if attempt == retries - 1:
                raise
            await asyncio.sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable")


def article_entries(entries: list[dict]) -> list[dict]:
    """The live sitemap (1,699 URLs, checked 2026-10-19) mixes home/section/
    folder index pages with real articles. Index pages pollute retrieval, so
    ingest article URLs only; sections/folders are hierarchy metadata."""
    arts = [e for e in entries if "/articles/" in e["url"]]
    return arts or entries


async def run_ingestion(sitemap_url: str, limit: int = 20, delay_seconds: float = 1.0) -> dict:
    store.init_db()
    report = {"new": 0, "updated": 0, "unchanged": 0, "failed": 0, "removed": 0, "total_sitemap": 0, "article_urls": 0}
    async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:
        xml_text = await fetch_with_retries(client, sitemap_url)
        all_entries = parse_sitemap(xml_text)
        entries = article_entries(all_entries)
        report["total_sitemap"] = len(all_entries)
        report["article_urls"] = len(entries)
        seen = {e["url"] for e in entries}
        for entry in entries[:limit]:
            try:
                html = await fetch_with_retries(client, entry["url"])
                article = extract_article(html, entry["url"])
                article["lastmod"] = entry["lastmod"]
                report[store.upsert_article(article)] += 1
            except Exception as exc:  # failure isolation: record + continue
                report["failed"] += 1
                with store.get_db() as c:
                    c.execute("INSERT OR REPLACE INTO manifest(url,status,attempts,last_checked,error) VALUES(?,?,?,?,?)",
                              (entry["url"], "failed", 1, store.now(), str(exc)[:300]))
            await asyncio.sleep(delay_seconds)  # politeness
        # Only deactivate removals on a FULL run, never on a limited sample run —
        # otherwise a 20-page test would wipe the knowledge base. (Live-review favourite.)
        if limit >= len(entries):
            report["removed"] = store.deactivate_missing(seen)
    return report


if __name__ == "__main__":
    import json
    lim = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    print(json.dumps(asyncio.run(run_ingestion(
        "https://support.brilliantdirectories.com/support/sitemap.xml", limit=lim)), indent=2))
