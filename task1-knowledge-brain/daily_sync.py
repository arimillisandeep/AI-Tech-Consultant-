"""Daily freshness job. Schedule with cron:  15 2 * * *  python daily_sync.py
Full-sitemap run => additions/updates re-indexed, removals deactivated.
Prints a one-line report so cron mail/logs show what changed."""
import asyncio, json
from ingestion.crawler import run_ingestion

if __name__ == "__main__":
    print(json.dumps(asyncio.run(run_ingestion(
        "https://support.brilliantdirectories.com/support/sitemap.xml",
        limit=100000, delay_seconds=1.0))))
