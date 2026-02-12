#!/usr/bin/env python3
"""
Async pipeline:
- Fetch list from SpaceFlightNews API
- If item exists in existing JSON with same id & updated_at, reuse detailed_news
- Otherwise fetch article HTML -> extract text
- Split text into chunks -> concurrently call HF summarize endpoint for each chunk
- Combine chunk summaries -> optional final short summary
- Attach as item['detailed_news']
- Save to public/space_news.json
"""

import os
import asyncio
import aiohttp
import json
from bs4 import BeautifulSoup
from tqdm.asyncio import tqdm_asyncio
from typing import List
import time

from config import HF_TOKEN, request_timeout
from hf_client import call_hf_api

SPACE_API = "https://api.spaceflightnewsapi.net/v4/articles/?limit=48&offset=0&ordering=-published_at"
OUTFILE = "public/space_news.json"
MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONC", "6"))
REQUEST_TIMEOUT = request_timeout(total=60)
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "2000"))
TARGET_SUMMARY_WORDS = int(os.getenv("TARGET_WORDS", "1000"))

if not HF_TOKEN:
    raise SystemExit("HF_TOKEN environment variable not set")

# --- Helpers ---
async def fetch_json(session: aiohttp.ClientSession, url: str):
    async with session.get(url, timeout=REQUEST_TIMEOUT) as resp:
        resp.raise_for_status()
        return await resp.json()

async def fetch_text(session: aiohttp.ClientSession, url: str) -> str:
    try:
        async with session.get(url, timeout=REQUEST_TIMEOUT) as resp:
            html = await resp.text()
    except Exception as e:
        print(f"Failed fetch {url}: {e}")
        return ""
    soup = BeautifulSoup(html, "html.parser")
    paragraphs = [p.get_text(separator=" ", strip=True) for p in soup.find_all("p")]
    text = " ".join(paragraphs)
    if not text:
        desc = soup.find("meta", {"name": "description"})
        if desc and desc.get("content"):
            text = desc["content"]

    print(f"Fetched {len(text)} chars from {url}")
    return text

def chunk_text(text: str, chunk_size_chars: int) -> List[str]:
    text = text.strip()
    if len(text) <= chunk_size_chars:
        return [text]
    chunks = []
    start = 0
    L = len(text)
    while start < L:
        end = min(start + chunk_size_chars, L)
        if end < L:
            slice_ = text[start:end]
            last_period = slice_.rfind('. ')
            if last_period != -1 and last_period > int(chunk_size_chars * 0.5):
                end = start + last_period + 1
        chunks.append(text[start:end].strip())
        start = end
    return chunks

async def hf_summarize_chunk(session: aiohttp.ClientSession, text: str, semaphore: asyncio.Semaphore, retries=3):
    print(f"Summarizing chunk of {len(text)} chars")
    async with semaphore:
        return await call_hf_api(session, text, max_new_tokens=512, retries=retries)

async def process_item(session: aiohttp.ClientSession, item: dict, semaphore: asyncio.Semaphore):
    url = item.get("url")
    if not url:
        item["detailed_news"] = item.get("summary", "")
        return item
    text = await fetch_text(session, url)
    if not text:
        item["detailed_news"] = item.get("summary", "")
        return item

    chunks = chunk_text(text, CHUNK_SIZE)
    tasks = [hf_summarize_chunk(session, chunk, semaphore) for chunk in chunks]
    chunk_summaries = await asyncio.gather(*tasks)

    combined = " ".join([s for s in chunk_summaries if s])
    final_summary = combined
    if len(combined) > CHUNK_SIZE:
        condensed = await hf_summarize_chunk(session, combined, semaphore)
        if condensed:
            final_summary = condensed

    words = final_summary.split()
    if len(words) < TARGET_SUMMARY_WORDS * 0.5:
        final_summary = combined if combined else final_summary

    item["detailed_news"] = final_summary
    return item

async def main():
    connector = aiohttp.TCPConnector(limit_per_host=MAX_CONCURRENT_REQUESTS)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    # Load existing items
    existing_items = {}
    if os.path.exists(OUTFILE):
        try:
            with open(OUTFILE, "r", encoding="utf-8") as f:
                old_data = json.load(f)
                existing_items = {item["id"]: item for item in old_data}
            print(f"Loaded {len(existing_items)} existing items from {OUTFILE}")
        except Exception as e:
            print(f"⚠️ Could not read {OUTFILE}: {e}")

    async with aiohttp.ClientSession(connector=connector) as session:
        print("Fetching list from SpaceFlightNews API...")
        data = await fetch_json(session, SPACE_API)
        items = data.get("results", [])
        print(f"Found {len(items)} items. Checking for updates...")

        # Separate existing items from items that need processing
        to_process = []
        processed = []

        for item in items:
            old_item = existing_items.get(item["id"])
            if old_item and old_item.get("id") == item.get("id"):
                # Reuse existing processed item
                processed.append(old_item)
            else:
                # Needs processing
                to_process.append(process_item(session, item, semaphore))

        # Process new items with progress bar
        if to_process:
            for completed_task in tqdm_asyncio.as_completed(to_process, desc="Processing articles"):
                processed_item = await completed_task
                processed.append(processed_item)

        processed_sorted = sorted(processed, key=lambda x: x.get("published_at", ""), reverse=True)

        os.makedirs(os.path.dirname(OUTFILE), exist_ok=True)
        with open(OUTFILE, "w", encoding="utf-8") as f:
            json.dump(processed_sorted, f, ensure_ascii=False, indent=2)
        print(f"✅ Wrote {len(processed_sorted)} items to {OUTFILE}")

if __name__ == "__main__":
    start = time.time()
    asyncio.run(main())
    print("Elapsed:", time.time() - start)
